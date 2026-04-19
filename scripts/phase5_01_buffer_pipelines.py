import geopandas as gpd

from scripts._region import load_region_paths
# Load region paths
REGION, RAW_DIR, PROC_DIR = load_region_paths("us_tx")
# Load Texas pipelines
pipes = gpd.read_file(f"{PROC_DIR}/pipelines_tx.geojson")

print("Original CRS:", pipes.crs)

# Reproject to UTM Zone 14N (Texas central zone)
pipes = pipes.to_crs(epsg=32614)

print("Reprojected CRS:", pipes.crs)

# Buffer in meters
BUFFER_DISTANCE = 2000  # 2 km

pipes_buffer = pipes.copy()
pipes_buffer["geometry"] = pipes_buffer.buffer(BUFFER_DISTANCE)
out_path = f"{PROC_DIR}/pipelines_tx_buffer_2km.geojson"

pipes_buffer.to_file(out_path, driver="GeoJSON")

print("Saved:", out_path)
