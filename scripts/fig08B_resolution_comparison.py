import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")
OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

OUTPNG = OUTDIR / "fig08B_resolution_sensitivity_tail.png"
OUTPDF = OUTDIR / "fig08B_resolution_sensitivity_tail.pdf"

CAND_10 = [
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_pFDR_fixed.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_pfdr_fixed.geojson",
]

CAND_5 = [
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_5km_ribbon.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_5km.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_5km_ribbon_reband.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_5km_pFDR_fixed.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_5km_pfdr_fixed.geojson",
]

# ----------------------------
# Tail-focused controls
# ----------------------------
Z_THR = 2.0          # anomaly threshold shown in plot
Z_MIN_PLOT = 1.0     # IMPORTANT: crop/plot only z >= this to avoid "clustered" look
X_MAX = 12.0         # default x-limit for panel A; script will auto-extend if needed

def pick(cands):
    for p in cands:
        if p.exists():
            return p
    raise FileNotFoundError("Missing inputs:\n" + "\n".join(str(x) for x in cands))

def props_df(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [(f.get("properties") or {}) for f in data.get("features", [])]
    return pd.DataFrame(rows)

def num(s, default=None):
    x = pd.to_numeric(s, errors="coerce")
    if default is not None:
        return x.fillna(default)
    return x

def ecdf_survival(zvals: np.ndarray):
    """
    Returns x (sorted z) and survival S(z)=P(Z>=z) evaluated at those x points.
    """
    z = np.asarray(zvals, dtype=float)
    z = z[np.isfinite(z)]
    if z.size == 0:
        return np.array([0.0]), np.array([1.0])

    z_sorted = np.sort(z)
    n = z_sorted.size
    # For each point i (0-based), survival at z_sorted[i] is (n - i)/n
    surv = (n - np.arange(n)) / n
    return z_sorted, surv

def pct(x):
    return 100.0 * float(x)

def q(x, p):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.quantile(x, p)) if x.size else np.nan

