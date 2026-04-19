import geopandas as gpd
import numpy as np
import pandas as pd

IN_PATH = "data/processed/pipelines_tx_segment_risk_fixed.geojson"

OUT_GEOJSON = "data/processed/pipelines_tx_segment_risk_fixed_minlen.geojson"
OUT_TOPCSV  = "data/processed/top20_segments_by_risk_fixed_minlen.csv"

# Set a minimum length for stable density (km)
MIN_LEN_KM = 1.0

gdf = gpd.read_file(IN_PATH)

# Expect these columns to exist from your earlier steps
# incident_count, length_km (or length_m), segment_id
if "length_km" not in gdf.columns:
    if "length_m" in gdf.columns:
        gdf["length_km"] = gdf["length_m"] / 1000.0
    else:
        raise SystemExit(f"length_km not found. Columns: {list(gdf.columns)}")

if "incident_count" not in gdf.columns:
    raise SystemExit(f"incident_count not found. Columns: {list(gdf.columns)}")

# Clamp length to avoid tiny-segment density blowups
gdf["length_km_clamped"] = gdf["length_km"].clip(lower=MIN_LEN_KM)

# Density with clamp
gdf["incident_density_clamped"] = gdf["incident_count"] / gdf["length_km_clamped"]

# Normalize for risk score
d = gdf["incident_density_clamped"].astype(float)
d_norm = (d - d.min()) / (d.max() - d.min() + 1e-12)
gdf["risk_score_minlen"] = d_norm

# Risk band by quantiles (stable for papers)
q = gdf["risk_score_minlen"].quantile([0.2, 0.4, 0.6, 0.8]).to_list()

def band(x):
    if x >= q[3]: return "Very High"
    if x >= q[2]: return "High"
    if x >= q[1]: return "Medium"
    if x >= q[0]: return "Low"
    return "Very Low"

gdf["risk_band_minlen"] = gdf["risk_score_minlen"].apply(band)

gdf.to_file(OUT_GEOJSON, driver="GeoJSON")

top = gdf.sort_values("incident_density_clamped", ascending=False).head(20)[
    ["segment_id", "incident_count", "length_km", "length_km_clamped", "incident_density_clamped", "risk_score_minlen", "risk_band_minlen"]
]
top.to_csv(OUT_TOPCSV, index=False)

print("Saved:", OUT_GEOJSON)
print("Saved:", OUT_TOPCSV)
print("\nTop 10 by incident_density_clamped:")
print(top.head(10).to_string(index=False))
