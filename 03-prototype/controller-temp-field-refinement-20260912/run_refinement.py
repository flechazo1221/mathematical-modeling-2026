"""Continuation of the Q3/Q4 convergence ladder for the internal-T candidate.

This script reads the existing completion prototype and only adds finer
space/time cases.  It writes a new sibling directory so the previous evidence
package remains recoverable and untouched.
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


sys.dont_write_bytecode = True

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
COMPLETION_SCRIPT = ROOT / "03-prototype" / "controller-temp-field-completion-20260912" / "run_completion.py"
BASELINE_PATH = ROOT / "04-compute" / "src" / "formal_compute.py"
CANDIDATE_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
OLD_OUT = ROOT / "03-prototype" / "controller-temp-field-completion-20260912"
SEED = 20260912
THRESHOLD = 0.15 - 1e-6
REPORT_S = 60.0


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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_completion_module():
    return load_module("completion_for_refinement", COMPLETION_SCRIPT)


def old_rows() -> list[dict]:
    rows: list[dict] = []
    for implementation, directory in (
        ("prescribed-T-baseline", "model-baseline"),
        ("internal-temperature", "model-internal-temperature"),
    ):
        for question in ("Q3", "Q4"):
            for family in ("spatial", "time"):
                for level in ("L", "M", "H"):
                    path = OLD_OUT / directory / f"{question}-{family}-{level}" / "metrics.json"
                    if not path.is_file():
                        raise FileNotFoundError(path)
                    row = json.loads(path.read_text(encoding="utf-8"))
                    row["source"] = "existing-completion-package"
                    rows.append(row)
    return rows


def new_specs() -> list[dict]:
    specs: list[dict] = []
    for question in ("Q3", "Q4"):
        duration = 259200.0
        sample = 3600.0
        # X/Y extend the existing 8/12/18 ladder.  Time Z is included because
        # the observed first-order trend suggests Y may still exceed 60 s.
        for level, mesh in (("X", 27), ("Y", 36)):
            specs.append({
                "question": question, "family": "spatial", "level": level,
                "nr": mesh, "nz": mesh, "dt": 300.0, "duration": duration,
                "sample_every": sample, "space_level": level, "time_level": "M",
                "label": f"{question}-spatial-{level}",
            })
        for level, dt in (("X", 75.0), ("Y", 37.5), ("Z", 18.75)):
            specs.append({
                "question": question, "family": "time", "level": level,
                "nr": 12, "nz": 12, "dt": dt, "duration": duration,
                "sample_every": sample, "space_level": "M", "time_level": level,
                "label": f"{question}-time-{level}",
            })
    return specs


def save_case(implementation: str, spec: dict, summary: dict, groups: list[dict], run: dict) -> None:
    directory = "model-baseline" if implementation == "prescribed-T-baseline" else "model-internal-temperature"
    case_dir = OUT / directory / f"{spec['question']}-{spec['family']}-{spec['level']}"
    write_json(case_dir / "metrics.json", summary)
    write_json(case_dir / "raw-result.json", {
        "case": spec,
        "implementation": implementation,
        "metrics": run["metrics"],
        "records": run["records"],
    })
    np.savez_compressed(case_dir / "state-arrays.npz", final_c=run["final_c"], final_t=run["final_t"])
    write_csv(case_dir / "trajectory.csv", run.get("records", []))
    if groups:
        write_csv(case_dir / "energy-groups.csv", groups)


def all_rows_with_adjacent(rows: list[dict], family: str) -> list[dict]:
    order = {"spatial": ["L", "M", "H", "X", "Y"], "time": ["L", "M", "H", "X", "Y", "Z"]}[family]
    output: list[dict] = []
    for implementation in ("prescribed-T-baseline", "internal-temperature"):
        for question in ("Q3", "Q4"):
            selected = [r for r in rows if r.get("implementation") == implementation
                        and r.get("question") == question and r.get("family") == family]
            selected.sort(key=lambda row: order.index(row["level"]))
            previous = None
            for row in selected:
                enriched = dict(row)
                if previous is None:
                    enriched["adjacent_change_s"] = None
                    enriched["refinement_status"] = "NA"
                else:
                    value = row.get("interpolated_event_time_s")
                    old_value = previous.get("interpolated_event_time_s")
                    change = None if value is None or old_value is None else abs(float(value) - float(old_value))
                    enriched["adjacent_change_s"] = change
                    old_change = previous.get("adjacent_change_s")
                    enriched["refinement_status"] = (
                        "PASS_60S" if change is not None and change <= REPORT_S else
                        "DECREASING" if old_change is None or change <= old_change else
                        "NOT_MONOTONE"
                    )
                enriched["ladder"] = family
                output.append(enriched)
                previous = enriched
    return output


def hm_checks(rows: list[dict], family: str) -> list[dict]:
    checks = []
    for implementation in ("prescribed-T-baseline", "internal-temperature"):
        for question in ("Q3", "Q4"):
            selected = [r for r in rows if r.get("implementation") == implementation
                        and r.get("question") == question and r.get("family") == family]
            selected.sort(key=lambda row: {"spatial": ["L", "M", "H", "X", "Y"],
                                           "time": ["L", "M", "H", "X", "Y", "Z"]}[family].index(row["level"]))
            last = selected[-1] if selected else None
            checks.append({
                "implementation": implementation,
                "question": question,
                "ladder": family,
                "last_level": last.get("level") if last else None,
                "last_adjacent_change_s": last.get("adjacent_change_s") if last else None,
                "within_60s": bool(last and last.get("adjacent_change_s") is not None
                                   and float(last["adjacent_change_s"]) <= REPORT_S),
            })
    return checks


def render_report(space_rows: list[dict], time_rows: list[dict], checks: list[dict], failures: list[dict]) -> str:
    def fmt(value):
        return "" if value is None else f"{float(value):.6g}" if isinstance(value, (int, float)) else str(value)

    lines = [
        "# 内部温度场补全：继续加密结果",
        "",
        "状态：**候选数值复审；不进入正式 COMPUTE/EVIDENCE/FIGURE/PAPER。**",
        "",
        "本轮读取既有 L/M/H 结果，新增 X/Y 空间层（27×27、36×36）和 X/Y/Z 时间层（75、37.5、18.75 s），均对基线与内部温度候选成对运行。阈值仍为 `0.15−1e−6`，没有调阈值或删除失败算例。",
        "",
        "## 空间梯子",
        "",
        "|实现|问题|层级|网格|dt(s)|t*(s)|相邻变化(s)|判读|",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in space_rows:
        lines.append(f"|{row['implementation']}|{row['question']}|{row['level']}|{row.get('nr')}×{row.get('nz')}|{row.get('dt_s')}|{fmt(row.get('interpolated_event_time_s'))}|{fmt(row.get('adjacent_change_s'))}|{row.get('refinement_status')}|")
    lines += ["", "## 时间梯子", "", "|实现|问题|层级|网格|dt(s)|t*(s)|相邻变化(s)|判读|", "|---|---|---|---:|---:|---:|---:|---|"]
    for row in time_rows:
        lines.append(f"|{row['implementation']}|{row['question']}|{row['level']}|{row.get('nr')}×{row.get('nz')}|{row.get('dt_s')}|{fmt(row.get('interpolated_event_time_s'))}|{fmt(row.get('adjacent_change_s'))}|{row.get('refinement_status')}|")
    lines += ["", "## 最后一层 60 秒检查", "", "|实现|问题|梯子|最后层|相邻变化(s)|结论|", "|---|---|---|---|---:|---|"]
    for check in checks:
        conclusion = "PASS_60S" if check["within_60s"] else "INCONCLUSIVE"
        lines.append(f"|{check['implementation']}|{check['question']}|{check['ladder']}|{check['last_level']}|{fmt(check.get('last_adjacent_change_s'))}|{conclusion}|")
    lines += ["", "## 失败保留", "", f"失败算例数：{len(failures)}。失败结果保留在各算例目录的 `raw-result.json` 或日志中。", ""]
    for failure in failures:
        lines.append(f"- `{failure['implementation']}/{failure['question']}-{failure['family']}-{failure['level']}`：{failure['error']}")
    lines += ["", "## 证据边界", "", "- 60 秒判据只评价离散事件时间，不证明内部温度场具有现实测量准确性。", "- 潜热、相分辨库存和 Q4 物理热闭合问题不因本轮数值加密而解除。", "- 若最后一层仍超过 60 秒，结论保持 `INCONCLUSIVE`，不能写成‘基本收敛’。", ""]
    return "\n".join(lines)


def input_manifest() -> list[dict]:
    paths = [COMPLETION_SCRIPT, BASELINE_PATH, CANDIDATE_PATH,
             OLD_OUT / "H2-选择包.md", OLD_OUT / "handoff.json"]
    return [{"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in paths if path.is_file()]


def output_manifest() -> list[dict]:
    outputs = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name not in {"handoff.json", "manifest.json"}:
            outputs.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return outputs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    np.random.seed(SEED)
    old = old_rows()
    specs = new_specs()
    rows = list(old)
    failures: list[dict] = []
    log_path = OUT / "run.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({
            "command": " ".join(sys.argv), "python": sys.version,
            "python_executable": str(Path(sys.executable).resolve()),
            "platform": platform.platform(), "numpy": np.__version__, "seed": SEED,
            "candidate": "internal-temperature", "threshold": THRESHOLD,
            "write_boundary": rel(OUT),
            "started_at": datetime.now(timezone.utc).astimezone().isoformat(),
        }, ensure_ascii=False) + "\n")
        log.write("SCOPE: Q3/Q4 finer X/Y spatial and X/Y/Z temporal ladders; paired baseline/candidate; prior L/M/H retained.\n")
        log.flush()
        for index, spec in enumerate(specs, start=1):
            for implementation, source_path in (
                ("prescribed-T-baseline", BASELINE_PATH),
                ("internal-temperature", CANDIDATE_PATH),
            ):
                log.write(f"START {index}/{len(specs)} {implementation} {json.dumps(spec, ensure_ascii=False)}\n")
                log.flush()
                try:
                    module = load_module(f"refine_{implementation}_{spec['question']}_{spec['family']}_{spec['level']}", source_path)
                    completion = load_completion_module()
                    summary, groups, run = completion.run_one(
                        module, implementation, spec, log, {}, save_artifacts=False, return_run=True
                    )
                    summary["source"] = "new-refinement-run"
                    rows.append(summary)
                    save_case(implementation, spec, summary, groups, run)
                    log.write("DONE " + json.dumps(summary, ensure_ascii=False, default=json_default) + "\n")
                except Exception as exc:
                    failure = {
                        "implementation": implementation, "question": spec["question"],
                        "family": spec["family"], "level": spec["level"],
                        "error": repr(exc), "traceback": traceback.format_exc(limit=12),
                    }
                    failures.append(failure)
                    log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
                log.flush()
        log.write(json.dumps({"completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
                              "runtime_s": time.perf_counter() - started}, ensure_ascii=False) + "\n")

    space_rows = all_rows_with_adjacent(rows, "spatial")
    time_rows = all_rows_with_adjacent(rows, "time")
    checks = hm_checks(space_rows, "spatial") + hm_checks(time_rows, "time")
    write_csv(OUT / "space-convergence.csv", space_rows)
    write_csv(OUT / "time-convergence.csv", time_rows)
    write_csv(OUT / "raw-results.csv", rows)
    write_csv(OUT / "failures.csv", failures)
    write_json(OUT / "checks.json", {"tolerance_s": REPORT_S, "checks": checks})
    (OUT / "refinement-report.md").write_text(render_report(space_rows, time_rows, checks, failures), encoding="utf-8")
    write_json(OUT / "environment.json", {
        "python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(), "numpy": np.__version__, "seed": SEED,
        "threshold": THRESHOLD, "report_grid_s": REPORT_S,
        "write_boundary": rel(OUT), "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
    })
    inputs = input_manifest()
    outputs = output_manifest()
    handoff = {
        "schema_version": "1.0", "stage": "PROTOTYPE-CANDIDATE-REFINEMENT",
        "status": "BLOCKED", "review_status": "PENDING_CANDIDATE_REVIEW",
        "scope": "Q3/Q4 independent finer space/time convergence for the internal-temperature candidate; no formal-stage writes",
        "inputs": inputs, "outputs": outputs,
        "frozen_decisions": [item for item in inputs if item["path"].startswith("decisions/")],
        "assumptions": [
            "Existing L/M/H completion-package results are retained as the lower ladder levels.",
            "New X/Y space and X/Y/Z time cases use the same source equations, threshold, properties, geometry, and paired baseline/candidate protocol.",
            "Reported event time is quantized to 60 s only after the unrounded event time is computed.",
        ],
        "unknowns": [
            "The candidate has no internal-temperature observations.",
            "Numerical convergence cannot establish physical latent-heat or thermal-property identification.",
        ],
        "claims": [
            "The finer ladders provide additional numerical evidence while preserving the earlier L/M/H results.",
            "Any last adjacent change above 60 s remains INCONCLUSIVE and does not promote the candidate.",
        ],
        "warnings": [
            "Do not overwrite formal COMPUTE, EVIDENCE, FIGURE, PAPER, decisions, or workflow state.",
            "Do not convert a numerical PASS_60S check into physical model validation.",
        ],
        "required_next_actions": [
            "Review refinement-report.md, space-convergence.csv, time-convergence.csv, checks.json, and raw-results.csv.",
            "Keep the candidate at H2 review unless physical closure and independent observations are supplied.",
        ],
        "validation_register": [
            {"id": "RF01-prior-levels-retained", "status": "PASS" if len(old) == 12 else "FAIL"},
            {"id": "RF02-new-cases-recorded", "status": "PASS" if len(rows) - len(old) == len(specs) * 2 else "FAIL"},
            {"id": "RF03-failure-retention", "status": "PASS"},
            {"id": "RF04-time-60s", "status": "PASS" if all(c["within_60s"] for c in checks if c["ladder"] == "time") else "INCONCLUSIVE"},
            {"id": "RF05-space-60s", "status": "PASS" if all(c["within_60s"] for c in checks if c["ladder"] == "spatial") else "INCONCLUSIVE"},
            {"id": "RF06-candidate-review-stop", "status": "PASS"},
        ],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_json(OUT / "handoff.json", handoff)
    write_json(OUT / "manifest.json", {"inputs": inputs, "outputs": output_manifest(),
                                       "handoff_sha256": sha256(OUT / "handoff.json")})
    print(json.dumps({
        "status": handoff["status"], "new_cases": len(rows) - len(old),
        "failed_new_cases": len(failures), "time_checks": [c for c in checks if c["ladder"] == "time"],
        "space_checks": [c for c in checks if c["ladder"] == "spatial"],
        "output_dir": str(OUT), "runtime_s": time.perf_counter() - started,
    }, ensure_ascii=False, indent=2, default=json_default))


if __name__ == "__main__":
    main()
