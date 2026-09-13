"""Candidate Q2 spatial-grid extension at the frozen formal time step dt=5 s.

This runs only additional Q2/M3 grid levels and writes an isolated candidate
package; it does not overwrite 04-compute/results.
"""
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04-compute" / "src"))
import formal_compute as fc  # noqa: E402

OUT = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-space-dt5"
OUT.mkdir(parents=True, exist_ok=True)

rows = []
previous = None
for nr in (42, 62, 93, 140, 175, 210):
    result = fc.simulate(fc.RunConfig(
        label=f"Q2-M3-nr{nr}-dt5",
        nr=nr, nz=36, dt=5, duration=10800, q=2, model="M3", sample_every=3600,
    ))
    value = float(result["metrics"]["final_max_C"])
    change = "" if previous is None else abs(value - previous)
    rows.append({
        "scope": "Q2", "family": "M3", "level": len(rows) + 1,
        "nr": nr, "nz": 36, "fixed_dt_s": 5.0,
        "metric": "final_max_C", "value": value,
        "adjacent_change": change,
        "runtime_s": result["metrics"]["runtime_s"],
    })
    previous = value

path = OUT / "field-grid-convergence.csv"
with path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(path)

