"""
D2_crossstate_map.py  (v4)
==========================
Cross-state comparison map — TX, LA, OK.

Key fix: each ribbon polygon is ~0.0001 deg2 (~300x300m) which is
sub-pixel at state scale. This version buffers significant corridors
to a visible size (0.08 degrees ~ 8km) before plotting, purely for
print visibility. Non-significant corridors shown as light lines.

RUN:
    conda activate rim12
    cd C:\\projects\\icvars-metaverse-pipeline-risk
    python scripts/corridor/D2_crossstate_map.py
"""

from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
from matplotlib.gridspec import GridSpec
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT   = Path(".")
OUTDIR = ROOT / "figures"
OUTDIR.mkdir(exist_ok=True)

DPI    = 600
STATES = ["us_tx", "us_la", "us_ok"]

STATE_FULL = {"us_tx": "Texas",     "us_la": "Louisiana", "us_ok": "Oklahoma"}
STATE_ABB  = {"us_tx": "TX",        "us_la": "LA",        "us_ok": "OK"}
STATE_FIPS = {"us_tx": "48",        "us_la": "22",        "us_ok": "40"}
STATE_UTM  = {"us_tx": 32614,       "us_la": 32615,       "us_ok": 32614}

STATE_SHP  = (ROOT / "data" / "raw" / "cb_2018_us_state_500k"
              / "cb_2018_us_state_500k.shp")

CMAP_NAME      = "YlOrRd"
Z_VMIN, Z_VMAX = 0, 50

# Buffer radius in metres for print visibility at state scale
PRINT_BUFFER_M = 8000   # 8 km — visible as ~3-4mm on print

plt.rcParams.update({
    "font.family":        "Times New Roman",
    "font.size":          9,
    "axes.labelsize":     9,
    "xtick.labelsize":    7,
    "ytick.labelsize":    7,
    "figure.dpi":         DPI,
    "savefig.dpi":        DPI,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.1,
    "figure.facecolor":   "white",
    "axes.facecolor":     "#EEF3F8",
    "axes.grid":          False,
})

_states_gdf = None
def get_states():
    global _states_gdf
    if _states_gdf is None:
        _states_gdf = gpd.read_file(STATE_SHP).to_crs("EPSG:4326")
    return _states_gdf


def save(fig, name):
    for ext in ["png", "svg"]:
        fig.savefig(OUTDIR / f"{name}.{ext}", format=ext)
    plt.close(fig)
    print(f"  Saved: {name}.png / .svg")


def load_fdr_csv(state, res):
    """Load corridor FDR CSV — these have the correct per-corridor counts."""
    p = ROOT / "data" / "regions" / state / "results_corridor" / f"corridor_fdr_{res}.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    df["_sig"] = df["significant_fdr05"].apply(
        lambda v: v is True or str(v).lower() in ("true", "1"))
    return df


def load_corridors_from_fdr(state, res):
    """
    Load corridorfdr GeoJSON for geometry.
    Join with corridor FDR CSV for authoritative significance flags.
    Deduplicate to one geometry per corridor.
    Returns (all_gdf, sig_gdf, n_corridors, n_sig).
    """
    p = (ROOT / "data" / "regions" / state / "results_corridor"
         / f"risk_windows_{res}_corridorfdr.geojson")
    if not p.exists():
        print(f"  WARNING: {p.name} not found")
        return None, None, 0, 0

    gdf = gpd.read_file(p)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    else:
        gdf = gdf.to_crs("EPSG:4326")

    # Load authoritative corridor-level FDR results
    fdr = load_fdr_csv(state, res)

    if not fdr.empty and "corr_id" in fdr.columns and "corr_id" in gdf.columns:
        # Merge significance from FDR CSV onto windows
        fdr_lookup = fdr.set_index("corr_id")[["_sig", "z_corridor", "q_fdr_bh"]]
        gdf = gdf.drop(columns=[c for c in ["_sig","z_corridor","q_fdr_bh"]
                                  if c in gdf.columns], errors="ignore")
        gdf = gdf.join(fdr_lookup, on="corr_id", how="left")
        gdf["_sig"] = gdf["_sig"].fillna(False)
        gdf["z_corridor"] = pd.to_numeric(
            gdf["z_corridor"], errors="coerce").fillna(0)
    else:
        gdf["_sig"] = gdf["significant_fdr05"].apply(
            lambda v: v is True or str(v).lower() in ("true", "1"))
        gdf["z_corridor"] = pd.to_numeric(
            gdf.get("z_corridor", 0), errors="coerce").fillna(0)

    # Deduplicate: one geometry per corridor (representative window = max z)
    if "corr_id" in gdf.columns:
        idx = gdf.groupby("corr_id")["z_corridor"].idxmax()
        gdf = gdf.loc[idx].reset_index(drop=True)

    n_total = len(gdf)
    nonsig  = gdf[~gdf["_sig"]].copy()
    sig     = gdf[gdf["_sig"]].copy()
    n_sig   = len(sig)

    return nonsig, sig, n_total, n_sig


def buffer_for_print(gdf, utm_epsg, buffer_m):
    """Buffer geometries in UTM metres then reproject to WGS84."""
    if gdf.empty:
        return gdf
    gdf_utm = gdf.to_crs(epsg=utm_epsg)
    gdf_utm["geometry"] = gdf_utm.geometry.buffer(buffer_m)
    return gdf_utm.to_crs("EPSG:4326")


