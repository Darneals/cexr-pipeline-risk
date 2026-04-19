import geopandas as gpd
import pandas as pd

# -----------------------------
# Load Data
# -----------------------------
buffers = gpd.read_file("data/processed/pipelines_tx_buffer_2km.geojson")
inc = gpd.read_file("data/processed/incidents_tx_hdbscan.geojson")

# -----------------------------
# Ensure Same CRS (UTM meters)
# -----------------------------
if buffers.crs != inc.crs:
    inc = inc.to_crs(buffers.crs)

# -----------------------------
# Remove Noise (HDBSCAN)
# -----------------------------
inc = inc[inc["cluster_hdbscan"] != -1]

# -----------------------------
# Spatial Join
# -----------------------------
joined = gpd.sjoin(inc, buffers, predicate="within")

# -----------------------------
# Count Incidents Per Corridor
# -----------------------------
counts = joined.groupby("index_right").size()

buffers["incident_count"] = counts
buffers["incident_count"] = buffers["incident_count"].fillna(0)

# -----------------------------
# Compute Corridor Length (km)
# -----------------------------
if buffers.crs.to_epsg() != 32614:
    buffers = buffers.to_crs(32614)

buffers["length_km"] = buffers.geometry.length / 1000

# Avoid divide by zero
buffers["incident_density"] = buffers.apply(
    lambda row: row["incident_count"] / row["length_km"]
    if row["length_km"] > 0 else 0,
    axis=1
)

# -----------------------------
# Rank
# -----------------------------
buffers["rank"] = buffers["incident_density"].rank(ascending=False)

# -----------------------------
# Save
# -----------------------------
out_path = "data/processed/pipeline_exposure.geojson"
buffers.to_file(out_path, driver="GeoJSON")

# -----------------------------
# Print Summary
# -----------------------------
print("Saved:", out_path)
print("\nTop exposed corridors (by density):")
print(
    buffers
    .sort_values("incident_density", ascending=False)
    [["incident_count", "length_km", "incident_density"]]
    .head()
)
