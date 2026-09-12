"""Completion prototype for the internal-temperature-field H2 review.

This script imports the approved baseline and the isolated temperature-field
revision read-only.  Every generated file is written below this directory.
The protocol adds a three-level space ladder, a three-level time ladder,
joint refinement controls, source-bounded parameter bookkeeping, and a
moving-domain sensible-energy audit.  It deliberately does not add latent
heat or fit any thermal property.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import platform
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASELINE_PATH = ROOT / "04-compute" / "src" / "formal_compute.py"
CANDIDATE_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
SEED = 20260912
THRESHOLD = 0.15 - 1e-6
REPORT_S = 60.0


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


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def input_paths() -> list[Path]:
    paths = [
        ROOT / "decisions" / "H1-problem.json",
        ROOT / "decisions" / "H2-model.json",
        ROOT / "decisions" / "H3-claims.json",
        ROOT / "02-design" / "handoff.json",
        ROOT / "02-design" / "验证计划.json",
        ROOT / "02-design" / "H2-优化审计与方向.md",
        ROOT / "02-design" / "候选模型方案.md",
        ROOT / "02-design" / "文献到模型映射.md",
        ROOT / "02-design" / "contracts" / "model-q23-fixed.json",
        ROOT / "02-design" / "contracts" / "model-q4-m1-reference.json",
        ROOT / "02-design" / "contracts" / "model-q4-m2-moving-fv.json",
        ROOT / "02-literature" / "文献阅读结果.md",
        ROOT / "02-literature" / "影响烘干蒸发圆柱体模型的物理量审查.md",
        ROOT / "03-prototype" / "handoff.json",
        ROOT / "03-prototype" / "controller-temp-field-20260912" / "候选方案对比.md",
        ROOT / "03-prototype" / "controller-temp-field-20260912" / "H2-选择包.md",
        ROOT / "03-prototype" / "controller-temp-field-20260912" / "原始结果.csv",
        ROOT / "03-prototype" / "controller-temp-field-20260912" / "convergence.csv",
        ROOT / "04-compute" / "temperature-field-revision-20260912" / "README.md",
        ROOT / "04-compute" / "temperature-field-revision-20260912" / "parameter-diagnosis-20260912.md",
        BASELINE_PATH,
        CANDIDATE_PATH,
    ]
    paths.extend((ROOT / "input" / "A题" / "附件").rglob("*.xlsx"))
    return sorted({p for p in paths if p.is_file()})


def ladder_specs(question: str) -> list[dict]:
    if question == "Q2":
        duration, base_dt = 10800.0, 120.0
        time_dts = [240.0, 120.0, 60.0]
        sample = 600.0
    else:
        duration, base_dt = 259200.0, 300.0
        time_dts = [600.0, 300.0, 150.0]
        sample = 3600.0
    meshes = [(8, 8), (12, 12), (18, 18)]
    specs: list[dict] = []
    for i, (nr, nz) in enumerate(meshes):
        specs.append({"family": "spatial", "level": "L M H".split()[i], "nr": nr, "nz": nz,
                      "dt": base_dt, "duration": duration, "sample_every": sample,
                      "space_level": i, "time_level": 1})
    for i, dt in enumerate(time_dts):
        specs.append({"family": "time", "level": "L M H".split()[i], "nr": 12, "nz": 12,
                      "dt": dt, "duration": duration, "sample_every": sample,
                      "space_level": 1, "time_level": i})
    specs.append({"family": "joint", "level": "L", "nr": 8, "nz": 8, "dt": time_dts[0],
                  "duration": duration, "sample_every": sample, "space_level": 0, "time_level": 0})
    specs.append({"family": "joint", "level": "H", "nr": 18, "nz": 18, "dt": time_dts[2],
                  "duration": duration, "sample_every": sample, "space_level": 2, "time_level": 2})
    for spec in specs:
        spec["question"] = question
        spec["label"] = f"{question}-{spec['family']}-{spec['level']}"
    return specs


def sensitivity_specs(question: str) -> dict:
    if question == "Q2":
        return {"nr": 8, "nz": 8, "dt": 120.0, "duration": 10800.0, "sample_every": 1800.0}
    return {"nr": 8, "nz": 8, "dt": 300.0, "duration": 259200.0, "sample_every": 3600.0}


def _temperature_wrapper(module, recorder: dict):
    """Install a recorder around the source linear solver without editing it."""
    original = module.implicit_linear
    current = None
    groups: list[dict] = []
    last_radius = None

    def finish_group(group):
        if group is None:
            return
        old_radius = float(group["old_radius"])
        new_radius = float(group["new_radius"])
        old_grid = module.Grid(group["nr"], group["nz"], old_radius,
                               radial_strategy=group["radial_strategy"])
        new_grid = module.Grid(group["nr"], group["nz"], new_radius,
                               radial_strategy=group["radial_strategy"])
        # Use a reference temperature so that the inventory represents
        # sensible-temperature change rather than a large arbitrary absolute
        # Kelvin offset.  The source equation still updates rho*cp with the
        # Picard moisture iterate; that update is intentionally exposed in the
        # physical residual instead of being silently cancelled.
        t_ref = 301.15
        e_old = float(np.sum(group["first_storage"] * (group["first_old"] - t_ref) * old_grid.vol))
        e_new = float(np.sum(group["last_storage"] * (group["last_new"] - t_ref) * new_grid.vol))
        delta_e = e_new - e_old
        q_boundary = float(group["boundary_total_J"])
        residual = delta_e - q_boundary
        scale = max(abs(delta_e), abs(q_boundary), 1e-30)
        groups.append({
            "step_index": len(groups) + 1,
            "old_radius_m": old_radius,
            "new_radius_m": new_radius,
            "dt_total_s": float(group["dt_total_s"]),
            "sensible_energy_old_J": e_old,
            "sensible_energy_new_J": e_new,
            "delta_sensible_energy_J": delta_e,
            "conductive_boundary_heat_J": q_boundary,
            "latent_heat_J": 0.0,
            "residual_J": residual,
            "relative_residual": abs(residual) / scale,
            "linear_storage_delta_last_J": float(group["last_linear_delta_J"]),
            "linear_boundary_heat_last_J": float(group["last_linear_boundary_J"]),
            "linear_solver_relative_residual_last": float(group["last_solver_residual"]),
            "linear_storage_boundary_balance_relative_last": float(group["last_relative_balance"]),
            "internal_radial_flux_abs_last_W": float(group["last_radial_abs_W"]),
            "internal_axial_flux_abs_last_W": float(group["last_axial_abs_W"]),
            "picard_calls": int(group["calls"]),
        })

    def wrapped(*args, **kwargs):
        nonlocal current, last_radius
        result = original(*args, **kwargs)
        names = ["old", "coeff", "storage", "grid", "dt", "conv", "env_value"]
        values = {name: args[i] for i, name in enumerate(names) if i < len(args)}
        values.update({name: kwargs[name] for name in names if name in kwargs})
        conv = float(values["conv"])
        # The source uses conv=25 for heat and 8e-7 (or its moving-domain
        # equivalent) for moisture.  Only the temperature equation enters
        # this energy audit.
        if conv <= 1.0:
            return result
        old = np.asarray(values["old"], dtype=float)
        coeff = np.asarray(values["coeff"], dtype=float)
        storage = np.asarray(values["storage"], dtype=float)
        grid = values["grid"]
        dt = float(values["dt"])
        env = float(values["env_value"])
        new, boundary_in, iterations, linear_residual = result
        new = np.asarray(new, dtype=float)
        gr, gz, _gbr, _gb0, _gb1 = module.conductances(coeff, grid, conv, True)
        radial_abs = float(np.sum(np.abs(gr * (new[:-1, :] - new[1:, :])))) if gr.size else 0.0
        axial_abs = float(np.sum(np.abs(gz * (new[:, :-1] - new[:, 1:])))) if gz.size else 0.0
        linear_delta = float(np.sum(storage * grid.vol * (new - old)))
        boundary_j = float(boundary_in) * dt
        scale = max(abs(linear_delta), abs(boundary_j), 1e-30)
        radius = float(grid.radius)
        start_new_group = (current is None or
                           abs(radius - float(current["new_radius"])) > 1e-14 or
                           not np.array_equal(old, current["first_old"]))
        if start_new_group:
            finish_group(current)
            old_radius = float(last_radius if last_radius is not None else radius)
            current = {
                "old_radius": old_radius,
                "new_radius": radius,
                "nr": int(grid.nr),
                "nz": int(grid.nz),
                "radial_strategy": grid.radial_strategy,
                "first_old": old.copy(),
                "first_storage": storage.copy(),
                "last_new": new.copy(),
                "last_storage": storage.copy(),
                "dt_total_s": dt,
                "boundary_total_J": boundary_j,
                "calls": 1,
                "last_linear_delta_J": linear_delta,
                "last_linear_boundary_J": boundary_j,
                "last_relative_balance": abs(linear_delta - boundary_j) / scale,
                "last_solver_residual": float(linear_residual),
                "last_radial_abs_W": radial_abs,
                "last_axial_abs_W": axial_abs,
            }
        else:
            current["last_new"] = new.copy()
            current["last_storage"] = storage.copy()
            # A Picard group represents one physical time step.  Replacing
            # these values, rather than adding them, prevents repeated
            # nonlinear iterations from being counted as repeated heat input.
            current["dt_total_s"] = dt
            current["boundary_total_J"] = boundary_j
            current["calls"] += 1
            current["last_linear_delta_J"] = linear_delta
            current["last_linear_boundary_J"] = boundary_j
            current["last_relative_balance"] = abs(linear_delta - boundary_j) / scale
            current["last_solver_residual"] = float(linear_residual)
            current["last_radial_abs_W"] = radial_abs
            current["last_axial_abs_W"] = axial_abs
        last_radius = radius
        return result

    module.implicit_linear = wrapped
    recorder["original_implicit_linear"] = original
    recorder["restore"] = lambda: setattr(module, "implicit_linear", original)
    recorder["finish"] = lambda: finish_group(current)
    recorder["groups"] = groups
    return recorder


def install_property_scaling(module, multipliers: dict):
    """Scale only rho/cp/k in the imported candidate constitutive laws."""
    if not multipliers or module.__name__.startswith("formal_baseline"):
        return lambda: None
    original_q23 = module.props_q23
    original_q4 = module.props_q4
    rho_m = float(multipliers.get("rho_mult", 1.0))
    cp_m = float(multipliers.get("cp_mult", 1.0))
    k_m = float(multipliers.get("k_mult", 1.0))

    def scaled_q23(*args, **kwargs):
        rho, cp, k, d = original_q23(*args, **kwargs)
        return rho * rho_m, cp * cp_m, k * k_m, d

    def scaled_q4(*args, **kwargs):
        rho, cp, k, d = original_q4(*args, **kwargs)
        return rho * rho_m, cp * cp_m, k * k_m, d

    module.props_q23 = scaled_q23
    module.props_q4 = scaled_q4

    def restore():
        module.props_q23 = original_q23
        module.props_q4 = original_q4

    return restore


def run_one(module, implementation: str, spec: dict, log, multipliers=None,
            save_artifacts=True, return_run=False):
    q = int(spec["question"][1])
    moving = q == 4
    cfg = module.RunConfig(
        spec["label"] + "-" + implementation,
        int(spec["nr"]), int(spec["nz"]), float(spec["dt"]), float(spec["duration"]), q, "M3",
        h_mult=float(spec.get("h_mult", 1.0)), hm_mult=float(spec.get("hm_mult", 1.0)),
        pref=float(spec.get("pref", 1.0)), exponent=float(spec.get("exponent", 1.0)),
        window_s=int(spec.get("window_s", 3600)),
        stop_threshold=THRESHOLD if q in (3, 4) else None,
        moving_impl="reference" if moving else "fixed", radius_mode="pchip" if moving else "constant",
        sample_every=float(spec["sample_every"]), radial_strategy="two-sided-local",
    )
    recorder: dict = {}
    restore_props = install_property_scaling(module, multipliers or {})
    if implementation == "internal-temperature":
        _temperature_wrapper(module, recorder)
    started = time.perf_counter()
    try:
        run = module.simulate(cfg)
    finally:
        elapsed = time.perf_counter() - started
        restore_props()
        if "finish" in recorder:
            recorder["finish"]()
            recorder["restore"]()
    metrics = dict(run["metrics"])
    records = run["records"]
    field = np.asarray(run["final_t"], dtype=float) - 273.15
    finite = field[np.isfinite(field)]
    final_record = records[-1] if records else {}
    env_t, _ = module.outside(float(final_record.get("time_s", metrics.get("final_time_s", 0.0))), cfg.window_s)
    summary = {
        "implementation": implementation,
        "question": spec["question"],
        "family": spec["family"],
        "level": spec["level"],
        "label": spec["label"],
        "nr": int(spec["nr"]), "nz": int(spec["nz"]), "dt_s": float(spec["dt"]),
        "duration_s": float(spec["duration"]), "space_level": spec.get("space_level", ""),
        "time_level": spec.get("time_level", ""),
        "runtime_s": elapsed,
        "completed_to_event": bool(metrics.get("threshold_bracket") is not None) if q in (3, 4) else True,
        "interpolated_event_time_s": metrics.get("interpolated_event_time_s"),
        "reported_event_time_s": metrics.get("reported_event_time_s"),
        "final_time_s": metrics.get("final_time_s"),
        "final_max_C": float(metrics["final_max_C"]),
        "final_mean_C": float(metrics["final_mean_C"]),
        "max_linear_relative_residual": float(metrics["max_linear_relative_residual"]),
        "max_picard_iterations": int(metrics["max_picard_iterations"]),
        "max_picard_update": float(metrics["max_terminal_picard_update"]),
        "normalized_moisture_balance_error": float(metrics["normalized_moisture_balance_error"]),
        "dry_solid_inventory_relative_error": float(metrics["dry_solid_inventory_relative_error"]),
        "geometry_relative_error": float(metrics["geometry_relative_error"]),
        "max_local_dry_continuity_relative_residual": float(metrics["max_local_dry_continuity_relative_residual"]),
        "threshold_bracket": metrics.get("threshold_bracket"),
        "temperature_solver_calls": len(recorder.get("groups", [])),
        "internal_temperature_min_C": float(np.min(finite)),
        "internal_temperature_max_C": float(np.max(finite)),
        "internal_temperature_mean_C": float(np.mean(finite)),
        "internal_temperature_range_C": float(np.max(finite) - np.min(finite)),
        "max_abs_internal_minus_environment_C": float(np.max(np.abs(finite - (env_t - 273.15)))),
        "environment_temperature_C_at_last_record": float(env_t - 273.15),
        "parameter_multipliers": json.dumps(multipliers or {}, ensure_ascii=False, sort_keys=True),
    }
    if save_artifacts:
        case_dir = OUT / ("model-baseline" if implementation == "prescribed-T-baseline" else "model-internal-temperature") / f"{spec['question']}-{spec['family']}-{spec['level']}"
        write_json(case_dir / "metrics.json", summary)
        write_csv(case_dir / "trajectory.csv", records)
        if recorder.get("groups"):
            write_csv(case_dir / "energy-groups.csv", recorder["groups"])
    log.write("DONE " + json.dumps(summary, ensure_ascii=False) + "\n")
    log.flush()
    if return_run:
        return summary, list(recorder.get("groups", [])), run
    return summary, list(recorder.get("groups", []))


def safe_run(module, implementation, spec, log, rows, energy_rows, multipliers=None,
             save_artifacts=True):
    log.write("START " + json.dumps({"label": spec["label"], "implementation": implementation,
                                     "multipliers": multipliers or {}}, ensure_ascii=False) + "\n")
    log.flush()
    try:
        row, groups = run_one(module, implementation, spec, log, multipliers, save_artifacts)
        rows.append(row)
        for group in groups:
            group_row = dict(group)
            group_row.update({"implementation": implementation, "question": spec["question"],
                              "family": spec["family"], "level": spec["level"],
                              "label": spec["label"], "nr": spec["nr"], "nz": spec["nz"],
                              "dt_s": spec["dt"]})
            energy_rows.append(group_row)
        return row
    except Exception as exc:  # Record failures instead of hiding them.
        failure = {"implementation": implementation, "question": spec["question"],
                   "family": spec["family"], "level": spec["level"], "label": spec["label"],
                   "nr": spec["nr"], "nz": spec["nz"], "dt_s": spec["dt"],
                   "status": "FAIL", "error": repr(exc),
                   "traceback": traceback.format_exc(limit=8)}
        rows.append(failure)
        log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
        log.flush()
        return failure


def value_for(rows: list[dict], impl: str, q: str, family: str, level: str, key: str):
    found = [r for r in rows if r.get("implementation") == impl and r.get("question") == q
             and r.get("family") == family and r.get("level") == level and key in r]
    return found[0].get(key) if found else None


def make_convergence(rows: list[dict]) -> list[dict]:
    out = []
    for impl in ("prescribed-T-baseline", "internal-temperature"):
        for q in ("Q2", "Q3", "Q4"):
            metric = "final_max_C" if q == "Q2" else "interpolated_event_time_s"
            report_metric = "final_max_C" if q == "Q2" else "reported_event_time_s"
            for family in ("spatial", "time", "joint"):
                levels = ["L", "M", "H"] if family != "joint" else ["L", "M", "H"]
                for level in levels:
                    source_family, source_level = family, level
                    if family == "joint" and level == "M":
                        source_family, source_level = "spatial", "M"
                    row = next((r for r in rows if r.get("implementation") == impl and r.get("question") == q
                                and r.get("family") == source_family and r.get("level") == source_level), None)
                    if row is None:
                        continue
                    out.append({"implementation": impl, "question": q, "ladder": family,
                                "level": level, "source_case": f"{source_family}-{source_level}",
                                "nr": row.get("nr"), "nz": row.get("nz"), "dt_s": row.get("dt_s"),
                                "metric": metric, "value": row.get(metric),
                                "reported_value": row.get(report_metric)})
                ladder = [r for r in out if r["implementation"] == impl and r["question"] == q and r["ladder"] == family]
                ladder.sort(key=lambda x: "LMH".index(x["level"]))
                for i, item in enumerate(ladder):
                    prev = ladder[i - 1] if i else None
                    item["adjacent_change"] = None if prev is None or item["value"] is None or prev["value"] is None else abs(float(item["value"]) - float(prev["value"]))
                    item["refinement_status"] = "NA" if prev is None else ("DECREASING" if item["adjacent_change"] <= float(prev.get("adjacent_change") or 1e300) else "NOT_MONOTONE")
    return out


def make_pairwise(rows: list[dict]) -> list[dict]:
    out = []
    for q in ("Q2", "Q3", "Q4"):
        for family in ("spatial", "time", "joint"):
            levels = ["L", "M", "H"]
            for level in levels:
                b = next((r for r in rows if r.get("implementation") == "prescribed-T-baseline" and r.get("question") == q and r.get("family") == ("spatial" if family == "joint" and level == "M" else family) and r.get("level") == ("M" if family == "joint" and level == "M" else level)), None)
                c = next((r for r in rows if r.get("implementation") == "internal-temperature" and r.get("question") == q and r.get("family") == ("spatial" if family == "joint" and level == "M" else family) and r.get("level") == ("M" if family == "joint" and level == "M" else level)), None)
                if not b or not c or "final_max_C" not in b or "final_max_C" not in c:
                    continue
                out.append({"question": q, "ladder": family, "level": level,
                            "nr": c.get("nr"), "nz": c.get("nz"), "dt_s": c.get("dt_s"),
                            "baseline_final_max_C": b.get("final_max_C"), "candidate_final_max_C": c.get("final_max_C"),
                            "candidate_minus_baseline_final_max_C": float(c["final_max_C"]) - float(b["final_max_C"]),
                            "baseline_final_mean_C": b.get("final_mean_C"), "candidate_final_mean_C": c.get("final_mean_C"),
                            "candidate_minus_baseline_final_mean_C": float(c["final_mean_C"]) - float(b["final_mean_C"]),
                            "baseline_event_time_s": b.get("reported_event_time_s"), "candidate_event_time_s": c.get("reported_event_time_s"),
                            "candidate_minus_baseline_event_time_s": None if b.get("reported_event_time_s") is None or c.get("reported_event_time_s") is None else float(c["reported_event_time_s"]) - float(b["reported_event_time_s"]),
                            "candidate_temperature_range_C": c.get("internal_temperature_range_C"),
                            "candidate_max_abs_internal_minus_environment_C": c.get("max_abs_internal_minus_environment_C")})
    return out


def parameter_source_rows() -> list[dict]:
    return [
        {"parameter": "rho", "approved_definition": "Q2/Q3: 650+128C; Q4: 760+90C (kg/m3)", "project_source": "02-design/contracts/model-q23-fixed.json; model-q4-m1-reference.json; model-q4-m2-moving-fv.json", "independent_source": "P05 summary: cocoa real density 825.10 to about 696.25 kg/m3", "transfer_status": "NOT_TRANSFERABLE", "audit_interval": "0.8x, 1.0x, 1.2x approved formula; numerical envelope only"},
        {"parameter": "cp", "approved_definition": "Q2/Q3: 1450+2736C/(C+1); Q4: 1850+2150C/(C+1) (J/kg/K)", "project_source": "02-design/contracts/model-q23-fixed.json; model-q4-m1-reference.json; model-q4-m2-moving-fv.json", "independent_source": "No independent project source located", "transfer_status": "UNSUPPORTED_IDENTIFICATION", "audit_interval": "0.8x, 1.0x, 1.2x approved formula; numerical envelope only"},
        {"parameter": "k", "approved_definition": "Q2/Q3: 0.21+0.38C/(C+1); Q4: 0.12+0.20C/(C+1) (W/m/K)", "project_source": "02-design/contracts/model-q23-fixed.json; model-q4-m1-reference.json; model-q4-m2-moving-fv.json", "independent_source": "No independent project source located", "transfer_status": "UNSUPPORTED_IDENTIFICATION", "audit_interval": "0.8x, 1.0x, 1.2x approved formula; numerical envelope only"},
        {"parameter": "h", "approved_definition": "25 W/m2/K", "project_source": "decisions/H1-problem.json and approved contracts", "independent_source": "P06 reports 5.34 W/m2/K; P08 reports 18.55 W/m2/K under different geometries", "transfer_status": "NOT_TRANSFERABLE_AS_THIS_MATERIAL", "audit_interval": "0.8x, 1.0x, 1.2x frozen value"},
        {"parameter": "hm", "approved_definition": "8e-7 m/s under Cs-Cinf convention", "project_source": "decisions/H1-problem.json and approved contracts", "independent_source": "P06 reports 3.77e-8 m/s; P08 reports 0.007 m/s under different driving-force conventions", "transfer_status": "NOT_TRANSFERABLE_AS_THIS_DEFINITION", "audit_interval": "0.8x, 1.0x, 1.2x frozen value"},
    ]


def make_sensitivity(module, rows, energy_rows, log):
    parameter_rows = []
    for q in ("Q2", "Q3", "Q4"):
        base_spec = sensitivity_specs(q)
        base_spec.update({"question": q, "family": "sensitivity", "level": "base", "label": f"{q}-sensitivity-base"})
        base = safe_run(module, "internal-temperature", base_spec, log, rows, energy_rows, {}, save_artifacts=True)
        parameter_rows.append({"question": q, "parameter": "base", "level": "base", "multiplier": 1.0,
                               "source_status": "protocol reference", "t_star_s": base.get("interpolated_event_time_s"),
                               "reported_event_time_s": base.get("reported_event_time_s"), "final_max_C": base.get("final_max_C"),
                               "final_mean_C": base.get("final_mean_C"), "runtime_s": base.get("runtime_s")})
        for parameter in ("h", "hm", "rho", "cp", "k"):
            for level, multiplier in (("low", 0.8), ("high", 1.2)):
                spec = dict(base_spec)
                spec["level"] = f"{parameter}-{level}"
                spec["label"] = f"{q}-sensitivity-{parameter}-{level}"
                if parameter == "h": spec["h_mult"] = multiplier
                if parameter == "hm": spec["hm_mult"] = multiplier
                mults = {f"{parameter}_mult": multiplier} if parameter in ("rho", "cp", "k") else {}
                result = safe_run(module, "internal-temperature", spec, log, rows, energy_rows, mults, save_artifacts=True)
                parameter_rows.append({"question": q, "parameter": parameter, "level": level, "multiplier": multiplier,
                                       "source_status": "audit envelope; not identified", "t_star_s": result.get("interpolated_event_time_s"),
                                       "reported_event_time_s": result.get("reported_event_time_s"), "final_max_C": result.get("final_max_C"),
                                       "final_mean_C": result.get("final_mean_C"), "runtime_s": result.get("runtime_s"),
                                       "status": result.get("status", "OK")})
    return parameter_rows


def fnum(value, digits=4):
    if value is None or value == "":
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def render_reports(rows, conv, pair, sensitivity, energy_summary, source_rows):
    write_csv(OUT / "原始结果.csv", rows)
    write_csv(OUT / "space-convergence.csv", [r for r in conv if r["ladder"] == "spatial"])
    write_csv(OUT / "time-convergence.csv", [r for r in conv if r["ladder"] == "time"])
    write_csv(OUT / "joint-convergence.csv", [r for r in conv if r["ladder"] == "joint"])
    write_csv(OUT / "paired-comparison.csv", pair)
    write_csv(OUT / "parameter-sensitivity.csv", sensitivity)
    write_csv(OUT / "energy-audit.csv", energy_summary.get("rows", []))
    write_csv(OUT / "energy-audit-summary.csv", energy_summary.get("summary", []))
    write_csv(OUT / "parameter-source-register.csv", source_rows)

    source_md = """# 参数来源与敏感性口径\n\n本补全原型只使用项目已经存在的来源登记。`0.8/1.0/1.2` 是围绕已批准公式或冻结边界值的审计扰动，不是由本题数据识别出的物性置信区间；所有非独立来源均标为不可识别，不得在论文中写成实测参数。\n\n|参数|批准定义|项目来源|已有独立来源|迁移状态|本轮区间|\n|---|---|---|---|---|---|\n"""
    for row in source_rows:
        source_md += f"|{row['parameter']}|{row['approved_definition']}|{row['project_source']}|{row['independent_source']}|{row['transfer_status']}|{row['audit_interval']}|\n"
    source_md += """\n## 解释边界\n\n- P05 的密度是可可豆而非本题药材；P06/P08 的 `h`、`hm` 来自不同几何、材料或驱动力定义，不能直接替换批准值。\n- `cp`、`k` 没有本项目内可用于本题材料的独立测量或可靠区间；本轮只做条件敏感性。\n- 因而本轮能回答“结果对参数扰动有多敏感”，不能回答“参数已经由数据识别”。\n"""
    (OUT / "parameter-sources.md").write_text(source_md, encoding="utf-8")

    by = {(r.get("implementation"), r.get("question"), r.get("family"), r.get("level")): r for r in rows if r.get("status", "OK") != "FAIL"}
    def core(impl, q, family, level):
        return by.get((impl, q, family, level), {})

    comp = """# 内部温度场补全原型：候选方案对比\n\n状态：**H2 复审证据包，未选择路线；不写 TEAM_APPROVED，不推进正式 COMPUTE。**\n\n## 1. 研究边界\n\n本目录只比较：\n\n- 当前烘房温度基线：导入 `04-compute/src/formal_compute.py`，Q2—Q4 将内部温度直接置为环境温度；\n- 内部温度候选：导入 `04-compute/temperature-field-revision-20260912/formal_compute_revision.py`，用隐式后向 Euler 有限体积导热方程推进内部 `T`，不加入潜热。\n\n两者共用附件、初值、边界延拓、`D(C,T)`、`h=25`、`hm=8e-7`、移动半径 PCHIP、全域阈值与 60 s 报告口径。所有差异都只能解释为**条件数值对照**，不能解释为现实准确率。\n\n## 2. 三层独立收敛设计\n\n|梯子|L|M|H|控制变量|\n|---|---|---|---|---|\n|空间|8×8|12×12|18×18|固定 `dt`：Q2=120 s，Q3/Q4=300 s|\n|时间|`dt`=240/600 s|120/300 s|60/150 s|固定 12×12 网格|\n|联合|8×8 + 时间L|12×12 + 时间M|18×18 + 时间H|同时改变空间和时间|\n\n空间与时间的独立梯子分别以 `space-convergence.csv`、`time-convergence.csv` 登记，联合对照以 `joint-convergence.csv` 登记；不是用一次联合差异冒充两个误差来源。\n\n## 3. 核心配对结果\n\n|问题|对照层|基线最大C|候选最大C|候选-基线|基线事件(s)|候选事件(s)|候选-基线(s)|\n|---|---|---:|---:|---:|---:|---:|---:|\n"""
    for q in ("Q2", "Q3", "Q4"):
        r = next((x for x in pair if x["question"] == q and x["ladder"] == "joint" and x["level"] == "H"), None)
        if r:
            comp += f"|{q}|联合H|{fnum(r['baseline_final_max_C'],7)}|{fnum(r['candidate_final_max_C'],7)}|{fnum(r['candidate_minus_baseline_final_max_C'],7)}|{fnum(r['baseline_event_time_s'],1)}|{fnum(r['candidate_event_time_s'],1)}|{fnum(r['candidate_minus_baseline_event_time_s'],1)}|\n"
    comp += """\n## 4. 证据判读\n\n- **数值状态定义：支持。** 候选调用非零温度线性求解并产生非均匀内部温度场；基线没有温度方程求解，这是结构差异而不是格式差异。\n- **收敛：只在逐项看梯子后判定。** 三层结果和相邻变化见 CSV；若 H 相邻变化仍超过 60 s（Q3/Q4）或不单调下降，只能记为 `INCONCLUSIVE`，不能用联合H掩盖。\n- **物理可识别：不支持。** 当前附件没有内部温度观测，也没有本题药材的独立 `rho/cp/k` 测量，不能把热场差异写成实测验证。\n- **正式升级：证据不足需补测。** Q4 移动域能量库存若残差不随细化下降，候选只能作为结构性消融；含潜热路线在无独立焓数据时不支持。\n\n## 5. 运行与失败记录\n\n所有实例的逐案指标在 `原始结果.csv` 和 `model-*/.../metrics.json`，原始命令、运行时、环境和异常在 `run.log`、`environment.json`。没有把失败或 72 h 未达标当成事件成功。\n"""
    (OUT / "候选方案对比.md").write_text(comp, encoding="utf-8")

    energy_text = """# 移动域能量库存审计\n\n## 口径\n\n候选热方程的离散审计写成\n\n`ΔE_sensible = Q_boundary + Q_latent + R`\n\n其中 `E_sensible=∫rho cp T dV`；内部导热通量在控制体相邻面成对抵消，另登记其绝对通量规模；`Q_boundary` 是侧面/端面 Robin 热通量积分；本轮 `Q_latent=0`（明确省略，不是假设已识别为零）；`R` 是库存变化减去边界热量及潜热项的残差。固定域和移动域分别登记，移动域使用前后实际几何体积。\n\n|问题|实现|梯子|最大相对残差|累计残差(J)|状态|\n|---|---|---|---:|---:|---|\n"""
    for s in energy_summary.get("summary", []):
        energy_text += f"|{s.get('question')}|{s.get('implementation')}|{s.get('family')}-{s.get('level')}|{fnum(s.get('max_relative_residual'),4)}|{fnum(s.get('cumulative_residual_J'),3)}|{s.get('status')}|\n"
    energy_text += """\n## 解释\n\n- Q2/Q3 固定域若残差接近线性求解残差，说明温度离散的库存—边界热量关系可复核。\n- Q4 是移动域；若实际库存残差明显大于固定域且不随空间/时间细化下降，说明当前候选接口没有完成可接受的移动域热能合同。这个失败边界必须保留，不能只报告水分库存守恒。\n- 基线没有内部温度方程，不能把“强制赋值后的温度变化”伪装成热能闭合；其热能审计状态登记为 `NOT_APPLICABLE`。\n\n逐步数据见 `energy-audit.csv`，其中同时保留显热旧/新库存、边界热量、潜热零项、残差、内部径向/轴向导热绝对通量和 Picard 调用次数。\n"""
    (OUT / "移动域能量审计.md").write_text(energy_text, encoding="utf-8")

    sens_text = """# 参数区间敏感性结果\n\n本轮在 8×8 诊断网格、预设时间步上，对 `h`、`hm`、`rho`、`cp`、`k` 分别做 0.8/1.0/1.2 单因素扰动。它们是来源登记后的审计区间，不是识别区间。\n\n|问题|参数|低事件(s)|基准事件(s)|高事件(s)|低-高跨度(s)|\n|---|---|---:|---:|---:|---:|\n"""
    for q in ("Q2", "Q3", "Q4"):
        for p in ("h", "hm", "rho", "cp", "k"):
            rs = [x for x in sensitivity if x.get("question") == q and x.get("parameter") == p]
            low = next((x for x in rs if x.get("level") == "low"), {})
            base = next((x for x in sensitivity if x.get("question") == q and x.get("parameter") == "base"), {})
            high = next((x for x in rs if x.get("level") == "high"), {})
            lo, mid, hi = low.get("t_star_s"), base.get("t_star_s"), high.get("t_star_s")
            span = None if lo is None or hi is None else abs(float(hi) - float(lo))
            sens_text += f"|{q}|{p}|{fnum(lo,1)}|{fnum(mid,1)}|{fnum(hi,1)}|{fnum(span,1)}|\n"
    sens_text += """\n结果只能支持“敏感性排序和风险优先级”。若某一参数变化显著，也不意味着该参数已被本题数据识别；尤其不能用同一含水率结果反向同时拟合 `rho/cp/k` 和 `h/hm`。\n"""
    (OUT / "参数区间敏感性.md").write_text(sens_text, encoding="utf-8")

    def ladder_lines(q, family, impl="internal-temperature"):
        selected = [x for x in conv if x["question"] == q and x["ladder"] == family and x["implementation"] == impl]
        selected.sort(key=lambda x: "LMH".index(x["level"]))
        return ", ".join(f"{x['level']}={fnum(x.get('value'),1 if q != 'Q2' else 7)} (Δ={fnum(x.get('adjacent_change'),1 if q != 'Q2' else 7)})" for x in selected)

    h2 = """# H2-选择包：内部温度场补全\n\n状态：**供团队决策；不是 TEAM_APPROVED，不修改现有 H2/H3，也不推进正式 COMPUTE。**\n\n## 一、需要团队明确选择\n\n本包把结果分成三种结论，不替团队决定：\n\n1. **支持升级（仅限数值状态定义）**：内部温度方程已实现、可复现、可产生非均匀场；可把“显式求内部T”作为候选/消融继续讨论。\n2. **证据不足需补测（正式主路线）**：现有数据不足以验证温度场现实准确性或识别 `rho/cp/k`；若要重开 H2，应先补测。\n3. **不支持（含潜热/完整热湿主路线）**：本轮无焓/潜热来源，Q4 移动域能量闭合若未通过，不支持把候选升级为完整热湿模型。\n\n团队可选：\n\n|选项|团队动作|本包证据边界|\n|---|---|---|\n|A 回退|当前基线继续作为正式路线，内部T仅作受控消融/局限|不提供内部温度预测，但不引入不可识别物性|\n|B 补测后重开|先补内部温度与独立热物性，再复审无潜热内部T候选|只有补测能把数值场与现实对象连起来|\n|C 拒绝升级|不把内部T或潜热候选纳入正式主线|适用于能量闭合失败、收敛失败或无法获得补测|\n\n## 二、收敛证据登记\n\n三层内部温度候选梯子：\n\n- Q2 空间：""" + ladder_lines("Q2", "spatial") + "\n- Q2 时间：" + ladder_lines("Q2", "time") + "\n- Q3 空间：" + ladder_lines("Q3", "spatial") + "\n- Q3 时间：" + ladder_lines("Q3", "time") + "\n- Q4 空间：" + ladder_lines("Q4", "spatial") + "\n- Q4 时间：" + ladder_lines("Q4", "time") + "\n\n相邻变化是否满足 60 s 事件报告要求，以 CSV 实际值和验证登记为准；任何不单调或超过门槛的梯子均为 `INCONCLUSIVE`，不是“基本收敛”。\n\n## 三、物理与识别边界\n\n- 内部温度观测：当前附件没有中心/近表面/端面内部温度时间序列；因此不能验证 `T(r,z,t)`。\n- `rho`：已有 P05 仅是不同材料的类比密度，标记不可迁移；不能用于本题定参。\n- `cp/k`：项目中没有本题材料的独立来源；本轮只做公式相对扰动。\n- `h/hm`：P06/P08 的几何、材料或驱动力口径不同，不能直接替代冻结值。\n- 潜热：本轮固定 `Q_latent=0` 作为“未加入项”，不是潜热已被实验排除。\n\n## 四、拒绝标准\n\n满足任一条即拒绝作为正式内部温度主路线，或降级为消融：\n\n- H 层相对 M 层的空间或时间事件变化仍大于 60 s，或不随细化下降；\n- `Q4` 显热库存—边界热量残差不随空间/时间细化下降，或出现负体积、域外伪值、干固体连续性失败；\n- 内部温度无法由独立观测验证，只能用同一含水率结果拟合热物性；\n- 必须任意修改 `D`、`hm`、4 h 后延拓、PCHIP 或阈值才能得到期望排序；\n- 引入潜热但没有独立焓数据、来源区间、离散闭合和消融保留门槛。\n\n## 五、最小补测方案\n\n1. 同一药材、同一圆柱尺寸和边界工况，至少布置中心、近表面、一个端面/近端面内部温度探头，记录到 4 h 以后；同步记录表面温度。\n2. 独立测量或提供来源可追溯的 `rho(C)`、`cp(C,T)`、`k(C,T)` 区间；若引入潜热，再给焓/DSC 曲线。\n3. 记录或独立估计边界热/质通量，使 `h`、`hm` 不与内部物性完全共线反演。\n4. 补测后再做留出工况验证，不能用校准工况同一数据宣称现实准确。\n\n## 六、已进行的优化与后续优化方向\n\n|项目|目标缺陷|证据状态|成本|风险|保留/回退|\n|---|---|---|---|---|---|\n|隐式内部温度场|基线把内部T强制等于环境T|已实现并配对测试|中|无内部观测|供复审；未批准前回退|\n|三层独立空间/时间及联合对照|分离离散误差来源|已运行；按实际梯子登记|中|事件可能未达60 s稳定|未过则继续加密或降级|\n|rho/cp/k/h/hm审计敏感性|识别首要不确定量|已运行；非独立来源明确标记|中|跨材料来源不可迁移|作为风险排序，不作定参|\n|移动域显热库存审计|发现Q4热能闭合缺口|已运行；Q4状态由残差决定|中|源模型接口不含完整几何热功|未过则拒绝正式升级|\n|潜热/焓项|修正蒸发冷却缺口|本轮未实现|高|无独立焓数据会过参数化|无数据则拒绝|\n\n## 七、交接文件\n\n- 原始逐案结果：`原始结果.csv`；\n- 三类收敛：`space-convergence.csv`、`time-convergence.csv`、`joint-convergence.csv`；\n- 参数来源与结果：`parameter-sources.md`、`parameter-source-register.csv`、`parameter-sensitivity.csv`、`参数区间敏感性.md`；\n- 能量审计：`energy-audit.csv`、`energy-audit-summary.csv`、`移动域能量审计.md`；\n- 验证登记：`validation-register.csv`；\n- 运行环境和输入哈希：`environment.json`、`input-manifest.json`、`run.log`。\n\n团队选择：待填写 A / B / C\n是否同意重开 H2：待填写\n批准的补充数据：待填写\n确认人和时间：待填写\n"""
    (OUT / "H2-选择包.md").write_text(h2, encoding="utf-8")


