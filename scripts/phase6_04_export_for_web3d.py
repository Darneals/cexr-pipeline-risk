import geopandas as gpd

IN_SEG_RISK = "data/processed/pipelines_tx_segment_risk.geojson"
OUT_WEB = "data/processed/pipelines_tx_segment_risk_web.geojson"

# Simplification tolerance in degrees after WGS84 reprojection.
# Keep small to avoid geometry collapse.
SIMPLIFY_DEG = 0.0001

def main():
    gdf = gpd.read_file(IN_SEG_RISK)

    # Convert to WGS84 for web viewers
    gdf = gdf.to_crs(epsg=4326)

    # Keep only the fields you need in metaverse/web
    keep = ["segment_id", "incident_count", "density_inc_per_km", "risk_score", "risk_band", "geometry"]
    cols = [c for c in keep if c in gdf.columns]
    gdf = gdf[cols].copy()

    # Light simplify for performance
    gdf["geometry"] = gdf["geometry"].simplify(SIMPLIFY_DEG, preserve_topology=True)

    gdf.to_file(OUT_WEB, driver="GeoJSON")
    print("Saved:", OUT_WEB)
    print("Features:", len(gdf))

if __name__ == "__main__":
    main()
