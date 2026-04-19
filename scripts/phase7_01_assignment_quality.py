import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

IN_INC_SEG = "data/processed/incidents_tx_with_segment.geojson"
OUT_CSV = "data/processed/phase7_assignment_quality.csv"
OUT_PNG = "data/processed/fig_phase7_distance_hist.png"

gdf = gpd.read_file(IN_INC_SEG)

if "dist_to_seg_m" not in gdf.columns:
    raise SystemExit("dist_to_seg_m not found in incidents_tx_with_segment.geojson")

s = gdf["dist_to_seg_m"].astype(float)

summary = s.describe(percentiles=[0.25, 0.5, 0.75, 0.90, 0.95]).to_frame("dist_to_seg_m").reset_index()
summary.to_csv(OUT_CSV, index=False)

print("Saved:", OUT_CSV)
print(summary)

plt.figure()
plt.hist(s, bins=40)
plt.xlabel("Distance to nearest segment (m)")
plt.ylabel("Count")
plt.title("Incident-to-segment assignment distance (<=5km filtered)")
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=200)
print("Saved:", OUT_PNG)
