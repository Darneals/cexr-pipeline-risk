import geopandas as gpd
import pandas as pd
import numpy as np

# -----------------------------
# Load Data (UTM CRS required)
# -----------------------------

segments = gpd.read_file("data/processed/pipelines_tx_segments_1km.geojson")
incidents = gpd.read_file("data/processed/incidents_tx_utm.geojson")

print("Segments CRS:", segments.crs)
print("Incidents CRS:", incidents.crs)
print("Segments:", len(segments), "Incidents:", len(incidents))

# -----------------------------
# Ensure same CRS
# -----------------------------

if segments.crs != incidents.crs:
    incidents = incidents.to_crs(segments.crs)

# -----------------------------
# Nearest segment join
# -----------------------------

joined = gpd.sjoin_nearest(
    incidents,
    segments,
    how="left",
    distance_col="dist_to_seg_m"
)

# -----------------------------
# Apply 5 km spatial constraint
# -----------------------------

THRESHOLD = 5000  # meters

joined_valid = joined[joined["dist_to_seg_m"] <= THRESHOLD].copy()

print("\nValid assignments (<=5km):", len(joined_valid))
print("Rejected (beyond 5km):", len(joined) - len(joined_valid))

# -----------------------------
# Save diagnostic distance stats
# -----------------------------

print("\nNearest-distance summary (m) AFTER filtering:")
print(joined_valid["dist_to_seg_m"].describe())

# -----------------------------
# Save outputs
# -----------------------------

joined_valid.to_file(
    "data/processed/incidents_tx_with_segment.geojson",
    driver="GeoJSON"
)

joined_valid[["segment_id", "dist_to_seg_m"]].to_csv(
    "data/processed/incident_to_segment.csv",
    index=False
)

print("\nSaved filtered incident-to-segment assignments.")
