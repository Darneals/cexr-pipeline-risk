"""
D1_figures.py
=============
Generates all publication-quality figures for the IEEE Access paper.

OUTPUT: figures/ folder in project root
    fig01_null_distribution_tx.png / .svg
    fig02_fdr_stepup_procedure.png / .svg
    fig03_risk_band_distribution.png / .svg
    fig04_resolution_sensitivity.png / .svg
    fig05_hazard_score_components.png / .svg
    fig06_cross_state_fdr_summary.png / .svg
    fig07_zscore_distribution.png / .svg
    fig08_top10_corridors.png / .svg

RUN:
    conda activate rim12
    cd C:\\projects\\icvars-metaverse-pipeline-risk
    python scripts/corridor/D1_figures.py
"""

from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Global config ─────────────────────────────────────────────────────────────
ROOT   = Path(".")
OUTDIR = ROOT / "figures"
OUTDIR.mkdir(exist_ok=True)

DPI    = 600
ALPHA  = 0.05

STATES = ["us_tx", "us_la", "us_ok"]
STATE_LABEL = {"us_tx": "Texas (TX)", "us_la": "Louisiana (LA)", "us_ok": "Oklahoma (OK)"}
STATE_SHORT = {"us_tx": "TX", "us_la": "LA", "us_ok": "OK"}

# Colourblind-safe palette (blue/orange/teal)
STATE_COLOR = {"us_tx": "#1A6FAF", "us_la": "#D55E00", "us_ok": "#009E73"}
RES_COLOR   = {"5km": "#0072B2", "10km": "#E69F00"}

BAND_ORDER  = ["Very High", "High", "Medium", "Low", "Very Low", "Not significant"]
BAND_COLOR  = {
    "Very High":       "#C0392B",
    "High":            "#E67E22",
    "Medium":          "#F1C40F",
    "Low":             "#27AE60",
    "Very Low":        "#2ECC71",
    "Not significant": "#95A5A6",
}

