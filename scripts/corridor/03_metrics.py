import os
import sys
import geopandas as gpd
import pandas as pd

ROOT = r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx"
PROCESSED = os.path.join(ROOT, "processed")
OUTDIR = os.path.join(ROOT, "results_corridor")
os.makedirs(OUTDIR, exist_ok=True)

BUFFER_M = 2000

SEGMENTS_FILE = os.path.join(PROCESSED, "pipelines_tx_segment_risk_fixed_minlen.geojson")
EXPOSURE_FILE = os.path.join(PROCESSED, "pipeline_exposure.geojson")

WINDOW_FILES = [
    ("10km", os.path.join(OUTDIR, "windows_10km.gpkg")),
    ("5km", os.path.join(OUTDIR, "windows_5km.gpkg")),
]

def main():
    if not os.path.exists(SEGMENTS_FILE):
        print("Missing SEGMENTS_FILE:", SEGMENTS_FILE)
        sys.exit(1)
    if not os.path.exists(EXPOSURE_FILE):
        print("Missing EXPOSURE_FILE:", EXPOSURE_FILE)
        sys.exit(1)

    seg = gpd.read_file(SEGMENTS_FILE)
    exp = gpd.read_file(EXPOSURE_FILE)

    if "incident_count" not in seg.columns:
        print("SEGMENTS_FILE must contain incident_count")
        sys.exit(1)

    seg = seg[seg.geometry.notna()].copy()
    exp = exp[exp.geometry.notna()].copy()

    for tag, wpath in WINDOW_FILES:
        w = gpd.read_file(wpath, layer="windows")

        # buffer windows for counting
        wbuf = w[["win_id", "geometry"]].copy()
        wbuf["geometry"] = wbuf.geometry.buffer(BUFFER_M)

        # exposure count inside window buffer
        jexp = gpd.sjoin(exp, wbuf, predicate="intersects", how="inner")
        exp_counts = jexp.groupby("win_id").size().rename("exposure_count")

        # incident mass: sum incident_count of segments intersecting window buffer
        jseg = gpd.sjoin(seg[["incident_count", "geometry"]], wbuf, predicate="intersects", how="inner")
        inc_counts = jseg.groupby("win_id")["incident_count"].sum().rename("incident_count")

        df = pd.DataFrame({"win_id": w["win_id"].values})
        df = df.merge(exp_counts.reset_index(), on="win_id", how="left")
        df = df.merge(inc_counts.reset_index(), on="win_id", how="left")

        df["exposure_count"] = df["exposure_count"].fillna(0).astype(int)
        df["incident_count"] = df["incident_count"].fillna(0).astype(int)

        # observed risk
        df["risk_obs"] = df["incident_count"] / df["exposure_count"].clip(lower=1)

        out = os.path.join(OUTDIR, f"metrics_{tag}.csv")
        df.to_csv(out, index=False)
        print("Wrote:", out)

if __name__ == "__main__":
    main()