from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06-figure"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


manifest = json.loads((OUT / "figure-manifest.json").read_text(encoding="utf-8"))
failures = []
active = set(manifest.get("main_figures", []) + manifest.get("appendix_figures", []))
forbidden_ids = {"FIG-Q3-TIME-CONV", "FIG-Q3-COMBINED-BOUNDARY", "FIG-Q4-COMBINED-BOUNDARY"}
if active & forbidden_ids:
    failures.append(f"legacy figure IDs remain active: {sorted(active & forbidden_ids)}")
if manifest.get("n_figures") != len(active) or len(active) != 13:
    failures.append("active manifest count is not 13")

new_renderer = OUT / "scripts" / "revise_q2_figures_20260913.py"
if not new_renderer.exists():
    failures.append("new renderer missing: revise_q2_figures_20260913.py")

checks = {}
for fid in active:
    item = next((x for x in manifest.get("items", []) if x.get("id") == fid), None)
    if not item:
        failures.append(f"missing manifest item: {fid}")
        continue
    for key in ("png", "svg"):
        path = ROOT / item[key]
        if not path.exists():
            failures.append(f"missing {key}: {fid}")
        elif item.get(f"{key}_sha256") and sha(path) != item[f"{key}_sha256"]:
            failures.append(f"hash mismatch: {fid} {key}")

f4 = read_csv(OUT / "data-snapshots" / "FIG-Q2-MODEL-ABLATION.csv")
counts = {}
for row in f4:
    counts[row["model"]] = counts.get(row["model"], 0) + 1
checks["FIG-Q2-MODEL-ABLATION"] = {"rows": len(f4), "rows_per_model": counts}
if len(f4) != 57 or set(counts.values()) != {19}:
    failures.append("Figure 4 is not 3 models x 19 time points")

f5 = read_csv(OUT / "data-snapshots" / "FIG-Q2-GRID-CONV.csv")
nr5 = sorted({int(float(row["nr"])) for row in f5})
checks["FIG-Q2-GRID-CONV"] = {"radial_grids": nr5, "count": len(nr5)}
if nr5 != [42, 62, 93, 140, 175, 210]:
    failures.append(f"Figure 5 radial grids unexpected: {nr5}")

for fid in ("FIG-Q3-SPACE-CONV", "FIG-Q4-SPACE-CONV"):
    rows = read_csv(OUT / "data-snapshots" / f"{fid}.csv")
    nrs = sorted({int(float(row["nr"])) for row in rows})
    checks[fid] = {"radial_grids": nrs, "count": len(nrs)}
    if nrs != [63, 93, 140, 175, 210]:
        failures.append(f"{fid} radial grids unexpected: {nrs}")

report = {
    "status": "PASS" if not failures else "FAIL",
    "pipeline": "CURRENT_20260913",
    "active_figure_count": len(active),
    "new_renderer": str(new_renderer.relative_to(ROOT)).replace("\\", "/"),
    "checks": checks,
    "failures": failures,
}
(OUT / "current-pipeline-verification.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(bool(failures))
