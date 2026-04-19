import numpy as np
import pandas as pd
import geopandas as gpd

# ----------------------------
# Inputs (project-relative)
# ----------------------------
segments_path = "data/processed/pipelines_tx_segments_1km.geojson"
assign_path   = "data/processed/incidents_to_segment.csv"

out_csv   = "data/processed/phase7_segment_null_global.csv"
out_hist  = "data/processed/phase7_null_global_hist.csv"

# ----------------------------
# Settings
# ----------------------------
N_ITER = 5000          # raise later if you want tighter p-values
SEED   = 42
MINLEN_KM = 1.0        # avoid tiny-length inflation

rng = np.random.default_rng(SEED)

# ----------------------------
# Load segments + assignments
# ----------------------------
segs = gpd.read_file(segments_path)

# Expect a segment id column (you used segment_id in Phase 6)
if "segment_id" not in segs.columns:
    raise SystemExit(f"segment_id not found in segments. Columns: {list(segs.columns)}")

# Compute length in km (segments are in EPSG:32614 -> meters)
segs = segs.copy()
segs["length_m"] = segs.geometry.length
segs["length_km"] = segs["length_m"] / 1000.0
segs["length_km_clamped"] = segs["length_km"].clip(lower=MINLEN_KM)

assign = pd.read_csv(assign_path)

# Must contain segment_id, dist_to_seg_m
need_cols = {"segment_id", "dist_to_seg_m"}
if not need_cols.issubset(assign.columns):
    raise SystemExit(f"Missing required columns in incidents_to_segment.csv. Need {need_cols}, got {set(assign.columns)}")

# Keep valid <=5km assignments only (your Phase 6.02 already prints this)
assign = assign[assign["dist_to_seg_m"] <= 5000].copy()

n_obs = len(assign)
if n_obs == 0:
    raise SystemExit("No valid incident-to-segment assignments found (<=5km).")

# Observed counts per segment
obs_counts = assign["segment_id"].value_counts().astype(int)
obs_counts = obs_counts.reindex(segs["segment_id"]).fillna(0).astype(int).to_numpy()

# Segment opportunity weights (length-weighted)
w = segs["length_km_clamped"].to_numpy()
p = w / w.sum()

# ----------------------------
# Global statistics
# ----------------------------
def hhi_from_counts(counts: np.ndarray) -> float:
    total = counts.sum()
    if total == 0:
        return 0.0
    s = counts / total
    return float(np.sum(s * s))

def max_density_from_counts(counts: np.ndarray, lengths_km: np.ndarray) -> float:
    dens = counts / lengths_km
    return float(np.max(dens))

lengths_km = segs["length_km_clamped"].to_numpy()

obs_hhi = hhi_from_counts(obs_counts)
obs_maxdens = max_density_from_counts(obs_counts, lengths_km)

# Simulate null counts ~ Multinomial(n_obs, p)
null_hhi = np.empty(N_ITER, dtype=float)
null_maxdens = np.empty(N_ITER, dtype=float)

for i in range(N_ITER):
    sim_counts = rng.multinomial(n_obs, p)
    null_hhi[i] = hhi_from_counts(sim_counts)
    null_maxdens[i] = max_density_from_counts(sim_counts, lengths_km)

# Empirical p-values (right-tail)
p_hhi = float((np.sum(null_hhi >= obs_hhi) + 1) / (N_ITER + 1))
p_maxdens = float((np.sum(null_maxdens >= obs_maxdens) + 1) / (N_ITER + 1))

# Save global results
global_df = pd.DataFrame([{
    "n_obs_incidents": n_obs,
    "n_segments": len(segs),
    "obs_hhi": obs_hhi,
    "null_hhi_mean": float(null_hhi.mean()),
    "null_hhi_std": float(null_hhi.std(ddof=1)),
    "p_empirical_hhi": p_hhi,
    "obs_max_density": obs_maxdens,
    "null_max_density_mean": float(null_maxdens.mean()),
    "null_max_density_std": float(null_maxdens.std(ddof=1)),
    "p_empirical_max_density": p_maxdens,
    "n_iter": N_ITER,
    "seed": SEED,
    "minlen_km_clamp": MINLEN_KM
}])
global_df.to_csv(out_csv, index=False)

# Save hist data (for plotting later)
hist_df = pd.DataFrame({
    "null_hhi": null_hhi,
    "null_max_density": null_maxdens
})
hist_df.to_csv(out_hist, index=False)

print("Saved:", out_csv)
print("Saved:", out_hist)
print("\nGlobal null-model tests:")
print(global_df.T)
