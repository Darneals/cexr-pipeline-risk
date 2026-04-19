import geopandas as gpd
from pathlib import Path

# Input: Texas pipelines (line geometry)
pipes_path = "data/processed/pipelines_tx.geojson"

# Output folder
out_dir = Path("data/processed/buffers")
out_dir.mkdir(parents=True, exist_ok=True)

# Buffer sizes (meters)
BUFFER_SIZES_M = [1000, 2000, 5000]

pipes = gpd.read_file(pipes_path)

# Force UTM for real meters
pipes = pipes.to_crs(epsg=32614)

print("Pipelines CRS:", pipes.crs)
print("Pipelines features:", len(pipes))

for b in BUFFER_SIZES_M:
    buf = pipes.copy()
    buf["geometry"] = buf.buffer(b)
    out_path = out_dir / f"pipelines_tx_buffer_{b}m.geojson"
    buf.to_file(out_path, driver="GeoJSON")
    print("Saved:", out_path)
