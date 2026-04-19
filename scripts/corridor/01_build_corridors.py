import os
import sys
import geopandas as gpd
from shapely.ops import unary_union, linemerge
from shapely.geometry import LineString, MultiLineString

REGION = "us_tx"

ROOT = r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx"
PROCESSED = os.path.join(ROOT, "processed")
OUTDIR = os.path.join(ROOT, "results_corridor")
os.makedirs(OUTDIR, exist_ok=True)

SEGMENTS_FILE = os.path.join(PROCESSED, "pipelines_tx_segment_risk_fixed_minlen.geojson")

TARGET_EPSG = 32614  # UTM 14N (meters)

def explode_lines(geom):
    if geom is None:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    # sometimes linemerge returns GeometryCollection-like
    try:
        return [g for g in geom.geoms if isinstance(g, (LineString, MultiLineString))]
    except Exception:
        return []

def main():
    if not os.path.exists(SEGMENTS_FILE):
        print("Missing SEGMENTS_FILE:", SEGMENTS_FILE)
        sys.exit(1)

    gdf = gpd.read_file(SEGMENTS_FILE)
    gdf = gdf[gdf.geometry.notna()].copy()

    # Ensure meters
    if gdf.crs is None:
        print("ERROR: SEGMENTS_FILE has no CRS. Fix CRS first.")
        sys.exit(1)

    if gdf.crs.to_epsg() != TARGET_EPSG:
        gdf = gdf.to_crs(epsg=TARGET_EPSG)

    # Merge connected linework into longer corridors
    merged = linemerge(unary_union(gdf.geometry.values))

    lines = []
    for part in explode_lines(merged):
        if isinstance(part, MultiLineString):
            lines.extend(list(part.geoms))
        elif isinstance(part, LineString):
            lines.append(part)

    corridors = gpd.GeoDataFrame(
        {"region": REGION, "geometry": lines},
        geometry="geometry",
        crs=gdf.crs
    )

    corridors = corridors[corridors.length > 0].copy()
    corridors = corridors.reset_index(drop=True)
    corridors["corr_id"] = [f"{REGION}_corr_{i}" for i in range(len(corridors))]

    out = os.path.join(OUTDIR, "corridors.gpkg")
    corridors.to_file(out, layer="corridors", driver="GPKG")

    print("Wrote:", out)
    print("Corridors:", len(corridors))
    print("Min length (km):", (corridors.length.min() / 1000.0))
    print("Max length (km):", (corridors.length.max() / 1000.0))

if __name__ == "__main__":
    main()