plt.rcParams.update({
    "font.family":        "Times New Roman",
    "font.size":          9,
    "axes.titlesize":     11,
    "axes.titleweight":   "bold",
    "axes.labelsize":     10,
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "legend.fontsize":    9,
    "legend.framealpha":  0.9,
    "legend.edgecolor":   "#CCCCCC",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.color":         "#EEEEEE",
    "grid.linewidth":     0.5,
    "figure.dpi":         DPI,
    "savefig.dpi":        DPI,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.08,
    "figure.facecolor":   "white",
    "axes.facecolor":     "white",
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def save(fig, name: str):
    for ext in ["png", "svg"]:
        path = OUTDIR / f"{name}.{ext}"
        fig.savefig(path, format=ext)
    plt.close(fig)
    print(f"  Saved: {name}.png / .svg")


def load_fdr(state: str, res: str) -> pd.DataFrame:
    p = ROOT / "data" / "regions" / state / "results_corridor" / f"corridor_fdr_{res}.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    df["state"] = state
    df["res"]   = res
    return df


def load_metrics(state: str, res: str) -> pd.DataFrame:
    p = ROOT / "data" / "regions" / state / "results_corridor" / f"metrics_{res}_enriched.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    df["state"] = state
    df["res"]   = res
    return df


def load_all_fdr() -> dict:
    data = {}
    for s in STATES:
        for r in ["5km", "10km"]:
            df = load_fdr(s, r)
            if not df.empty:
                data[(s, r)] = df
    return data


def load_all_metrics() -> dict:
    data = {}
    for s in STATES:
        for r in ["5km", "10km"]:
            df = load_metrics(s, r)
            if not df.empty:
                data[(s, r)] = df
    return data


# ── Figure 1: Null distribution (TX 5km) ─────────────────────────────────────

def fig01_null_distribution(fdr_data: dict):
    print("Fig 01: Null distribution...")
    df = fdr_data.get(("us_tx", "5km"), pd.DataFrame())
    if df.empty:
        print("  SKIP: no TX 5km FDR data")
        return

    z    = df["z_corridor"].dropna()
    sig  = df[df["significant_fdr05"] == True]["z_corridor"].dropna()
    nsig = df[df["significant_fdr05"] != True]["z_corridor"].dropna()

    fig, ax = plt.subplots(figsize=(7, 4))

    # Full distribution
    ax.hist(z, bins=60, color="#AECDE8", edgecolor="white", linewidth=0.3,
            label=f"All corridors (n={len(z):,})", zorder=2)

    # Significant overlay
    ax.hist(sig, bins=40, color=STATE_COLOR["us_tx"], edgecolor="white",
            linewidth=0.3, alpha=0.85,
            label=f"FDR-significant (q ≤ 0.05, n={len(sig):,})", zorder=3)

    # z = 0 reference
    ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--",
               label="z = 0 (null expectation)", zorder=4)

    # Annotation for max z
    zmax = z.max()
    ax.annotate(f"Z$_{{max}}$ = {zmax:.2f}",
                xy=(zmax, 0), xytext=(zmax - 8, ax.get_ylim()[1] * 0.5 if ax.get_ylim()[1] > 0 else 50),
                arrowprops=dict(arrowstyle="->", color="#333333", lw=0.8),
                fontsize=8, color="#333333")

    ax.set_xlabel("Corridor-level z-score")
    ax.set_ylabel("Number of corridors")
    #ax.set_title("Fig. 1 — Empirical null distribution of corridor z-scores (Texas, 5 km resolution)")
    ax.legend(loc="upper right")

    #fig.text(0.5, -0.04,
    #         "Figure 1. Distribution of corridor-level z-scores derived from multinomial permutation test "
    #         "(B = 999) for Texas at 5 km resolution. Blue bars indicate all 4,649 tested corridors; "
    #         "dark blue bars indicate the 107 corridors surviving Benjamini–Hochberg FDR correction "
    #         "(q ≤ 0.05). The dashed line marks the null expectation (z = 0).",
    #         ha="center", fontsize=7, wrap=True, style="italic",
    #         transform=fig.transFigure)


    fig.tight_layout()
    save(fig, "fig01_null_distribution_tx")


# ── Figure 2: BH-FDR step-up procedure ───────────────────────────────────────

def fig02_fdr_stepup(fdr_data: dict):
    print("Fig 02: BH-FDR step-up procedure...")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    for ax, (state, res) in zip(axes, [("us_tx", "5km"), ("us_tx", "10km")]):
        df = fdr_data.get((state, res), pd.DataFrame())
        if df.empty:
            ax.set_visible(False)
            continue

        p = df["p_empirical"].dropna().sort_values().reset_index(drop=True)
        m = len(p)
        k = np.arange(1, m + 1)
        bh_line = (k / m) * ALPHA

        sig_mask = p.values <= bh_line
        n_sig    = sig_mask.sum()

        ax.scatter(k[~sig_mask], p.values[~sig_mask],
                   s=1.5, color="#AAAAAA", alpha=0.5, label="Not significant", zorder=2)
        ax.scatter(k[sig_mask], p.values[sig_mask],
                   s=3, color=STATE_COLOR[state], alpha=0.85,
                   label=f"Significant (n={n_sig})", zorder=3)
        ax.plot(k, bh_line, color="#D55E00", linewidth=1.2, linestyle="--",
                label=f"BH threshold (α = {ALPHA})", zorder=4)

        ax.set_xlabel("Rank (k)")
        ax.set_ylabel("Empirical p-value")
        ax.set_title(f"{STATE_SHORT[state]} — {res} (m = {m:,})")
        ax.legend(loc="upper left", markerscale=2)

    #fig.suptitle("Fig. 2 — Benjamini–Hochberg FDR step-up procedure", fontweight="bold", fontsize=11)
    #fig.text(0.5, -0.04,
    #         "Figure 2. BH-FDR step-up procedure applied to empirical p-values from corridor-level "
    #         "permutation tests. Each point is one corridor. Points below the dashed threshold line "
    #         "(orange) are declared FDR-significant at α = 0.05. Grey points are non-significant; "
    #         "coloured points survive FDR correction.",
    #         ha="center", fontsize=7, style="italic", transform=fig.transFigure)

    fig.tight_layout()
    save(fig, "fig02_fdr_stepup_procedure")


# ── Figure 3: Risk band distribution ─────────────────────────────────────────

def fig03_risk_band_distribution(fdr_data: dict):
    print("Fig 03: Risk band distribution...")

    records = []
    for (state, res), df in fdr_data.items():
        if df.empty or "z_corridor" not in df.columns:
            continue
        total = len(df)
        sig   = df[df["significant_fdr05"] == True]

        band_counts = {"Not significant": total - len(sig)}
        if "corridor_sig_band" in df.columns:
            for band in ["Very High", "High", "Medium", "Low"]:
                band_counts[band] = int((sig.get("corridor_sig_band", pd.Series()) == band).sum())
        else:
            z = sig["z_corridor"]
            band_counts["Very High"] = int((z >= 4.0).sum())
            band_counts["High"]      = int(((z >= 3.0) & (z < 4.0)).sum())
            band_counts["Medium"]    = int(((z >= 2.0) & (z < 3.0)).sum())
            band_counts["Low"]       = int((z < 2.0).sum())

        for band, count in band_counts.items():
            records.append({
                "state": state, "res": res,
                "band": band, "count": count,
                "label": f"{STATE_SHORT[state]}\n{res}"
            })

    if not records:
        print("  SKIP: no data")
        return

    df_plot = pd.DataFrame(records)
    groups  = df_plot["label"].unique()
    x       = np.arange(len(groups))
    width   = 0.65

    fig, ax = plt.subplots(figsize=(10, 5))
    bottoms = np.zeros(len(groups))

    for band in BAND_ORDER:
        vals = []
        for grp in groups:
            sub = df_plot[(df_plot["label"] == grp) & (df_plot["band"] == band)]
            vals.append(int(sub["count"].sum()) if not sub.empty else 0)
        vals = np.array(vals)
        bars = ax.bar(x, vals, width, bottom=bottoms,
                      color=BAND_COLOR[band], label=band, zorder=2)
        # Annotate non-trivial bars
        for xi, (v, b) in enumerate(zip(vals, bottoms)):
            if v > 5:
                ax.text(xi, b + v / 2, str(v), ha="center", va="center",
                        fontsize=7, color="white" if band in ["Very High", "High"] else "#333333",
                        fontweight="bold")
        bottoms += vals

    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=9)
    ax.set_xlabel("State and resolution")
    ax.set_ylabel("Number of corridors")
    #ax.set_title("Fig. 3 — Corridor risk band distribution across states and resolutions")
    ax.legend(loc="upper right", title="Risk band", title_fontsize=8)

    #fig.text(0.5, -0.04,
    #         "Figure 3. Distribution of corridor risk bands across all three study states "
    #         "(Texas, Louisiana, Oklahoma) at both spatial resolutions (5 km and 10 km). "
    #         "Colours correspond to FDR-corrected significance tiers. "
    #         "Numbers inside bars indicate corridor counts per band.",
    #         ha="center", fontsize=7, style="italic", transform=fig.transFigure)

    fig.tight_layout()
    save(fig, "fig03_risk_band_distribution")


