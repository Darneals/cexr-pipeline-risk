import pandas as pd
from pathlib import Path

path = "data/raw/gtggungs2010toPresent.xlsx"
sheet = "gtggungs2010toPresent"

# Prefer incident location state over operator state if both exist
preferred = [
    "LOCATION_STATE_ABBREVIATION",
    "LOCATION_STATE",
    "STATE",
    "OPERATOR_STATE_ABBREVIATION",
]

df = pd.read_excel(path, sheet_name=sheet, nrows=5)
cols = list(df.columns)

STATE_COL = next((c for c in preferred if c in cols), None)
if not STATE_COL:
    raise SystemExit(f"No preferred state column found. Closest matches: {[c for c in cols if 'STATE' in str(c).upper()][:20]}")

# Load only the state column (fast)
df = pd.read_excel(path, sheet_name=sheet, usecols=[STATE_COL])

s = (
    df[STATE_COL]
    .astype(str)
    .str.strip()
    .replace({"nan": None, "None": None, "": None})
    .dropna()
)

counts = s.value_counts()
top_state = counts.index[0]

print("State column used:", STATE_COL)
print("Top state:", top_state)
print("\nTop 15 states by incident count:")
print(counts.head(15))

Path("data/processed").mkdir(parents=True, exist_ok=True)
counts.head(60).to_csv("data/processed/state_incident_counts.csv", header=["count"])

with open("data/processed/top_state.txt", "w", encoding="utf-8") as f:
    f.write(str(top_state))

print("\nSaved:")
print("- data/processed/state_incident_counts.csv")
print("- data/processed/top_state.txt")
