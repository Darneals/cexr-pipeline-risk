import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

# Paths
pipes_path = "data/processed/pipelines_tx.geojson"
inc_path = "data/processed/incidents_tx_hdbscan.geojson"
tx_states_path = "data/raw/cb_2018_us_state_500k/cb_2018_us_state_500k.shp"
out_png = "results/figures/tx_hotspots_hdbscan_overlay.png"

# Load data
pipes = gpd.read_file(pipes_path)
inc = gpd.read_file(inc_path)

# Split clusters vs noise
clusters = inc[inc["cluster_hdbscan"] != -1].copy()
noise = inc[inc["cluster_hdbscan"] == -1].copy()

# Ensure same CRS
clusters = clusters.to_crs(pipes.crs)
noise = noise.to_crs(pipes.crs)

# Load Texas boundary
tx = gpd.read_file(tx_states_path)
tx = tx[tx["STUSPS"] == "TX"].to_crs(pipes.crs)

# Build a categorical color map for cluster IDs
cluster_ids = sorted(clusters["cluster_hdbscan"].unique().tolist())
cmap = plt.get_cmap("tab10", max(10, len(cluster_ids)))

color_lookup = {cid: cmap(i) for i, cid in enumerate(cluster_ids)}
clusters["plot_color"] = clusters["cluster_hdbscan"].map(color_lookup)

# Plot
fig, ax = plt.subplots(figsize=(9, 9))

# Texas outline
tx.boundary.plot(ax=ax, color="black", linewidth=1)

# Pipelines (slightly faded)
pipes.plot(ax=ax, color="black", linewidth=0.3, alpha=0.4)

# Noise (very light)
noise.plot(ax=ax, color="lightgray", markersize=3, alpha=0.25)

# Clusters (colored points)
clusters.plot(ax=ax, color=clusters["plot_color"], markersize=10)

# Title and axes
ax.set_title("Texas Gas Pipeline Incident Hotspots (HDBSCAN)")
ax.axis("off")

# Tight crop to Texas (+ small padding)
minx, miny, maxx, maxy = tx.total_bounds
pad_x = (maxx - minx) * 0.08
pad_y = (maxy - miny) * 0.08
ax.set_xlim(minx - pad_x, maxx + pad_x)
ax.set_ylim(miny - pad_y, maxy + pad_y)

# Custom legend (Cluster IDs)
handles = [mpatches.Patch(color=color_lookup[cid], label=f"Cluster {cid}") for cid in cluster_ids]
ax.legend(handles=handles, title="Cluster ID", loc="lower left", frameon=True)

# Save
os.makedirs("results/figures", exist_ok=True)
plt.subplots_adjust(top=0.92)
plt.savefig(out_png, dpi=300, bbox_inches="tight")
plt.show()

print("Saved figure:", out_png)