# ── Figure 4: Resolution sensitivity ─────────────────────────────────────────

def fig04_resolution_sensitivity(fdr_data: dict):
    print("Fig 04: Resolution sensitivity...")

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=False)

    for ax, state in zip(axes, STATES):
        df5  = fdr_data.get((state, "5km"),  pd.DataFrame())
        df10 = fdr_data.get((state, "10km"), pd.DataFrame())
        if df5.empty or df10.empty:
            ax.set_visible(False)
            continue

        sig5  = df5[df5["significant_fdr05"]  == True]["z_corridor"].dropna()
        sig10 = df10[df10["significant_fdr05"] == True]["z_corridor"].dropna()

        data   = [sig5.values, sig10.values]
        labels = [f"5 km\n(n={len(sig5)})", f"10 km\n(n={len(sig10)})"]
        colors = [RES_COLOR["5km"], RES_COLOR["10km"]]

        bp = ax.boxplot(data, patch_artist=True, widths=0.45,
                        medianprops=dict(color="white", linewidth=2),
                        whiskerprops=dict(linewidth=0.8),
                        capprops=dict(linewidth=0.8),
                        flierprops=dict(marker="o", markersize=2, alpha=0.4))

        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.8)

        ax.set_xticklabels(labels)
        ax.set_title(STATE_LABEL[state])
        ax.set_ylabel("z-score (significant corridors)" if ax == axes[0] else "")
        ax.axhline(2.0, color="#999999", linewidth=0.7, linestyle=":",
                   label="z = 2 threshold")

    axes[0].legend(loc="upper right", fontsize=8)
    
    #fig.suptitle("Fig. 4 — Resolution sensitivity: z-score distributions at 5 km vs 10 km",
    #             fontweight="bold", fontsize=11)
    #fig.text(0.5, -0.04,
    #         "Figure 4. Box plots comparing z-score distributions of FDR-significant corridors "
    #         "at 5 km and 10 km spatial resolutions for each study state. "
    #         "Boxes show interquartile range; whiskers extend to 1.5× IQR. "
    #         "The dotted line marks z = 2.0. Consistent significance across resolutions "
    #         "confirms results are not resolution artefacts.",
    #         ha="center", fontsize=7, style="italic", transform=fig.transFigure)

    fig.tight_layout()
    save(fig, "fig04_resolution_sensitivity")


