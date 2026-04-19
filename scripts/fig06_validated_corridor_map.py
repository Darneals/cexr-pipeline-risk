import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")
BOUNDARY = ROOT / "data" / "raw" / "cb_2018_us_state_500k" / "cb_2018_us_state_500k.shp"

# Use your corridor output
CANDIDATE_FILES = [
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon_reband.geojson",
]

OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTPNG = OUTDIR / "fig06_candidate_corridor_map.png"
OUTPDF = OUTDIR / "fig06_candidate_corridor_map.pdf"

TOPK = 250          # how many candidate corridors to highlight
Z_MIN = 2.0         # minimum z threshold for candidates
CONTEXT_ALPHA = 0.15
CAND_ALPHA = 0.95

def pick_input() -> Path:
    for p in CANDIDATE_FILES:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find any candidate corridor file:\n" + "\n".join(str(p) for p in CANDIDATE_FILES))

def safe_to_ll(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        # If CRS missing, we assume it is already lon/lat only if values look like degrees.
        # Otherwise, keep as-is (better than crashing).
        return gdf
    try:
        return gdf.to_crs("EPSG:4326")
    except Exception:
        return gdf

def plot_layer(ax, gdf, lw, alpha):
    # Plot geometry robustly for lines or polygons
    try:
        gdf.plot(ax=ax, linewidth=lw, alpha=alpha)
    except Exception:
        gdf.boundary.plot(ax=ax, linewidth=lw, alpha=alpha)

def main():
    src = pick_input()

    texas = gpd.read_file(BOUNDARY)
    texas = texas[texas["NAME"] == "Texas"].copy()

    gdf = gpd.read_file(src)

    # Required
    if "z_score" not in gdf.columns:
        raise KeyError(f"Missing z_score in {src.name}. Found: {list(gdf.columns)[:40]}")

    gdf["z_score"] = pd.to_numeric(gdf["z_score"], errors="coerce")

    # Candidate set
    cand = gdf[gdf["z_score"].notna() & (gdf["z_score"] >= Z_MIN)].copy()
    cand = cand.sort_values("z_score", ascending=False).head(TOPK)

    # lon/lat for plotting
    texas_ll = safe_to_ll(texas)
    gdf_ll = safe_to_ll(gdf)
    cand_ll = safe_to_ll(cand)

    fig, ax = plt.subplots(figsize=(12, 12))

    # Outline
    texas_ll.boundary.plot(ax=ax, linewidth=2.0)

    # Context (all corridors faint)
    plot_layer(ax, gdf_ll, lw=0.10, alpha=CONTEXT_ALPHA)

    # Candidates (top-K emphasized)
    plot_layer(ax, cand_ll, lw=0.60, alpha=CAND_ALPHA)

    ax.set_axis_off()
    ax.set_aspect("auto")

    # No title inside the figure (Q1 style)
    plt.savefig(OUTPNG, dpi=600, bbox_inches="tight")
    plt.savefig(OUTPDF, bbox_inches="tight")
    plt.close()

    print("Input:", src)
    print(f"Candidates shown: top {TOPK} by z_score (z>={Z_MIN})")
    print("Saved:", OUTPNG)
    print("Saved:", OUTPDF)

if __name__ == "__main__":
    main()