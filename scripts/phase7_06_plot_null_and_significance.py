import pandas as pd
import matplotlib.pyplot as plt

global_csv = "data/processed/phase7_segment_null_global.csv"
hist_csv   = "data/processed/phase7_null_global_hist.csv"
sig_csv    = "data/processed/phase7_segment_significance.csv"

out1 = "data/processed/fig_phase7_null_hhi.png"
out2 = "data/processed/fig_phase7_null_maxdens.png"
out3 = "data/processed/fig_phase7_qvalue_hist.png"

g = pd.read_csv(global_csv).iloc[0]
h = pd.read_csv(hist_csv)
s = pd.read_csv(sig_csv)

# HHI null vs observed
plt.figure()
plt.hist(h["null_hhi"], bins=30)
plt.axvline(g["obs_hhi"])
plt.title("Null vs Observed: HHI (segment-opportunity null)")
plt.xlabel("HHI")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(out1, dpi=200)
plt.close()

# Max density null vs observed
plt.figure()
plt.hist(h["null_max_density"], bins=30)
plt.axvline(g["obs_max_density"])
plt.title("Null vs Observed: Max incident density")
plt.xlabel("Max incident density (incidents/km)")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(out2, dpi=200)
plt.close()

# Q-values distribution
plt.figure()
plt.hist(s["q_fdr_bh"], bins=30)
plt.title("BH-FDR q-values across segments")
plt.xlabel("q-value")
plt.ylabel("Count of segments")
plt.tight_layout()
plt.savefig(out3, dpi=200)
plt.close()

print("Saved:", out1)
print("Saved:", out2)
print("Saved:", out3)