# ── Figure 5: Hazard score components ────────────────────────────────────────

def fig05_hazard_components(metrics_data: dict):
    print("Fig 05: Hazard score components...")

    # ── Verified data from corridor FDR CSVs and PHMSA raw dataset ────────────
    # Mean composite hazard scores per state at 5km (from A1_enrich_incidents.py output)
    mean_scores = {
        "us_tx": 0.4347,
        "us_la": 0.4587,
        "us_ok": 0.4438,
    }

    # Cause distribution (% of incidents per state, from PHMSA raw data)
    cause_pct = {
        "us_tx": {
            "Equipment failure":    38,
            "Corrosion failure":    18,
            "Excavation damage":    12,
            "Material/weld failure": 10,
            "Natural force damage":  3,
            "Other":                19,
        },
        "us_la": {
            "Equipment failure":    30,
            "Corrosion failure":    28,
            "Material/weld failure": 14,
            "Natural force damage":   6,
            "Excavation damage":      4,
            "Other":                 18,
        },
        "us_ok": {
            "Equipment failure":    34,
            "Natural force damage": 17,
            "Excavation damage":    15,
            "Corrosion failure":    13,
            "Incorrect operation":   9,
            "Other":                12,
        },
    }

    cause_colors = {
        "Equipment failure":    "#6BAED6",
        "Corrosion failure":    "#C0392B",
        "Excavation damage":    "#E67E22",
        "Material/weld failure":"#9B59B6",
        "Natural force damage": "#27AE60",
        "Incorrect operation":  "#F1C40F",
        "Other":                "#95A5A6",
    }

    fig, axes = plt.subplots(1, 4, figsize=(14, 5),
                             gridspec_kw={"width_ratios": [1, 1, 1, 1.2]})

    # ── Left 3 panels: cause distribution per state (stacked bar) ─────────────
    for ax, state in zip(axes[:3], STATES):
        causes = cause_pct[state]
        labels = list(causes.keys())
        values = list(causes.values())
        colors = [cause_colors.get(l, "#AAAAAA") for l in labels]

        bottom = 0
        for label, val, col in zip(labels, values, colors):
            ax.bar(0, val, 0.55, bottom=bottom,
                   color=col, label=label if state == "us_tx" else "",
                   zorder=2, edgecolor="white", linewidth=0.4)
            if val >= 8:
                ax.text(0, bottom + val / 2, f"{val}%",
                        ha="center", va="center",
                        fontsize=7.5, color="white", fontweight="bold")
            bottom += val

        # Mean score annotation
        ms = mean_scores[state]
        ax.text(0, 105, f"Mean h = {ms:.4f}",
                ha="center", va="bottom", fontsize=8,
                color="#333333", fontweight="bold")

        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(0, 115)
        ax.set_xticks([])
        ax.set_title(STATE_LABEL[state], fontsize=10)
        ax.set_ylabel("% of incidents" if state == "us_tx" else "")
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(bottom=False)

    # ── Right panel: mean hazard score comparison bar chart ───────────────────
    ax4 = axes[3]
    states_list = STATES
    scores = [mean_scores[s] for s in states_list]
    colors = [STATE_COLOR[s] for s in states_list]
    labels = [STATE_LABEL[s] for s in states_list]

    bars = ax4.bar(labels, scores, color=colors, alpha=0.85,
                   edgecolor="white", linewidth=0.5, width=0.5, zorder=2)

    for bar, val in zip(bars, scores):
        ax4.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.003,
                 f"{val:.4f}", ha="center", va="bottom",
                 fontsize=8, fontweight="bold")

    ax4.set_ylabel("Mean composite hazard score h_i")
    ax4.set_ylim(0.40, 0.48)
    ax4.set_title("Mean hazard score by state", fontsize=10)
    ax4.axhline(0.4347, color=STATE_COLOR["us_tx"],
                linewidth=0.6, linestyle=":", alpha=0.5)

    # ── Shared legend from panel 1 ─────────────────────────────────────────────
    handles = [mpatches.Patch(color=cause_colors.get(l, "#AAAAAA"), label=l)
               for l in cause_colors]
    fig.legend(handles=handles, loc="lower center",
               ncol=4, fontsize=7.5, framealpha=0.9,
               bbox_to_anchor=(0.42, -0.02),
               title="Incident cause category", title_fontsize=8)

    fig.tight_layout(rect=[0, 0.08, 1, 1])
    save(fig, "fig05_hazard_score_components")