def main():
    p10 = pick(CAND_10)
    p5  = pick(CAND_5)

    d10 = props_df(p10)
    d5  = props_df(p5)

    required = ["z_score", "p_raw", "p_fdr", "risk_score_fixed", "exceedance"]
    for col in required:
        if col not in d10.columns or col not in d5.columns:
            raise KeyError(f"Missing {col}. 10km has {col in d10.columns}, 5km has {col in d5.columns}")

    # Clean numeric columns
    for df in (d10, d5):
        df["z_score"] = num(df["z_score"], default=0.0)
        df["p_raw"] = num(df["p_raw"], default=1.0).clip(0, 1)
        df["p_fdr"] = num(df["p_fdr"], default=1.0).clip(0, 1)
        df["risk_score_fixed"] = num(df["risk_score_fixed"], default=0.0)
        df["exceedance"] = num(df["exceedance"], default=0.0)

    z10 = d10["z_score"].to_numpy()
    z5  = d5["z_score"].to_numpy()

    # Tail cropping for plotting (THIS is the refinement)
    z10_tail = z10[z10 >= Z_MIN_PLOT]
    z5_tail  = z5[z5 >= Z_MIN_PLOT]

    x10, s10 = ecdf_survival(z10_tail)
    x5,  s5  = ecdf_survival(z5_tail)

    # Metrics for table
    def metrics(df):
        z = df["z_score"].to_numpy()
        pr = df["p_raw"].to_numpy()
        pf = df["p_fdr"].to_numpy()

        n = int(np.isfinite(z).sum())
        maxz = float(np.nanmax(z)) if n else np.nan
        z95 = q(z, 0.95)
        z99 = q(z, 0.99)

        c_z2 = int(np.sum(z >= Z_THR))
        r_z2 = (c_z2 / n) if n else np.nan

        c_pr05 = int(np.sum(pr <= 0.05))
        r_pr05 = (c_pr05 / n) if n else np.nan

        validated = int(np.sum((pf <= 0.05) & (z >= Z_THR)))

        mean_exc = float(np.nanmean(df["exceedance"])) if n else np.nan
        mean_risk = float(np.nanmean(df["risk_score_fixed"])) if n else np.nan
        med_risk = float(np.nanmedian(df["risk_score_fixed"])) if n else np.nan
        std_risk = float(np.nanstd(df["risk_score_fixed"])) if n else np.nan

        return {
            "N windows": n,
            "Max z": maxz,
            "z 95th pct": z95,
            "z 99th pct": z99,
            f"Count(z ≥ {Z_THR:g}) (pre-FDR)": c_z2,
            f"Rate(z ≥ {Z_THR:g})": r_z2,
            "Count(p_raw ≤ 0.05) (pre-FDR)": c_pr05,
            "Rate(p_raw ≤ 0.05)": r_pr05,
            f"Validated count (p_fdr ≤ 0.05 & z ≥ {Z_THR:g})": validated,
            "Mean exceedance": mean_exc,
            "Mean risk_score_fixed": mean_risk,
            "Median risk_score_fixed": med_risk,
            "Std risk_score_fixed": std_risk,
        }

    m10 = metrics(d10)
    m5  = metrics(d5)

    # Figure layout
    fig = plt.figure(figsize=(14, 6))

    # ----------------------------
    # Panel A: Tail survival plot
    # ----------------------------
    ax1 = fig.add_subplot(1, 2, 1)

    # Ensure x-limits cover tail nicely
    xmax = max(X_MAX, float(np.nanmax([m10["Max z"], m5["Max z"]])) * 0.65)
    xmax = max(xmax, Z_THR + 1.0)

    ax1.step(x10, s10, where="post", label="10km")
    ax1.step(x5,  s5,  where="post", label="5km")

    ax1.set_yscale("log")
    ax1.set_xlim(Z_MIN_PLOT, xmax)

    # Shade z >= threshold
    ax1.axvspan(Z_THR, ax1.get_xlim()[1], alpha=0.12)
    ax1.axvline(Z_THR, linestyle="--")
    ax1.text(
        Z_THR + 0.05, ax1.get_ylim()[0]*6,
        f"z ≥ {Z_THR:g} region",
        fontsize=10,
        rotation=90,
        va="bottom"
    )

    ax1.set_xlabel("z_score")
    ax1.set_ylabel("Survival probability  P(Z ≥ z)")
    ax1.set_title("A) Tail survival of z-score (resolution sensitivity)")

    # Compact stats annotation (in-axes)
    ann = (
        f"Tail-focused view: z ≥ {Z_MIN_PLOT:g}\n"
        f"10km: max={m10['Max z']:.3f}, z99={m10['z 99th pct']:.3f}, tail(z≥{Z_THR:g})={pct(m10[f'Rate(z ≥ {Z_THR:g})']):.2f}%\n"
        f" 5km: max={m5['Max z']:.3f}, z99={m5['z 99th pct']:.3f}, tail(z≥{Z_THR:g})={pct(m5[f'Rate(z ≥ {Z_THR:g})']):.2f}%"
    )
    ax1.text(0.02, 0.98, ann, transform=ax1.transAxes, va="top", fontsize=10)

    ax1.legend(loc="upper right")

    # ----------------------------
    # Panel B: Table summary
    # ----------------------------
    ax2 = fig.add_subplot(1, 2, 2)
    ax2.axis("off")
    ax2.set_title("B) Tail + stability summary (10km vs 5km)")

    # Build table rows in an intentional order
    rows = [
        "N windows",
        "Max z",
        "z 95th pct",
        "z 99th pct",
        f"Count(z ≥ {Z_THR:g}) (pre-FDR)",
        f"Rate(z ≥ {Z_THR:g})",
        "Count(p_raw ≤ 0.05) (pre-FDR)",
        "Rate(p_raw ≤ 0.05)",
        f"Validated count (p_fdr ≤ 0.05 & z ≥ {Z_THR:g})",
        "Mean exceedance",
        "Mean risk_score_fixed",
        "Median risk_score_fixed",
        "Std risk_score_fixed",
    ]

    def fmt(k, v):
        if isinstance(v, (int, np.integer)):
            return f"{int(v)}"
        if isinstance(v, (float, np.floating)):
            if "Rate(" in k:
                return f"{pct(v):.2f}%"
            if np.isnan(v):
                return "n/a"
            # small metrics
            return f"{v:.3f}"
        return str(v)

    cell = []
    for k in rows:
        cell.append([fmt(k, m10[k]), fmt(k, m5[k])])

    table = ax2.table(
        cellText=cell,
        rowLabels=rows,
        colLabels=["10km", "5km"],
        loc="center",
        cellLoc="center",
        rowLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.1, 1.6)

    # Footnote (paper framing)
    fig.text(
        0.52, 0.03,
        "Note: pre-FDR counts indicate candidate anomalies; validated count may be 0 after BH-FDR correction.",
        ha="center",
        fontsize=10
    )

    fig.tight_layout(rect=[0, 0.06, 1, 1])

    plt.savefig(OUTPNG, dpi=600, bbox_inches="tight")
    plt.savefig(OUTPDF, bbox_inches="tight")
    plt.close()

    print("10km:", p10)
    print("5km :", p5)
    print("Saved:", OUTPNG)
    print("Saved:", OUTPDF)
    print(f"Tail plot uses z >= {Z_MIN_PLOT:g}, threshold shaded at z >= {Z_THR:g}")

if __name__ == "__main__":
    main()