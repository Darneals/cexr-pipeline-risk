import pandas as pd

path = "data/raw/gtggungs2010toPresent.xlsx"
sheet = "gtggungs2010toPresent"

df = pd.read_excel(path, sheet_name=sheet, nrows=5)  # only sample rows for speed

cols = list(df.columns)

def find_cols(keyword_list):
    hits = []
    for c in cols:
        cu = str(c).upper()
        if any(k in cu for k in keyword_list):
            hits.append(c)
    return hits

state_hits = find_cols(["STATE", "STUSPS"])
lat_hits   = find_cols(["LAT"])
lon_hits   = find_cols(["LON", "LONG"])

print("Possible STATE columns:")
for c in state_hits[:30]:
    print("-", c)

print("\nPossible LAT columns:")
for c in lat_hits[:30]:
    print("-", c)

print("\nPossible LON/LONG columns:")
for c in lon_hits[:30]:
    print("-", c)
