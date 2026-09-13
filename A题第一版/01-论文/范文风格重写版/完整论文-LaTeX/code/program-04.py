"""Bounded radial-resolution probe for V02/V06 repair."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from formal_compute import RunConfig, simulate

CASES = [
    ("Q1-M1", 1, "M1", 0.5, 1800, [81, 122, 183]),
    ("Q1-M2", 54, "M2", 0.5, 1800, [62, 93, 140]),
    ("Q2-M3", 36, "M3", 5.0, 10800, [62, 93, 140]),
    ("Q3-M3", 36, "M3", 60.0, 259200, [62, 93, 140, 210]),
    ("Q4-M3", 32, "M3", 60.0, 259200, [93, 140, 210]),
]

ap=argparse.ArgumentParser(); ap.add_argument("--family"); args=ap.parse_args()
rows=[]
for family,nz,model,dt,duration,nrs in CASES:
    if args.family and family != args.family:
        continue
    q = 1 if family.startswith("Q1") else (2 if family.startswith("Q2") else (3 if family.startswith("Q3") else 4))
    for nr in nrs:
        cfg=RunConfig(f"probe-{family}-nr{nr}",nr,nz,dt,duration,q,model,
                      moving_impl=("reference" if q==4 else "fixed"),
                      stop_threshold=(.15-1e-6 if q in (3,4) else None),sample_every=duration)
        r=simulate(cfg)
        row={"family":family,"nr":nr,"nz":nz,"dt_s":dt,
             "grid_strategy":cfg.radial_strategy,
             "final_max_C":r["metrics"]["final_max_C"],
             "final_mean_C":r["metrics"]["final_mean_C"],
             "event_time_s":r["metrics"]["interpolated_event_time_s"],
             "reported_event_time_s":r["metrics"]["reported_event_time_s"],
             "runtime_s":r["metrics"]["runtime_s"]}
        rows.append(row); print(json.dumps(row,ensure_ascii=False),flush=True)

out=Path(__file__).resolve().parents[1]/"results"/"repair-probe.json"
out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")