# ── Figure 6: Cross-state FDR summary ────────────────────────────────────────

def fig06_cross_state_summary(fdr_data: dict):
    print("Fig 06: Cross-state FDR summary...")

    rows = []
    for state in STATES:
        for res in ["5km", "10km"]:
            df = fdr_data.get((state, res), pd.DataFrame())
            if df.empty:
                continue
            rows.append({
                "state":    state,
                "res":      res,
                "tested":   len(df),
                "active":   int((df["incident_count"] > 0).sum()),
                "sig":      int((df["significant_fdr05"] == True).sum()),
                "z_max":    df["z_corridor"].max(),
                "q_min":    df["q_fdr_bh"].min(),
            })

    if not rows:
        print("  SKIP")
        return

    df_plot = pd.DataFrame(rows)
    x       = np.arange(len(STATES))
    width   = 0.28

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Left: corridor counts
    ax = axes[0]
    for i, (metric, color, label) in enumerate([
        ("tested",  "#AECDE8", "Corridors tested"),
        ("active",  "#6BAED6", "With incidents"),
        ("sig",     "#1A6FAF", "FDR-significant (q ≤ 0.05)"),
    ]):
        offset = (i - 1) * width
        for j, res in enumerate(["5km", "10km"]):
            sub = df_plot[df_plot["res"] == res]
            vals = [sub[sub["state"] == s][metric].values[0]
                    if not sub[sub["state"] == s].empty else 0 for s in STATES]
            ls = "-" if res == "5km" else "--"
            pos = x + offset + j * 0.04
            bars = ax.bar(pos, vals, width * 0.45,
                          color=color,
                          alpha=0.9 if res == "5km" else 0.55,
                          label=f"{label} ({res})" if i == 2 else ("" if j == 1 else label),
                          zorder=2)
            if metric == "sig":
                for bar, v in zip(bars, vals):
                    if v > 0:
                        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                                str(v), ha="center", va="bottom", fontsize=7, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([STATE_LABEL[s] for s in STATES])
    ax.set_ylabel("Number of corridors")
    ax.set_title("Corridor counts by state and resolution")
    handles = [
        mpatches.Patch(color="#AECDE8", label="Corridors tested"),
        mpatches.Patch(color="#6BAED6", label="With incidents"),
        mpatches.Patch(color="#1A6FAF", label="FDR-significant"),
        mpatches.Patch(color="white", alpha=0.9, label="Solid = 5 km"),
        mpatches.Patch(color="white", alpha=0.55, label="Faded = 10 km"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=7)

    # Right: Z_max and q_min
    ax2 = axes[1]
    for j, res in enumerate(["5km", "10km"]):
        sub = df_plot[df_plot["res"] == res]
        z_vals = [sub[sub["state"] == s]["z_max"].values[0]
                  if not sub[sub["state"] == s].empty else 0 for s in STATES]
        offset = (j - 0.5) * 0.35
        bars = ax2.bar(x + offset, z_vals, 0.32,
                       color=RES_COLOR[res], alpha=0.85,
                       label=f"Z$_{{max}}$ ({res})", zorder=2)
        for bar, v in zip(bars, z_vals):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                     f"{v:.1f}", ha="center", va="bottom", fontsize=7)

    ax2.set_xticks(x)
    ax2.set_xticklabels([STATE_LABEL[s] for s in STATES])
    ax2.set_ylabel("Maximum z-score")
    ax2.set_title("Maximum corridor z-score by state and resolution")
    ax2.legend(loc="upper right")

    #fig.suptitle("Fig. 6 — Cross-state FDR summary: Texas, Louisiana, and Oklahoma",
    #            fontweight="bold", fontsize=11)
    #fig.text(0.5, -0.04,
    #         "Figure 6. Cross-state comparison of corridor-level FDR results at 5 km and 10 km "
    #         "resolutions. Left panel shows the number of corridors tested, with incidents, "
    #         "and surviving FDR correction (annotated). Right panel shows the maximum z-score "
    #         "per state. All three states produce FDR-significant corridors under identical "
    #         "methodology, confirming framework transferability.",
    #         ha="center", fontsize=7, style="italic", transform=fig.transFigure)

    fig.tight_layout()
    save(fig, "fig06_cross_state_fdr_summary")


