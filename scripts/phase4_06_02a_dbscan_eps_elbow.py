import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors

K = 10  # usually equals min_samples
gdf = gpd.read_file("data/processed/incidents_tx_utm.geojson")

coords = np.vstack([gdf.geometry.x.values, gdf.geometry.y.values]).T

nbrs = NearestNeighbors(n_neighbors=K).fit(coords)
distances, _ = nbrs.kneighbors(coords)

# distance to the Kth neighbor
kdist = np.sort(distances[:, -1])

plt.figure(figsize=(8, 5))
plt.plot(kdist)
plt.title(f"k-distance plot (k={K})")
plt.xlabel("Points sorted by distance")
plt.ylabel("Distance to k-th nearest neighbor (m)")
plt.tight_layout()
plt.show()

print("Tip: pick eps near the elbow region of this curve.")
