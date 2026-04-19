"""
D3_architecture.py (v3)
=======================
Left-to-right system architecture diagram.
Fixed spacing — sub-columns A and B properly separated.
Arrow labels placed outside bands.

RUN:
    conda activate rim12
    cd C:\\projects\\icvars-metaverse-pipeline-risk
    python scripts/corridor/D3_architecture.py
"""

from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

OUTDIR = Path("figures")
OUTDIR.mkdir(exist_ok=True)

FIG_W, FIG_H = 22, 11
DPI = 600

plt.rcParams.update({
    "font.family":        "Times New Roman",
    "figure.facecolor":   "white",
    "axes.facecolor":     "white",
    "savefig.dpi":        DPI,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.15,
})

C = {
    "data":    {"fill": "#D6E8F5", "edge": "#1A6FAF", "text": "#0A3D6B", "band": "#EBF4FB"},
    "proc":    {"fill": "#D5ECD9", "edge": "#2E7D32", "text": "#1B4D1E", "band": "#EAF4EB"},
    "store":   {"fill": "#FFF3CD", "edge": "#B8860B", "text": "#6B4F00", "band": "#FFFAED"},
    "present": {"fill": "#F8D7DA", "edge": "#C0392B", "text": "#7B1010", "band": "#FDF0F1"},
}

ARROW_C = "#555555"
TICK_C  = "#BBBBBB"


def box(ax, cx, cy, w, h, title, subtitle, kind, fs_title=8.5, fs_sub=7.0):
    c = C[kind]
    p = FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.018",
        facecolor=c["fill"], edgecolor=c["edge"],
        linewidth=1.1, zorder=3, clip_on=False
    )
    ax.add_patch(p)
    if subtitle:
        ax.text(cx, cy + h * 0.14, title,
                ha="center", va="center",
                fontsize=fs_title, fontweight="bold",
                color=c["text"], zorder=4, clip_on=False)
        ax.text(cx, cy - h * 0.20, subtitle,
                ha="center", va="center",
                fontsize=fs_sub, style="italic",
                color=c["text"], zorder=4, clip_on=False,
                linespacing=1.4)
    else:
        ax.text(cx, cy, title,
                ha="center", va="center",
                fontsize=fs_title, fontweight="bold",
                color=c["text"], zorder=4, clip_on=False)


def arrow(ax, x0, y0, x1, y1, label="", label_side="top"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=ARROW_C, lw=0.9,
                    mutation_scale=10,
                    connectionstyle="arc3,rad=0.0",
                ), zorder=2, clip_on=False)
    if label:
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2
        dy = 0.015 if label_side == "top" else -0.015
        ax.text(mx, my + dy, label,
                ha="center", va="center",
                fontsize=6.5, color="#666666",
                style="italic",
                bbox=dict(facecolor="white", edgecolor="none",
                          pad=1.5, alpha=0.85),
                zorder=6, clip_on=False)


def band(ax, x0, x1, line1, line2, kind):
    c = C[kind]
    p = FancyBboxPatch(
        (x0, 0.06), x1 - x0, 0.86,
        boxstyle="round,pad=0.008",
        facecolor=c["band"], edgecolor=c["edge"],
        linewidth=0.8, alpha=0.55, zorder=0, clip_on=False
    )
    ax.add_patch(p)
    cx = (x0 + x1) / 2
    ax.text(cx, 0.955, line1,
            ha="center", va="bottom",
            fontsize=9, fontweight="bold",
            color=c["edge"], zorder=1, clip_on=False)
    ax.text(cx, 0.938, line2,
            ha="center", va="top",
            fontsize=7.5, color=c["edge"],
            style="italic", zorder=1, clip_on=False)


def divider(ax, x):
    ax.plot([x, x], [0.08, 0.92],
            color=TICK_C, linewidth=0.7,
            linestyle="--", zorder=1, clip_on=False)