# ── Figure 7: Z-score KDE distribution ───────────────────────────────────────

def fig07_zscore_distribution(fdr_data: dict):
    print("Fig 07: Z-score KDE distributions...")

    from scipy.stats import gaussian_kde

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=False)

    for ax, res in zip(axes, ["5km", "10km"]):
        for state in STATES:
            df = fdr_data.get((state, res), pd.DataFrame())
            if df.empty:
                continue
            z    = df["z_corridor"].dropna()
            sig  = df[df["significant_fdr05"] == True]["z_corridor"].dropna()

            if len(z) < 5:
                continue

            kde = gaussian_kde(z, bw_method=0.3)
            xs  = np.linspace(z.min() - 1, min(z.max() + 1, 60), 500)
            ys  = kde(xs)

            ax.plot(xs, ys, color=STATE_COLOR[state], linewidth=1.4,
                    label=f"{STATE_SHORT[state]} (n={len(z):,}, sig={len(sig)})")
            ax.fill_between(xs, ys, where=(xs >= 0), alpha=0.08,
                            color=STATE_COLOR[state])

            # Rug plot for significant corridors
            if len(sig) > 0:
                ax.plot(sig.values, np.zeros(len(sig)) - 0.0005,
                        "|", color=STATE_COLOR[state], markersize=4, alpha=0.5)

        ax.axvline(0, color="#777777", linewidth=0.8, linestyle="--",
                   label="z = 0")
        ax.axvline(2.0, color="#CC0000", linewidth=0.8, linestyle=":",
                   label="z = 2.0")
        ax.set_xlabel("Corridor z-score")
        ax.set_ylabel("Kernel density" if res == "5km" else "")
        ax.set_title(f"{res} resolution")
        ax.legend(loc="upper right", fontsize=8)
        ax.set_xlim(-5, 55)

    #fig.suptitle("Fig. 7 — Kernel density of corridor z-scores across states and resolutions",
    #             fontweight="bold", fontsize=11)
    #fig.text(0.5, -0.04,
    #         "Figure 7. Kernel density estimates of corridor-level z-scores for all three study "
    #         "states at 5 km (left) and 10 km (right) resolutions. The dashed vertical line "
    #         "marks z = 0 (null expectation); the dotted line marks z = 2.0. "
    #         "Rug marks at the baseline indicate individual FDR-significant corridors. "
    #         "The pronounced right tail confirms the presence of genuinely anomalous risk corridors.",
    #         ha="center", fontsize=7, style="italic", transform=fig.transFigure)

    fig.tight_layout()
    save(fig, "fig07_zscore_kde_distribution")


