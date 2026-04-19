from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Any

import pandas as pd


@dataclass(frozen=True)
class LayerSpec:
    key: str
    kind: str  # "geojson" | "csv"
    relpath: str
    required: bool = False
    description: str = ""


DEFAULT_LAYER_SPECS: List[LayerSpec] = [
    # Required for Phase 9
    LayerSpec(
        key="risk_segments",
        kind="geojson",
        relpath="results/pipelines_tx_segment_risk_fixed_minlen_wgs84_reband.geojson",
        required=True,
        description="Segment-level risk output (Phase 6).",
    ),
    
    
    # Phase 7 validation artifacts
        
    LayerSpec(
        key="null_global_hist",
        kind="csv",
        relpath="results/phase7_null_global_hist.csv",
        required=False,
        description="Global null model simulation draws (Phase 7).",  
    ),
    LayerSpec(
        key="null_global",
        kind="csv",
        relpath="results/phase7_null_global.csv",
        required=False,
        description="Global null model summary stats (Phase 7).",
    ),
    # Optional (if you exported them)
    LayerSpec(
        key="hotspot_clusters",
        kind="geojson",
        relpath="results/hotspot_clusters.geojson",
        required=False,
        description="Hotspot clusters (Phase 4).",
    ),
    LayerSpec(
        key="exposure_density",
        kind="geojson",
        relpath="results/exposure_density.geojson",
        required=False,
        description="Exposure density grid/polygons (Phase 5).",
    ),
    LayerSpec(
    key="null_global_summary",
    kind="csv",
    relpath="results/phase7_null_global_summary.csv",
    required=False,
    description="Global null model summary (computed from null draws).",
    ),

]


def _safe_read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _safe_read_csv(path: Path) -> List[Dict[str, Any]]:
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


class RegionStore:
    def __init__(self, data_root: str | Path):
        self.data_root = Path(data_root).resolve()
        self.regions_root = self.data_root / "regions"

    def list_regions(self) -> List[Dict[str, str]]:
        if not self.regions_root.exists():
            return []
        out = []
        for p in sorted(self.regions_root.iterdir()):
            if p.is_dir():
                slug = p.name
                out.append(
                    {
                        "slug": slug,
                        "label": slug.upper().replace("_", "-"),
                    }
                )
        return out

    def region_path(self, slug: str) -> Path:
        return (self.regions_root / slug).resolve()

    def resolve_layer_path(self, slug: str, spec: LayerSpec) -> Path:
        region_dir = self.region_path(slug)
        region_token = slug.replace("us_", "").replace("_", "")
        # For us_tx -> "tx" token, used in your current filenames.
        # If your future naming differs, you can add a region.json mapping later.
        rel = spec.relpath.format(region=region_token)
        return region_dir / rel

    def manifest(self, slug: str, specs: Optional[List[LayerSpec]] = None) -> Dict[str, Any]:
        specs = specs or DEFAULT_LAYER_SPECS
        region_dir = self.region_path(slug)
        if not region_dir.exists():
            raise FileNotFoundError(f"Region not found: {slug}")

        layers = []
        missing_required = []

        for spec in specs:
            p = self.resolve_layer_path(slug, spec)
            exists = p.exists()
            if spec.required and not exists:
                missing_required.append(spec.key)

            layers.append(
                {
                    "key": spec.key,
                    "kind": spec.kind,
                    "exists": exists,
                    "required": spec.required,
                    "description": spec.description,
                    "path": str(p),
                }
            )

        return {
            "slug": slug,
            "layers": layers,
            "missing_required": missing_required,
        }

    def load_layer(self, slug: str, layer_key: str) -> Dict[str, Any] | List[Dict[str, Any]]:
        spec = next((s for s in DEFAULT_LAYER_SPECS if s.key == layer_key), None)
        if not spec:
            raise FileNotFoundError(f"Unknown layer: {layer_key}")

        p = self.resolve_layer_path(slug, spec)
        if not p.exists():
            raise FileNotFoundError(f"Layer file not found: {layer_key}")

        if spec.kind == "geojson":
            return _safe_read_json(p)
        if spec.kind == "csv":
            return _safe_read_csv(p)

        raise ValueError(f"Unsupported kind: {spec.kind}")
