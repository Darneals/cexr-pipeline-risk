import pandas as pd

for state in ['us_tx', 'us_la', 'us_ok']:
    for res in ['5km', '10km']:
        df = pd.read_csv(f'data/regions/{state}/results_corridor/corridor_fdr_{res}.csv')
        df['state'] = state
        df.to_csv(f'corridor_fdr_{state}_{res}.csv', index=False)
        print(f'Saved: corridor_fdr_{state}_{res}.csv')