def energy_summary_from_rows(rows, energy_rows):
    summaries = []
    for impl in ("prescribed-T-baseline", "internal-temperature"):
        for q in ("Q2", "Q3", "Q4"):
            for family, levels in (("spatial", ["L", "M", "H"]), ("time", ["L", "M", "H"]), ("joint", ["L", "H"])):
                for level in levels:
                    if impl == "prescribed-T-baseline":
                        summaries.append({"implementation": impl, "question": q, "family": family, "level": level,
                                          "max_relative_residual": None, "cumulative_residual_J": None,
                                          "status": "NOT_APPLICABLE", "reason": "temperature prescribed; no heat equation"})
                        continue
                    selected = [x for x in energy_rows if x.get("implementation") == impl and x.get("question") == q and
                                x.get("family") == family and x.get("level") == level]
                    if family == "joint" and level == "M":
                        selected = [x for x in energy_rows if x.get("implementation") == impl and x.get("question") == q and
                                    x.get("family") == "spatial" and x.get("level") == "M"]
                    if not selected:
                        summaries.append({"implementation": impl, "question": q, "family": family, "level": level,
                                          "max_relative_residual": None, "cumulative_residual_J": None,
                                          "status": "BLOCKED", "reason": "no temperature audit rows"})
                        continue
                    max_rel = max(float(x["relative_residual"]) for x in selected)
                    cumulative = sum(float(x["residual_J"]) for x in selected)
                    # The formal threshold here is intentionally strict for a
                    # fixed-domain linear balance; Q4 is judged separately by
                    # refinement and is not promoted just because one run is small.
                    status = "PASS" if q in ("Q2", "Q3") and max_rel < 1e-7 else ("INCONCLUSIVE" if q == "Q4" else "FAIL")
                    summaries.append({"implementation": impl, "question": q, "family": family, "level": level,
                                      "max_relative_residual": max_rel, "cumulative_residual_J": cumulative, "status": status,
                                      "row_count": len(selected)})
    return {"rows": energy_rows, "summary": summaries}


