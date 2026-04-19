import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------
# Paths
# ---------------------------
ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")
NULL_FILE = ROOT / "data" / "regions" / "us_tx" / "results" / "phase7_null_global_hist.csv"

OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

OUTPNG = OUTDIR / "fig03_global_null_validation.png"
OUTPDF = OUTDIR / "fig03_global_null_validation.pdf"

# ---------------------------
# Load + validate
# ---------------------------
if not NULL_FILE.exists():
    raise FileNotFoundError(f"Missing file: {NULL_FILE}")

df = pd.read_csv(NULL_FILE)

required = ["null_hhi", "null_max_density"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise KeyError(f"Missing columns {missing}. Found columns: {df.columns.tolist()}")

# Coerce to numeric and drop bad rows
hhi = pd.to_numeric(df["null_hhi"], errors="coerce").dropna().to_numpy()
md  = pd.to_numeric(df["null_max_density"], errors="coerce").dropna().to_numpy()

if len(hhi) < 10 or len(md) < 10:
    raise ValueError(
        f"Too few valid samples to plot (hhi={len(hhi)}, max_density={len(md)}). "
        "Check the CSV content."
    )

# ---------------------------
# Helper: FD bins for Q1-style histogram stability
# ---------------------------
def freedman_diaconis_bins(x: np.ndarray, max_bins: int = 80, min_bins: int = 15) -> int:
    x = np.asarray(x)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 2:
        return min_bins
    q75, q25 = np.percentile(x, [75, 25])
    iqr = q75 - q25
    if iqr <= 0:
        return min_bins
    bin_width = 2 * iqr * (n ** (-1 / 3))
    if bin_width <= 0:
        return min_bins
    bins = int(np.ceil((x.max() - x.min()) / bin_width))
    return int(np.clip(bins, min_bins, max_bins))

bins_hhi = freedman_diaconis_bins(hhi)
bins_md  = freedman_diaconis_bins(md)

# ---------------------------
# Plot (no embedded title; caption handles explanation)
# ---------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Panel (a): HHI
ax = axes[0]
ax.hist(hhi, bins=bins_hhi, alpha=0.85)
ax.set_xlabel("Null HHI (Herfindahl–Hirschman Index)")
ax.set_ylabel("Frequency")
ax.text(0.02, 0.98, "(a)", transform=ax.transAxes, va="top")

# Panel (b): Max density
ax = axes[1]
ax.hist(md, bins=bins_md, alpha=0.85)
ax.set_xlabel("Null Maximum Segment Density")
ax.set_ylabel("Frequency")
ax.text(0.02, 0.98, "(b)", transform=ax.transAxes, va="top")

# Clean layout
for ax in axes:
    ax.grid(False)

fig.tight_layout()

# Save
fig.savefig(OUTPNG, dpi=600, bbox_inches="tight")
fig.savefig(OUTPDF, bbox_inches="tight")
plt.close(fig)

print("Saved:", OUTPNG)
print("Saved:", OUTPDF)
print(f"Samples plotted: null_hhi={len(hhi)}, null_max_density={len(md)}")
print(f"Bins used: hhi={bins_hhi}, max_density={bins_md}")