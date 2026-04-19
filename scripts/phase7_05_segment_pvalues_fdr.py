import numpy as np
import pandas as pd
import geopandas as gpd

segments_path = "data/processed/pipelines_tx_segments_1km.geojson"
assign_path   = "data/processed/incidents_to_segment.csv"

out_geojson = "data/processed/pipelines_tx_segments_significant.geojson"
out_csv     = "data/processed/phase7_segment_significance.csv"

N_ITER = 5000
SEED   = 42
MINLEN_KM = 1.0
ALPHA_FDR = 0.05

rng = np.random.default_rng(SEED)

segs = gpd.read_file(segments_path)
if "segment_id" not in segs.columns:
    raise SystemExit(f"segment_id not found. Columns: {list(segs.columns)}")

segs = segs.copy()
segs["length_m"] = segs.geometry.length
segs["length_km"] = segs["length_m"] / 1000.0
segs["length_km_clamped"] = segs["length_km"].clip(lower=MINLEN_KM)

assign = pd.read_csv(assign_path)
need_cols = {"segment_id", "dist_to_seg_m"}
if not need_cols.issubset(assign.columns):
    raise SystemExit(f"Need columns {need_cols} in incidents_to_segment.csv")

assign = assign[assign["dist_to_seg_m"] <= 5000].copy()
n_obs = len(assign)
if n_obs == 0:
    raise SystemExit("No valid incident-to-segment assignments (<=5km).")

# Observed counts aligned to segs
obs_counts_series = assign["segment_id"].value_counts().astype(int)
obs_counts = obs_counts_series.reindex(segs["segment_id"]).fillna(0).astype(int).to_numpy()

# Weights
w = segs["length_km_clamped"].to_numpy()
p = w / w.sum()

# Simulate counts
# We accumulate how often simulated count >= observed count (for each segment)
geq_hits = np.zeros(len(segs), dtype=int)

for _ in range(N_ITER):
    sim = rng.multinomial(n_obs, p)
    geq_hits += (sim >= obs_counts)

# Empirical p per segment (right-tail), add +1 smoothing
pvals = (geq_hits + 1) / (N_ITER + 1)

# Benjamini–Hochberg FDR
m = len(pvals)
order = np.argsort(pvals)
p_sorted = pvals[order]
q = p_sorted * m / (np.arange(1, m + 1))
q = np.minimum.accumulate(q[::-1])[::-1]  # monotone
q = np.clip(q, 0, 1)

qvals = np.empty_like(q)
qvals[order] = q

# Attach to segs
segs["incident_count_obs"] = obs_counts
segs["p_empirical"] = pvals
segs["q_fdr_bh"] = qvals
segs["significant_fdr05"] = segs["q_fdr_bh"] <= ALPHA_FDR

# Also compute density for reporting
segs["incident_density"] = segs["incident_count_obs"] / segs["length_km_clamped"]

# Save
segs.to_file(out_geojson, driver="GeoJSON")

report = segs[["segment_id", "incident_count_obs", "length_km_clamped", "incident_density", "p_empirical", "q_fdr_bh", "significant_fdr05"]].copy()
report = report.sort_values(["significant_fdr05", "incident_density"], ascending=[False, False])
report.to_csv(out_csv, index=False)

print("Saved:", out_geojson)
print("Saved:", out_csv)

print("\nSummary:")
print("Segments:", len(segs))
print("Observed incidents:", n_obs)
print("Significant (FDR<=0.05):", int(segs["significant_fdr05"].sum()))
print("\nTop 15 by density (with q-values):")
print(report.head(15).to_string(index=False))
