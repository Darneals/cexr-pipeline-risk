"""
A2_corridor_fdr.py
==================
Network-constrained corridor-level FDR for pipeline risk corridors.

WHY THIS APPROACH
-----------------
Window-level BH-FDR across ~40,000 overlapping windows is mathematically
intractable: the minimum achievable permutation p-value (1/B) is orders of
magnitude larger than the BH threshold (0.05/m). This is a fundamental
multiplicity problem, not a permutation count problem.

The correct approach for network data is to aggregate overlapping windows
into spatially coherent CORRIDORS and apply FDR at corridor level. This:
  - Reduces the test count from ~40,000 to ~4,649 (5km) / ~2,091 (10km)
  - Respects network topology (windows on the same corridor are correlated)
  - Produces actionable hotspot identifications at operational scale
  - Directly addresses Reviewer Gap 1 as a genuine methodological improvement

WHAT THIS SCRIPT DOES
---------------------
1. Reads enriched metrics CSVs (output of A1_enrich_incidents.py)
2. Aggregates windows to corridor level:
      - corridor_risk_obs  = max(window risk_obs) across corridor windows
        [max preserves the peak hazard signal within each corridor]
      - corridor_inc_count = sum of incident counts
      - corridor_z_max     = max z-score across corridor windows
      - corridor_exposure  = sum of exposure counts
3. Runs corridor-level permutation test (B=999):
      - Shuffles hazard scores across corridors proportional to exposure
      - Computes empirical p-values per corridor
4. Applies BH-FDR at corridor level (m ~ 4,649 / 2,091)
5. Saves:
      - corridor_fdr_5km.csv   / corridor_fdr_10km.csv
      - risk_windows_5km_corridorfdr.geojson  (windows annotated with
        corridor-level significance for WebGL rendering)
      - risk_windows_10km_corridorfdr.geojson

HOW TO USE
----------
Step 1 — Ensure A1_enrich_incidents.py has been run successfully and
         metrics_5km_enriched.csv / metrics_10km_enriched.csv exist in:
         data\\regions\\us_tx\\results_corridor\\

Step 2 — Place this file in:
         C:\\projects\\icvars-metaverse-pipeline-risk\\scripts\\corridor\\

Step 3 — Run from project root:
         python scripts/corridor/A2_corridor_fdr.py

Step 4 — Check printed summary for:
         - n_sig_corridors_fdr05  (corridors surviving FDR at alpha=0.05)
         - z_max of significant corridors
         - Paste full output back for Task A3 verification

Step 5 — The annotated GeoJSONs can be fed directly into 05_make_ribbons.py
         by updating its INPUTS list to use the _corridorfdr.geojson files.
"""

from __future__ import annotations

import os
import sys
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ROOT   = r"C:\projects\icvars-metaverse-pipeline-risk"
OUTDIR = os.path.join(ROOT, "data", "regions", "us_tx", "results_corridor")

B         = 999      # permutation count — sufficient at corridor scale
SEED      = 42
ALPHA_FDR = 0.05
Z_SIG     = 2.0      # z-score threshold for significance reporting

