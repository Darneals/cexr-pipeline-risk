import geopandas as gpd
import numpy as np
from sklearn.cluster import DBSCAN

# meters
EPS_M = 8000   # 5 km baseline
MIN_SAMPLES = 5

gdf = gpd.read_file("data/processed/incidents_tx_utm.geojson")

coords = np.vstack([gdf.geometry.x.values, gdf.geometry.y.values]).T

model = DBSCAN(eps=EPS_M, min_samples=MIN_SAMPLES)
labels = model.fit_predict(coords)

gdf["cluster_dbscan"] = labels

n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
n_noise = int((labels == -1).sum())

print("DBSCAN eps(m):", EPS_M, "min_samples:", MIN_SAMPLES)
print("Clusters:", n_clusters)
print("Noise points:", n_noise)

out_path = "data/processed/incidents_tx_dbscan.geojson"
gdf.to_file(out_path, driver="GeoJSON")
print("Saved:", out_path)
