import os
import json
import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx")
OUTDIR = ROOT / "results_corridor"

FILES = {
    "10km": OUTDIR / "risk_windows_10km_ribbon.geojson",
    "5km":  OUTDIR / "risk_windows_5km_ribbon.geojson",
}

def read_geojson(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for f in data.get("features", []):
        p = f.get("properties") or {}
        rows.append(p)
    return pd.DataFrame(rows)

def main():
    out_tables = OUTDIR / "paper_tables"
    out_tables.mkdir(parents=True, exist_ok=True)

    dfs = {}
    for tag, fp in FILES.items():
        if not fp.exists():
            print("Missing:", fp)
            continue
        df = read_geojson(fp)
        df["resolution"] = tag
        dfs[tag] = df
        print(tag, "rows:", len(df))

    # ---------- Table 2: band distribution ----------
    rows = []
    for tag, df in dfs.items():
        fixed = df["risk_band_fixed"].fillna("NA").value_counts()
        story = df["risk_band_story"].fillna("NA").value_counts()

        bands = sorted(set(fixed.index).union(set(story.index)))
        for b in bands:
            rows.append({
                "resolution": tag,
                "band": b,
                "count_validated(risk_band_fixed)": int(fixed.get(b, 0)),
                "count_story(risk_band_story)": int(story.get(b, 0)),
            })

    t2 = pd.DataFrame(rows).sort_values(["resolution","band"])
    t2.to_csv(out_tables / "Table2_band_distribution.csv", index=False)
    print("Wrote Table2_band_distribution.csv")

    # ---------- Table 3: top story hotspots by z_score ----------
    top_rows = []
    keep_cols = [
        "win_id","comp_id","start_m","end_m","win_len_m",
        "risk_band_story","risk_band_fixed",
        "risk_score_fixed","z_score","p_raw","p_fdr",
        "incident_count","exposure_count",
        "expected_null","sd_null","exceedance"
    ]

    for tag, df in dfs.items():
        d = df.copy()
        d["z_score"] = pd.to_numeric(d.get("z_score"), errors="coerce").fillna(0.0)
        d = d[d["risk_band_story"].isin(["High","Very High"])]
        d = d.sort_values("z_score", ascending=False).head(20)
        d["resolution"] = tag
        top_rows.append(d[[c for c in (["resolution"] + keep_cols) if c in d.columns]])

    if top_rows:
        t3 = pd.concat(top_rows, ignore_index=True)
        t3.to_csv(out_tables / "Table3_top_hotspots.csv", index=False)
        print("Wrote Table3_top_hotspots.csv")

    # ---------- Table 4: sensitivity summary ----------
    summ = []
    for tag, df in dfs.items():
        z = pd.to_numeric(df.get("z_score"), errors="coerce").fillna(0.0)
        expc = pd.to_numeric(df.get("exposure_count"), errors="coerce").fillna(0).astype(int)
        story_hot = int(df["risk_band_story"].isin(["High","Very High"]).sum())
        validated_hot = int(((pd.to_numeric(df.get("p_fdr"), errors="coerce").fillna(1.0) <= 0.05) &
                             (z >= 2)).sum())
        summ.append({
            "resolution": tag,
            "corridor_count": len(df),
            "median_exposure_count": int(expc.median()) if len(expc) else 0,
            "max_z_score": float(z.max()) if len(z) else 0.0,
            "story_hotspots": story_hot,
            "validated_hotspots(p_fdr<=0.05,z>=2)": validated_hot,
        })

    t4 = pd.DataFrame(summ).sort_values("resolution")
    t4.to_csv(out_tables / "Table4_sensitivity_summary.csv", index=False)
    print("Wrote Table4_sensitivity_summary.csv")

    print("Done.")

if __name__ == "__main__":
    main()