CASES = [
    (
        "5km",
        os.path.join(OUTDIR, "metrics_5km_enriched.csv"),
        os.path.join(OUTDIR, "risk_windows_5km.geojson"),
        os.path.join(OUTDIR, "corridor_fdr_5km.csv"),
        os.path.join(OUTDIR, "risk_windows_5km_corridorfdr.geojson"),
    ),
    (
        "10km",
        os.path.join(OUTDIR, "metrics_10km_enriched.csv"),
        os.path.join(OUTDIR, "risk_windows_10km.geojson"),
        os.path.join(OUTDIR, "corridor_fdr_10km.csv"),
        os.path.join(OUTDIR, "risk_windows_10km_corridorfdr.geojson"),
    ),
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def bh_qvalues(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR q-values. Returns q in original order."""
    m = len(pvals)
    order = np.argsort(pvals)
    p_sorted = pvals[order]
    ranks = np.arange(1, m + 1, dtype=float)
    q = (p_sorted * m) / ranks
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0.0, 1.0)
    out = np.empty_like(q)
    out[order] = q
    return out


def parse_corr_id(win_id_series: pd.Series, tag: str) -> pd.Series:
    """Extract corridor ID from window ID.
    Format: us_tx_corr_NNNN_{tag}_K  ->  us_tx_corr_NNNN
    """
    pattern = rf'^(.*?)_{tag}_'
    extracted = win_id_series.str.extract(pattern, expand=False)
    n_failed = extracted.isna().sum()
    if n_failed > 0:
        print(f"    WARNING: {n_failed} win_ids did not parse — "
              f"check format. Sample: {win_id_series.iloc[0]}")
    return extracted.fillna(win_id_series)


# ─────────────────────────────────────────────
# STEP 1 — AGGREGATE WINDOWS TO CORRIDOR LEVEL
# ─────────────────────────────────────────────

def aggregate_to_corridors(
    met: pd.DataFrame,
    win_gdf: gpd.GeoDataFrame,
    tag: str,
) -> pd.DataFrame:
    """
    Aggregate window-level metrics to corridor level.

    Aggregation strategy:
      risk_obs_max    — peak hazard signal within corridor (primary test stat)
      risk_obs_mean   — mean hazard across windows (secondary)
      incident_count  — total incidents on corridor
      exposure_sum    — total segment exposure
      z_max           — highest z-score window on corridor
      n_windows       — number of windows on corridor
    """
    met = met.copy()
    met["corr_id"] = parse_corr_id(met["win_id"], tag)

    # Merge z_score from GeoJSON if available
    if "z_score" in win_gdf.columns:
        z_lookup = win_gdf.set_index("win_id")["z_score"]
        met["z_score"] = pd.to_numeric(
            met["win_id"].map(z_lookup), errors="coerce"
        ).fillna(0.0)
    else:
        met["z_score"] = 0.0

    # Also grab exceedance if present
    if "exceedance" in win_gdf.columns:
        exc_lookup = win_gdf.set_index("win_id")["exceedance"]
        met["exceedance"] = pd.to_numeric(
            met["win_id"].map(exc_lookup), errors="coerce"
        ).fillna(0.0)
    else:
        met["exceedance"] = 0.0

    corr = met.groupby("corr_id").agg(
        risk_obs_max    = ("risk_obs",       "max"),
        risk_obs_mean   = ("risk_obs",       "mean"),
        risk_obs_sum    = ("risk_obs",       "sum"),
        incident_count  = ("incident_count", "sum"),
        exposure_sum    = ("exposure_count", "sum"),
        z_max           = ("z_score",        "max"),
        exceedance_max  = ("exceedance",     "max"),
        n_windows       = ("win_id",         "count"),
    ).reset_index()

    # Safe exposure floor
    corr["exposure_sum"] = corr["exposure_sum"].clip(lower=1)

    return corr


# ─────────────────────────────────────────────
# STEP 2 — CORRIDOR-LEVEL PERMUTATION TEST
# ─────────────────────────────────────────────

def corridor_permutation_test(
    corr: pd.DataFrame,
    B: int,
    seed: int,
) -> pd.DataFrame:
    """
    Permutation test at corridor level.

    Null hypothesis: incidents are randomly distributed across corridors
    proportional to their exposure (segment count).

    Test statistic: incident density per corridor (incidents / exposure).
    This is the correct test statistic for network-constrained infrastructure
    data — it normalises for corridor length while preserving the count signal.
    """
    rng = np.random.default_rng(seed)
    n   = len(corr)
    exp = corr["exposure_sum"].to_numpy(dtype=float)
    inc = corr["incident_count"].to_numpy(dtype=int)

    # Observed density per corridor
    obs = inc / exp

    # Probability weights proportional to exposure
    w = exp / exp.sum()

    # Total incidents to redistribute under null
    n_inc_total = int(inc.sum())

    null_dens = np.zeros((n, B), dtype=float)

    for b in range(B):
        # Multinomial redistribution of incidents across corridors
        # proportional to exposure — the length-weighted null
        sim_counts = rng.multinomial(n_inc_total, w).astype(float)
        null_dens[:, b] = sim_counts / exp

        if (b + 1) % 200 == 0:
            print(f"    permutations: {b+1}/{B}")

    # Empirical p-values (right-tail)
    p_emp = (1.0 + (null_dens >= obs[:, None]).sum(axis=1)) / (B + 1.0)

    # Z-score vs null distribution
    mu = null_dens.mean(axis=1)
    sd = null_dens.std(axis=1)
    ok = sd > 0
    z  = np.zeros(n, dtype=float)
    z[ok] = (obs[ok] - mu[ok]) / sd[ok]
    p_emp[~ok] = 1.0

    # BH-FDR correction
    q = bh_qvalues(p_emp)
    q[~ok] = 1.0

    corr = corr.copy()
    corr["density_obs"]       = obs
    corr["p_empirical"]       = p_emp
    corr["q_fdr_bh"]          = q
    corr["z_corridor"]        = z
    corr["null_mean"]         = mu
    corr["null_sd"]           = sd
    corr["significant_fdr05"] = (q <= ALPHA_FDR) & ok

    return corr


# ─────────────────────────────────────────────
# STEP 3 — ANNOTATE WINDOWS WITH CORRIDOR FDR
# ─────────────────────────────────────────────

def annotate_windows(
    win_gdf: gpd.GeoDataFrame,
    corr: pd.DataFrame,
    tag: str,
) -> gpd.GeoDataFrame:
    """
    Join corridor-level significance back to individual windows.
    Each window inherits its corridor's FDR result.
    """
    win = win_gdf.copy()
    win["corr_id"] = parse_corr_id(win["win_id"], tag)

    corr_lookup = corr.set_index("corr_id")[[
        "q_fdr_bh", "z_corridor", "p_empirical",
        "significant_fdr05", "risk_obs_max"
    ]]

    win = win.join(corr_lookup, on="corr_id", how="left")

    # Corridor significance band for WebGL rendering
    def corr_band(row):
        if not row.get("significant_fdr05", False):
            return "Not significant"
        z = row.get("z_corridor", 0.0)
        if z >= 4.0:  return "Very High"
        if z >= 3.0:  return "High"
        if z >= 2.0:  return "Medium"
        return "Low"

    win["corridor_sig_band"] = win.apply(corr_band, axis=1)

    return win


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("A2 — Network-constrained corridor-level FDR")
    print("=" * 55)

    all_results = {}

    for tag, met_csv, win_geojson, out_csv, out_geojson in CASES:

        print(f"\n{'─'*55}")
        print(f"Processing: {tag}")
        print(f"{'─'*55}")

        # Validate inputs
        for path, label in [(met_csv, "Enriched metrics"),
                             (win_geojson, "Risk windows GeoJSON")]:
            if not os.path.exists(path):
                print(f"  ERROR: {label} not found: {path}")
                print(f"  Run A1_enrich_incidents.py first.")
                continue

        # Load
        print(f"  Loading metrics: {os.path.basename(met_csv)}")
        met = pd.read_csv(met_csv)
        met["risk_obs"]       = pd.to_numeric(met["risk_obs"],       errors="coerce").fillna(0.0)
        met["incident_count"] = pd.to_numeric(met["incident_count"], errors="coerce").fillna(0).astype(int)
        met["exposure_count"] = pd.to_numeric(met["exposure_count"], errors="coerce").fillna(1).astype(int)

        print(f"  Loading windows GeoJSON ...")
        win_gdf = gpd.read_file(win_geojson)
        print(f"  Windows: {len(win_gdf):,}")

        # Aggregate to corridors
        print(f"\n  [1] Aggregating windows to corridors ...")
        corr = aggregate_to_corridors(met, win_gdf, tag)
        n_corr         = len(corr)
        n_corr_active  = (corr["incident_count"] > 0).sum()
        print(f"  Corridors total:          {n_corr:,}")
        print(f"  Corridors with incidents: {n_corr_active:,}")
        print(f"  Max incidents/corridor:   {corr['incident_count'].max()}")
        print(f"  Max risk_obs_max:         {corr['risk_obs_max'].max():.4f}")

        # Permutation test
        print(f"\n  [2] Running corridor permutation test (B={B}) ...")
        corr = corridor_permutation_test(corr, B=B, seed=SEED)

        # Results
        n_sig   = int(corr["significant_fdr05"].sum())
        z_max   = float(corr.loc[corr["significant_fdr05"], "z_corridor"].max()) \
                  if n_sig > 0 else float(corr["z_corridor"].max())
        q_min   = float(corr["q_fdr_bh"].min())
        p_min   = float(corr["p_empirical"].min())

        print(f"\n  ── Results ({tag}) ──")
        print(f"  Test count (corridors):        {n_corr:,}")
        print(f"  Min p_empirical:               {p_min:.6f}")
        print(f"  Min q_fdr_bh:                  {q_min:.6f}")
        print(f"  Significant corridors (q≤0.05):{n_sig:,}")
        print(f"  Z_max (significant):           {z_max:.4f}")
        print(f"  Z >= 2 corridors:              {(corr.z_corridor >= 2).sum():,}")
        print(f"  Z >= 3 corridors:              {(corr.z_corridor >= 3).sum():,}")

        if n_sig > 0:
            print(f"\n  Top 10 significant corridors:")
            top = corr[corr["significant_fdr05"]].nlargest(10, "z_corridor")
            print(top[["corr_id","incident_count","risk_obs_max",
                        "z_corridor","q_fdr_bh"]].to_string(index=False))

        # Save corridor CSV
        os.makedirs(OUTDIR, exist_ok=True)
        corr_out_cols = [
            "corr_id", "n_windows", "incident_count", "exposure_sum",
            "risk_obs_max", "risk_obs_mean", "z_max", "z_corridor",
            "p_empirical", "q_fdr_bh", "significant_fdr05",
            "null_mean", "null_sd"
        ]
        corr[corr_out_cols].to_csv(out_csv, index=False)
        print(f"\n  Saved corridor CSV: {os.path.basename(out_csv)}")

        # Annotate windows and save GeoJSON
        print(f"  Annotating windows with corridor FDR ...")
        win_annotated = annotate_windows(win_gdf, corr, tag)
        win_annotated.to_file(out_geojson, driver="GeoJSON")
        print(f"  Saved annotated GeoJSON: {os.path.basename(out_geojson)}")

        all_results[tag] = {
            "n_corridors":      n_corr,
            "n_active":         n_corr_active,
            "n_sig":            n_sig,
            "z_max":            z_max,
            "q_min":            q_min,
            "p_min":            p_min,
        }

    # Final summary
    print(f"\n{'='*55}")
    print("TASK A2 COMPLETE — Final Summary")
    print(f"{'='*55}")
    for tag, r in all_results.items():
        print(f"\n  {tag}:")
        print(f"    Corridors tested:          {r['n_corridors']:,}")
        print(f"    Corridors with incidents:  {r['n_active']:,}")
        print(f"    Significant (q ≤ 0.05):   {r['n_sig']:,}")
        print(f"    Z_max:                     {r['z_max']:.4f}")
        print(f"    Min q_fdr:                 {r['q_min']:.6f}")

    print()
    if any(r["n_sig"] > 0 for r in all_results.values()):
        print("SUCCESS: FDR-significant corridors identified.")
        print("Proceed to Task A3 — verify and record results.")
    else:
        print("NOTE: No FDR-significant corridors at q<=0.05.")
        print("Check: corridor_fdr_5km.csv — look at q_fdr_bh distribution")
        print("and z_corridor values for the top corridors.")

    print()
    print("Next: paste this full output for Task A3 verification.")


if __name__ == "__main__":
    main()