import geopandas as gpd
import numpy as np
import os
import pandas as pd

ROOT = r'C:\projects\icvars-metaverse-pipeline-risk\data\regions\us_tx\results_corridor'

for tag in ['5km', '10km']:
    g = gpd.read_file(os.path.join(ROOT, f'risk_windows_{tag}.geojson'))
    p = pd.to_numeric(g['p_raw'], errors='coerce')
    print(f'=== {tag} ===')
    print(f'p_raw min:              {p.min():.6f}')
    print(f'p_raw < 0.05:           {(p < 0.05).sum()}')
    print(f'p_raw < 0.10:           {(p < 0.10).sum()}')
    print(f'p_raw unique values:    {p.nunique()}')
    print(f'sd_null == 0 (degenerate): {(pd.to_numeric(g["sd_null"], errors="coerce") == 0).sum()}')
    print(f'exceedance > 0:         {(pd.to_numeric(g["exceedance"], errors="coerce") > 0).sum()}')
    print()