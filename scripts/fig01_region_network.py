import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")

# TODO: set this to your real incident file
INCIDENTS = ROOT / "data" / "processed" / "incidents_tx.geojson"

BOUNDARY  = ROOT / "data" / "raw" / "cb_2018_us_state_500k" / "cb_2018_us_state_500k.shp"

OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

OUTPNG = OUTDIR / "fig01_tx_incident_hexbin.png"
OUTPDF = OUTDIR / "fig01_tx_incident_hexbin.pdf"

pts = gpd.read_file(INCIDENTS)
states = gpd.read_file(BOUNDARY)
texas = states[states["NAME"] == "Texas"].copy()

# Ensure CRS (assume incident points are lon/lat only if missing)
if pts.crs is None:
    pts = pts.set_crs("EPSG:4326")

pts_ll = pts.to_crs("EPSG:4326")
texas_ll = texas.to_crs("EPSG:4326")

# Clip points to Texas (prevents out-of-state points)
pts_ll = gpd.clip(pts_ll, texas_ll)

x = pts_ll.geometry.x.to_numpy()
y = pts_ll.geometry.y.to_numpy()

fig, ax = plt.subplots(figsize=(12, 12))

# Texas outline
texas_ll.boundary.plot(ax=ax, linewidth=2.0)

# Hexbin density
hb = ax.hexbin(
    x, y,
    gridsize=70,        # adjust 50–100
    mincnt=1,
    linewidths=0.0,
    alpha=0.85
)

# Tight extent
minx, miny, maxx, maxy = texas_ll.total_bounds
mx = (maxx - minx) * 0.03
my = (maxy - miny) * 0.03
ax.set_xlim(minx - mx, maxx + mx)
ax.set_ylim(miny - my, maxy + my)

ax.set_axis_off()
ax.set_aspect("auto")


# Colorbar (makes density interpretable)
cbar = plt.colorbar(hb, ax=ax, fraction=0.03, pad=0.01)
cbar.set_label("Incidents per hexagon")

plt.savefig(OUTPNG, dpi=600, bbox_inches="tight")
plt.savefig(OUTPDF, bbox_inches="tight")
plt.close()

print("Saved:", OUTPNG)
print("Saved:", OUTPDF)