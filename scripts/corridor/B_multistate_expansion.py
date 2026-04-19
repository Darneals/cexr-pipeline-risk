"""
B_multistate_expansion.py
=========================
Phase B — Multi-state expansion: Louisiana (LA) and Oklahoma (OK)

WHAT THIS SCRIPT DOES
---------------------
Runs the complete pipeline for each companion state in sequence:

  B1. Identify state geometry and UTM projection
  B2. Clip national pipeline shapefile to state boundary
  B3. Filter and export incidents for state
  B4. Segment pipelines into 5km and 10km corridor windows
  B5. Compute enriched multivariate metrics (reuses A1 scoring)
  B6. Run corridor-level permutation FDR (reuses A2 approach)
  B7. Save all outputs mirroring the TX folder structure

OUTPUT STRUCTURE (created automatically)
-----------------------------------------
  data/regions/us_la/results_corridor/
      corridors.gpkg
      windows_5km.gpkg
      windows_10km.gpkg
      metrics_5km_enriched.csv
      metrics_10km_enriched.csv
      corridor_fdr_5km.csv
      corridor_fdr_10km.csv
      risk_windows_5km_corridorfdr.geojson
      risk_windows_10km_corridorfdr.geojson

  data/regions/us_ok/  (same structure)

HOW TO USE
----------
Step 1 — Place this file in:
    C:\\projects\\icvars-metaverse-pipeline-risk\\scripts\\corridor\\

Step 2 — Run from project root:
    python scripts/corridor/B_multistate_expansion.py

Step 3 — Takes approximately 10-20 minutes total for both states.
         Paste the full terminal output for Task B4/B5 verification.

REQUIREMENTS
------------
Ensure A1_enrich_incidents.py has been run for TX first (confirms
the PHMSA Excel file path is correct).
"""

from __future__ import annotations

import os
import sys
import math
import json
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import LineString, box
from shapely.ops import substring

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ROOT = r"C:\projects\icvars-metaverse-pipeline-risk"

PIPELINE_SHP  = os.path.join(ROOT, "data", "raw",
    "Natural_Gas_Interstate_and_Intrastate_Pipelines",
    "Natural_Gas_Interstate_and_Intrastate_Pipelines.shp")

STATES_SHP    = os.path.join(ROOT, "data", "raw",
    "cb_2018_us_state_500k", "cb_2018_us_state_500k.shp")

INCIDENT_XLSX = os.path.join(ROOT, "data", "raw",
    "gtggungs2010toPresent.xlsx")
INCIDENT_SHEET = "gtggungs2010toPresent"

# Target states for expansion
TARGET_STATES = ["LA", "OK"]

# Corridor window sizes
WIN_SIZES = [("5km", 5_000), ("10km", 10_000)]
STEP_M    = 1_000      # sliding step along corridor (metres)

# Permutation settings
B_PERM    = 999
SEED      = 42
ALPHA_FDR = 0.05

# Spatial buffer for metric join (metres)
BUFFER_M  = 2_000

# Reference year for pipe age calculation
REFERENCE_YEAR = 2024
MAX_PIPE_AGE   = 80

# Cause weights (identical to A1)
CAUSE_WEIGHTS = {
    "CORROSION FAILURE":                 1.0,
    "EXCAVATION DAMAGE":                 0.95,
    "MATERIAL FAILURE OF PIPE OR WELD":  0.85,
    "NATURAL FORCE DAMAGE":              0.75,
    "INCORRECT OPERATION":               0.70,
    "OTHER OUTSIDE FORCE DAMAGE":        0.65,
    "EQUIPMENT FAILURE":                 0.55,
    "OTHER INCIDENT CAUSE":              0.50,
}


# ─────────────────────────────────────────────
# HELPERS — GEOMETRY
# ─────────────────────────────────────────────

