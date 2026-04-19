import geopandas as gpd

pipelines_path = "data/raw/Natural_Gas_Interstate_and_Intrastate_Pipelines/Natural_Gas_Interstate_and_Intrastate_Pipelines.shp"
states_path = "data/raw/cb_2018_us_state_500k/cb_2018_us_state_500k.shp"

with open("data/processed/top_state.txt", "r", encoding="utf-8") as f:
    st = f.read().strip()

pipes = gpd.read_file(pipelines_path)
states = gpd.read_file(states_path)

# cb_2018 uses STUSPS
if "STUSPS" not in states.columns:
    raise SystemExit(f"STUSPS not found. Columns: {list(states.columns)}")

state_poly = states.loc[states["STUSPS"] == st]
if len(state_poly) != 1:
    raise SystemExit(f"Expected 1 polygon for {st}, found {len(state_poly)}")

state_poly = state_poly.to_crs(pipes.crs)

clipped = gpd.clip(pipes, state_poly)

print("Pipelines original:", len(pipes))
print("Pipelines clipped:", len(clipped))
print("CRS:", clipped.crs)

out_path = "data/processed/pipelines_tx.geojson"
clipped.to_file(out_path, driver="GeoJSON")
print("Saved:", out_path)
