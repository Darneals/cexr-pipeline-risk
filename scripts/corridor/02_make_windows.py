import os
import math
import geopandas as gpd
from shapely.geometry import LineString

ROOT = r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx"
OUTDIR = os.path.join(ROOT, "results_corridor")
CORRIDORS = os.path.join(OUTDIR, "corridors.gpkg")

STEP_M = 1000  # step along corridor (NOT the scoring unit)
WINDOWS = [
    ("10km", 10_000),
    ("5km", 5_000),
]

def cut_linestring(ls: LineString, start_m: float, end_m: float) -> LineString:
    start_m = max(0.0, start_m)
    end_m = min(ls.length, end_m)
    if end_m <= start_m:
        return None

    pts = []
    # sample every ~50m for a stable cut
    n = max(2, int(math.ceil((end_m - start_m) / 50.0)))
    for i in range(n):
        d = start_m + (end_m - start_m) * (i / (n - 1))
        p = ls.interpolate(d)
        pts.append((p.x, p.y))
    return LineString(pts)

def make_windows(corridors, win_len_m: int, tag: str):
    rows = []
    for _, r in corridors.iterrows():
        geom = r.geometry
        if geom is None:
            continue
        corr_id = r["corr_id"]
        L = geom.length
        if L < win_len_m:
            continue

        k = 0
        for start in range(0, int(L - win_len_m) + 1, STEP_M):
            end = start + win_len_m
            seg = cut_linestring(geom, start, end)
            if seg is None:
                continue
            rows.append({
                "corr_id": corr_id,
                "win_id": f"{corr_id}_{tag}_{k}",
                "win_len_m": win_len_m,
                "start_m": start,
                "end_m": end,
                "geometry": seg
            })
            k += 1

    return gpd.GeoDataFrame(rows, crs=corridors.crs)

def main():
    corridors = gpd.read_file(CORRIDORS, layer="corridors")
    os.makedirs(OUTDIR, exist_ok=True)

    for tag, win_len_m in WINDOWS:
        w = make_windows(corridors, win_len_m, tag)
        out = os.path.join(OUTDIR, f"windows_{tag}.gpkg")
        w.to_file(out, layer="windows", driver="GPKG")
        print("Wrote:", out, "windows:", len(w))

if __name__ == "__main__":
    main()