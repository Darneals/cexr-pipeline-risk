import geopandas as gpd

segments_path = "data/processed/pipelines_tx_segments_1km.geojson"
grid_path = "data/processed/tx_grid_50km_utm.geojson"

out_csv = "data/processed/segment_to_cell.csv"

segs = gpd.read_file(segments_path)
grid = gpd.read_file(grid_path)

if segs.crs.to_epsg() != 32614 or grid.crs.to_epsg() != 32614:
    raise SystemExit(f"CRS mismatch. segs={segs.crs}, grid={grid.crs}")

# Ensure segment_id exists
if "segment_id" not in segs.columns:
    raise SystemExit(f"segment_id not found in segments columns: {list(segs.columns)}")

# Use centroid for stable assignment
cent = segs.copy()
cent["geometry"] = segs.geometry.centroid

joined = gpd.sjoin(cent[["segment_id", "geometry"]], grid[["cell_id", "geometry"]], predicate="within", how="left")

# Some centroids may fall exactly on borders -> fill by nearest cell
missing = joined["cell_id"].isna().sum()
if missing > 0:
    # nearest join fallback
    joined_missing = joined[joined["cell_id"].isna()].drop(columns=["index_right"])
    nearest = gpd.sjoin_nearest(joined_missing, grid[["cell_id", "geometry"]], how="left", distance_col="dist_m")
    joined.loc[joined["cell_id"].isna(), "cell_id"] = nearest["cell_id"].values

joined[["segment_id", "cell_id"]].to_csv(out_csv, index=False)

print("Saved:", out_csv)
print("Segments:", len(segs))
print("Missing after fix:", joined["cell_id"].isna().sum())
print("Unique cells used:", joined["cell_id"].nunique())
