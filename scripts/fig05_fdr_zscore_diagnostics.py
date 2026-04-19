import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")
OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

# Prefer 10km (more stable)
CANDIDATES = [
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon_reband.geojson",
]

OUTPNG = OUTDIR / "fig05_fdr_zscore_diagnostics.png"
OUTPDF = OUTDIR / "fig05_fdr_zscore_diagnostics.pdf"


def load_props(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for f in data.get("features", []):
        p = f.get("properties") or {}
        rows.append(p)
    return pd.DataFrame(rows)


def pick_input() -> Path:
    for p in CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Could not find any of:\n" + "\n".join(str(p) for p in CANDIDATES)
    )


def main():
    src = pick_input()
    df = load_props(src)

    # Required fields
    for col in ["p_raw", "p_fdr", "z_score"]:
        if col not in df.columns:
            raise KeyError(f"Missing column '{col}' in {src.name}. Found: {list(df.columns)[:30]} ...")

    p_raw = pd.to_numeric(df["p_raw"], errors="coerce").dropna().clip(0, 1)
    p_fdr = pd.to_numeric(df["p_fdr"], errors="coerce").dropna().clip(0, 1)
    z = pd.to_numeric(df["z_score"], errors="coerce").dropna()

    fig = plt.figure(figsize=(12, 4))

    # Panel A: p_raw histogram
    ax1 = fig.add_subplot(1, 3, 1)
    ax1.hist(p_raw.values, bins=30, alpha=0.8)
    ax1.set_xlabel("p_raw")
    ax1.set_ylabel("Count")
    ax1.set_title("A) Raw p-value distribution")

    # Panel B: p_raw vs p_fdr
    ax2 = fig.add_subplot(1, 3, 2)
    n = min(len(p_raw), len(p_fdr))
    ax2.scatter(p_raw.values[:n], p_fdr.values[:n], s=6, alpha=0.5)
    ax2.plot([0, 1], [0, 1], linewidth=1)
    ax2.set_xlabel("p_raw")
    ax2.set_ylabel("p_fdr")
    ax2.set_title("B) FDR adjustment effect")

    # Panel C: z_score histogram (clipped for readability)
    ax3 = fig.add_subplot(1, 3, 3)
    z_clip = z.clip(lower=-3, upper=8)
    ax3.hist(z_clip.values, bins=30, alpha=0.8)
    ax3.set_xlabel("z_score (clipped to [-3, 8])")
    ax3.set_ylabel("Count")
    ax3.set_title("C) z-score distribution")

    fig.tight_layout()

    plt.savefig(OUTPNG, dpi=600, bbox_inches="tight")
    plt.savefig(OUTPDF, bbox_inches="tight")
    plt.close()

    print("Input:", src)
    print("Saved:", OUTPNG)
    print("Saved:", OUTPDF)


if __name__ == "__main__":
    main()