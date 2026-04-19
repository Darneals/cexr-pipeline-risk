import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SEGS_PATH = "data/processed/pipelines_tx_segments_1km.geojson"
INC_SEG_PATH = "data/processed/incidents_tx_with_segment.geojson"

OUT_CSV = "data/processed/phase7_topk_stability.csv"
OUT_PNG = "data/processed/fig_phase7_topk_stability.png"

N_BOOT = 200
TOPK = 50
MIN_LEN_KM = 1.0

segs = gpd.read_file(SEGS_PATH)
inc = gpd.read_file(INC_SEG_PATH)

if segs.crs is None or str(segs.crs.to_epsg()) != "32614":
    segs = segs.to_crs(epsg=32614)

segs["length_km"] = (segs.geometry.length / 1000.0)
segs["length_km_clamped"] = segs["length_km"].clip(lower=MIN_LEN_KM)

# incident segment ids list
seg_ids = inc["segment_id"].dropna().astype(int).values
rng = np.random.default_rng(7)

appear = np.zeros(len(segs), dtype=int)

for b in range(N_BOOT):
    sample = rng.choice(seg_ids, size=len(seg_ids), replace=True)
    counts = pd.Series(sample).value_counts()
    tmp = np.zeros(len(segs), dtype=int)
    # Map counts by segment_id -> index
    id_to_idx = pd.Series(segs.index.values, index=segs["segment_id"].values)
    valid = counts.index.values[np.isin(counts.index.values, id_to_idx.index.values)]
    idx = id_to_idx.loc[valid].values
    tmp[idx] = counts.loc[valid].values

    dens = tmp / segs["length_km_clamped"].values
    top_idx = np.argsort(dens)[::-1][:TOPK]
    appear[top_idx] += 1

stability = pd.DataFrame({
    "segment_id": segs["segment_id"].values,
    "appearances": appear,
    "appearance_rate": appear / N_BOOT
}).sort_values("appearance_rate", ascending=False)

stability.to_csv(OUT_CSV, index=False)
print("Saved:", OUT_CSV)
print(stability.head(15))

plt.figure()
plt.hist(stability["appearance_rate"].values, bins=30)
plt.xlabel("Top-K appearance rate")
plt.ylabel("Count of segments")
plt.title(f"Bootstrap stability of Top-{TOPK} risk segments (N={N_BOOT})")
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=200)
print("Saved:", OUT_PNG)
