from pathlib import Path
import re

root = Path(r"C:\projects\icvars-metaverse-pipeline-risk")
pat = re.compile(r"\bp_fdr\b", re.I)

hits = 0
for p in root.rglob("*.py"):
    t = p.read_text(encoding="utf-8", errors="ignore")
    if pat.search(t):
        hits += 1
        print(f"\n=== {p} ===")
        for i, line in enumerate(t.splitlines(), 1):
            if pat.search(line):
                print(f"{i:4d}: {line}")

print("\nTOTAL FILES WITH p_fdr:", hits)