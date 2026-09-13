from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04-compute" / "src"))
import formal_compute as fc  # noqa: E402

OUT = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "space-extra-dt60"
OUT.mkdir(parents=True, exist_ok=True)

rows = []
for scope, nr, nz, q, model, moving_impl in [
    ("Q3", 63, 36, 3, "M3", "fixed"),
    ("Q3", 175, 36, 3, "M3", "fixed"),
    ("Q4", 63, 32, 4, "M3", "reference"),
    ("Q4", 175, 32, 4, "M3", "reference"),
]:
    result = fc.simulate(fc.RunConfig(
        label=f"{scope}-M3-nr{nr}-dt60-extra", nr=nr, nz=nz, dt=60,
        duration=259200, q=q, model=model, moving_impl=moving_impl,
        stop_threshold=0.15 - 1e-6, sample_every=60,
    ))
    rows.append({
        "scope": scope, "nr": nr, "nz": nz, "grid_strategy": "two-sided-local",
        "fixed_dt_s": 60, "interpolated_event_time_s": result["metrics"]["interpolated_event_time_s"],
        "reported_event_time_s": result["metrics"]["reported_event_time_s"],
    })

path = OUT / "threshold-grid-extra.csv"
with path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
print(path)