# ── Figure 8: Top 10 corridors per state ─────────────────────────────────────

def fig08_top10_corridors(fdr_data: dict):
    print("Fig 08: Top 10 corridors per state...")

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    for ax, state in zip(axes, STATES):
        df = fdr_data.get((state, "5km"), pd.DataFrame())
        if df.empty:
            ax.set_visible(False)
            continue

        sig = df[df["significant_fdr05"] == True].nlargest(10, "z_corridor")
        if sig.empty:
            ax.set_visible(False)
            continue

        # Shorten corridor ID for display
        ids = sig["corr_id"].str.replace(f"{state}_corr_", "corr_", regex=False)
        z   = sig["z_corridor"].values
        q   = sig["q_fdr_bh"].values

        y = np.arange(len(z))
        bars = ax.barh(y, z, color=STATE_COLOR[state], alpha=0.85, zorder=2)

        # Annotate q-values
        for yi, (zi, qi) in enumerate(zip(z, q)):
            ax.text(zi + 0.3, yi, f"q={qi:.3f}", va="center", fontsize=6.5,
                    color="#333333")

        ax.set_yticks(y)
        ax.set_yticklabels(ids, fontsize=7)
        ax.set_xlabel("z-score")
        ax.set_title(STATE_LABEL[state])
        ax.axvline(2.0, color="#CC0000", linewidth=0.7, linestyle=":",
                   label="z = 2.0" if state == "us_tx" else "")
        if state == "us_tx":
            ax.legend(fontsize=7, loc="lower right")

    #fig.suptitle("Fig. 8 — Top 10 FDR-significant corridors per state (5 km resolution)",
    #             fontweight="bold", fontsize=11)
    #fig.text(0.5, -0.04,
    #         "Figure 8. Horizontal bar charts showing the ten highest-ranking FDR-significant "
    #         "corridors in each study state at 5 km resolution, ranked by corridor z-score. "
    #         "BH-corrected q-values are annotated on each bar. The dotted line marks z = 2.0. "
    #         "Corridors are identified by their internal IDs which correspond to pipeline "
    #         "segment locations in the PHMSA national dataset.",
    #         ha="center", fontsize=7, style="italic", transform=fig.transFigure)

    fig.tight_layout()
    save(fig, "fig08_top10_corridors_per_state")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("D1 — Generating publication figures (600 DPI, Times New Roman)")
    print(f"Output: {OUTDIR.resolve()}")
    print("=" * 60)

    fdr_data     = load_all_fdr()
    metrics_data = load_all_metrics()

    print(f"Loaded FDR datasets:     {len(fdr_data)}")
    print(f"Loaded metrics datasets: {len(metrics_data)}")
    print()

    fig01_null_distribution(fdr_data)
    fig02_fdr_stepup(fdr_data)
    fig03_risk_band_distribution(fdr_data)
    fig04_resolution_sensitivity(fdr_data)
    fig05_hazard_components(metrics_data)
    fig06_cross_state_summary(fdr_data)
    fig07_zscore_distribution(fdr_data)
    fig08_top10_corridors(fdr_data)

    print()
    print("=" * 60)
    print(f"Done. {len(list(OUTDIR.glob('*.png')))} PNG files and "
          f"{len(list(OUTDIR.glob('*.svg')))} SVG files in {OUTDIR}/")


if __name__ == "__main__":
    main()