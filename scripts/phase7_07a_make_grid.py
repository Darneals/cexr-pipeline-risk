import geopandas as gpd
import numpy as np
from shapely.geometry import box

# Inputs (already in UTM EPSG:32614 in your pipeline)
segments_path = "data/processed/pipelines_tx_segments_1km.geojson"

# Output
grid_out = "data/processed/tx_grid_50km_utm.geojson"

# Grid cell size (meters): 50km is a good balance
CELL = 50_000

segs = gpd.read_file(segments_path)
if segs.crs is None or segs.crs.to_epsg() != 32614:
    raise SystemExit(f"Expected EPSG:32614 for segments, got {segs.crs}")

minx, miny, maxx, maxy = segs.total_bounds

xs = np.arange(minx, maxx + CELL, CELL)
ys = np.arange(miny, maxy + CELL, CELL)

cells = []
cell_ids = []
cid = 0
for x0 in xs[:-1]:
    for y0 in ys[:-1]:
        x1 = x0 + CELL
        y1 = y0 + CELL
        cells.append(box(x0, y0, x1, y1))
        cell_ids.append(cid)
        cid += 1

grid = gpd.GeoDataFrame({"cell_id": cell_ids}, geometry=cells, crs=segs.crs)

# Keep only cells that intersect Texas segments (cuts size)
grid = grid[grid.intersects(segs.geometry.union_all())].copy()

grid.to_file(grid_out, driver="GeoJSON")
print("Saved:", grid_out)
print("Grid cells:", len(grid))
print("CRS:", grid.crs)
print("Cell size (m):", CELL)