def utm_epsg_for_state(state_gdf: gpd.GeoDataFrame) -> int:
    """Compute UTM EPSG from state centroid longitude."""
    centroid = state_gdf.to_crs("EPSG:4326").geometry.iloc[0].centroid
    zone = int((centroid.x + 180) // 6) + 1
    return 32600 + zone   # Northern Hemisphere


def cut_linestring(ls: LineString, start_m: float, end_m: float) -> LineString | None:
    start_m = max(0.0, start_m)
    end_m   = min(ls.length, end_m)
    if end_m <= start_m:
        return None
    n = max(2, int(math.ceil((end_m - start_m) / 50.0)))
    pts = []
    for i in range(n):
        d = start_m + (end_m - start_m) * (i / (n - 1))
        p = ls.interpolate(d)
        pts.append((p.x, p.y))
    return LineString(pts) if len(pts) >= 2 else None


def make_windows(corridors: gpd.GeoDataFrame,
                 win_len_m: int, tag: str,
                 state_tag: str) -> gpd.GeoDataFrame:
    rows = []
    for _, r in corridors.iterrows():
        geom    = r.geometry
        if geom is None:
            continue
        corr_id = r["corr_id"]
        L       = geom.length
        if L < win_len_m:
            continue
        k = 0
        for start in range(0, int(L - win_len_m) + 1, STEP_M):
            end = start + win_len_m
            seg = cut_linestring(geom, start, end)
            if seg is None:
                continue
            rows.append({
                "corr_id":   corr_id,
                "win_id":    f"{state_tag}_corr_{corr_id}_{tag}_{k}",
                "win_len_m": win_len_m,
                "start_m":   start,
                "end_m":     end,
                "geometry":  seg,
            })
            k += 1
    return gpd.GeoDataFrame(rows, crs=corridors.crs)


# ─────────────────────────────────────────────
# HELPERS — SCORING (mirrors A1)
# ─────────────────────────────────────────────

def _safe_float(val, default=0.0) -> float:
    try:
        v = float(val)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _parse_year(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip().upper()
    if s in ("UNKNOWN", "UNK", "", "NAN", "NONE"):
        return None
    try:
        y = int(float(s))
        if 1900 <= y <= REFERENCE_YEAR:
            return float(y)
    except (ValueError, TypeError):
        pass
    return None


def _minmax(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mn) / (mx - mn)


def compute_hazard_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_fatal"]    = df["FATAL"].fillna(0).apply(_safe_float)
    df["_injure"]   = df["INJURE"].fillna(0).apply(_safe_float)
    df["_cost"]     = df["TOTAL_COST_CURRENT"].fillna(0).apply(_safe_float)
    df["_log_cost"] = np.log1p(df["_cost"])

    severity_raw        = df["_fatal"]*3.0 + df["_injure"]*1.0 + _minmax(df["_log_cost"])
    df["score_severity"] = _minmax(severity_raw)

    cause_clean         = df["CAUSE"].astype(str).str.strip().str.upper()
    df["score_cause"]   = cause_clean.map(
        {k.upper(): v for k, v in CAUSE_WEIGHTS.items()}
    ).fillna(0.50)

    years    = df["INSTALLATION_YEAR"].apply(_parse_year)
    age_raw  = years.apply(
        lambda y: float(REFERENCE_YEAR - y) if y is not None
                  else float(MAX_PIPE_AGE * 0.6)
    )
    age_norm = (age_raw.clip(0, MAX_PIPE_AGE) / MAX_PIPE_AGE)

    median_diam          = df["PIPE_DIAMETER"].median()
    if pd.isna(median_diam):
        median_diam = 12.75
    diam_filled          = df["PIPE_DIAMETER"].fillna(median_diam).apply(_safe_float)
    diam_norm            = _minmax(pd.Series(diam_filled))
    df["score_vulnerability"] = 0.6 * age_norm + 0.4 * diam_norm

    df["hazard_score"] = (
        0.40 * df["score_cause"] +
        0.35 * df["score_severity"] +
        0.25 * df["score_vulnerability"]
    )
    return df


# ─────────────────────────────────────────────
# HELPERS — FDR (mirrors A2)
# ─────────────────────────────────────────────

def bh_qvalues(pvals: np.ndarray) -> np.ndarray:
    m     = len(pvals)
    order = np.argsort(pvals)
    p_s   = pvals[order]
    q     = (p_s * m) / np.arange(1, m + 1, dtype=float)
    q     = np.minimum.accumulate(q[::-1])[::-1]
    q     = np.clip(q, 0.0, 1.0)
    out   = np.empty_like(q)
    out[order] = q
    return out


def parse_corr_id(win_id_series: pd.Series, tag: str) -> pd.Series:
    pattern   = rf'^(.*?)_{tag}_'
    extracted = win_id_series.str.extract(pattern, expand=False)
    return extracted.fillna(win_id_series)


def run_corridor_fdr(met: pd.DataFrame,
                     win_gdf: gpd.GeoDataFrame,
                     tag: str,
                     state_tag: str,
                     b: int, seed: int) -> tuple[pd.DataFrame, gpd.GeoDataFrame]:

    met = met.copy()
    met["corr_id"] = parse_corr_id(met["win_id"], tag)

    # Aggregate to corridor level
    corr = met.groupby("corr_id").agg(
        risk_obs_max   = ("risk_obs",       "max"),
        risk_obs_sum   = ("risk_obs",       "sum"),
        incident_count = ("incident_count", "sum"),
        exposure_sum   = ("exposure_count", "sum"),
        n_windows      = ("win_id",         "count"),
    ).reset_index()
    corr["exposure_sum"] = corr["exposure_sum"].clip(lower=1)

    n   = len(corr)
    exp = corr["exposure_sum"].to_numpy(float)
    inc = corr["incident_count"].to_numpy(int)
    obs = inc / exp
    w   = exp / exp.sum()
    n_inc_total = int(inc.sum())

    rng       = np.random.default_rng(seed)
    null_dens = np.zeros((n, b), dtype=float)
    for bi in range(b):
        sim         = rng.multinomial(max(1, n_inc_total), w).astype(float)
        null_dens[:, bi] = sim / exp
        if (bi + 1) % 200 == 0:
            print(f"    permutations: {bi+1}/{b}")

    p_emp = (1.0 + (null_dens >= obs[:, None]).sum(axis=1)) / (b + 1.0)
    mu    = null_dens.mean(axis=1)
    sd    = null_dens.std(axis=1)
    ok    = sd > 0
    z     = np.zeros(n, dtype=float)
    z[ok] = (obs[ok] - mu[ok]) / sd[ok]
    p_emp[~ok] = 1.0
    q     = bh_qvalues(p_emp)
    q[~ok] = 1.0

    corr["density_obs"]       = obs
    corr["p_empirical"]       = p_emp
    corr["q_fdr_bh"]          = q
    corr["z_corridor"]        = z
    corr["null_mean"]         = mu
    corr["null_sd"]           = sd
    corr["significant_fdr05"] = (q <= ALPHA_FDR) & ok

    # Annotate windows
    win = win_gdf.copy()
    win["corr_id"] = parse_corr_id(win["win_id"], tag)
    lookup = corr.set_index("corr_id")[[
        "q_fdr_bh", "z_corridor", "p_empirical", "significant_fdr05", "risk_obs_max"
    ]]
    win = win.join(lookup, on="corr_id", how="left")

    def corr_band(row):
        if not row.get("significant_fdr05", False):
            return "Not significant"
        z_val = row.get("z_corridor", 0.0)
        if z_val >= 4.0: return "Very High"
        if z_val >= 3.0: return "High"
        if z_val >= 2.0: return "Medium"
        return "Low"

    win["corridor_sig_band"] = win.apply(corr_band, axis=1)

    return corr, win


# ─────────────────────────────────────────────
# MAIN PIPELINE PER STATE
# ─────────────────────────────────────────────

def process_state(state: str,
                  pipes_national: gpd.GeoDataFrame,
                  states_gdf: gpd.GeoDataFrame,
                  inc_df: pd.DataFrame) -> dict:

    state_tag = f"us_{state.lower()}"
    out_dir   = os.path.join(ROOT, "data", "regions", state_tag, "results_corridor")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  STATE: {state}  ({state_tag})")
    print(f"{'='*60}")

    # ── Step B1: State geometry + UTM ─────────────────────────────
    print(f"\n[B1] State geometry and UTM projection")
    state_poly = states_gdf[states_gdf["STUSPS"] == state].copy()
    if len(state_poly) == 0:
        print(f"  ERROR: State {state} not found in states shapefile.")
        return {}

    utm_epsg = utm_epsg_for_state(state_poly)
    print(f"  UTM EPSG: {utm_epsg}")

    state_poly_utm = state_poly.to_crs(epsg=utm_epsg)

    # ── Step B2: Clip pipelines ────────────────────────────────────
    print(f"\n[B2] Clipping pipelines to {state}")
    pipes_4326  = pipes_national.to_crs("EPSG:4326")
    state_4326  = state_poly.to_crs("EPSG:4326")
    pipes_clip  = gpd.clip(pipes_4326, state_4326)
    pipes_utm   = pipes_clip.to_crs(epsg=utm_epsg)
    print(f"  Clipped pipeline segments: {len(pipes_utm):,}")

    if len(pipes_utm) == 0:
        print(f"  ERROR: No pipelines found for {state}. Check shapefile coverage.")
        return {}

    # Build corridors GeoPackage (one row per pipeline segment = one corridor)
    corridors = pipes_utm[["geometry"]].copy().reset_index(drop=True)
    corridors["corr_id"] = corridors.index.astype(str)
    corr_gpkg = os.path.join(out_dir, "corridors.gpkg")
    corridors.to_file(corr_gpkg, layer="corridors", driver="GPKG")
    print(f"  Saved corridors: {corr_gpkg}")

    # ── Step B3: Filter incidents ──────────────────────────────────
    print(f"\n[B3] Filtering incidents for {state}")
    inc_state = inc_df[
        inc_df["ONSHORE_STATE_ABBREVIATION"].astype(str).str.strip() == state
    ].dropna(subset=["LOCATION_LATITUDE", "LOCATION_LONGITUDE"]).copy()
    inc_state = inc_state.reset_index(drop=True)
    print(f"  Incidents: {len(inc_state)}")

    # Score incidents
    inc_state    = compute_hazard_scores(inc_state)
    inc_gdf      = gpd.GeoDataFrame(
        inc_state,
        geometry=gpd.points_from_xy(
            inc_state["LOCATION_LONGITUDE"],
            inc_state["LOCATION_LATITUDE"]
        ),
        crs="EPSG:4326"
    ).to_crs(epsg=utm_epsg)
    print(f"  Mean hazard score: {inc_state['hazard_score'].mean():.4f}")

    # ── Step B4: Build corridor windows ───────────────────────────
    print(f"\n[B4] Building corridor windows")
    all_results = {}

    for tag, win_len_m in WIN_SIZES:
        print(f"\n  --- {tag} ---")

        windows = make_windows(corridors, win_len_m, tag, state_tag)
        print(f"  Windows created: {len(windows):,}")

        if len(windows) == 0:
            print(f"  WARNING: No windows created for {tag}. Skipping.")
            continue

        win_gpkg = os.path.join(out_dir, f"windows_{tag}.gpkg")
        windows.to_file(win_gpkg, layer="windows", driver="GPKG")
        print(f"  Saved: {win_gpkg}")

        # ── Step B5: Enriched metrics ──────────────────────────────
        print(f"  Computing enriched metrics ...")

        # Buffer windows for spatial join
        win_buf = windows.copy()
        win_buf["geometry"] = win_buf.geometry.buffer(BUFFER_M)

        inc_cols = ["geometry", "hazard_score"]
        joined   = gpd.sjoin(
            inc_gdf[inc_cols],
            win_buf[["win_id", "geometry"]],
            predicate="within",
            how="inner"
        )

        # Aggregate hazard per window
        agg = joined.groupby("win_id").agg(
            incident_count = ("hazard_score", "count"),
            sum_hazard     = ("hazard_score", "sum"),
        ).reset_index()

        all_win_ids = windows["win_id"].tolist()
        met = pd.DataFrame({"win_id": all_win_ids})
        met = met.merge(agg, on="win_id", how="left")
        met["incident_count"] = met["incident_count"].fillna(0).astype(int)
        met["sum_hazard"]     = met["sum_hazard"].fillna(0.0)

        # Exposure = number of pipeline segments intersecting buffered window
        seg_for_exp = corridors[["corr_id", "geometry"]].copy()
        exp_join    = gpd.sjoin(
            seg_for_exp,
            win_buf[["win_id", "geometry"]],
            predicate="intersects",
            how="inner"
        )
        exposure    = exp_join.groupby("win_id").size().rename("exposure_count")
        met         = met.merge(exposure, on="win_id", how="left")
        met["exposure_count"] = met["exposure_count"].fillna(1).astype(int)

        # risk_obs = sum_hazard / exposure
        met["risk_obs"] = met["sum_hazard"] / met["exposure_count"].clip(lower=1)

        n_active = (met["risk_obs"] > 0).sum()
        print(f"  Windows with risk > 0: {n_active:,} / {len(met):,}")
        print(f"  Max risk_obs: {met['risk_obs'].max():.4f}")

        met_csv = os.path.join(out_dir, f"metrics_{tag}_enriched.csv")
        met[["win_id", "exposure_count", "incident_count",
             "risk_obs", "sum_hazard"]].to_csv(met_csv, index=False)
        print(f"  Saved metrics: {met_csv}")

        # ── Step B6: Corridor-level FDR ────────────────────────────
        print(f"  Running corridor FDR (B={B_PERM}) ...")

        # Need GeoJSON for annotate step — save windows temporarily
        win_geojson = os.path.join(out_dir, f"risk_windows_{tag}_base.geojson")
        windows.to_crs("EPSG:4326").to_file(win_geojson, driver="GeoJSON")

        win_gdf_4326 = gpd.read_file(win_geojson)

        corr_df, win_annotated = run_corridor_fdr(
            met, win_gdf_4326, tag, state_tag, B_PERM, SEED
        )

        n_sig  = int(corr_df["significant_fdr05"].sum())
        z_max  = float(corr_df.loc[corr_df["significant_fdr05"], "z_corridor"].max()) \
                 if n_sig > 0 else float(corr_df["z_corridor"].max())
        q_min  = float(corr_df["q_fdr_bh"].min())

        print(f"\n  ── FDR Results ({state} {tag}) ──")
        print(f"  Corridors tested:          {len(corr_df):,}")
        print(f"  Corridors with incidents:  {(corr_df.incident_count>0).sum():,}")
        print(f"  Significant (q ≤ 0.05):   {n_sig:,}")
        print(f"  Z_max:                     {z_max:.4f}")
        print(f"  Min q_fdr:                 {q_min:.6f}")
        print(f"  Z >= 2:                    {(corr_df.z_corridor>=2).sum():,}")
        print(f"  Z >= 3:                    {(corr_df.z_corridor>=3).sum():,}")

        if n_sig > 0:
            print(f"\n  Top 5 significant corridors:")
            top = corr_df[corr_df["significant_fdr05"]].nlargest(5, "z_corridor")
            print(top[["corr_id","incident_count","z_corridor","q_fdr_bh"]].to_string(index=False))

        # Save outputs
        corr_csv = os.path.join(out_dir, f"corridor_fdr_{tag}.csv")
        corr_df.to_csv(corr_csv, index=False)

        out_geojson = os.path.join(out_dir, f"risk_windows_{tag}_corridorfdr.geojson")
        win_annotated.to_file(out_geojson, driver="GeoJSON")
        print(f"\n  Saved: {corr_csv}")
        print(f"  Saved: {out_geojson}")

        all_results[tag] = {
            "n_corridors": len(corr_df),
            "n_active":    int((corr_df.incident_count > 0).sum()),
            "n_sig":       n_sig,
            "z_max":       z_max,
            "q_min":       q_min,
            "n_incidents": int(inc_state['hazard_score'].count()),
        }

    return all_results


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("B — Multi-state pipeline expansion: LA + OK")
    print("=" * 60)

    # Validate paths
    for path, label in [
        (PIPELINE_SHP,  "Pipeline shapefile"),
        (STATES_SHP,    "States shapefile"),
        (INCIDENT_XLSX, "Incident Excel"),
    ]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found:\n  {path}")
            sys.exit(1)

    # Load shared datasets once
    print("\nLoading national pipeline shapefile ...")
    pipes_national = gpd.read_file(PIPELINE_SHP)
    print(f"  Pipeline rows: {len(pipes_national):,}  CRS: {pipes_national.crs}")

    print("Loading state boundaries ...")
    states_gdf = gpd.read_file(STATES_SHP)

    print("Loading incident data ...")
    cols_needed = [
        "ONSHORE_STATE_ABBREVIATION", "LOCATION_LATITUDE", "LOCATION_LONGITUDE",
        "CAUSE", "PIPE_DIAMETER", "INSTALLATION_YEAR",
        "TOTAL_COST_CURRENT", "FATAL", "INJURE", "IYEAR",
    ]
    inc_df = pd.read_excel(INCIDENT_XLSX, sheet_name=INCIDENT_SHEET,
                           usecols=cols_needed)
    print(f"  Total incident rows: {len(inc_df):,}")

    # Process each state
    summary = {}
    for state in TARGET_STATES:
        results = process_state(state, pipes_national, states_gdf, inc_df)
        if results:
            summary[state] = results

    # Final cross-state summary
    print(f"\n{'='*60}")
    print("PHASE B COMPLETE — Cross-state Summary")
    print(f"{'='*60}")
    print(f"\n{'State':<6} {'Res':<6} {'Corridors':>10} {'Active':>8} "
          f"{'Incidents':>10} {'Sig q≤.05':>10} {'Z_max':>8} {'q_min':>8}")
    print("-" * 70)

    for state, res in summary.items():
        for tag, r in res.items():
            print(f"{state:<6} {tag:<6} {r['n_corridors']:>10,} "
                  f"{r['n_active']:>8,} {r['n_incidents']:>10,} "
                  f"{r['n_sig']:>10,} {r['z_max']:>8.2f} {r['q_min']:>8.4f}")

    print()
    print("Next: paste full output for cross-state comparison (Task B5).")
    print("Then proceed to Phase C — user evaluation instrument.")


if __name__ == "__main__":
    main()