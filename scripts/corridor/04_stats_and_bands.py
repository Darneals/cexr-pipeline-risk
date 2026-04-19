import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd

# -------------------------
# Paths / constants
# -------------------------
ROOT = r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx"
OUTDIR = os.path.join(ROOT, "results_corridor")
PROCESSED = os.path.join(ROOT, "processed")

BUFFER_M = 2000

# Permutations
B = 399          # fast test run; change to 999 for final paper
Q_FDR = 0.05

SEGMENTS_FILE = os.path.join(PROCESSED, "pipelines_tx_segment_risk_fixed_minlen.geojson")
EXPOSURE_FILE = os.path.join(PROCESSED, "pipeline_exposure.geojson")  # only used to ensure same environment; not used directly here

CASES = [
    ("10km", os.path.join(OUTDIR, "windows_10km.gpkg"), os.path.join(OUTDIR, "metrics_10km_enriched.csv")),
    ("5km",  os.path.join(OUTDIR, "windows_5km.gpkg"),  os.path.join(OUTDIR, "metrics_5km_enriched.csv")),
]


# -------------------------
# Helpers
# -------------------------
def bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR q-values."""
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    q = ranked * n / (np.arange(n) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.clip(q, 0, 1)
    return out


def require_exists(path: str, label: str):
    if not os.path.exists(path):
        print(f"ERROR: Missing {label}: {path}")
        sys.exit(1)


# -------------------------
# Main
# -------------------------
def main():
    require_exists(SEGMENTS_FILE, "SEGMENTS_FILE")
    require_exists(OUTDIR, "OUTDIR")

    # Read segment lines with incident_count (used for permutation shuffling)
    seg = gpd.read_file(SEGMENTS_FILE)
    if "incident_count" not in seg.columns:
        print("ERROR: incident_count not found in SEGMENTS_FILE")
        sys.exit(1)

    seg = seg[seg.geometry.notna()].copy()
    seg = seg[["incident_count", "geometry"]].copy()
    seg = seg.reset_index(drop=True)

    # weights to shuffle across segments
    weights = seg["incident_count"].to_numpy(dtype=int)
    rng = np.random.default_rng(42)

    for tag, win_gpkg, metrics_csv in CASES:
        require_exists(win_gpkg, f"windows ({tag})")
        require_exists(metrics_csv, f"metrics ({tag})")

        print(f"\n--- Running stats for {tag} ---")
        print("Windows:", win_gpkg)
        print("Metrics:", metrics_csv)

        # Read windows
        w = gpd.read_file(win_gpkg, layer="windows")
        w = w[w.geometry.notna()].copy()

        # Read metrics
        met = pd.read_csv(metrics_csv)
        needed = {"win_id", "exposure_count", "risk_obs"}
        if not needed.issubset(set(met.columns)):
            print("ERROR: metrics CSV missing required columns. Need:", needed)
            print("Found:", list(met.columns))
            sys.exit(1)

        # Align metrics to windows order
        win_ids = w["win_id"].tolist()
        met = met.set_index("win_id").reindex(win_ids)

        # Fill missing metrics with zeros
        met["exposure_count"] = met["exposure_count"].fillna(0).astype(int)
        met["incident_count"] = met.get("incident_count", 0)
        met["incident_count"] = pd.Series(met["incident_count"]).fillna(0).astype(int)
        met["risk_obs"] = met["risk_obs"].fillna(0.0).astype(float)

        # --- critical: mark "no data" windows BEFORE clipping exposure ---
        exposure_raw = met["exposure_count"].to_numpy(dtype=int)
        no_data = exposure_raw <= 0

        # Safe exposure for math (avoid divide-by-zero). Keep raw separately for output.
        exposure = np.where(no_data, 1, exposure_raw).astype(float)
        obs = met["risk_obs"].to_numpy(dtype=float)

        # Build window buffers
        wbuf = w[["win_id", "geometry"]].copy()
        wbuf["geometry"] = wbuf.geometry.buffer(BUFFER_M)

        # Spatial join: which segments intersect which window buffer
        seg_for_join = seg.reset_index().rename(columns={"index": "seg_i"})
        join = gpd.sjoin(seg_for_join, wbuf, predicate="intersects", how="inner")

        if "win_id" not in join.columns or "seg_i" not in join.columns:
            print("ERROR: join missing win_id or seg_i. Columns:", list(join.columns))
            sys.exit(1)

        # Map win_id -> numpy array of segment indices
        win_to_seg = join.groupby("win_id")["seg_i"].apply(lambda s: s.to_numpy()).to_dict()

        # Pre-allocate permutation risk matrix
        nwin = len(win_ids)
        perm_risk = np.zeros((nwin, B), dtype=float)

        # Index mapping for fast write
        idx = {wid: i for i, wid in enumerate(win_ids)}

        # Permute
        for b in range(B):
            shuffled = weights.copy()
            rng.shuffle(shuffled)

            inc_perm = np.zeros(nwin, dtype=int)
            for wid, seg_idx in win_to_seg.items():
                i = idx.get(wid)
                if i is None:
                    continue
                inc_perm[i] = int(shuffled[seg_idx].sum())

            perm_risk[:, b] = inc_perm / exposure

            if (b + 1) % 50 == 0:
                print(f"  permutations: {b+1}/{B}")

        # -------------------------
        # p-values (right-tail)
        # -------------------------
        p = (1.0 + (perm_risk >= obs[:, None]).sum(axis=1)) / (B + 1.0)

        # -------------------------
        # z-score vs permutation (PATCHED)
        # + exceedance
        # + ok mask for degenerate nulls
        # -------------------------
        mu = perm_risk.mean(axis=1)
        sd = perm_risk.std(axis=1)

        exceedance = obs - mu

        # If sd == 0, permutation distribution is degenerate (no variability)
        # In that case: z is not meaningful. Force z=0, and treat as not significant.
        z = np.zeros_like(obs, dtype=float)
        ok = sd > 0
        z[ok] = (obs[ok] - mu[ok]) / sd[ok]

        # Force p-values to be consistent with degenerate nulls:
        # if sd==0, we do not allow any "significance" evidence
        p[~ok] = 1.0

        p_fdr = bh_fdr(p)
        p_fdr[~ok] = 1.0

        # -------------------------
        # render score 0..1: percentile vs null
        # -------------------------
        pct = (perm_risk < obs[:, None]).mean(axis=1)
        risk_score = np.clip(pct, 0, 1)

        # Force no-data windows to 0 score (explicit)
        risk_score[no_data] = 0.0

        # -------------------------
        # Story band (metaverse/UI)
        # Fix: DO NOT let zeros become High.
        # -------------------------
        VERY_HIGH_PCT = 0.01  # top 1% (of positive scores)
        HIGH_PCT = 0.05       # top 5% (of positive scores)

        score = np.nan_to_num(risk_score.copy(), nan=0.0, posinf=1.0, neginf=0.0)

        story_band = np.full(nwin, "No data", dtype=object)

        pos = score > 0
        if pos.any():
            pos_scores = score[pos]

            # If too few positives, avoid unstable quantiles
            if len(pos_scores) >= 20:
                vh_cut = np.quantile(pos_scores, 1.0 - VERY_HIGH_PCT)
                h_cut = np.quantile(pos_scores, 1.0 - HIGH_PCT)
            else:
                # fallback: treat all positives as High, top 1 as Very High
                vh_cut = pos_scores.max()
                h_cut = pos_scores.min()

            story_band[pos] = "Very Low"
            story_band[pos & (score >= h_cut)] = "High"
            story_band[pos & (score >= vh_cut)] = "Very High"

        # -------------------------
        # Statistical bands (FDR + z)
        # -------------------------
        band = np.full(nwin, "Very Low", dtype=object)

        # Prevent "significant" labels when the test is not valid (PATCHED)
        sig = (p_fdr <= Q_FDR) & ok

        band[sig & (z >= 1.65) & (z < 2.0)] = "Low"
        band[sig & (z >= 2.0) & (z < 3.0)] = "Medium"
        band[sig & (z >= 3.0) & (z < 4.0)] = "High"
        band[sig & (z >= 4.0)] = "Very High"

        # No-data windows must never claim a band
        band[no_data] = "No data"

        out = w.merge(
            pd.DataFrame({
                "win_id": win_ids,
                "risk_score_fixed": risk_score,
                "risk_band_fixed": band,
                "risk_band_story": story_band,
                "p_raw": p,
                "p_fdr": p_fdr,
                "z_score": z,
                # PATCHED: write full statistical story
                "exceedance": exceedance,
                "expected_null": mu,
                "sd_null": sd,
                "exposure_count": exposure_raw,  # keep raw
                "incident_count": met["incident_count"].to_numpy(),
            }),
            on="win_id",
            how="left"
        )

        geojson = os.path.join(OUTDIR, f"risk_windows_{tag}.geojson")
        out.to_file(geojson, driver="GeoJSON")
        print("Wrote:", geojson)

    print("\nDone.")


if __name__ == "__main__":
    main()