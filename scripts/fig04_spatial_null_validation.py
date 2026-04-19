import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# -----------------------------
# Paths
# -----------------------------
ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")

SEGS_PATH = ROOT / "data" / "processed" / "pipelines_tx_segments_1km.geojson"
INC_SEG_PATH = ROOT / "data" / "processed" / "incidents_tx_with_segment.geojson"

# Analysis outputs (CSV)
OUT_CSV = ROOT / "data" / "processed" / "phase7_null_model_results.csv"
OUT_DRAWS = ROOT / "data" / "processed" / "phase7_null_model_draws.csv"

# Paper figures (PNG / PDF)
FIGDIR = ROOT / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

OUTPNG = FIGDIR / "fig04_spatial_null_validation.png"
OUTPDF = FIGDIR / "fig04_spatial_null_validation.pdf"

# -----------------------------
# Settings
# -----------------------------
N_ITER = 200
SEED = 42
MIN_LEN_KM = 1.0

# -----------------------------
# Helpers
# -----------------------------
def hhi_from_counts(counts: np.ndarray) -> float:
    total = counts.sum()
    if total <= 0:
        return 0.0
    p = counts / total
    return float(np.sum(p * p))

def fd_bins(x: np.ndarray, min_bins=15, max_bins=80) -> int:
    x = x[np.isfinite(x)]
    if x.size < 2:
        return min_bins
    q75, q25 = np.percentile(x, [75, 25])
    iqr = q75 - q25
    if iqr <= 0:
        return min_bins
    bw = 2 * iqr * (x.size ** (-1/3))
    if bw <= 0:
        return min_bins
    bins = int(np.ceil((x.max() - x.min()) / bw))
    return int(np.clip(bins, min_bins, max_bins))

# -----------------------------
# Load data
# -----------------------------
segs = gpd.read_file(SEGS_PATH)
inc  = gpd.read_file(INC_SEG_PATH)

if segs.crs is None or segs.crs.to_epsg() != 32614:
    segs = segs.to_crs(epsg=32614)
if inc.crs is None or inc.crs.to_epsg() != 32614:
    inc = inc.to_crs(epsg=32614)

# Segment lengths
segs["length_km"] = segs.geometry.length / 1000.0
segs["length_km"] = segs["length_km"].clip(lower=MIN_LEN_KM)

# Observed counts
obs_counts = inc.groupby("segment_id").size()
segs["obs_count"] = segs["segment_id"].map(obs_counts).fillna(0).astype(int)

obs_vec = segs["obs_count"].to_numpy()
obs_hhi = hhi_from_counts(obs_vec)
n_points = int(obs_vec.sum())

# -----------------------------
# Null simulation
# -----------------------------
rng = np.random.default_rng(SEED)

lengths = segs["length_km"].to_numpy()
weights = lengths / lengths.sum()

n_segs = len(segs)
null_hhi = np.zeros(N_ITER)

for i in range(N_ITER):
    chosen = rng.choice(np.arange(n_segs), size=n_points, replace=True, p=weights)
    counts = np.bincount(chosen, minlength=n_segs)
    null_hhi[i] = hhi_from_counts(counts)

# Stats
null_mean = float(null_hhi.mean())
null_std  = float(null_hhi.std(ddof=0))
z_score = (obs_hhi - null_mean) / null_std if null_std > 0 else np.nan
p_emp = float((null_hhi >= obs_hhi).mean())

# -----------------------------
# Save CSV outputs
# -----------------------------
pd.DataFrame([{
    "observed_hhi": obs_hhi,
    "null_mean_hhi": null_mean,
    "null_std_hhi": null_std,
    "z_score": z_score,
    "p_empirical": p_emp,
    "n_iter": N_ITER,
    "n_points": n_points,
    "seed": SEED
}]).to_csv(OUT_CSV, index=False)

pd.DataFrame({
    "null_hhi": null_hhi,
    "observed_hhi": obs_hhi
}).to_csv(OUT_DRAWS, index=False)

# -----------------------------
# Plot (Q1 style — no title)
# -----------------------------
bins = fd_bins(null_hhi)

fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.hist(null_hhi, bins=bins, alpha=0.85)
ax.axvline(obs_hhi, linewidth=2)

ax.set_xlabel("HHI (incident concentration)")
ax.set_ylabel("Frequency")

ax.text(
    0.98, 0.98,
    f"Observed={obs_hhi:.5f}\nμ={null_mean:.5f}, σ={null_std:.5f}\nz={z_score:.2f}, p={p_emp:.3f}",
    transform=ax.transAxes,
    ha="right", va="top"
)

fig.tight_layout()
fig.savefig(OUTPNG, dpi=600, bbox_inches="tight")
fig.savefig(OUTPDF, bbox_inches="tight")
plt.close(fig)

print("Saved figure:", OUTPNG)
print("Saved figure:", OUTPDF)
print("Saved CSVs:", OUT_CSV, OUT_DRAWS)