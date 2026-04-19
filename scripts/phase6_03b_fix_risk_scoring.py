import geopandas as gpd
import pandas as pd
import numpy as np

IN_PATH = "data/processed/pipelines_tx_segment_risk.geojson"
OUT_PATH = "data/processed/pipelines_tx_segment_risk_fixed.geojson"
TOP_OUT = "data/processed/top20_segments_by_risk_fixed.csv"

gdf = gpd.read_file(IN_PATH)

# --- Sanity: required columns ---
needed = ["segment_id", "incident_count", "geometry"]
missing = [c for c in needed if c not in gdf.columns]
if missing:
    raise SystemExit(f"Missing columns in input: {missing}")

# --- Length in km in projected CRS ---
# If already in EPSG:32614, length is in meters.
# If not, we force to EPSG:32614 for correct meters.
if gdf.crs is None or str(gdf.crs.to_epsg()) != "32614":
    gdf = gdf.to_crs(epsg=32614)

gdf["length_m"] = gdf.geometry.length
gdf["length_km"] = (gdf["length_m"] / 1000.0).replace(0, np.nan)

# --- Incident density per km ---
gdf["incident_density"] = (gdf["incident_count"] / gdf["length_km"]).fillna(0)

# --- Robust scaling for score (log to reduce heavy tail) ---
# score = normalized log(1 + density)
x = np.log1p(gdf["incident_density"].astype(float))
x_min, x_max = float(x.min()), float(x.max())
if x_max == x_min:
    gdf["risk_score_fixed"] = 0.0
else:
    gdf["risk_score_fixed"] = (x - x_min) / (x_max - x_min)

# --- Quantile bands (stable, reviewer-friendly) ---
# 5 bands: Very Low, Low, Medium, High, Very High
labels = ["Very Low", "Low", "Medium", "High", "Very High"]
try:
    gdf["risk_band_fixed"] = pd.qcut(
        gdf["incident_density"].rank(method="first"),
        q=5,
        labels=labels
    )
except ValueError:
    # fallback if qcut fails (e.g., too many ties)
    gdf["risk_band_fixed"] = "Medium"

# Save
gdf.to_file(OUT_PATH, driver="GeoJSON")

top = gdf.sort_values("incident_density", ascending=False).head(20)
top_cols = ["segment_id", "incident_count", "length_km", "incident_density", "risk_score_fixed", "risk_band_fixed"]
top[top_cols].to_csv(TOP_OUT, index=False)

print("Saved:", OUT_PATH)
print("Saved:", TOP_OUT)

print("\nTop 10 segments by incident_density:")
print(top[top_cols].head(10))
