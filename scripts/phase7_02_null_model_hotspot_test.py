import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Inputs
SEGS_PATH = "data/processed/pipelines_tx_segments_1km.geojson"
INC_SEG_PATH = "data/processed/incidents_tx_with_segment.geojson"

# Outputs
OUT_CSV = "data/processed/phase7_null_model_results.csv"
OUT_PNG = "data/processed/fig_phase7_null_vs_observed.png"

# Settings
N_ITER = 200
SEED = 42
MIN_LEN_KM = 1.0  # clamp length to avoid exploding density on tiny segments

# -----------------------------
# Helpers
# -----------------------------
def hhi_from_counts(counts: np.ndarray) -> float:
    """
    Herfindahl–Hirschman Index on incident shares per segment.
    HHI = sum_i (p_i^2), where p_i = count_i / total.
    Larger = more concentrated hotspots.
    """
    total = counts.sum()
    if total <= 0:
        return 0.0
    p = counts / total
    return float(np.sum(p * p))

# -----------------------------
# Load
# -----------------------------
segs = gpd.read_file(SEGS_PATH)
inc = gpd.read_file(INC_SEG_PATH)

# Ensure UTM meters
if segs.crs is None or segs.crs.to_epsg() != 32614:
    segs = segs.to_crs(epsg=32614)
if inc.crs is None or inc.crs.to_epsg() != 32614:
    inc = inc.to_crs(epsg=32614)

# Segment length in km + clamp
segs["length_km"] = segs.geometry.length / 1000.0
segs["length_km_clamped"] = segs["length_km"].clip(lower=MIN_LEN_KM)

# Observed incident counts per segment
obs_counts = inc.groupby("segment_id").size()
segs["obs_incident_count"] = segs["segment_id"].map(obs_counts).fillna(0).astype(int)

# Observed HHI
obs_vec = segs["obs_incident_count"].to_numpy(dtype=int)
obs_metric = hhi_from_counts(obs_vec)

# Number of incidents to simulate under null
n_points = int(obs_vec.sum())
print("Observed assigned incidents:", n_points)
print("Observed HHI:", obs_metric)

# -----------------------------
# Null model
# Sample incidents along the pipeline network proportional to segment length
# -----------------------------
rng = np.random.default_rng(SEED)

lengths = segs["length_km"].to_numpy(dtype=float)
length_sum = float(lengths.sum())
if length_sum <= 0:
    raise SystemExit("Segment lengths sum to 0. Check geometry / CRS.")
w = lengths / length_sum

seg_idx = segs.index.to_numpy()  # indices we can sample
n_segs = len(segs)

null_metrics = np.zeros(N_ITER, dtype=float)

for it in range(N_ITER):
    # IMPORTANT: regenerate random assignments INSIDE the loop
    chosen = rng.choice(seg_idx, size=n_points, replace=True, p=w)

    # Counts per segment (aligned to segs row order)
    tmp = np.bincount(chosen, minlength=n_segs).astype(int)

    # HHI on counts (concentration), no density needed for HHI
    null_metrics[it] = hhi_from_counts(tmp)

# Empirical p-value: how often null >= observed
p_emp = float(np.mean(null_metrics >= obs_metric))

# Effect size (z-score)
z_score = float((obs_metric - null_metrics.mean()) / null_metrics.std(ddof=0))

# Save results
df = pd.DataFrame({
    "observed_metric_hhi": [obs_metric],
    "null_mean_hhi": [float(null_metrics.mean())],
    "null_std_hhi": [float(null_metrics.std(ddof=0))],
    "z_score": [z_score],
    "p_empirical": [p_emp],
    "n_iter": [N_ITER],
    "n_points": [n_points],
    "seed": [SEED],
})
df.to_csv(OUT_CSV, index=False)

print("Saved:", OUT_CSV)
print(df.to_string(index=False))
print("Z-score:", z_score)

# Plot
plt.figure(figsize=(7, 4))
plt.hist(null_metrics, bins=30)
plt.axvline(obs_metric)
plt.xlabel("HHI (incident concentration)")
plt.ylabel("Frequency")
plt.title("Null-model vs observed hotspot concentration (HHI)")
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=200)
print("Saved:", OUT_PNG)

# Quick sanity checks
print("Null min/max:", float(null_metrics.min()), float(null_metrics.max()))
