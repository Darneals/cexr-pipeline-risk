import geopandas as gpd
import pandas as pd
import numpy as np

IN_SEGS = "data/processed/pipelines_tx_segments_1km.geojson"
IN_INC_WITH_SEG = "data/processed/incidents_tx_with_segment.geojson"

OUT_SEG_RISK = "data/processed/pipelines_tx_segment_risk.geojson"
OUT_TOP20 = "data/processed/top20_segments_by_risk.csv"

def minmax(series):
    s = series.astype(float)
    mn, mx = float(s.min()), float(s.max())
    if mx == mn:
        return s * 0.0
    return (s - mn) / (mx - mn)

def risk_band(score):
    # simple, readable bands
    if score >= 0.80:
        return "Very High"
    if score >= 0.60:
        return "High"
    if score >= 0.40:
        return "Medium"
    if score >= 0.20:
        return "Low"
    return "Very Low"

def main():
    segs = gpd.read_file(IN_SEGS)
    inc = gpd.read_file(IN_INC_WITH_SEG)

    # Count incidents per segment
    counts = inc.groupby("segment_id").size().rename("incident_count")
    segs = segs.merge(counts, how="left", left_on="segment_id", right_index=True)
    segs["incident_count"] = segs["incident_count"].fillna(0).astype(int)

    # Density (incidents per km)
    segs["length_km"] = segs["length_m"] / 1000.0
    segs["density_inc_per_km"] = segs.apply(
        lambda r: (r["incident_count"] / r["length_km"]) if r["length_km"] > 0 else 0,
        axis=1
    )

    # Risk score: normalize density 0–1
    segs["risk_score"] = minmax(segs["density_inc_per_km"])
    segs["risk_band"] = segs["risk_score"].apply(risk_band)

    segs.to_file(OUT_SEG_RISK, driver="GeoJSON")
    print("Saved:", OUT_SEG_RISK)

    top = segs.sort_values("risk_score", ascending=False).head(20)
    top[["segment_id","incident_count","length_m","density_inc_per_km","risk_score","risk_band"]].to_csv(OUT_TOP20, index=False)
    print("Saved:", OUT_TOP20)

    print("\nTop 10 segments by risk:")
    print(top[["segment_id","incident_count","density_inc_per_km","risk_score","risk_band"]].head(10))

if __name__ == "__main__":
    main()
