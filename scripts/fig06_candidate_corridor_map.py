# fig06_candidate_corridor_map.py
# Q1-style candidate corridor anomaly map (no in-figure title)
# - De-emphasize full corridor background
# - Highlight top-K candidates by z-score with colormap + colorbar
# - No FDR claim inside figure (put that in caption)

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")

BOUNDARY = ROOT / "data" / "raw" / "cb_2018_us_state_500k" / "cb_2018_us_state_500k.shp"

CANDIDATE_FILES = [
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon_reband.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_pfdr_fixed.geojson",
]

OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

OUTPNG = OUTDIR / "fig06_candidate_corridor_map.png"
OUTPDF = OUTDIR / "fig06_candidate_corridor_map.pdf"

# -----------------------------
# Q1 visual controls
# -----------------------------
TOPK = 75                 # <- key: keep small so it doesn't look like Fig 1
Z_MIN = 2.0               # candidate threshold
CTX_ALPHA = 0.05          # background fade (very faint)
CTX_LW = 0.05
CAND_LW = 0.90            # candidates thicker
CAND_ALPHA = 0.95
CMAP = "magma"            # strong sequential map (good for print)
TEXAS_LW = 2.0

# -----------------------------
# Helpers
# -----------------------------
def pick_input() -> Path:
    for p in CANDIDATE_FILES:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find any candidate corridor file:\n" + "\n".join(str(p) for p in CANDIDATE_FILES))

def to_ll(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Project to lon/lat if CRS known; otherwise return as-is (avoid crashing)."""
    if gdf.crs is None:
        return gdf
    try:
        return gdf.to_crs("EPSG:4326")
    except Exception:
        return gdf

def plot_geom(ax, gdf, **kwargs):
    """Robust plot for lines/polygons."""
    try:
        gdf.plot(ax=ax, **kwargs)
    except Exception:
        gdf.boundary.plot(ax=ax, **kwargs)

def main():
    src = pick_input()

    texas = gpd.read_file(BOUNDARY)
    texas = texas[texas["NAME"] == "Texas"].copy()

    gdf = gpd.read_file(src)

    if "z_score" not in gdf.columns:
        raise KeyError(f"Missing 'z_score' in {src.name}. Found: {list(gdf.columns)[:40]}")

    gdf["z_score"] = pd.to_numeric(gdf["z_score"], errors="coerce")

    # Candidate subset
    cand = gdf[gdf["z_score"].notna() & (gdf["z_score"] >= Z_MIN)].copy()
    cand = cand.sort_values("z_score", ascending=False).head(TOPK)

    # If nothing passes Z_MIN, fall back to top-K by z_score (non-NaN)
    if cand.empty:
        cand = gdf[gdf["z_score"].notna()].sort_values("z_score", ascending=False).head(TOPK).copy()

    # lon/lat
    texas_ll = to_ll(texas)
    gdf_ll = to_ll(gdf)
    cand_ll = to_ll(cand)

    # Build z normalization for stable color mapping
    z_vals = cand_ll["z_score"].to_numpy(dtype=float)
    z_min = float(np.nanmin(z_vals)) if np.isfinite(z_vals).any() else 0.0
    z_max = float(np.nanmax(z_vals)) if np.isfinite(z_vals).any() else 1.0
    if z_max <= z_min:
        z_max = z_min + 1e-9  # avoid degenerate norm

    # Figure
    fig, ax = plt.subplots(figsize=(12, 12))

    # Texas outline (crisp)
    texas_ll.boundary.plot(ax=ax, linewidth=TEXAS_LW)

    # Background corridors (very faint)
    plot_geom(ax, gdf_ll, linewidth=CTX_LW, alpha=CTX_ALPHA)

    # Candidates colored by z-score
    # Note: GeoPandas handles colormap + legend colorbar
    plot_geom(
        ax,
        cand_ll,
        column="z_score",
        cmap=CMAP,
        linewidth=CAND_LW,
        alpha=CAND_ALPHA,
        legend=True,
        legend_kwds={
            "label": "z-score",
            "shrink": 0.65,
            "pad": 0.02,
        },
    )

    ax.set_axis_off()
    ax.set_aspect("auto")

    # No in-figure title (caption goes in paper)
    plt.savefig(OUTPNG, dpi=600, bbox_inches="tight")
    plt.savefig(OUTPDF, bbox_inches="tight")
    plt.close()

    print("Input:", src)
    print(f"Candidates shown: top {TOPK} by z_score (threshold z>={Z_MIN})")
    print(f"Candidate z-score range: {z_min:.3f} to {z_max:.3f}")
    print("Saved:", OUTPNG)
    print("Saved:", OUTPDF)

if __name__ == "__main__":
    main()