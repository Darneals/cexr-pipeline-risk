# C:\projects\icvars-metaverse-pipeline-risk\scripts\diag_corridor_pvalues.py
# Purpose: Diagnose why p_fdr is constant (e.g., all 1.0) by inspecting p_raw/p_fdr/z_score quality.

import geopandas as gpd
import pandas as pd
from pathlib import Path


ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")
GEOJSON = ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson"

CANDIDATES = [
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon_reband.geojson",
]

FIELDS = ["p_raw", "p_fdr", "z_score"]


def pick_input() -> Path:
    for p in CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("None found:\n" + "\n".join(str(p) for p in CANDIDATES))


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def main():
    f = pick_input()
    print("Input:", f)

    g = gpd.read_file(f)
    print("Rows:", len(g))
    print("Columns (first 40):", list(g.columns)[:40])

    # Ensure columns exist
    for c in FIELDS:
        if c not in g.columns:
            print(f"\n[ERROR] Missing column '{c}'.")
            related = [x for x in g.columns if any(k in x.lower() for k in ["p", "q", "fdr", "z"])]
            print("Related columns:", related)
            return

    # Coerce numeric
    g["p_raw"] = to_num(g["p_raw"])
    g["p_fdr"] = to_num(g["p_fdr"])
    g["z_score"] = to_num(g["z_score"])

    # Basic stats
    print("\n--- Basic Stats ---")
    print("p_raw NaN:", int(g["p_raw"].isna().sum()))
    print("p_fdr NaN:", int(g["p_fdr"].isna().sum()))
    print("z_score NaN:", int(g["z_score"].isna().sum()))

    in01 = (g["p_raw"] >= 0) & (g["p_raw"] <= 1)
    print("p_raw in [0,1]:", int(in01.sum()), "/", len(g))

    if g["p_raw"].notna().any():
        print("p_raw min/max:", float(g["p_raw"].min()), float(g["p_raw"].max()))
        print("p_raw < 0.05:", int((g["p_raw"] < 0.05).sum()))
        print("p_raw < 0.10:", int((g["p_raw"] < 0.10).sum()))
    else:
        print("p_raw min/max: n/a (all NaN)")

    nunique_pfdr = int(g["p_fdr"].nunique(dropna=True))
    print("\np_fdr nunique (non-NaN):", nunique_pfdr)
    if nunique_pfdr > 0:
        uniques = g["p_fdr"].dropna().unique()
        print("p_fdr unique sample:", uniques[:10])

    if g["z_score"].notna().any():
        print("\nz_score min/max:", float(g["z_score"].min()), float(g["z_score"].max()))
        print("z_score >= 2:", int((g["z_score"] >= 2).sum()))
        print("z_score >= 3:", int((g["z_score"] >= 3).sum()))
    else:
        print("z_score min/max: n/a (all NaN)")

    # Combined conditions (what Fig 6 uses)
    validated = (g["p_fdr"] <= 0.05) & (g["z_score"] >= 2)
    print("\n--- Validated Corridor Count ---")
    print("validated (p_fdr<=0.05 & z>=2):", int(validated.sum()))

    # Useful quick sanity: show a few best z and their p-values
    print("\n--- Top 10 z_score rows: (z_score, p_raw, p_fdr) ---")
    top = g.sort_values("z_score", ascending=False).head(10)[["z_score", "p_raw", "p_fdr"]]
    print(top.to_string(index=False))

    print("\nDone.")


if __name__ == "__main__":
    main()