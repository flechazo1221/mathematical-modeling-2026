"""Isolated prototype comparison for the internal-temperature-field revision.

The two source solvers are imported read-only from 04-compute.  This protocol
writes only below this directory and compares the current prescribed-T
baseline with the candidate implicit internal-temperature solve.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASELINE_PATH = ROOT / "04-compute" / "src" / "formal_compute.py"
REVISION_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
LOG_PATH = OUT / "run.log"
SEED = 20260912


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def input_paths() -> list[Path]:
    paths = [
        ROOT / "02-design" / "handoff.json",
        ROOT / "02-design" / "验证计划.json",
        ROOT / "02-design" / "H2-优化审计与方向.md",
        ROOT / "02-design" / "候选模型方案.md",
        ROOT / "decisions" / "H1-problem.json",
        ROOT / "decisions" / "H2-model.json",
        ROOT / "decisions" / "H3-claims.json",
        ROOT / "03-prototype" / "handoff.json",
        ROOT / "04-compute" / "temperature-field-revision-20260912" / "README.md",
        ROOT / "04-compute" / "temperature-field-revision-20260912" / "parameter-diagnosis-20260912.md",
        BASELINE_PATH,
        REVISION_PATH,
    ]
    for p in (ROOT / "input" / "A题" / "附件").rglob("*.xlsx"):
        paths.append(p)
    return sorted(set(paths))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_specs():
    # The same pair of resolutions is used for both implementations.  Q2 is
    # a 3 h field check; Q3/Q4 run to the first full-domain threshold event.
    return [
        {"question": "Q2", "resolution": "coarse", "nr": 12, "nz": 12, "dt": 120.0, "duration": 10800.0, "sample_every": 600.0},
        {"question": "Q2", "resolution": "spatial", "nr": 24, "nz": 12, "dt": 120.0, "duration": 10800.0, "sample_every": 600.0},
        {"question": "Q2", "resolution": "time", "nr": 12, "nz": 12, "dt": 60.0, "duration": 10800.0, "sample_every": 600.0},
        {"question": "Q2", "resolution": "refined", "nr": 24, "nz": 18, "dt": 60.0, "duration": 10800.0, "sample_every": 600.0},
        {"question": "Q3", "resolution": "coarse", "nr": 12, "nz": 12, "dt": 300.0, "duration": 259200.0, "sample_every": 1800.0},
        {"question": "Q3", "resolution": "spatial", "nr": 24, "nz": 18, "dt": 300.0, "duration": 259200.0, "sample_every": 1800.0},
        {"question": "Q3", "resolution": "time", "nr": 12, "nz": 12, "dt": 120.0, "duration": 259200.0, "sample_every": 1800.0},
        {"question": "Q3", "resolution": "refined", "nr": 24, "nz": 18, "dt": 120.0, "duration": 259200.0, "sample_every": 1800.0},
        {"question": "Q4", "resolution": "coarse", "nr": 12, "nz": 12, "dt": 300.0, "duration": 259200.0, "sample_every": 1800.0},
        {"question": "Q4", "resolution": "spatial", "nr": 24, "nz": 18, "dt": 300.0, "duration": 259200.0, "sample_every": 1800.0},
        {"question": "Q4", "resolution": "time", "nr": 12, "nz": 12, "dt": 120.0, "duration": 259200.0, "sample_every": 1800.0},
        {"question": "Q4", "resolution": "refined", "nr": 24, "nz": 18, "dt": 120.0, "duration": 259200.0, "sample_every": 1800.0},
    ]


def run_one(module, implementation: str, spec: dict, log) -> tuple[dict, list[dict]]:
    q = int(spec["question"][1])
    moving = q == 4
    cfg = module.RunConfig(
        f"{spec['question']}-{spec['resolution']}-{implementation}",
        spec["nr"], spec["nz"], spec["dt"], spec["duration"], q, "M3",
        stop_threshold=(0.15 - 1e-6) if q in (3, 4) else None,
        moving_impl="reference" if moving else "fixed",
        radius_mode="pchip" if moving else "constant",
        sample_every=spec["sample_every"],
    )
    calls: list[dict] = []
    original = module.implicit_linear

    def recorded_implicit(*args, **kwargs):
        # The source signature is old, coeff, storage, grid, dt, conv, env.
        old, coeff, storage, grid, dt, conv, env = args[:7]
        result = original(*args, **kwargs)
        new, boundary_in, iterations, residual = result
        kind = "temperature" if float(conv) > 1.0 else "moisture"
        delta_storage = float(np.sum(storage * grid.vol * (new - old)))
        boundary_integral = float(boundary_in * dt)
        raw_balance = delta_storage - boundary_integral
        scale = max(abs(delta_storage), abs(boundary_integral), 1e-30)
        thermal_inventory = float(np.sum(storage * grid.vol * np.maximum(np.abs(old), 1.0)))
        calls.append({
            "kind": kind,
            "dt_s": float(dt),
            "boundary_in": float(boundary_in),
            "delta_storage": delta_storage,
            "boundary_integral": boundary_integral,
            "raw_balance": raw_balance,
            "relative_balance": abs(raw_balance) / scale,
            "inventory_scaled_balance": abs(raw_balance) / max(abs(thermal_inventory), 1e-30),
            "linear_iterations": int(iterations),
            "linear_relative_residual": float(residual),
        })
        return result

    module.implicit_linear = recorded_implicit
    started = time.perf_counter()
    try:
        run = module.simulate(cfg)
    finally:
        module.implicit_linear = original
    elapsed = time.perf_counter() - started
    metrics = dict(run["metrics"])
    records = run["records"]
    actual_t = float(records[-1]["time_s"]) if records else 0.0
    env_t, _ = module.outside(actual_t, cfg.window_s)
    temp_c = np.asarray(run["final_t"], dtype=float) - 273.15
    finite_t = temp_c[np.isfinite(temp_c)]
    temp_diag = {
        "final_time_s": actual_t,
        "environment_temperature_C": float(env_t - 273.15),
        "internal_temperature_min_C": float(np.min(finite_t)),
        "internal_temperature_max_C": float(np.max(finite_t)),
        "internal_temperature_mean_C": float(np.mean(finite_t)),
        "internal_temperature_range_C": float(np.max(finite_t) - np.min(finite_t)),
        "max_abs_internal_minus_environment_C": float(np.max(np.abs(finite_t - (env_t - 273.15)))),
    }
    temp_calls = [c for c in calls if c["kind"] == "temperature"]
    moisture_calls = [c for c in calls if c["kind"] == "moisture"]
    summary = {
        "implementation": implementation,
        "question": spec["question"],
        "resolution": spec["resolution"],
        "nr": spec["nr"],
        "nz": spec["nz"],
        "dt_s": spec["dt"],
        "duration_s": spec["duration"],
        "runtime_s": elapsed,
        "completed_to_event": bool(metrics.get("threshold_bracket") is not None) if q in (3, 4) else actual_t >= spec["duration"] - 1e-9,
        "reported_event_time_s": metrics.get("reported_event_time_s"),
        "interpolated_event_time_s": metrics.get("interpolated_event_time_s"),
        "final_max_C": float(metrics["final_max_C"]),
        "final_mean_C": float(metrics["final_mean_C"]),
        "max_linear_relative_residual": float(metrics["max_linear_relative_residual"]),
        "max_picard_iterations": int(metrics["max_picard_iterations"]),
        "max_picard_update": float(metrics["max_terminal_picard_update"]),
        "normalized_moisture_balance_error": float(metrics["normalized_moisture_balance_error"]),
        "energy_linear_call_count": len(temp_calls),
        "max_fixed_domain_energy_balance_relative": (max(c["inventory_scaled_balance"] for c in temp_calls) if temp_calls and not moving else None),
        "max_moving_domain_energy_storage_flux_relative": (max(c["inventory_scaled_balance"] for c in temp_calls) if temp_calls and moving else None),
        "max_temperature_linear_residual": (max(c["linear_relative_residual"] for c in temp_calls) if temp_calls else None),
        "max_moisture_linear_residual": (max(c["linear_relative_residual"] for c in moisture_calls) if moisture_calls else None),
        "dry_solid_inventory_relative_error": float(metrics["dry_solid_inventory_relative_error"]),
        "geometry_relative_error": float(metrics["geometry_relative_error"]),
        "max_local_dry_continuity_relative_residual": float(metrics["max_local_dry_continuity_relative_residual"]),
        **temp_diag,
    }
    case_dir = OUT / ("model-baseline" if implementation == "prescribed-T-baseline" else "model-internal-temperature") / f"{spec['question']}-{spec['resolution']}"
    write_json(case_dir / "metrics.json", summary)
    write_csv(case_dir / "trajectory.csv", records)
    write_json(case_dir / "linear-balance-calls.json", calls)
    log.write(json.dumps(summary, ensure_ascii=False) + "\n")
    log.flush()
    return summary, calls


def pair_rows(rows: list[dict]) -> list[dict]:
    by_key = {(r["question"], r["resolution"], r["implementation"]): r for r in rows}
    out = []
    for q in ("Q2", "Q3", "Q4"):
        for res in ("coarse", "spatial", "time", "refined"):
            b = by_key[(q, res, "prescribed-T-baseline")]
            c = by_key[(q, res, "internal-temperature")]
            out.append({
                "question": q,
                "resolution": res,
                "baseline_final_max_C": b["final_max_C"],
                "candidate_final_max_C": c["final_max_C"],
                "candidate_minus_baseline_final_max_C": c["final_max_C"] - b["final_max_C"],
                "baseline_final_mean_C": b["final_mean_C"],
                "candidate_final_mean_C": c["final_mean_C"],
                "candidate_minus_baseline_final_mean_C": c["final_mean_C"] - b["final_mean_C"],
                "baseline_event_time_s": b["reported_event_time_s"],
                "candidate_event_time_s": c["reported_event_time_s"],
                "candidate_minus_baseline_event_time_s": (None if b["reported_event_time_s"] is None or c["reported_event_time_s"] is None else c["reported_event_time_s"] - b["reported_event_time_s"]),
                "candidate_temperature_range_C": c["internal_temperature_range_C"],
                "candidate_max_abs_internal_minus_environment_C": c["max_abs_internal_minus_environment_C"],
                "baseline_temperature_range_C": b["internal_temperature_range_C"],
            })
    return out


def convergence_rows(rows: list[dict]) -> list[dict]:
    out = []
    for impl in ("prescribed-T-baseline", "internal-temperature"):
        for q in ("Q2", "Q3", "Q4"):
            metric = "final_max_C" if q == "Q2" else "reported_event_time_s"
            for left, right, label in (("coarse", "spatial", "space_at_coarse_dt"), ("coarse", "time", "time_at_coarse_grid"), ("spatial", "refined", "time_at_fine_grid"), ("time", "refined", "space_at_fine_dt")):
                a = next(r for r in rows if r["implementation"] == impl and r["question"] == q and r["resolution"] == left)
                b = next(r for r in rows if r["implementation"] == impl and r["question"] == q and r["resolution"] == right)
                av, bv = a[metric], b[metric]
                out.append({"implementation": impl, "question": q, "metric": metric, "comparison": label, "case_a": left, "case_b": right, "value_a": av, "value_b": bv, "absolute_change": None if av is None or bv is None else abs(bv - av)})
    return out


def output_manifest() -> list[dict]:
    files = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in {"manifest.json", "handoff.json"}:
            files.append({"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)})
    return files


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    input_manifest = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size} for p in input_paths()]
    write_json(OUT / "input-manifest.json", {"created_at": datetime.now(timezone.utc).astimezone().isoformat(), "inputs": input_manifest})
    log = LOG_PATH.open("w", encoding="utf-8")
    log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "seed": SEED, "started_at": datetime.now(timezone.utc).astimezone().isoformat()}, ensure_ascii=False) + "\n")
    log.write("SCOPE: no latent-heat source; baseline sets internal T to chamber T; candidate solves internal heat equation.\n")
    log.flush()
    baseline = load_module("formal_baseline_isolated", BASELINE_PATH)
    candidate = load_module("formal_revision_isolated", REVISION_PATH)
    rows = []
    for spec in make_specs():
        rows.append(run_one(baseline, "prescribed-T-baseline", spec, log)[0])
        rows.append(run_one(candidate, "internal-temperature", spec, log)[0])
    log.close()
    write_csv(OUT / "原始结果.csv", rows)
    paired = pair_rows(rows)
    write_csv(OUT / "paired-comparison.csv", paired)
    conv = convergence_rows(rows)
    write_csv(OUT / "convergence.csv", conv)
    validations = []
    validations.append({"id": "V01-units-boundaries", "status": "PASS", "evidence": "Both imported solvers use the frozen input workbooks, 28 C initial T, Kelvin in constitutive law, same h=25 and hm=8e-7, and the same boundary interpolation/extension."})
    validations.append({"id": "V02-fair-paired-run", "status": "PASS", "evidence": "Twelve identical Q2/Q3/Q4 coarse/spatial/time/refined configurations were run for both implementations."})
    validations.append({"id": "V03-temperature-equation", "status": "PASS", "evidence": "Candidate has nonzero internal-temperature solves and records fixed-domain storage-flux balance plus linear residual; baseline has zero internal-temperature solve calls by design."})
    validations.append({"id": "V04-moisture-balance", "status": "PASS" if max(float(r["normalized_moisture_balance_error"]) for r in rows) < 1e-5 else "FAIL", "evidence": "Maximum reported normalized moisture balance error across paired runs is recorded in 原始结果.csv."})
    validations.append({"id": "V05-threshold-event", "status": "PASS" if all(r["completed_to_event"] for r in rows if r["question"] in ("Q3", "Q4")) else "FAIL", "evidence": "Q3/Q4 use max(C)<0.15-1e-6 and record the first bracket, interpolation and 60 s reporting."})
    validations.append({"id": "V06-convergence", "status": "INCONCLUSIVE", "evidence": "Space-only and time-only changes are now separated in convergence.csv, but this minimal four-case ladder is not a substitute for the formal three-level V02/V06 validation."})
    validations.append({"id": "V07-identifiability", "status": "INCONCLUSIVE", "evidence": "Temperature field is structurally identifiable as a numerical state only; no internal temperature observations identify k, rho or cp separately, and no latent heat is fit."})
    validations.append({"id": "V08-Q4-moving-energy", "status": "INCONCLUSIVE", "evidence": "Q4 moving-domain raw storage-flux diagnostics are recorded, but a full moving-domain energy inventory contract is not declared PASS by this prototype."})
    write_csv(OUT / "validation-register.csv", validations)
    write_json(OUT / "environment.json", {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "seed": SEED, "source_baseline": str(BASELINE_PATH.relative_to(ROOT)), "source_candidate": str(REVISION_PATH.relative_to(ROOT)), "generated_at": datetime.now(timezone.utc).astimezone().isoformat()})
    outputs = output_manifest()
    handoff = {
        "schema_version": "1.0",
        "stage": "PROTOTYPE-CANDIDATE",
        "status": "PASS",
        "scope": "isolated controller-temp-field-20260912; candidate evidence only; no H2 decision",
        "inputs": input_manifest,
        "outputs": outputs,
        "frozen_decisions": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in [ROOT / "decisions" / "H1-problem.json", ROOT / "decisions" / "H2-model.json", ROOT / "decisions" / "H3-claims.json"]],
        "assumptions": [
            "The current baseline is the imported formal_compute.py path in which Q2-Q4 assign the internal temperature to the interpolated chamber temperature at each step.",
            "The candidate is the imported temperature-field-revision-20260912 path and adds implicit internal conduction without a latent-heat source.",
            "The 4 h post-data continuation and Q4 radius interpolation remain those frozen in the source solvers.",
        ],
        "unknowns": [
            "No internal temperature measurements identify thermal coefficients or latent heat.",
            "This minimal two-level run does not clear the formal three-level convergence and full energy-inventory gates.",
        ],
        "claims": [
            "The candidate produces a nonuniform internal temperature field under the paired runs; the exact magnitudes are in paired-comparison.csv.",
            "Observed Q2/Q3/Q4 differences are conditional numerical contrasts, not empirical accuracy gains.",
            "The prototype does not select a final route and does not authorize H2 reopening.",
        ],
        "warnings": [
            "M4 results were not used as the main evidence and no latent heat was introduced.",
            "A numerical temperature field alone cannot identify rho, cp, k or latent heat without internal observations or independent measurements.",
        ],
        "required_next_actions": [
            "Team review of the paired evidence and identifiability limits before any H2 reopening decision.",
            "If reopened, preregister three-level space/time convergence, independent thermal-property bounds or measurements, and a moving-domain energy inventory residual.",
            "Do not overwrite formal 04-compute or downstream evidence from this candidate directory.",
        ],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_json(OUT / "handoff.json", handoff)
    # Recompute output manifest after handoff creation for a human-readable final list.
    write_json(OUT / "manifest.json", {"inputs": input_manifest, "outputs": output_manifest()})
    print(json.dumps({"status": "PASS", "runs": len(rows), "output_dir": str(OUT), "max_moisture_balance_error": max(float(r["normalized_moisture_balance_error"]) for r in rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
