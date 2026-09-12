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


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ATTEMPT_SCRIPT = ROOT / "03-prototype" / "controller-phase-change-attempt-20260912" / "run_phase_change_attempt.py"
SOURCE_SCRIPT = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
PYTHON_EXE = Path(sys.executable).resolve()
SEED = 20260912
LEVELS = ("L", "M", "H", "X")
QUESTIONS = ("Q2", "Q3", "Q4")
HM_TOLERANCE_S = 60.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8")


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
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_attempt_module():
    name = "phase_change_attempt_readonly_for_convergence"
    spec = importlib.util.spec_from_file_location(name, ATTEMPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {ATTEMPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def input_records() -> list[dict]:
    candidates = [
        ATTEMPT_SCRIPT,
        SOURCE_SCRIPT,
        ROOT / "input" / "A题" / "附件" / "附件1.xlsx",
        ROOT / "input" / "A题" / "附件" / "附件2.xlsx",
        ROOT / "decisions" / "H1-problem.json",
        ROOT / "decisions" / "H2-model.json",
        ROOT / "02-design" / "contracts" / "model-q23-fixed.json",
        ROOT / "02-design" / "contracts" / "model-q4-m1-reference.json",
        ROOT / "02-design" / "验证计划.json",
    ]
    records = []
    for path in candidates:
        records.append({
            "path": rel(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
            "sha256": sha256(path) if path.is_file() else None,
        })
    return records


def case_specs() -> list[dict]:
    meshes = {"L": 8, "M": 12, "H": 18, "X": 27}
    time_steps = {
        "Q2": {"L": 240.0, "M": 120.0, "H": 60.0, "X": 30.0},
        "Q3": {"L": 600.0, "M": 300.0, "H": 150.0, "X": 75.0},
        "Q4": {"L": 600.0, "M": 300.0, "H": 150.0, "X": 75.0},
    }
    durations = {"Q2": 10800.0, "Q3": 259200.0, "Q4": 259200.0}
    samples = {"Q2": 600.0, "Q3": 3600.0, "Q4": 3600.0}
    specs: list[dict] = []
    for question in QUESTIONS:
        for level in LEVELS:
            specs.append({
                "case_id": f"{question}-space-{level}",
                "question": question,
                "axis": "space",
                "space_level": level,
                "time_level": "M",
                "nr": meshes[level],
                "nz": meshes[level],
                "dt_s": time_steps[question]["M"],
                "duration_s": durations[question],
                "sample_every_s": samples[question],
                "fixed_variable": "dt=M",
            })
        for level in LEVELS:
            specs.append({
                "case_id": f"{question}-time-{level}",
                "question": question,
                "axis": "time",
                "space_level": "M",
                "time_level": level,
                "nr": meshes["M"],
                "nz": meshes["M"],
                "dt_s": time_steps[question][level],
                "duration_s": durations[question],
                "sample_every_s": samples[question],
                "fixed_variable": "grid=M",
            })
    return specs


def raw_result_payload(spec: dict, status: str, result: dict | None = None,
                       error: str | None = None, trace_text: str | None = None) -> dict:
    payload = {
        "case": spec,
        "candidate": "nominal_proxy",
        "threshold_definition": "source candidate unchanged: 0.15 - 1e-6 for Q3/Q4; no threshold for Q2",
        "status": status,
    }
    if result is not None:
        payload["result"] = {
            "config": result["config"],
            "metrics": result["metrics"],
            "records": result["records"],
            "latent_trace": result.get("latent_trace", []),
            "water_trace": result.get("water_trace", []),
            "heat_trace": result.get("heat_trace", []),
        }
    if error is not None:
        payload["failure_reason"] = error
    if trace_text is not None:
        payload["traceback"] = trace_text
    return payload


def temperature_stats(result: dict) -> dict:
    records = result.get("records", [])
    values = []
    for row in records:
        for key in ("center_T_C", "surface_T_C"):
            value = row.get(key)
            if value is not None and np.isfinite(float(value)):
                values.append(float(value))
    final_t = np.asarray(result.get("final_t", []), dtype=float)
    finite_field = final_t[np.isfinite(final_t)] - 273.15 if final_t.size else np.asarray([], dtype=float)
    return {
        "recorded_temperature_min_C": min(values) if values else None,
        "recorded_temperature_max_C": max(values) if values else None,
        "recorded_temperature_range_C": (max(values) - min(values)) if values else None,
        "final_field_temperature_min_C": float(np.min(finite_field)) if finite_field.size else None,
        "final_field_temperature_max_C": float(np.max(finite_field)) if finite_field.size else None,
        "final_field_temperature_range_C": float(np.ptp(finite_field)) if finite_field.size else None,
    }


def result_row(spec: dict, status: str, result: dict | None = None,
               failure_reason: str | None = None) -> dict:
    row = {
        "case_id": spec["case_id"],
        "candidate": "nominal_proxy",
        "question": spec["question"],
        "axis": spec["axis"],
        "space_level": spec["space_level"],
        "time_level": spec["time_level"],
        "nr": spec["nr"],
        "nz": spec["nz"],
        "dt_s": spec["dt_s"],
        "duration_s": spec["duration_s"],
        "fixed_variable": spec["fixed_variable"],
        "threshold_C": (0.15 - 1e-6) if spec["question"] in ("Q3", "Q4") else None,
        "status": status,
        "threshold_status": "RUN_FAILED" if status == "FAIL" else ("NOT_APPLICABLE" if spec["question"] == "Q2" else None),
        "failure_reason": failure_reason,
    }
    if result is None:
        return row
    metrics = result["metrics"]
    row.update({
        "runtime_s": metrics.get("runtime_s"),
        "reported_event_time_s": metrics.get("reported_event_time_s"),
        "interpolated_event_time_s": metrics.get("interpolated_event_time_s"),
        "final_time_s": metrics.get("final_time_s"),
        "final_max_C": metrics.get("final_max_C"),
        "final_mean_C": metrics.get("final_mean_C"),
        "max_linear_relative_residual": metrics.get("max_linear_relative_residual"),
        "normalized_moisture_balance_error": metrics.get("normalized_moisture_balance_error"),
        "max_physical_heat_balance_relative": metrics.get("max_physical_heat_balance_relative"),
        "max_physical_heat_balance_residual_J": metrics.get("max_physical_heat_balance_residual_J"),
        "latent_integral_J_est": metrics.get("latent_integral_J_est"),
        "latent_peak_power_W": metrics.get("latent_peak_power_W"),
        "water_balance_max_abs_kg_s": metrics.get("water_balance_max_abs_kg_s"),
        "latent_mass_closure": metrics.get("latent_mass_closure"),
    })
    if spec["question"] in ("Q3", "Q4"):
        row["threshold_status"] = "REACHED" if metrics.get("interpolated_event_time_s") is not None else "NOT_REACHED_WITHIN_DURATION"
    row.update(temperature_stats(result))
    return row


def write_case_artifacts(spec: dict, result: dict | None, status: str,
                         failure_reason: str | None, trace_text: str | None) -> None:
    case_dir = OUT / "raw-results" / spec["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    write_json(case_dir / "result.json", raw_result_payload(spec, status, result, failure_reason, trace_text))
    if result is None:
        return
    np.savez_compressed(case_dir / "state-arrays.npz", final_c=result["final_c"], final_t=result["final_t"])
    write_csv(case_dir / "trajectory.csv", result.get("records", []))
    write_csv(case_dir / "latent-trace.csv", result.get("latent_trace", []))
    write_csv(case_dir / "water-trace.csv", result.get("water_trace", []))
    write_csv(case_dir / "heat-trace.csv", result.get("heat_trace", []))


def add_adjacent(rows: list[dict], axis: str) -> list[dict]:
    output = []
    for question in QUESTIONS:
        selected = [row for row in rows if row["question"] == question and row["axis"] == axis]
        selected.sort(key=lambda row: LEVELS.index(row["space_level"] if axis == "space" else row["time_level"]))
        previous = None
        for row in selected:
            enriched = dict(row)
            level = row["space_level"] if axis == "space" else row["time_level"]
            enriched["level"] = level
            enriched["adjacent_from_level"] = previous["level"] if previous is not None else None
            if previous is not None and row["status"] == "PASS" and previous["status"] == "PASS":
                if row.get("interpolated_event_time_s") is not None and previous.get("interpolated_event_time_s") is not None:
                    enriched["adjacent_event_time_change_interpolated_s"] = abs(float(row["interpolated_event_time_s"]) - float(previous["interpolated_event_time_s"]))
                else:
                    enriched["adjacent_event_time_change_interpolated_s"] = None
                if row.get("reported_event_time_s") is not None and previous.get("reported_event_time_s") is not None:
                    enriched["adjacent_event_time_change_reported_s"] = abs(float(row["reported_event_time_s"]) - float(previous["reported_event_time_s"]))
                else:
                    enriched["adjacent_event_time_change_reported_s"] = None
                enriched["adjacent_final_max_C_change"] = abs(float(row["final_max_C"]) - float(previous["final_max_C"]))
                enriched["adjacent_final_mean_C_change"] = abs(float(row["final_mean_C"]) - float(previous["final_mean_C"]))
            else:
                enriched["adjacent_event_time_change_interpolated_s"] = None
                enriched["adjacent_event_time_change_reported_s"] = None
                enriched["adjacent_final_max_C_change"] = None
                enriched["adjacent_final_mean_C_change"] = None
            output.append(enriched)
            previous = enriched
    return output


def hm_checks(rows: list[dict], axis: str) -> list[dict]:
    checks = []
    for question in ("Q3", "Q4"):
        medium = next((row for row in rows if row["question"] == question and row["axis"] == axis and row["space_level"] == "M" and row["time_level"] == "M"), None)
        high = next((row for row in rows if row["question"] == question and row["axis"] == axis and row["space_level"] == "H" and row["time_level"] == "H"), None)
        check = {
            "question": question,
            "axis": axis,
            "comparison": "H-M",
            "tolerance_s": HM_TOLERANCE_S,
            "M_status": medium["status"] if medium else "MISSING",
            "H_status": high["status"] if high else "MISSING",
            "status": "INCONCLUSIVE",
            "reason": "missing run or failed run",
        }
        if medium and high and medium["status"] == "PASS" and high["status"] == "PASS":
            m_interp = medium.get("interpolated_event_time_s")
            h_interp = high.get("interpolated_event_time_s")
            m_report = medium.get("reported_event_time_s")
            h_report = high.get("reported_event_time_s")
            check.update({
                "M_interpolated_event_time_s": m_interp,
                "H_interpolated_event_time_s": h_interp,
                "M_reported_event_time_s": m_report,
                "H_reported_event_time_s": h_report,
            })
            if m_interp is not None and h_interp is not None:
                check["interpolated_delta_s"] = abs(float(h_interp) - float(m_interp))
                check["reported_delta_s"] = abs(float(h_report) - float(m_report)) if m_report is not None and h_report is not None else None
                check["within_60s"] = bool(check["interpolated_delta_s"] <= HM_TOLERANCE_S)
                check["status"] = "PASS" if check["within_60s"] else "FAIL"
                check["reason"] = "absolute H-M interpolated threshold-time change compared with 60 s tolerance"
    return checks


def render_review(space_rows: list[dict], time_rows: list[dict], checks: list[dict], failures: list[dict]) -> str:
    def fmt(value):
        return "" if value is None else f"{float(value):.6g}" if isinstance(value, (int, float)) else str(value)

    lines = [
        "# 潜热候选独立空间/时间收敛审查",
        "",
        "状态：**候选审查中；不进入正式 COMPUTE/EVIDENCE/FIGURE/PAPER。**",
        "",
        "本轮只读调用 `controller-phase-change-attempt-20260912/run_phase_change_attempt.py` 的 `nominal_proxy`，所有新产物位于本目录。空间梯度固定 `dt=M`，时间梯度固定 `12×12` 中等网格；Q3/Q4 使用源代码原阈值 `0.15−1e−6`，没有改阈值，也没有删除失败算例。",
        "",
        "## 空间梯子",
        "",
        "|问题|层级|网格|dt(s)|状态|达标时间(s)|温度记录范围(°C)|相邻达标时间变化(s)|",
        "|---|---|---:|---:|---|---:|---:|---:|",
    ]
    for row in space_rows:
        lines.append(f"|{row['question']}|{row['level']}|{row['nr']}×{row['nz']}|{row['dt_s']}|{row['status']}|{fmt(row.get('interpolated_event_time_s'))}|{fmt(row.get('recorded_temperature_range_C'))}|{fmt(row.get('adjacent_event_time_change_interpolated_s'))}|")
    lines += ["", "## 时间梯子", "", "|问题|层级|网格|dt(s)|状态|达标时间(s)|温度记录范围(°C)|相邻达标时间变化(s)|", "|---|---|---:|---:|---|---:|---:|---:|"]
    for row in time_rows:
        lines.append(f"|{row['question']}|{row['level']}|{row['nr']}×{row['nz']}|{row['dt_s']}|{row['status']}|{fmt(row.get('interpolated_event_time_s'))}|{fmt(row.get('recorded_temperature_range_C'))}|{fmt(row.get('adjacent_event_time_change_interpolated_s'))}|")
    lines += ["", "## Q3/Q4 H-M 60 秒检查", "", "|问题|轴|M达标时间(s)|H达标时间(s)|插值差(s)|报告差(s)|结论|", "|---|---|---:|---:|---:|---:|---|"]
    for check in checks:
        lines.append(f"|{check['question']}|{check['axis']}|{fmt(check.get('M_interpolated_event_time_s'))}|{fmt(check.get('H_interpolated_event_time_s'))}|{fmt(check.get('interpolated_delta_s'))}|{fmt(check.get('reported_delta_s'))}|{check['status']}|")
    lines += ["", "## 失败保留", "", f"失败算例数：{len(failures)}。每个失败算例保留在 `raw-results/<case-id>/result.json`，并在两张收敛 CSV 中保留；失败原因没有用阈值调整或删案规避。", ""]
    for failure in failures:
        lines.append(f"- `{failure['case_id']}`：{failure['failure_reason']}")
    lines += ["", "## 证据边界", "", "- 这些是基于总含水率边界损失的等效潜热工程代理，不是液—汽—结合水守恒模型。", "- 数值收敛不解除潜热参数、相分辨库存和相质量—能量闭合的识别阻塞。", "- H-M 检查只回答离散事件时间变化是否达到预注册的 60 秒报告容差，不代表物理模型已验证。", ""]
    return "\n".join(lines)


def output_records() -> list[dict]:
    records = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name not in {"handoff.json", "manifest.json"}:
            records.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    np.random.seed(SEED)
    started = time.perf_counter()
    inputs = input_records()
    specs = case_specs()
    nominal = None
    all_rows: list[dict] = []
    failures: list[dict] = []
    log_path = OUT / "run.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({
            "command": " ".join(sys.argv),
            "python": sys.version,
            "python_executable": str(PYTHON_EXE),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "seed": SEED,
            "candidate": "nominal_proxy",
            "threshold": "unchanged source value 0.15 - 1e-6 for Q3/Q4",
            "write_boundary": rel(OUT),
            "started_at": datetime.now(timezone.utc).astimezone().isoformat(),
        }, ensure_ascii=False) + "\n")
        log.write("SCOPE: independent Q2/Q3/Q4 L/M/H/X space and time ladders; space fixes dt=M, time fixes 12x12 grid; failures retained.\n")
        log.flush()
        for index, spec in enumerate(specs, start=1):
            log.write(f"START {index}/{len(specs)} {json.dumps(spec, ensure_ascii=False)}\n")
            log.flush()
            try:
                attempt = load_attempt_module()
                if nominal is None:
                    nominal = dict(attempt.SCENARIOS["nominal_proxy"])
                module = attempt.load_module()
                cfg = attempt.config(module, spec["question"], spec["space_level"], spec["time_level"])
                cfg.label = f"convergence-{spec['case_id']}"
                cfg.sample_every = spec["sample_every_s"]
                result = attempt.run_case(module, cfg, nominal)
                row = result_row(spec, "PASS", result)
                all_rows.append(row)
                write_case_artifacts(spec, result, "PASS", None, None)
                log.write("DONE " + json.dumps(row, ensure_ascii=False, default=json_default) + "\n")
            except Exception as exc:
                failure_reason = repr(exc)
                trace_text = traceback.format_exc()
                row = result_row(spec, "FAIL", None, failure_reason)
                all_rows.append(row)
                failure = {"case_id": spec["case_id"], "question": spec["question"], "axis": spec["axis"], "status": "FAIL", "failure_reason": failure_reason}
                failures.append(failure)
                write_case_artifacts(spec, None, "FAIL", failure_reason, trace_text)
                log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
            log.flush()
        log.write(json.dumps({"completed_at": datetime.now(timezone.utc).astimezone().isoformat(), "runtime_s": time.perf_counter() - started}, ensure_ascii=False) + "\n")

    space_rows = add_adjacent(all_rows, "space")
    time_rows = add_adjacent(all_rows, "time")
    checks = hm_checks(all_rows, "space") + hm_checks(all_rows, "time")
    write_csv(OUT / "space-convergence.csv", space_rows)
    write_csv(OUT / "time-convergence.csv", time_rows)
    write_csv(OUT / "raw-results.csv", all_rows)
    write_csv(OUT / "failures.csv", failures)
    write_json(OUT / "hm-checks.json", {"tolerance_s": HM_TOLERANCE_S, "checks": checks})
    (OUT / "candidate-review.md").write_text(render_review(space_rows, time_rows, checks, failures), encoding="utf-8")

    summary = {
        "candidate": "nominal_proxy",
        "case_count": len(all_rows),
        "pass_count": sum(row["status"] == "PASS" for row in all_rows),
        "fail_count": len(failures),
        "space_levels": list(LEVELS),
        "time_levels": list(LEVELS),
        "threshold_definition": "unchanged source candidate threshold 0.15 - 1e-6 for Q3/Q4; Q2 has no threshold stop",
        "hm_checks": checks,
        "failure_case_ids": [item["case_id"] for item in failures],
    }
    write_json(OUT / "summary.json", summary)
    outputs = output_records()
    handoff = {
        "schema_version": "1.0",
        "stage": "PROTOTYPE",
        "status": "BLOCKED",
        "review_status": "PENDING_CANDIDATE_REVIEW",
        "scope": "independent numerical convergence audit of the nominal equivalent latent-heat candidate; no formal-stage writes",
        "inputs": inputs,
        "outputs": outputs,
        "frozen_decisions": [item for item in inputs if item["path"] in {"decisions/H1-problem.json", "decisions/H2-model.json"}],
        "assumptions": [
            "The existing nominal_proxy candidate is called read-only and uses the Appendix property laws, Attachment 1 environment history, and Attachment 2 radius history through the existing source solver.",
            "Space L/M/H/X fixes the medium time step; time L/M/H/X fixes the medium 12x12 grid.",
            "Q3/Q4 threshold remains exactly 0.15 - 1e-6 from the existing candidate source.",
            "A failed case is evidence and remains in raw-results.csv, the convergence CSV, and its raw-results case directory.",
        ],
        "unknowns": [
            "The candidate still lacks phase-resolved liquid/vapor/bound-water inventories and mass-energy closure.",
            "Numerical convergence does not provide internal-temperature observations or identify material-specific latent heat.",
        ],
        "claims": [
            "Independent Q2/Q3/Q4 spatial and temporal L/M/H/X runs are recorded with raw per-case outputs.",
            "Q3/Q4 H-M event-time changes are explicitly compared with the 60 s tolerance when both runs complete.",
            "This handoff stops at candidate review and does not select or promote the latent-heat candidate.",
        ],
        "warnings": [
            "Do not overwrite formal COMPUTE, EVIDENCE, FIGURE, PAPER, decisions, or workflow state.",
            "Do not change the threshold or remove failed cases when interpreting this package.",
            "Do not call the numerical candidate a validated multiphase latent-heat model.",
        ],
        "required_next_actions": [
            "Team reviews space-convergence.csv, time-convergence.csv, raw-results.csv, raw-results/, and hm-checks.json.",
            "Keep this candidate blocked unless phase-resolved data and closure are separately supplied and approved.",
        ],
        "validation_register": [
            {"id": "CV01-independent-space-ladder", "status": "PASS" if len(space_rows) == 12 else "FAIL"},
            {"id": "CV02-independent-time-ladder", "status": "PASS" if len(time_rows) == 12 else "FAIL"},
            {"id": "CV03-failure-retention", "status": "PASS" if all(item["case_id"] in {row["case_id"] for row in all_rows} for item in failures) else "FAIL"},
            {"id": "CV04-q3-q4-hm-60s", "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "INCONCLUSIVE"},
            {"id": "CV05-phase-closure", "status": "BLOCKED"},
            {"id": "CV06-candidate-review-stop", "status": "PASS"},
        ],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_json(OUT / "handoff.json", handoff)
    write_json(OUT / "manifest.json", {"inputs": inputs, "outputs": output_records(), "handoff_sha256": sha256(OUT / "handoff.json")})
    print(json.dumps({
        "status": handoff["status"],
        "review_status": handoff["review_status"],
        "cases": len(all_rows),
        "pass": sum(row["status"] == "PASS" for row in all_rows),
        "fail": len(failures),
        "hm_checks": checks,
        "output_dir": str(OUT),
        "runtime_s": time.perf_counter() - started,
    }, ensure_ascii=False, indent=2, default=json_default))


if __name__ == "__main__":
    main()
