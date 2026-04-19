import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")

INCIDENTS = ROOT / "data" / "processed" / "incidents_tx_utm.geojson"
BOUNDARY  = ROOT / "data" / "raw" / "cb_2018_us_state_500k" / "cb_2018_us_state_500k.shp"

OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

OUTPNG = OUTDIR / "fig02_raw_incidents_distribution.png"
OUTPDF = OUTDIR / "fig02_raw_incidents_distribution.pdf"

# Load
incidents = gpd.read_file(INCIDENTS)
states = gpd.read_file(BOUNDARY)
texas = states[states["NAME"] == "Texas"].copy()

# Align CRS
texas = texas.to_crs(incidents.crs)

# Clip incidents to Texas
incidents_tx = gpd.clip(incidents, texas)

fig, ax = plt.subplots(figsize=(12, 12))

# Boundary
texas.boundary.plot(ax=ax, linewidth=2.0)

# Incidents
incidents_tx.plot(
    ax=ax,
    markersize=10,
    alpha=0.65,
    edgecolor="white",
    linewidth=0.25
)

# Tight extent
minx, miny, maxx, maxy = texas.total_bounds
mx = (maxx - minx) * 0.03
my = (maxy - miny) * 0.03
ax.set_xlim(minx - mx, maxx + mx)
ax.set_ylim(miny - my, maxy + my)

ax.set_axis_off()
ax.set_aspect("auto")

# ❌ TITLE REMOVED

plt.savefig(OUTPNG, dpi=600, bbox_inches="tight")
plt.savefig(OUTPDF, bbox_inches="tight")
plt.close()

print("Saved:", OUTPNG)
print("Saved:", OUTPDF)