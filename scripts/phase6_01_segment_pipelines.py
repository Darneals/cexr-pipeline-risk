import geopandas as gpd
from shapely.geometry import LineString
from shapely.ops import substring
import pandas as pd

IN_PIPES = "data/processed/pipelines_tx.geojson"
OUT_SEGS = "data/processed/pipelines_tx_segments_1km.geojson"

SEG_LEN_M = 1000  # fixed-length segments in meters
TARGET_EPSG = 32614  # your TX UTM choice

def segment_line(line: LineString, seg_len_m: float):
    """
    Split a LineString into fixed-length segments using substring in projected meters.
    Returns a list of LineStrings.
    """
    if line is None or line.is_empty:
        return []
    if line.length <= seg_len_m:
        return [line]

    segs = []
    start = 0.0
    L = line.length
    while start < L:
        end = min(start + seg_len_m, L)
        seg = substring(line, start, end, normalized=False)
        if seg is not None and (not seg.is_empty) and seg.length > 0:
            segs.append(seg)
        start = end
    return segs

def main():
    pipes = gpd.read_file(IN_PIPES)

    # Ensure projected meters
    if pipes.crs is None:
        raise ValueError("Pipelines CRS is missing. Fix CRS before segmenting.")
    pipes = pipes.to_crs(epsg=TARGET_EPSG)

    rows = []
    seg_id = 0

    for idx, row in pipes.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        # Handle MultiLineString by exploding
        if geom.geom_type == "MultiLineString":
            parts = list(geom.geoms)
        else:
            parts = [geom]

        for p_i, part in enumerate(parts):
            for seg in segment_line(part, SEG_LEN_M):
                rows.append({
                    "segment_id": seg_id,
                    "parent_idx": int(idx),
                    "part_idx": int(p_i),
                    "length_m": float(seg.length),
                    "geometry": seg
                })
                seg_id += 1

    segs = gpd.GeoDataFrame(rows, crs=f"EPSG:{TARGET_EPSG}")

    # Sanity stats
    print("Pipelines:", len(pipes))
    print("Segments:", len(segs))
    print("Median segment length (m):", float(segs["length_m"].median()))

    segs.to_file(OUT_SEGS, driver="GeoJSON")
    print("Saved:", OUT_SEGS)

if __name__ == "__main__":
    main()
