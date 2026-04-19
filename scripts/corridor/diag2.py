import geopandas as gpd
import pandas as pd
from pathlib import Path

for state in ['us_tx', 'us_la', 'us_ok']:
    p = Path(f'data/regions/{state}/results_corridor/risk_windows_5km_ribbon.geojson')
    gdf = gpd.read_file(p)
    gdf['_sig'] = gdf['significant_fdr05'].apply(lambda v: v is True or str(v).lower() in ('true', '1'))
    sig = gdf[gdf['_sig']]
    if not sig.empty:
        b = sig.total_bounds
        w = b[2]-b[0]
        h = b[3]-b[1]
        first = sig.geometry.iloc[0]
        print(f'{state}: sig={len(sig)}, full extent={w:.2f}x{h:.2f} deg, first poly area={first.area:.8f} deg2')