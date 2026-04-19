import pandas as pd

df = pd.read_excel('data/raw/gtggungs2010toPresent.xlsx',
                   sheet_name='gtggungs2010toPresent',
                   usecols=['ONSHORE_STATE_ABBREVIATION', 'LOCATION_LATITUDE', 'LOCATION_LONGITUDE'])

df = df.dropna(subset=['LOCATION_LATITUDE', 'LOCATION_LONGITUDE'])
counts = df['ONSHORE_STATE_ABBREVIATION'].value_counts()
print(counts.head(15))