import pandas as pd
import geopandas as gpd
import os

df = pd.read_excel('data/raw/gtggungs2010toPresent.xlsx',
                   sheet_name='gtggungs2010toPresent',
                   usecols=['ONSHORE_STATE_ABBREVIATION', 'LOCATION_LATITUDE', 'LOCATION_LONGITUDE'])

for st in ['LA', 'OK']:
    sub = df[df['ONSHORE_STATE_ABBREVIATION'] == st].dropna(subset=['LOCATION_LATITUDE', 'LOCATION_LONGITUDE'])
    print(f'{st}: {len(sub)} incidents with valid coords')
    print(f'  lat range: {sub.LOCATION_LATITUDE.min():.2f} to {sub.LOCATION_LATITUDE.max():.2f}')
    print(f'  lon range: {sub.LOCATION_LONGITUDE.min():.2f} to {sub.LOCATION_LONGITUDE.max():.2f}')

if os.path.exists('data/raw/Natural_Gas_Interstate_and_Intrastate_Pipelines.shp'):
    pipes = gpd.read_file('data/raw/Natural_Gas_Interstate_and_Intrastate_Pipelines.shp')
elif os.path.exists('pipelines.csv'):
    pipes = gpd.read_file('pipelines.csv')
else:
    pipes = gpd.read_file('data/processed/pipelines_tx.geojson')

print(f'Pipeline rows available: {len(pipes)}')