def main():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Band boundaries — wider proc band to fit two sub-columns cleanly ──────
    X_DATA_L,  X_DATA_R  = 0.010, 0.175
    X_PROC_L,  X_PROC_R  = 0.185, 0.620
    X_STORE_L, X_STORE_R = 0.630, 0.800
    X_PRES_L,  X_PRES_R  = 0.810, 0.990

    band(ax, X_DATA_L,  X_DATA_R,  "Layer 1",  "Data ingestion",           "data")
    band(ax, X_PROC_L,  X_PROC_R,  "Layer 2",  "Analytical processing",    "proc")
    band(ax, X_STORE_L, X_STORE_R, "Layer 3",  "Geospatial outputs",        "store")
    band(ax, X_PRES_L,  X_PRES_R,  "Layer 4",  "Metaverse visualisation",  "present")

    divider(ax, X_PROC_L)
    divider(ax, X_STORE_L)
    divider(ax, X_PRES_L)

    # ── Box dimensions ────────────────────────────────────────────────────────
    BW  = 0.145   # data / storage / presentation boxes
    BH  = 0.120   # height for two-line boxes

    # Processing sub-column widths — sized to fit within the wider proc band
    # Proc band width = 0.620 - 0.185 = 0.435
    # Two sub-cols + gap: 0.17 + 0.06 gap + 0.17 = 0.40 — fits with 0.035 margin each side
    BW_PA = 0.170
    BW_PB = 0.170

    # Sub-column A centre: 0.185 + 0.035 + 0.17/2 = 0.305
    X_PA  = 0.305
    # Sub-column B centre: 0.620 - 0.035 - 0.17/2 = 0.500
    X_PB  = 0.500

    # Verify no overlap: A right = 0.305+0.085 = 0.390, B left = 0.500-0.085 = 0.415
    # Gap = 0.415 - 0.390 = 0.025 — clean separation

    # ── LAYER 1 — Data sources ────────────────────────────────────────────────
    X_D  = (X_DATA_L + X_DATA_R) / 2   # 0.0925

    Y1, Y2, Y3, Y4 = 0.80, 0.63, 0.46, 0.29

    box(ax, X_D, Y1, BW, BH,
        "PHMSA incident data",
        "1,985 records\n2010–present (.xlsx)",
        "data")

    box(ax, X_D, Y2, BW, BH,
        "Pipeline shapefile",
        "32,892 segments\nnational (.shp)",
        "data")

    box(ax, X_D, Y3, BW, BH,
        "State boundaries",
        "TX · LA · OK\nTIGER/Line (.shp)",
        "data")

    box(ax, X_D, Y4, BW, BH,
        "Attribute fields",
        "CAUSE · DIAMETER\nINSTAL_YEAR · COST",
        "data")

    # ── LAYER 2 — Sub-column A: pre-processing ────────────────────────────────
    box(ax, X_PA, Y1, BW_PA, BH,
        "State clipping",
        "gpd.clip() per state\nUTM reprojection",
        "proc")

    box(ax, X_PA, Y2, BW_PA, BH,
        "Corridor windowing",
        "02_make_windows.py\n5 km / 10 km sliding",
        "proc")

    box(ax, X_PA, Y3, BW_PA, BH,
        "Hazard enrichment",
        "A1_enrich_incidents.py\ncause × severity × vulnerability",
        "proc")

    box(ax, X_PA, Y4, BW_PA, BH,
        "Multi-state expansion",
        "B_multistate_expansion.py\nTX · LA · OK",
        "proc")

    # Sub-col A internal chain
    arrow(ax, X_PA, Y1 - BH/2, X_PA, Y2 + BH/2)
    arrow(ax, X_PA, Y2 - BH/2, X_PA, Y3 + BH/2)
    arrow(ax, X_PA, Y3 - BH/2, X_PA, Y4 + BH/2)

    # ── LAYER 2 — Sub-column B: statistical pipeline ──────────────────────────
    # Three boxes centred at Y1 mid / Y2 mid / Y3+Y4 mid
    YB1 = 0.755   # between Y1 and Y2
    YB2 = 0.545   # between Y2 and Y3
    YB3 = 0.340   # between Y3 and Y4

    box(ax, X_PB, YB1, BW_PB, BH,
        "Permutation test",
        "04_stats_and_bands.py\nB = 999, multinomial null",
        "proc")

    box(ax, X_PB, YB2, BW_PB, BH,
        "Corridor-level FDR",
        "A2_corridor_fdr.py\nBH correction, α = 0.05",
        "proc")

    box(ax, X_PB, YB3, BW_PB, BH,
        "Ribbon generation",
        "05_make_ribbons.py\n8 km buffer for WebGL",
        "proc")

    # Sub-col B internal chain
    arrow(ax, X_PB, YB1 - BH/2, X_PB, YB2 + BH/2)
    arrow(ax, X_PB, YB2 - BH/2, X_PB, YB3 + BH/2)

    # Sub-col A → B horizontal arrows (right edge of A → left edge of B)
    arrow(ax, X_PA + BW_PA/2, Y2, X_PB - BW_PB/2, YB1)
    arrow(ax, X_PA + BW_PA/2, Y3, X_PB - BW_PB/2, YB2)
    arrow(ax, X_PA + BW_PA/2, Y4, X_PB - BW_PB/2, YB3)

    # ── LAYER 1 → 2 horizontal arrows ─────────────────────────────────────────
    arrow(ax, X_D + BW/2, Y1, X_PA - BW_PA/2, Y1)
    arrow(ax, X_D + BW/2, Y2, X_PA - BW_PA/2, Y2)
    arrow(ax, X_D + BW/2, Y3, X_PA - BW_PA/2, Y3)
    arrow(ax, X_D + BW/2, Y4, X_PA - BW_PA/2, Y4)

    # ── LAYER 3 — Storage outputs ─────────────────────────────────────────────
    X_S = (X_STORE_L + X_STORE_R) / 2   # 0.715

    box(ax, X_S, Y1, BW, BH,
        "corridor_fdr_*.csv",
        "z · q · p · sig flag\nper corridor per state",
        "store")

    box(ax, X_S, Y2, BW, BH,
        "metrics_*_enriched.csv",
        "risk_obs · hazard scores\nper window per state",
        "store")

    box(ax, X_S, Y3, BW, BH,
        "*_corridorfdr.geojson",
        "Line geometry + FDR fields\n6 files (3 states × 2 res.)",
        "store")

    box(ax, X_S, Y4, BW, BH,
        "*_ribbon.geojson",
        "Polygon geometry\n6 files for WebGL",
        "store")

    # Processing → Storage arrows (sub-col B right edge → storage left edge)
    arrow(ax, X_PB + BW_PB/2, YB1, X_S - BW/2, Y1)
    arrow(ax, X_PB + BW_PB/2, YB2, X_S - BW/2, Y2)
    arrow(ax, X_PB + BW_PB/2, YB2, X_S - BW/2, Y3)
    arrow(ax, X_PB + BW_PB/2, YB3, X_S - BW/2, Y4)

    # ── LAYER 4 — Presentation ────────────────────────────────────────────────
    X_PR = (X_PRES_L + X_PRES_R) / 2   # 0.900

    YP1 = 0.755
    YP2 = 0.545
    YP3 = 0.335

    box(ax, X_PR, YP1, BW, BH,
        "FastAPI backend",
        "app.py\n/regions · /manifest · /data",
        "present")

    box(ax, X_PR, YP2, BW, BH,
        "Vite / React frontend",
        "MapView.jsx\nMapLibre GL 3D viewer",
        "present")

    box(ax, X_PR, YP3, BW, BH,
        "ngrok tunnel",
        "HTTPS public URL\nEvaluator remote access",
        "present")

    # Presentation internal chain
    arrow(ax, X_PR, YP1 - BH/2, X_PR, YP2 + BH/2)
    arrow(ax, X_PR, YP2 - BH/2, X_PR, YP3 + BH/2)

    # Storage → Presentation
    # Label placed outside the storage band (to the right of X_STORE_R)
    arrow(ax, X_S + BW/2, Y1,  X_PR - BW/2, YP1,
          label="REST API", label_side="top")
    arrow(ax, X_S + BW/2, Y4,  X_PR - BW/2, YP2,
          label="GeoJSON", label_side="top")

    # ── Legend ────────────────────────────────────────────────────────────────
    leg_items = [
        ("Data source",     "data"),
        ("Processing step", "proc"),
        ("Output artefact", "store"),
        ("Visualisation",   "present"),
    ]
    for i, (lbl, kind) in enumerate(leg_items):
        c  = C[kind]
        lx = 0.01 + i * 0.25
        ly = 0.010
        p  = FancyBboxPatch(
            (lx, ly), 0.020, 0.024,
            boxstyle="round,pad=0.005",
            facecolor=c["fill"], edgecolor=c["edge"],
            linewidth=0.8, zorder=5, clip_on=False
        )
        ax.add_patch(p)
        ax.text(lx + 0.025, ly + 0.012, lbl,
                ha="left", va="center",
                fontsize=8.5, color="#222222",
                zorder=6, clip_on=False)

    for ext in ["png", "svg"]:
        fig.savefig(OUTDIR / f"fig10_system_architecture.{ext}", format=ext)
    plt.close(fig)
    print("Saved: fig10_system_architecture.png / .svg")


if __name__ == "__main__":
    main()
