import json
from pathlib import Path
from pyproj import CRS, Transformer

# --- CHANGE THIS if needed ---
SRC_EPSG = 26914  # guess: UTM 14N (common for Texas)
DST_EPSG = 4326   # lon/lat

IN_PATH = Path(r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx\results\pipelines_tx_segment_risk_fixed_minlen.geojson")
OUT_PATH = Path(r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx\results\pipelines_tx_segment_risk_fixed_minlen_wgs84.geojson")


def reproject_coords(coords, tfm):
    # coords can be nested (LineString, MultiLineString)
    if isinstance(coords[0], (int, float)):
        x, y = coords
        lon, lat = tfm.transform(x, y)
        return [lon, lat]
    return [reproject_coords(c, tfm) for c in coords]


def main():
    src = CRS.from_epsg(SRC_EPSG)
    dst = CRS.from_epsg(DST_EPSG)
    tfm = Transformer.from_crs(src, dst, always_xy=True)

    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    for f in data.get("features", []):
        g = f.get("geometry")
        if not g:
            continue
        g["coordinates"] = reproject_coords(g["coordinates"], tfm)

    OUT_PATH.write_text(json.dumps(data), encoding="utf-8")
    print("Wrote:", OUT_PATH)


if __name__ == "__main__":
    main()
