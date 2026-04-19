import json
import geopandas as gpd

states_path = "data/raw/cb_2018_us_state_500k/cb_2018_us_state_500k.shp"

with open("data/processed/top_state.txt", "r", encoding="utf-8") as f:
    st = f.read().strip()

states = gpd.read_file(states_path).to_crs("EPSG:4326")
poly = states.loc[states["STUSPS"] == st]

centroid = poly.geometry.iloc[0].centroid
lon = float(centroid.x)
lat = float(centroid.y)

zone = int((lon + 180) // 6) + 1
epsg = 32600 + zone  # Texas is Northern Hemisphere

out = {"state": st, "centroid_lon": lon, "centroid_lat": lat, "utm_zone": zone, "utm_epsg": epsg}

print(out)

with open("data/processed/crs_tx.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("Saved: data/processed/crs_tx.json")
