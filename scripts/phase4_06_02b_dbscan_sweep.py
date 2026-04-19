import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

gdf = gpd.read_file("data/processed/incidents_tx_utm.geojson")
coords = np.vstack([gdf.geometry.x.values, gdf.geometry.y.values]).T

eps_list = [1000, 2000, 3000, 5000, 8000, 10000]  # meters
min_samples_list = [5, 10, 15, 25]

rows = []
for eps in eps_list:
    for ms in min_samples_list:
        labels = DBSCAN(eps=eps, min_samples=ms).fit_predict(coords)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int((labels == -1).sum())
        noise_ratio = n_noise / len(labels)
        rows.append({
            "eps_m": eps,
            "min_samples": ms,
            "clusters": n_clusters,
            "noise_points": n_noise,
            "noise_ratio": round(noise_ratio, 3)
        })

df = pd.DataFrame(rows).sort_values(["noise_ratio", "clusters"], ascending=[True, False])
print(df.head(15))

df.to_csv("data/processed/dbscan_sweep.csv", index=False)
print("Saved: data/processed/dbscan_sweep.csv")
