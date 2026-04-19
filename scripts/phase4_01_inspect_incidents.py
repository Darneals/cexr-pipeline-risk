import pandas as pd

path = "data/raw/gtggungs2010toPresent.xlsx"
df = pd.read_excel(path, sheet_name="gtggungs2010toPresent")

print("Rows:", len(df))
print("Columns:")
for c in df.columns:
    print("-", c)

print("\nHead:")
print(df.head(3))
