import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")

INFILE = ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson"
OUTFILE = ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_pfdr_fixed.geojson"

Q = 0.05  # target FDR level (used only for reporting counts)


def bh_qvalues(p: np.ndarray) -> np.ndarray:
    """
    Benjamini–Hochberg FDR adjusted p-values (q-values).
    Returns q-values in the original order.
    """
    p = p.astype(float)
    m = p.size

    order = np.argsort(p)
    p_sorted = p[order]

    ranks = np.arange(1, m + 1, dtype=float)
    q_sorted = (p_sorted * m) / ranks

    # Enforce monotonicity (non-increasing when moving from small to large p)
    q_sorted = np.minimum.accumulate(q_sorted[::-1])[::-1]
    q_sorted = np.clip(q_sorted, 0.0, 1.0)

    q = np.empty_like(q_sorted)
    q[order] = q_sorted
    return q


def main():
    if not INFILE.exists():
        raise FileNotFoundError(INFILE)

    g = gpd.read_file(INFILE)

    if "p_raw" not in g.columns:
        raise KeyError(f"Missing p_raw in {INFILE.name}. Found: {list(g.columns)}")

    p_raw = pd.to_numeric(g["p_raw"], errors="coerce").to_numpy()
    ok = np.isfinite(p_raw) & (p_raw >= 0) & (p_raw <= 1)

    # Default to 1.0, then fill valid entries with BH q-values
    qvals = np.ones(len(g), dtype=float)
    qvals[ok] = bh_qvalues(p_raw[ok])

    g["p_fdr"] = qvals

    # Quick reporting
    z = pd.to_numeric(g.get("z_score"), errors="coerce")
    validated = (g["p_fdr"] <= Q) & (z >= 2)

    print("Rows:", len(g))
    print("p_raw min (ok):", float(np.nanmin(p_raw[ok])) if ok.any() else None)
    print("p_fdr nunique:", int(pd.Series(g["p_fdr"]).nunique()))
    print("Validated (p_fdr<=0.05 & z>=2):", int(validated.sum()))

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(OUTFILE, driver="GeoJSON")
    print("Saved:", OUTFILE)


if __name__ == "__main__":
    main()