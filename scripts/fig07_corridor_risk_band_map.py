# fig07_corridor_risk_band_map.py
# Q1-oriented styling: de-emphasize background network, emphasize higher-risk bands,
# clean legend, no title inside figure, high-res PNG + vector PDF.

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")

BOUNDARY = ROOT / "data" / "raw" / "cb_2018_us_state_500k" / "cb_2018_us_state_500k.shp"

# Pick the best available corridor file (adjust if you have a single canonical one)
CANDIDATES = [
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon_reband.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_ribbon.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km_reband.geojson",
    ROOT / "data" / "regions" / "us_tx" / "results_corridor" / "risk_windows_10km.geojson",
]

OUTDIR = ROOT / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

OUTPNG = OUTDIR / "fig07_corridor_risk_band_map.png"
OUTPDF = OUTDIR / "fig07_corridor_risk_band_map.pdf"


def pick_input() -> Path:
    for p in CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find any of:\n" + "\n".join(str(p) for p in CANDIDATES))


def _coerce_band(series: pd.Series) -> pd.Series:
    """
    Accepts 'risk_band_story' or 'risk_band_fixed' etc.
    Normalizes common variants to: Very Low, Low, Medium, High, Very High
    """
    s = series.astype(str).str.strip().str.lower()

    mapping = {
        "very low": "Very Low",
        "vlow": "Very Low",
        "low": "Low",
        "medium": "Medium",
        "med": "Medium",
        "high": "High",
        "very high": "Very High",
        "vhigh": "Very High",
    }

    # numeric fallback (1..5)
    out = s.map(mapping)
    num = pd.to_numeric(s, errors="coerce")
    out = out.fillna(
        num.map(
            {
                1: "Very Low",
                2: "Low",
                3: "Medium",
                4: "High",
                5: "Very High",
            }
        )
    )

    return out


def main():
    src = pick_input()

    texas = gpd.read_file(BOUNDARY)
    texas = texas[texas["NAME"] == "Texas"].copy()

    gdf = gpd.read_file(src)

    # ---- Choose risk band column (robust) ----
    band_col = None
    for c in ["risk_band_story", "risk_band_fixed", "risk_band", "band"]:
        if c in gdf.columns:
            band_col = c
            break
    if band_col is None:
        raise KeyError(
            f"No risk-band column found in {src.name}. "
            f"Tried: risk_band_story, risk_band_fixed, risk_band, band. "
            f"Found: {list(gdf.columns)[:40]} ..."
        )

    gdf["band"] = _coerce_band(gdf[band_col])

    order = ["Very Low", "Low", "Medium", "High", "Very High"]
    gdf["band"] = pd.Categorical(gdf["band"], categories=order, ordered=True)

    # Drop rows with unknown band
    gdf = gdf.dropna(subset=["band"]).copy()

    # ---- Reproject to lon/lat for stable plotting & aspect ----
    texas_ll = texas.to_crs("EPSG:4326")
    gdf_ll = gdf.to_crs("EPSG:4326")

    # ---- Palette (kept consistent with your legend intent) ----
    colors = {
        "Very Low": "#2ecc71",   # green
        "Low": "#27ae60",        # darker green
        "Medium": "#f1c40f",     # yellow
        "High": "#e67e22",       # orange
        "Very High": "#e74c3c",  # red
    }

    # ---- Layer strategy (THIS is the Q1 upgrade) ----
    # 1) Plot ALL corridors as faint context (light gray) to avoid “all-green” dominance
    # 2) Re-plot each band on top with increasing linewidth + opacity for higher risk
    # 3) Clean legend (patches) + no title inside plot

    fig, ax = plt.subplots(figsize=(10.5, 10.5))  # slightly tighter than 12x12 for print layouts

    # Texas outline: crisp but not overpowering
    texas_ll.boundary.plot(ax=ax, linewidth=2.0, color="black")

    # Base network: faint neutral context
    try:
        gdf_ll.plot(ax=ax, linewidth=0.10, alpha=0.15, color="#9aa0a6")  # neutral gray
    except Exception:
        gdf_ll.boundary.plot(ax=ax, linewidth=0.10, alpha=0.15, color="#9aa0a6")

    # Band emphasis settings (higher band = more visible)
    lw = {"Very Low": 0.18, "Low": 0.22, "Medium": 0.45, "High": 0.75, "Very High": 1.10}
    al = {"Very Low": 0.25, "Low": 0.35, "Medium": 0.70, "High": 0.85, "Very High": 0.95}

    for b in order:
        sub = gdf_ll[gdf_ll["band"] == b]
        if len(sub) == 0:
            continue

        # If polygons, using boundary often reads cleaner for corridor “ribbons”
        geom_types = set(sub.geometry.geom_type.unique())
        use_boundary = any(t in {"Polygon", "MultiPolygon"} for t in geom_types)

        if use_boundary:
            sub.boundary.plot(ax=ax, linewidth=lw[b], alpha=al[b], color=colors[b])
        else:
            sub.plot(ax=ax, linewidth=lw[b], alpha=al[b], color=colors[b])

    ax.set_axis_off()
    ax.set_aspect("auto")  # prevents the geopandas aspect crash in some setups

    # Legend (clean, fixed order)
    handles = [Patch(facecolor=colors[b], edgecolor="none", label=b) for b in order]
    leg = ax.legend(
        handles=handles,
        title="Corridor Risk Band",
        loc="lower left",
        frameon=True,
        framealpha=0.95,
    )
    leg._legend_box.align = "left"

    plt.savefig(OUTPNG, dpi=600, bbox_inches="tight")
    plt.savefig(OUTPDF, bbox_inches="tight")
    plt.close()

    # Basic readout (helps you sanity-check skew)
    counts = gdf["band"].value_counts().reindex(order).fillna(0).astype(int)
    print("Input:", src)
    print("Band counts:\n", counts.to_string())
    print("Saved:", OUTPNG)
    print("Saved:", OUTPDF)


if __name__ == "__main__":
    main()