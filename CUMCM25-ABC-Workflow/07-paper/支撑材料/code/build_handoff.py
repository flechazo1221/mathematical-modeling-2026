from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "04-compute"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def record(path: Path) -> dict:
    return {"path": rel(path), "sha256": digest(path)}


def dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_csv(name: str) -> list[dict]:
    with (STAGE / "results" / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable (not required by the built-in XLSX reader)"


def main() -> None:
    full = json.loads((STAGE / "logs" / "full-run.json").read_text(encoding="utf-8"))
    structural = json.loads((STAGE / "results" / "structural_feasibility.json").read_text(encoding="utf-8"))
    failures = read_csv("failure_summary.csv")
    pressure = read_csv("fft_pressure_test.csv")
    max_pressure = {}
    for variant in sorted({row["variant"] for row in pressure}):
        values = [float(row["relative_change_vs_approved_F"]) for row in pressure
                  if row["variant"] == variant and row["relative_change_vs_approved_F"]]
        max_pressure[variant] = max(values) if values else None

    evidence = {
        "schema_version": "1.0",
        "stage": "COMPUTE",
        "truth_boundary": "Observed checks measure internal consistency only; no independent thickness truth is available.",
        "claims": [
            {"id": "C01", "claim": "Frozen F is structurally feasible on the approved synthetic grid.",
             "evidence": ["04-compute/results/structural_feasibility.json", "04-compute/results/synthetic_recovery.csv"],
             "key_values": structural},
            {"id": "C02", "claim": "All fixed windows, both angles, and raw/reasoned masks were reported for B/F/P.",
             "evidence": ["04-compute/results/observed_all_models.csv", "04-compute/results/validation_metrics.csv"],
             "key_values": {"observed_rows": full["row_counts"]["observed"], "validation_rows": full["row_counts"]["validations"]}},
            {"id": "C03", "claim": "Failures are retained; P remains supplementary and M remains closed.",
             "evidence": ["04-compute/results/failure_summary.csv", "04-compute/results/M_diagnostic.json"],
             "key_values": {"failure_summary": failures}},
            {"id": "C04", "claim": "Zero padding and taper changes are diagnostic pressure tests and do not replace approved F.",
             "evidence": ["04-compute/results/fft_pressure_test.csv", "04-compute/diagnostic-figures/diagnostic_fft_pressure.png"],
             "key_values": {"maximum_relative_change_vs_approved_F": max_pressure}},
            {"id": "C05", "claim": "Only q and conditional d(n) are reported; no unique true thickness is claimed.",
             "evidence": ["04-compute/results/conditional_sensitivity.csv"],
             "key_values": {"rows": full["row_counts"]["conditional_sensitivity"]}},
        ],
        "diagnostic_figures_only": True,
    }
    dump(STAGE / "证据索引.json", evidence)

    input_paths = [
        ROOT / "decisions" / "H1-problem.json",
        ROOT / "decisions" / "H2-model.json",
        ROOT / "decisions" / "prototype-authorization.json",
        ROOT / "02-design" / "验证计划.json",
        ROOT / "03-prototype" / "预注册规则.json",
        ROOT / "03-prototype" / "run_prototypes.py",
        *(ROOT / "input" / "B题" / "附件" / f"附件{i}.xlsx" for i in range(1, 5)),
    ]
    output_paths = sorted(
        [p for p in STAGE.rglob("*") if p.is_file() and p.name not in {"handoff.json", "handoff.sha256", "复现清单.json"}],
        key=lambda p: rel(p),
    )
    manifest = {
        "schema_version": "1.0",
        "stage": "COMPUTE",
        "seed": 20260907,
        "parameters": {
            "windows_cm_inv": [[600.0, 1600.0], [1600.0, 2800.0], [2800.0, 3800.0]],
            "masks": ["raw", "reasoned"], "angles_deg": [10, 15],
            "F": "n-point Hann rFFT; discrete peak from bin 2 onward; no zero padding or sub-grid interpolation",
            "P": "401-point discrete frequency grid; no sub-grid interpolation; supplementary diagnostic only",
            "M": "closed",
        },
        "commands": [
            "python 04-compute/src/run_compute.py --smoke",
            "python 04-compute/src/run_compute.py",
            "python 04-compute/src/build_handoff.py",
        ],
        "working_directory": ".",
        "environment": {
            "python": sys.version, "platform": platform.platform(),
            "packages": {name: package_version(name) for name in ("numpy", "matplotlib", "openpyxl")},
        },
        "inputs": [record(p) for p in input_paths],
        "outputs_before_manifest": [record(p) for p in output_paths],
        "key_values": {"runtime_s": full["runtime_s"], "row_counts": full["row_counts"], "structural": structural,
                       "maximum_fft_pressure_relative_change": max_pressure},
    }
    dump(STAGE / "复现清单.json", manifest)

    handoff_outputs = sorted(
        [p for p in STAGE.rglob("*") if p.is_file() and p.name not in {"handoff.json", "handoff.sha256"}],
        key=lambda p: rel(p),
    )
    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    handoff = {
        "schema_version": "1.0", "stage": "COMPUTE", "status": "PASS",
        "inputs": [record(p) for p in input_paths],
        "outputs": [record(p) for p in handoff_outputs],
        "frozen_decisions": [record(ROOT / "decisions" / "H1-problem.json"), record(ROOT / "decisions" / "H2-model.json")],
        "assumptions": ["Only team-approved H1 assumptions and A1-A7 were used; no new structural, parameter, or conclusion-affecting assumption was introduced."],
        "unknowns": ["Material-specific n(sigma), k(sigma), angle-error magnitude, instrument resolution, coherence length, and independent thickness truth remain unavailable.",
                     "Observed cross-window, dual-angle, and mask checks establish internal consistency or sensitivity, not true accuracy."],
        "claims": ["B and frozen F were computed in full; P was retained only as a supplementary diagnostic and M remained closed.",
                   "Frozen F passed all 144 approved synthetic cases and is structurally feasible under the approved calibration model.",
                   "All three fixed windows, two angles, and raw/reasoned mask pairs are preserved in the result tables.",
                   "Outputs report optical thickness q and conditional d(n), not a unique true thickness."],
        "evidence": ["04-compute/证据索引.json maps each claim to real result tables and diagnostic figures.",
                     "04-compute/复现清单.json records hashes, seed, environment, parameters, commands, and key values.",
                     "04-compute/logs/恢复审查记录.md and p1-independent-review.json preserve the prior deviation and independent recovery PASS."],
        "warnings": ["The earlier stopped COMPUTE implementation deviated via 8x zero padding/sub-grid F and 601-point/sub-grid P; the failure history is retained in the recovery log.",
                     "Diagnostic zero-padding/taper variants change q by as much as recorded in fft_pressure_test.csv and must not replace the approved F result.",
                     "P synthetic failures and all B/P status codes are retained; no failures may be hidden.",
                     "No result is a claim of observed true-thickness accuracy."],
        "required_next_actions": ["Workflow control must validate the handoff schema and all listed hashes before any EVIDENCE task.",
                                  "The team must review and approve the claim boundary at H3 before downstream evidence writing."],
        "completed_at": now,
    }
    dump(STAGE / "handoff.json", handoff)
    (STAGE / "handoff.sha256").write_text(digest(STAGE / "handoff.json") + "  handoff.json\n", encoding="ascii")
    print(json.dumps({"status": "PASS", "outputs": len(handoff_outputs), "handoff_sha256": digest(STAGE / "handoff.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
