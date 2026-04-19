import geopandas as gpd
import pandas as pd

db = gpd.read_file("data/processed/incidents_tx_dbscan.geojson")
hb = gpd.read_file("data/processed/incidents_tx_hdbscan.geojson")

def summarize(gdf, col):
    s = gdf[col]
    n_noise = int((s == -1).sum())
    n_clusters = len(set(s)) - (1 if -1 in set(s) else 0)
    counts = s[s != -1].value_counts().sort_index()
    return n_clusters, n_noise, counts

db_ncl, db_noise, db_counts = summarize(db, "cluster_dbscan")
hb_ncl, hb_noise, hb_counts = summarize(hb, "cluster_hdbscan")

summary = pd.DataFrame([
    {"method":"DBSCAN", "clusters":db_ncl, "noise_points":db_noise},
    {"method":"HDBSCAN", "clusters":hb_ncl, "noise_points":hb_noise},
])

summary.to_csv("data/processed/cluster_summary.csv", index=False)

print(summary)
print("Saved: data/processed/cluster_summary.csv")
