import geopandas as gpd
import numpy as np
import hdbscan

MIN_CLUSTER_SIZE = 25
MIN_SAMPLES = 10

gdf = gpd.read_file("data/processed/incidents_tx_utm.geojson")
coords = np.vstack([gdf.geometry.x.values, gdf.geometry.y.values]).T

clusterer = hdbscan.HDBSCAN(
    min_cluster_size=MIN_CLUSTER_SIZE,
    min_samples=MIN_SAMPLES,
    metric="euclidean",
)

labels = clusterer.fit_predict(coords)
gdf["cluster_hdbscan"] = labels

# Optional but valuable for analysis
gdf["cluster_prob"] = clusterer.probabilities_

n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
n_noise = int((labels == -1).sum())

print("HDBSCAN min_cluster_size:", MIN_CLUSTER_SIZE, "min_samples:", MIN_SAMPLES)
print("Clusters:", n_clusters)
print("Noise points:", n_noise)
print("\nTop cluster sizes:")
print(gdf["cluster_hdbscan"].value_counts().head(15))

out_path = "data/processed/incidents_tx_hdbscan.geojson"
gdf.to_file(out_path, driver="GeoJSON")
print("Saved:", out_path)
