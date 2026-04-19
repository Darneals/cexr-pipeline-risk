import pandas as pd
import numpy as np

# Inputs
seg_cells_csv = "data/processed/segment_to_cell.csv"
seg_risk_geojson = "data/processed/pipelines_tx_segment_risk_fixed_minlen.geojson"  # produced by phase6_03c
inc_to_seg_csv = "data/processed/incidents_to_segment.csv"  # your filtered <=5km mapping (274 rows)

# Outputs
out_csv = "data/processed/phase7_spatial_null_grid.csv"
out_hist = "data/processed/phase7_spatial_null_grid_hist.csv"

# Settings
N_ITER = 5000
SEED = 42

rng = np.random.default_rng(SEED)

# Load segment meta (needs segment_id + length_km_clamped)
import geopandas as gpd
segs = gpd.read_file(seg_risk_geojson)

need_cols = ["segment_id", "length_km_clamped"]
for c in need_cols:
    if c not in segs.columns:
        raise SystemExit(f"Missing {c} in {seg_risk_geojson}. Columns: {list(segs.columns)}")

seg_meta = segs[["segment_id", "length_km_clamped"]].copy()
seg_meta["length_km_clamped"] = seg_meta["length_km_clamped"].astype(float)

seg_cells = pd.read_csv(seg_cells_csv)
inc_map = pd.read_csv(inc_to_seg_csv)

if "segment_id" not in inc_map.columns:
    raise SystemExit(f"incidents_to_segment.csv must have segment_id. Columns: {list(inc_map.columns)}")

# observed counts per segment (from assigned incidents)
obs_counts = inc_map.groupby("segment_id").size().rename("incident_count_obs").reset_index()

# merge meta + cells
df = seg_meta.merge(seg_cells, on="segment_id", how="left").merge(obs_counts, on="segment_id", how="left")
df["incident_count_obs"] = df["incident_count_obs"].fillna(0).astype(int)

# sanity
if df["cell_id"].isna().any():
    raise SystemExit("Some segments have no cell_id. Re-run 7.07B; check CRS and grid coverage.")

# observed density
df["density_obs"] = df["incident_count_obs"] / df["length_km_clamped"].clip(lower=1.0)

# observed metrics
dens = df["density_obs"].to_numpy()
dens_sum = dens.sum()
if dens_sum <= 0:
    raise SystemExit("Observed density sum is 0. Check incidents_to_segment.csv mapping.")
p = dens / dens_sum
obs_hhi = np.sum(p * p)
obs_max = np.max(dens)

# Prepare per-cell segment lists
cell_groups = df.groupby("cell_id")["segment_id"].apply(list).to_dict()

# Total incidents per cell (preserve this)
seg_to_cell = df.set_index("segment_id")["cell_id"].to_dict()
inc_map["cell_id"] = inc_map["segment_id"].map(seg_to_cell)
cell_inc_totals = inc_map.groupby("cell_id").size().to_dict()

# Pre-build index lookup for speed
seg_index = {sid: i for i, sid in enumerate(df["segment_id"].tolist())}
lengths = df["length_km_clamped"].to_numpy()

null_hhi = np.zeros(N_ITER, dtype=float)
null_max = np.zeros(N_ITER, dtype=float)

# run null
for it in range(N_ITER):
    counts = np.zeros(len(df), dtype=int)

    for cell_id, seg_list in cell_groups.items():
        m = len(seg_list)
        if m == 0:
            continue

        n_inc = cell_inc_totals.get(cell_id, 0)
        if n_inc == 0:
            continue

        # assign incidents uniformly at random among segments in same cell
        picks = rng.integers(0, m, size=n_inc)
        for j in picks:
            sid = seg_list[j]
            counts[seg_index[sid]] += 1

    dens_null = counts / np.clip(lengths, 1.0, None)
    s = dens_null.sum()
    if s <= 0:
        null_hhi[it] = 0.0
        null_max[it] = 0.0
    else:
        pp = dens_null / s
        null_hhi[it] = np.sum(pp * pp)
        null_max[it] = np.max(dens_null)

# p-values (greater-or-equal)
p_hhi = float(np.mean(null_hhi >= obs_hhi))
p_max = float(np.mean(null_max >= obs_max))

summary = pd.DataFrame([{
    "n_iter": N_ITER,
    "seed": SEED,
    "n_segments": len(df),
    "n_assigned_incidents": int(df["incident_count_obs"].sum()),
    "grid_cell_m": 50000,
    "obs_hhi": obs_hhi,
    "null_hhi_mean": float(null_hhi.mean()),
    "null_hhi_std": float(null_hhi.std(ddof=1)),
    "p_empirical_hhi": p_hhi,
    "obs_max_density": obs_max,
    "null_max_mean": float(null_max.mean()),
    "null_max_std": float(null_max.std(ddof=1)),
    "p_empirical_max_density": p_max,
}])

hist = pd.DataFrame({"null_hhi": null_hhi, "null_max_density": null_max})
summary.to_csv(out_csv, index=False)
hist.to_csv(out_hist, index=False)

print("Saved:", out_csv)
print("Saved:", out_hist)
print("\nSpatial-null summary (grid constrained):")
print(summary.T)
