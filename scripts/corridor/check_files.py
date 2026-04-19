import os
from pathlib import Path

dirs = [
    'data/regions/us_tx/results_corridor',
    'data/regions/us_la/results_corridor',
    'data/regions/us_ok/results_corridor',
]

for d in dirs:
    print(f'\n=== {d} ===')
    p = Path(d)
    if p.exists():
        for f in sorted(p.iterdir()):
            if f.suffix in ['.csv', '.geojson']:
                size = round(f.stat().st_size/1024/1024, 1)
                print(f'  {f.name} ({size}MB)')
    else:
        print('  NOT FOUND')