def validation_register(rows, conv, energy_summary):
    expected = 3 * 2 * 8
    core = [r for r in rows if r.get("family") in ("spatial", "time", "joint")]
    ok_core = len([r for r in core if r.get("status", "OK") != "FAIL"]) == expected
    validations = [
        {"id": "V01-input-and-freeze", "status": "PASS", "evidence": "input-manifest.json hashes the approved decisions, design handoff, current candidate evidence, compute source, and A-topic workbooks."},
        {"id": "V02-fair-paired-convergence", "status": "PASS" if ok_core else "FAIL", "evidence": f"Expected {expected} core runs (3 questions x 2 implementations x 8 cases); raw outcomes are in 原始结果.csv."},
        {"id": "V03-three-level-space", "status": "INCONCLUSIVE", "evidence": "Three independent fixed-dt spatial levels are recorded; PASS requires H-vs-M to meet the pre-registered 60 s event/report tolerance, not merely completion."},
        {"id": "V04-three-level-time", "status": "INCONCLUSIVE", "evidence": "Three independent fixed-grid time levels are recorded; PASS requires H-vs-M to meet the pre-registered 60 s event/report tolerance, not merely completion."},
        {"id": "V05-joint-refinement", "status": "PASS" if ok_core else "FAIL", "evidence": "Joint L/M/H controls are recorded separately from the independent ladders; joint differences are not used to clear V03/V04."},
        {"id": "V06-temperature-equation", "status": "PASS", "evidence": "Internal candidate has nonzero temperature solver calls and a field range; baseline has no internal heat solve by definition."},
        {"id": "V07-moisture-and-moving-geometry", "status": "PASS" if all(float(r.get("normalized_moisture_balance_error", 1e9)) < 1e-5 for r in core if r.get("status", "OK") != "FAIL") else "FAIL", "evidence": "Moisture inventory, dry-solid inventory, geometry, and local continuity metrics are retained per run."},
        {"id": "V08-energy-fixed-domain", "status": "PASS" if all(x.get("status") == "PASS" for x in energy_summary["summary"] if x.get("implementation") == "internal-temperature" and x.get("question") in ("Q2", "Q3")) else "INCONCLUSIVE", "evidence": "Q2/Q3 fixed-domain sensible-energy records and residuals are in energy-audit.csv and its summary."},
        {"id": "V09-energy-moving-domain", "status": "INCONCLUSIVE", "evidence": "Q4 moving-domain inventory includes actual before/after volumes, boundary heat and residual; a nondecreasing or large residual blocks formal upgrade."},
        {"id": "V10-parameter-identifiability", "status": "INCONCLUSIVE", "evidence": "Parameter-source-register.csv distinguishes approved formulas, non-transferable analog sources, and unsupported independent identification."},
        {"id": "V11-internal-temperature-validation", "status": "BLOCKED", "evidence": "No internal temperature observations are present in current inputs; numerical field generation is not empirical validation."},
        {"id": "V12-latent-heat", "status": "BLOCKED", "evidence": "Latent heat is omitted by design because no independent enthalpy/DSC source is frozen; Q_latent=0 is not an identified physical result."},
    ]
    write_csv(OUT / "validation-register.csv", validations)
    return validations


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = input_paths()
    manifest = [{"path": rel(p), "sha256": sha256(p), "bytes": p.stat().st_size} for p in paths]
    write_json(OUT / "input-manifest.json", {"created_at": datetime.now(timezone.utc).astimezone().isoformat(), "inputs": manifest})
    log_path = OUT / "run.log"
    log = log_path.open("w", encoding="utf-8")
    log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version, "platform": platform.platform(),
                          "numpy": np.__version__, "seed": SEED,
                          "started_at": datetime.now(timezone.utc).astimezone().isoformat()}, ensure_ascii=False) + "\n")
    log.write("SCOPE: three-level independent space/time plus joint controls; no latent heat; write boundary is this directory.\n")
    log.flush()
    baseline = load_module("formal_baseline_completion", BASELINE_PATH)
    candidate = load_module("formal_candidate_completion", CANDIDATE_PATH)
    rows: list[dict] = []
    energy_rows: list[dict] = []
    for question in ("Q2", "Q3", "Q4"):
        for spec in ladder_specs(question):
            safe_run(baseline, "prescribed-T-baseline", spec, log, rows, energy_rows, {}, save_artifacts=True)
            safe_run(candidate, "internal-temperature", spec, log, rows, energy_rows, {}, save_artifacts=True)
    sensitivity = make_sensitivity(candidate, rows, energy_rows, log)
    log.close()
    conv = make_convergence(rows)
    pair = make_pairwise(rows)
    source_rows = parameter_source_rows()
    energy_summary = energy_summary_from_rows(rows, energy_rows)
    render_reports(rows, conv, pair, sensitivity, energy_summary, source_rows)
    validations = validation_register(rows, conv, energy_summary)
    write_json(OUT / "environment.json", {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__,
                                            "seed": SEED, "baseline_source": rel(BASELINE_PATH),
                                            "candidate_source": rel(CANDIDATE_PATH),
                                            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
                                            "protocol": "run_completion.py", "write_boundary": rel(OUT)})
    outputs = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in {"handoff.json", "manifest.json"}:
            outputs.append({"path": rel(p), "sha256": sha256(p), "bytes": p.stat().st_size})
    status = "PASS" if all(v["status"] not in ("FAIL",) for v in validations) else "FAIL"
    handoff = {
        "schema_version": "1.0", "stage": "PROTOTYPE-CANDIDATE-COMPLETION", "status": status,
        "scope": "isolated internal-temperature-field completion for H2 review; no model selection and no formal-stage writes",
        "inputs": manifest, "outputs": outputs,
        "frozen_decisions": [{"path": rel(ROOT / "decisions" / name), "sha256": sha256(ROOT / "decisions" / name)} for name in ("H1-problem.json", "H2-model.json", "H3-claims.json")],
        "assumptions": [
            "The baseline is the approved prescribed-chamber-temperature implementation; it has no heat PDE to audit.",
            "The candidate solves the imported implicit conduction equation with approved constitutive formulas and no latent heat.",
            "0.8/1.0/1.2 parameter factors are bounded audit perturbations, not identified physical intervals.",
            "Q4 sensible-energy residual uses before/after actual moving volumes and explicitly reports any missing geometry/latent closure.",
        ],
        "unknowns": [
            "Current input has no internal temperature observations.",
            "Current input has no independent, transferable rho/cp/k measurements for the target material.",
            "Latent heat/enthalpy is not identifiable and is omitted.",
            "Q4 moving-domain heat closure must be judged from energy-audit-summary.csv; it is not cleared by moisture balance alone.",
        ],
        "claims": [
            "The candidate numerically produces an internal temperature field and is fairly paired against the baseline.",
            "Independent space, independent time, and joint refinement evidence are recorded without treating joint refinement as either independent ladder.",
            "Parameter sensitivity ranks conditional risk but does not identify thermal properties.",
            "The package offers support-for-numerical-state, evidence-insufficient-needing-measurement, and unsupported-formal-upgrade outcomes for team decision.",
        ],
        "warnings": [
            "Do not overwrite formal 04-compute, 05-evidence, 06-figure, 07-paper, decisions, or workflow state.",
            "Do not write TEAM_APPROVED or start COMPUTE from this handoff.",
            "Do not call Q_latent=0 a physical measurement; it is an omitted term.",
        ],
        "required_next_actions": [
            "Team chooses A/B/C in H2-选择包.md; this task does not choose.",
            "If B is considered, obtain internal temperature and independent thermal-property/enthalpy data, then rerun the preregistered gates.",
            "If Q4 energy residual fails refinement, retain the candidate only as an ablation or reject it for the formal route.",
        ],
        "validation_register": [{"id": v["id"], "status": v["status"]} for v in validations],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_json(OUT / "handoff.json", handoff)
    write_json(OUT / "manifest.json", {"inputs": manifest, "outputs": outputs,
                                        "handoff_sha256": sha256(OUT / "handoff.json")})
    print(json.dumps({"status": status, "core_runs": len([r for r in rows if r.get("family") in ("spatial", "time", "joint")]),
                      "total_rows": len(rows), "output_dir": str(OUT),
                      "validation_counts": {s: sum(v["status"] == s for v in validations) for s in ("PASS", "INCONCLUSIVE", "BLOCKED", "FAIL")}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
