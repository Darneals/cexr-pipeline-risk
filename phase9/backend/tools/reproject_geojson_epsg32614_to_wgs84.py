import json
from pathlib import Path
from pyproj import Transformer

# INPUT: your current projected file (UTM 14N)
IN_PATH = Path(r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx\results\pipelines_tx_segment_risk_fixed_minlen.geojson")

# OUTPUT: lon/lat version for web maps
OUT_PATH = Path(r"C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx\results\pipelines_tx_segment_risk_fixed_minlen_wgs84.geojson")

# EPSG:32614 (UTM Zone 14N, WGS84) -> EPSG:4326 (lon/lat)
tfm = Transformer.from_crs("EPSG:32614", "EPSG:4326", always_xy=True)


def reproj_any(coords):
    """
    Reproject nested coordinate arrays for LineString / MultiLineString / etc.
    """
    if not coords:
        return coords

    # Base case: [x, y]
    if isinstance(coords[0], (int, float)):
        x, y = coords[0], coords[1]
        lon, lat = tfm.transform(x, y)
        return [lon, lat]

    # Recursive case
    return [reproj_any(c) for c in coords]


def main():
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))

    features = data.get("features", [])
    if not features:
        raise SystemExit("No features found in input GeoJSON.")

    for f in features:
        g = f.get("geometry")
        if not g:
            continue
        g["coordinates"] = reproj_any(g["coordinates"])

    OUT_PATH.write_text(json.dumps(data), encoding="utf-8")
    print("OK: wrote", OUT_PATH)


if __name__ == "__main__":
    main()
