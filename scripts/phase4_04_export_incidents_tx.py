import pandas as pd
import geopandas as gpd

path = "data/raw/gtggungs2010toPresent.xlsx"
sheet = "gtggungs2010toPresent"

with open("data/processed/top_state.txt", "r", encoding="utf-8") as f:
    st = f.read().strip()

STATE_COL = "OPERATOR_STATE_ABBREVIATION"  # from your ranking output

df0 = pd.read_excel(path, sheet_name=sheet, nrows=5)
cols = list(df0.columns)

def find_candidates(keys):
    hits = []
    for c in cols:
        cu = str(c).upper()
        if any(k in cu for k in keys):
            hits.append(c)
    return hits

lat_candidates = find_candidates(["LAT"])
lon_candidates = find_candidates(["LON", "LONG"])

print("LAT candidates (first 20):", lat_candidates[:20])
print("LON candidates (first 20):", lon_candidates[:20])

# pick first candidate by default
LAT_COL = lat_candidates[0] if lat_candidates else None
LON_COL = lon_candidates[0] if lon_candidates else None

if not LAT_COL or not LON_COL:
    raise SystemExit("Could not detect LAT/LON columns. Paste the candidates list here and we will pick manually.")

df = pd.read_excel(path, sheet_name=sheet)

df = df[df[STATE_COL].astype(str).str.strip() == st].copy()
df = df.dropna(subset=[LAT_COL, LON_COL]).copy()

gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df[LON_COL], df[LAT_COL]),
    crs="EPSG:4326"
)

out_path = "data/processed/incidents_tx.geojson"
gdf.to_file(out_path, driver="GeoJSON")

print("Using:", STATE_COL, LAT_COL, LON_COL)
print("Incidents TX:", len(gdf))
print("Saved:", out_path)
