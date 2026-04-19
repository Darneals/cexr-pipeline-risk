import json
import numpy as np
from pathlib import Path

REGION = "us_tx"
INP = Path(f"data/regions/{REGION}/results/pipelines_tx_segment_risk_fixed_minlen_wgs84.geojson")
OUT = Path(f"data/regions/{REGION}/results/pipelines_tx_segment_risk_fixed_minlen_wgs84_reband_from_score.geojson")

BANDS = ["Very Low", "Low", "Medium", "High", "Very High"]

def main():
    d = json.loads(INP.read_text(encoding="utf-8"))
    feats = d.get("features", [])

    scores = []
    for f in feats:
        s = f.get("properties", {}).get("risk_score_fixed", None)
        try:
            s = float(s)
        except Exception:
            continue
        if np.isfinite(s):
            scores.append(s)

    if not scores:
        raise SystemExit("No finite risk_score_fixed values found.")

    # quantile cuts: 20% each band
    qs = np.quantile(scores, [0.2, 0.4, 0.6, 0.8]).tolist()

    def band_for(s):
        if s <= qs[0]: return BANDS[0]
        if s <= qs[1]: return BANDS[1]
        if s <= qs[2]: return BANDS[2]
        if s <= qs[3]: return BANDS[3]
        return BANDS[4]

    for f in feats:
        p = f.setdefault("properties", {})
        try:
            s = float(p.get("risk_score_fixed", 0.0))
        except Exception:
            s = 0.0
        p["risk_band_from_score_fixed"] = band_for(s)
        p["risk_band_thresholds_q20_40_60_80"] = qs

    OUT.write_text(json.dumps(d), encoding="utf-8")
    print("Wrote:", OUT)
    print("Cuts:", qs)

if __name__ == "__main__":
    main()