def draw_panel(ax, state, res, cmap, norm):
    states   = get_states()
    boundary = states[states["STATEFP"] == STATE_FIPS[state]]
    utm_epsg = STATE_UTM[state]

    # State background
    if not boundary.empty:
        boundary.plot(ax=ax, facecolor="#D6E8F5", edgecolor="#555555",
                      linewidth=0.9, zorder=1)

    nonsig, sig, n_total, n_sig = load_corridors_from_fdr(state, res)
    if nonsig is None:
        ax.set_title(STATE_FULL[state], fontsize=10, fontweight="bold")
        return 0, 0

    # Non-significant corridors — thin dark lines (geometry already lines)
    if not nonsig.empty:
        nonsig.plot(ax=ax, color="#888888", linewidth=0.25,
                    alpha=0.45, zorder=2)

    # Significant corridors — buffered to print-visible size, coloured by z
    if not sig.empty:
        sig_buf = buffer_for_print(sig, utm_epsg, PRINT_BUFFER_M)
        sig_z   = sig_buf["z_corridor"].clip(Z_VMIN, Z_VMAX).values
        colors  = [cmap(norm(z)) for z in sig_z]
        sig_buf.plot(ax=ax, facecolor=colors, edgecolor="none",
                     alpha=0.88, zorder=3)

    # State border on top
    if not boundary.empty:
        boundary.plot(ax=ax, facecolor="none", edgecolor="#333333",
                      linewidth=1.0, zorder=4)

    # State watermark
    if not boundary.empty:
        cx = boundary.geometry.centroid.x.values[0]
        cy = boundary.geometry.centroid.y.values[0]
        ax.text(cx, cy, STATE_ABB[state], fontsize=20, fontweight="bold",
                ha="center", va="center", color="#AAAAAA",
                alpha=0.25, zorder=1, style="italic")

    # Stats box
    pct = 100 * n_sig / n_total if n_total > 0 else 0
    ax.text(0.02, 0.03,
            f"Corridors: {n_total:,}\nFDR-sig (q ≤ 0.05): {n_sig:,} ({pct:.1f}%)",
            transform=ax.transAxes, fontsize=7.5,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="#AAAAAA", alpha=0.95),
            zorder=6)

    # Fit to state bounds
    if not boundary.empty:
        b     = boundary.total_bounds
        pad_x = (b[2] - b[0]) * 0.03
        pad_y = (b[3] - b[1]) * 0.03
        ax.set_xlim(b[0] - pad_x, b[2] + pad_x)
        ax.set_ylim(b[1] - pad_y, b[3] + pad_y)

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(STATE_FULL[state], fontsize=10, fontweight="bold", pad=5)
    ax.set_xlabel("Longitude (°)", fontsize=8)

    return n_total, n_sig


def make_map(res):
    print(f"\n  Drawing {res} cross-state map...")

    cmap = plt.get_cmap(CMAP_NAME)
    norm = mcolors.Normalize(vmin=Z_VMIN, vmax=Z_VMAX)

    fig = plt.figure(figsize=(16, 5.8))
    gs  = GridSpec(1, 4, figure=fig,
                   width_ratios=[1, 1, 1, 0.055],
                   wspace=0.22,
                   left=0.055, right=0.94,
                   top=0.88,   bottom=0.14)

    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
    cax  = fig.add_subplot(gs[0, 3])

    totals, sigs = [], []
    for i, (ax, state) in enumerate(zip(axes, STATES)):
        n_total, n_sig = draw_panel(ax, state, res, cmap, norm)
        totals.append(n_total)
        sigs.append(n_sig)
        ax.set_ylabel("Latitude (°)" if i == 0 else "", fontsize=8)

    # Colorbar
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax, orientation="vertical")
    cb.set_label("Corridor z-score", fontsize=8, labelpad=6)
    cb.ax.tick_params(labelsize=7)
    cb.set_ticks([0, 10, 20, 30, 40, 50])
    cb.set_ticklabels(["0", "10", "20", "30", "40", "≥50"])

    # Legend
    legend_handles = [
        mpatches.Patch(facecolor="#888888", edgecolor="none",
                       alpha=0.45, label="Non-significant corridor"),
        mpatches.Patch(facecolor=cmap(norm(5)),  edgecolor="none",
                       label="Low z (< 10)"),
        mpatches.Patch(facecolor=cmap(norm(20)), edgecolor="none",
                       label="Mid z (10–30)"),
        mpatches.Patch(facecolor=cmap(norm(45)), edgecolor="none",
                       label="High z (> 30)"),
    ]
    fig.legend(handles=legend_handles, loc="lower center",
               bbox_to_anchor=(0.465, 0.01), ncol=4,
               fontsize=8, framealpha=0.95, edgecolor="#CCCCCC",
               title=f"FDR significance tier  (α = 0.05, B = 999 permutations, {res} resolution)",
               title_fontsize=7.5)

    save(fig, f"fig09_crossstate_risk_map_{res}")
    print(f"    TX: {sigs[0]}/{totals[0]} sig | "
          f"LA: {sigs[1]}/{totals[1]} sig | "
          f"OK: {sigs[2]}/{totals[2]} sig")


def main():
    print("D2 — Cross-state comparison maps (v4)")
    print("=" * 55)
    for res in ["5km", "10km"]:
        make_map(res)
    print("\nDone. All figures written to figures/")


if __name__ == "__main__":
    main()
