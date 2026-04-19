import geopandas as gpd
import pandas as pd
from pathlib import Path

# Inputs
inc_path = "data/processed/incidents_tx_hdbscan.geojson"
buffers_dir = Path("data/processed/buffers")

# Buffer set to test
BUFFER_SIZES_M = [1000, 2000, 5000]

# Load incidents (clustered only)
inc = gpd.read_file(inc_path)

# Ensure UTM meters
inc = inc.to_crs(epsg=32614)

# Remove noise
inc = inc[inc["cluster_hdbscan"] != -1].copy()

rows = []

for b in BUFFER_SIZES_M:
    buf_path = buffers_dir / f"pipelines_tx_buffer_{b}m.geojson"
    buffers = gpd.read_file(buf_path).to_crs(epsg=32614)

    # Spatial join
    joined = gpd.sjoin(inc, buffers, predicate="within")

    # Count incidents per buffer feature
    counts = joined.groupby("index_right").size()

    buffers["incident_count"] = counts
    buffers["incident_count"] = buffers["incident_count"].fillna(0)

    # Corridor length (km) based on buffer boundary length is NOT meaningful,
    # so we compute length from the ORIGINAL pipeline line geometry by reloading and matching index.
    # Here we approximate using buffer perimeter length would be wrong, so instead:
    # use buffers' index as proxy and recompute from the original pipeline lines.
    # Best practical: reload pipelines and match by index.

    pipes = gpd.read_file("data/processed/pipelines_tx.geojson").to_crs(epsg=32614)
    pipes["length_km"] = pipes.geometry.length / 1000

    # Align lengths by index
    buffers["length_km"] = pipes["length_km"]

    # Density
    buffers["incident_density"] = buffers.apply(
        lambda r: (r["incident_count"] / r["length_km"]) if r["length_km"] > 0 else 0,
        axis=1
    )

    # Top 10 by density
    top = (
        buffers.sort_values("incident_density", ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={"index": "corridor_id"})
    )

    top["buffer_m"] = b
    rows.append(top[["buffer_m", "corridor_id", "incident_count", "length_km", "incident_density"]])

result = pd.concat(rows, ignore_index=True)

# Save
out_csv = "data/processed/exposure_sensitivity_top10.csv"
result.to_csv(out_csv, index=False)

print("Saved:", out_csv)

# Quick stability view: which corridor_ids repeat across buffers?
pivot = result.pivot_table(index="corridor_id", columns="buffer_m", values="incident_density", aggfunc="max")
pivot["appearances"] = pivot.notna().sum(axis=1)
pivot_sorted = pivot.sort_values(["appearances"], ascending=False)

print("\nMost stable corridor IDs across buffers (appearances):")
print(pivot_sorted.head(15))
