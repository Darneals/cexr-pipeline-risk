import json
from pathlib import Path

DEFAULT_REGION = "us_tx"

def load_region_paths(region: str = DEFAULT_REGION):
    cfg_path = Path("data") / "regions" / region / "config" / "paths.json"
    if not cfg_path.exists():
        raise SystemExit(f"Missing region config: {cfg_path}")

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    raw_dir = Path(cfg["raw_dir"])
    processed_dir = Path(cfg["processed_dir"])

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    return region, raw_dir, processed_dir
