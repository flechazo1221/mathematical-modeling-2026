from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04-compute" / "src"))
import formal_compute as fc  # noqa: E402

OUT = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-model-trajectories"
OUT.mkdir(parents=True, exist_ok=True)

configs = [
    ("M2 常物性", 18, 36, 10.0, "M2"),
    ("M3 主路线", 140, 36, 5.0, "M3"),
    ("M4 温度耦合消融", 18, 36, 10.0, "M4"),
]
rows = []
for label, nr, nz, dt, model in configs:
    result = fc.simulate(fc.RunConfig(
        label=f"Q2-{model}-trajectory", nr=nr, nz=nz, dt=dt,
        duration=10800, q=2, model=model, sample_every=600,
    ))
    for rec in result["records"]:
        rows.append({"model": label, "time_s": rec["time_s"], "max_C": rec["max_C"], "mean_C": rec["mean_C"]})

path = OUT / "q2-model-trajectories.csv"
with path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
print(path)
