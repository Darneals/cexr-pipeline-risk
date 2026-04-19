import json
import numpy as np
from pathlib import Path

SRC = Path("data/regions/us_tx/results/pipelines_tx_segment_risk_fixed_minlen_wgs84.geojson")
DST = Path("data/regions/us_tx/results/pipelines_tx_segment_risk_fixed_minlen_wgs84_reband.geojson")

with open(SRC, "r", encoding="utf-8") as f:
    geo = json.load(f)

scores = []

for feat in geo["features"]:
    s = feat["properties"].get("risk_score_fixed", 0)
    if s > 0:
        scores.append(s)

scores = np.array(scores)

# compute quartiles ONLY from positive scores
q20, q40, q60, q80 = np.quantile(scores, [0.2, 0.4, 0.6, 0.8])

def band_from_score(s):
    if s == 0:
        return "Very Low"
    if s <= q20:
        return "Low"
    if s <= q40:
        return "Medium"
    if s <= q60:
        return "High"
    return "Very High"

for feat in geo["features"]:
    s = feat["properties"].get("risk_score_fixed", 0)
    feat["properties"]["risk_band_fixed"] = band_from_score(s)

with open(DST, "w", encoding="utf-8") as f:
    json.dump(geo, f)

print("Saved:", DST)
