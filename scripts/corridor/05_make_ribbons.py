# scripts/corridor/05_make_ribbons.py
# UPDATED: builds ribbons for TX, LA, OK from corridorfdr source files
# Overwrites existing ribbon files — safe, MapView is the only consumer.

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

ROOT = Path("data") / "regions"

# Each entry: (tag, region_slug, input_utm_epsg)
# TX uses UTM 14N (32614), LA uses UTM 15N (32615), OK uses UTM 14N (32614)
REGIONS = [
    ("us_tx", 32614),
    ("us_la", 32615),
    ("us_ok", 32614),
]

RIBBON_HALF_WIDTH_M = {
    "10km": 150.0,
    "5km":  120.0,
}

METRIC_CRS = "EPSG:3857"
OUT_CRS    = "EPSG:4326"


def _make_valid(g: BaseGeometry) -> BaseGeometry:
    if g is None:
        return g
    try:
        from shapely import make_valid
        return make_valid(g)
    except Exception:
        try:
            return g.buffer(0)
        except Exception:
            return g


def _buffer_lines_to_polys(
    gdf_in: gpd.GeoDataFrame,
    input_epsg: int,
    half_width_m: float,
) -> gpd.GeoDataFrame:
    if gdf_in.crs is None:
        gdf_in = gdf_in.set_crs(epsg=input_epsg)

    gdf_ll = gdf_in.to_crs(OUT_CRS)
    gdf_m  = gdf_ll.to_crs(METRIC_CRS)

    polys = []
    for geom in gdf_m.geometry:
        if geom is None or geom.is_empty:
            polys.append(None)
            continue
        try:
            g = _make_valid(geom)
            b = g.buffer(half_width_m, cap_style=2, join_style=2)
            b = _make_valid(b)
            polys.append(b if (b is not None and not b.is_empty) else None)
        except Exception:
            polys.append(None)

    out = gdf_m.copy()
    out.geometry = polys
    out = out[out.geometry.notnull()]
    out = out[~out.geometry.is_empty]
    return out.to_crs(OUT_CRS)


def _write_ribbon(
    src_path: Path,
    ribbon_gdf: gpd.GeoDataFrame,
    out_path: Path,
    hw: float,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    src       = json.loads(src_path.read_text(encoding="utf-8"))
    src_feats = src.get("features", [])

    props_by_win = {}
    for f in src_feats:
        if not isinstance(f, dict):
            continue
        p   = f.get("properties") or {}
        wid = p.get("win_id")
        if wid is None:
            continue
        props_by_win[wid] = dict(p)

    features = []
    for _, row in ribbon_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        wid   = row.get("win_id", None)
        props = dict(props_by_win[wid]) if wid in props_by_win \
                else {k: row[k] for k in ribbon_gdf.columns if k != "geometry"}

        props["ribbon_half_width_m"] = float(hw)
        props["ribbon_width_m"]      = float(hw) * 2.0
        props["geom0"]               = "LineString"

        feat = {
            "type":       "Feature",
            "geometry":   mapping(geom),
            "properties": props,
        }
        if feat["geometry"].get("coordinates"):
            features.append(feat)

    fc = {"type": "FeatureCollection", "features": features}
    out_path.write_text(json.dumps(fc), encoding="utf-8")
    return len(features)


def main():
    for region_slug, input_epsg in REGIONS:
        results_dir = ROOT / region_slug / "results_corridor"

        for res_tag, win_len in [("5km", "5km"), ("10km", "10km")]:
            # SOURCE: corridorfdr file (carries new field schema)
            src  = results_dir / f"risk_windows_{win_len}_corridorfdr.geojson"
            # OUTPUT: ribbon file (same name MapView expects — safe overwrite)
            out  = results_dir / f"risk_windows_{win_len}_ribbon.geojson"

            if not src.exists():
                print(f"[SKIP] {region_slug} {res_tag}: source not found: {src}")
                continue

            print(f"[{region_slug}] {res_tag} — reading {src.name} ...")
            gdf = gpd.read_file(src)
            if len(gdf) == 0:
                print(f"[SKIP] {region_slug} {res_tag}: empty source")
                continue

            hw      = RIBBON_HALF_WIDTH_M[res_tag]
            ribbons = _buffer_lines_to_polys(gdf, input_epsg, hw)
            n_out   = _write_ribbon(src, ribbons, out, hw)

            print(f"  features in : {len(gdf):,}")
            print(f"  features out: {n_out:,}")
            print(f"  written to  : {out}")

    print("\nDone. All ribbon files updated.")


if __name__ == "__main__":
    main()
