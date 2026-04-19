import json
import numpy as np
from pathlib import Path

# ---- CONFIG ----
IN_PATH  = Path("data/regions/us_tx/results/pipelines_tx_segment_risk_fixed_minlen_wgs84.geojson")
OUT_PATH = Path("data/regions/us_tx/results/pipelines_tx_segment_risk_fixed_minlen_wgs84_reband.geojson")

SCORE_FIELD = "risk_score_fixed"      # model output we trust
OUT_BAND    = "risk_band_fixed"       # we will overwrite/recompute this

LABELS = ["Very Low", "Low", "Medium", "High", "Very High"]
# ----------------

def band_from_score(score: float, q25, q50, q75) -> str:
    # keep zeros honest
    if score <= 0.0:
        return "Very Low"
    # spread non-zero scores into 4 buckets
    if score <= q25:
        return "Low"
    if score <= q50:
        return "Medium"
    if score <= q75:
        return "High"
    return "Very High"

def main():
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    feats = data.get("features", [])

    scores = []
    for f in feats:
        p = f.get("properties", {})
        s = p.get(SCORE_FIELD, 0)
        try:
            s = float(s)
        except Exception:
            s = 0.0
        if np.isfinite(s) and s > 0:
            scores.append(s)

    if len(scores) == 0:
        raise SystemExit("No non-zero scores found. Can't compute quantiles.")

    scores = np.array(scores, dtype=float)
    q25, q50, q75 = np.quantile(scores, [0.25, 0.50, 0.75])

    # write bands back
    for f in feats:
        p = f.setdefault("properties", {})
        try:
            s = float(p.get(SCORE_FIELD, 0) or 0)
        except Exception:
            s = 0.0
        if not np.isfinite(s):
            s = 0.0
        p[OUT_BAND] = band_from_score(s, q25, q50, q75)

    OUT_PATH.write_text(json.dumps(data), encoding="utf-8")
    print("Wrote:", OUT_PATH)
    print("Nonzero count:", int((scores > 0).sum()), "out of", len(feats))
    print("Quantiles:", {"q25": float(q25), "q50": float(q50), "q75": float(q75)})

if __name__ == "__main__":
    main()
