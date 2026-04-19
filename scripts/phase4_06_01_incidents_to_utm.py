import json
import geopandas as gpd

with open("data/processed/crs_tx.json", "r", encoding="utf-8") as f:
    crs_info = json.load(f)

utm_epsg = crs_info["utm_epsg"]

inc = gpd.read_file("data/processed/incidents_tx.geojson")

# if incidents are not in WGS84, force to 4326 only if missing CRS
if inc.crs is None:
    inc = inc.set_crs("EPSG:4326")

inc_utm = inc.to_crs(epsg=utm_epsg)

out_path = "data/processed/incidents_tx_utm.geojson"
inc_utm.to_file(out_path, driver="GeoJSON")

print("Saved:", out_path)
print("Incidents:", len(inc_utm))
print("UTM EPSG:", utm_epsg)
