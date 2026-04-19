import os
import pandas as pd

ROOT = r"C:\projects\icvars-metaverse-pipeline-risk"
REGION = "us_tx"

hist_path = os.path.join(ROOT, "data", "regions", REGION, "results", "phase7_null_global_hist.csv")
out_path  = os.path.join(ROOT, "data", "regions", REGION, "results", "phase7_null_global_summary.csv")

df = pd.read_csv(hist_path)

required = {"null_hhi", "null_max_density"}
missing = required - set(df.columns)
if missing:
    raise SystemExit(f"Missing columns in hist file: {missing}. Found: {list(df.columns)}")

def summarize(series: pd.Series, prefix: str):
    s = pd.to_numeric(series, errors="coerce").dropna()
    return {
        f"{prefix}_mean": float(s.mean()),
        f"{prefix}_std": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
        f"{prefix}_min": float(s.min()),
        f"{prefix}_max": float(s.max()),
        f"{prefix}_p01": float(s.quantile(0.01)),
        f"{prefix}_p05": float(s.quantile(0.05)),
        f"{prefix}_p50": float(s.quantile(0.50)),
        f"{prefix}_p95": float(s.quantile(0.95)),
        f"{prefix}_p99": float(s.quantile(0.99)),
    }

summary = {"n_iter": int(len(df))}
summary.update(summarize(df["null_hhi"], "null_hhi"))
summary.update(summarize(df["null_max_density"], "null_max_density"))

pd.DataFrame([summary]).to_csv(out_path, index=False)
print("Wrote:", out_path)
print(pd.DataFrame([summary]).T)
