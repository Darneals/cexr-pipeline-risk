from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from region_store import RegionStore

DATA_ROOT = "../../data"

app = FastAPI(title="Phase 9 Region API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = RegionStore(DATA_ROOT)

# Serve the entire data/ folder as static files at /data
# This lets MapView fetch GeoJSON directly from the backend:
#   http://localhost:8000/data/regions/us_la/results_corridor/risk_windows_5km_ribbon.geojson
app.mount("/data", StaticFiles(directory=os.path.abspath(DATA_ROOT)), name="data")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/regions")
def regions():
    return {"regions": store.list_regions()}


@app.get("/regions/{slug}/manifest")
def manifest(slug: str):
    try:
        return store.manifest(slug)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/regions/{slug}/geo/{layer_key}")
def geo_layer(slug: str, layer_key: str):
    try:
        data = store.load_layer(slug, layer_key)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
