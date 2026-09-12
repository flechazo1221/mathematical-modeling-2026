"""Continue only the spatial convergence ladder after time convergence.

The previous refinement package already contains L/M/H/X/Y results.  This
script reads them, adds Z/W/V/U = 54/72/108/144 cells, and writes a separate
package without touching earlier evidence or formal-stage directories.
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
PREVIOUS_OUT = ROOT / "03-prototype" / "controller-temp-field-refinement-20260912"
BASELINE_PATH = ROOT / "04-compute" / "src" / "formal_compute.py"
CANDIDATE_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
THRESHOLD = 0.15 - 1e-6
REPORT_S = 60.0
SEED = 20260912
ORDER = ["L", "M", "H", "X", "Y", "Z", "W", "V", "U"]


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
    return load_module("completion_for_space_refinement", COMPLETION_SCRIPT)


def read_metrics(path: Path, source: str) -> dict:
    row = json.loads(path.read_text(encoding="utf-8"))
    row["source"] = source
    return row


def existing_space_rows() -> list[dict]:
    rows: list[dict] = []
    for implementation, directory in (
        ("prescribed-T-baseline", "model-baseline"),
        ("internal-temperature", "model-internal-temperature"),
    ):
        for question in ("Q3", "Q4"):
            for level in ("L", "M", "H"):
                path = ROOT / "03-prototype" / "controller-temp-field-completion-20260912" / directory / f"{question}-spatial-{level}" / "metrics.json"
                if not path.is_file():
                    raise FileNotFoundError(path)
                rows.append(read_metrics(path, "existing-completion-package"))
            for level in ("X", "Y"):
                path = PREVIOUS_OUT / directory / f"{question}-spatial-{level}" / "metrics.json"
                if not path.is_file():
                    raise FileNotFoundError(path)
                rows.append(read_metrics(path, "previous-refinement-package"))
    return rows


def new_specs() -> list[dict]:
    specs: list[dict] = []
    for question in ("Q3", "Q4"):
        for level, mesh in (("Z", 54), ("W", 72), ("V", 108), ("U", 144)):
            specs.append({
                "question": question, "family": "spatial", "level": level,
                "nr": mesh, "nz": mesh, "dt": 300.0, "duration": 259200.0,
                "sample_every": 3600.0, "space_level": level, "time_level": "M",
                "label": f"{question}-spatial-{level}",
            })
    return specs


def save_case(implementation: str, spec: dict, summary: dict, groups: list[dict], run: dict) -> None:
    directory = "model-baseline" if implementation == "prescribed-T-baseline" else "model-internal-temperature"
    case_dir = OUT / directory / f"{spec['question']}-spatial-{spec['level']}"
    write_json(case_dir / "metrics.json", summary)
    write_json(case_dir / "raw-result.json", {
        "case": spec, "implementation": implementation,
        "metrics": run["metrics"], "records": run["records"],
    })
    np.savez_compressed(case_dir / "state-arrays.npz", final_c=run["final_c"], final_t=run["final_t"])
    write_csv(case_dir / "trajectory.csv", run.get("records", []))
    if groups:
        write_csv(case_dir / "energy-groups.csv", groups)


def ladder_rows(rows: list[dict]) -> list[dict]:
    output: list[dict] = []
    for implementation in ("prescribed-T-baseline", "internal-temperature"):
        for question in ("Q3", "Q4"):
            selected = [r for r in rows if r.get("implementation") == implementation
                        and r.get("question") == question and r.get("family") == "spatial"]
            selected.sort(key=lambda row: ORDER.index(row["level"]))
            previous = None
            for row in selected:
                enriched = dict(row)
                if previous is None:
                    enriched["adjacent_change_s"] = None
                    enriched["refinement_status"] = "NA"
                else:
                    change = abs(float(row["interpolated_event_time_s"]) - float(previous["interpolated_event_time_s"]))
                    enriched["adjacent_change_s"] = change
                    old_change = previous.get("adjacent_change_s")
                    enriched["refinement_status"] = (
                        "PASS_60S" if change <= REPORT_S else
                        "DECREASING" if old_change is None or change <= old_change else
                        "NOT_MONOTONE"
                    )
                enriched["ladder"] = "spatial"
                output.append(enriched)
                previous = enriched
    return output


def last_checks(rows: list[dict]) -> list[dict]:
    checks = []
    for implementation in ("prescribed-T-baseline", "internal-temperature"):
        for question in ("Q3", "Q4"):
            selected = [r for r in rows if r.get("implementation") == implementation
                        and r.get("question") == question and r.get("family") == "spatial"]
            selected.sort(key=lambda row: ORDER.index(row["level"]))
            last = selected[-1] if selected else None
            checks.append({
                "implementation": implementation, "question": question,
                "last_level": last.get("level") if last else None,
                "last_adjacent_change_s": last.get("adjacent_change_s") if last else None,
                "within_60s": bool(last and last.get("adjacent_change_s") is not None
                                   and float(last["adjacent_change_s"]) <= REPORT_S),
            })
    return checks


def render_report(rows: list[dict], checks: list[dict], failures: list[dict]) -> str:
    def fmt(value):
        return "" if value is None else f"{float(value):.6g}"

    lines = [
        "# 内部温度场补全：空间继续加密结果", "",
        "状态：**候选数值复审；不进入正式 COMPUTE/EVIDENCE/FIGURE/PAPER。**", "",
        "本轮保留既有 L/M/H/X/Y 空间结果，新增 Z/W/V/U = 54/72/108/144 个径向/轴向单元；时间步固定 300 s，基线与内部温度候选成对运行。阈值仍为 `0.15−1e−6`。", "",
        "|实现|问题|层级|网格|t*(s)|相邻变化(s)|判读|", "|---|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"|{row['implementation']}|{row['question']}|{row['level']}|{row.get('nr')}×{row.get('nz')}|{fmt(row.get('interpolated_event_time_s'))}|{fmt(row.get('adjacent_change_s'))}|{row.get('refinement_status')}|")
    lines += ["", "## 最后一层检查", "", "|实现|问题|最后层|相邻变化(s)|结论|", "|---|---|---|---:|---|"]
    for check in checks:
        lines.append(f"|{check['implementation']}|{check['question']}|{check['last_level']}|{fmt(check.get('last_adjacent_change_s'))}|{'PASS_60S' if check['within_60s'] else 'INCONCLUSIVE'}|")
    lines += ["", "## 失败保留", "", f"失败新算例数：{len(failures)}。", ""]
    for failure in failures:
        lines.append(f"- `{failure['implementation']}/{failure['question']}-{failure['level']}`：{failure['error']}")
    lines += ["", "## 证据边界", "", "- 60 秒判据只评价离散事件时刻，不等于物理模型验证。", "- 本轮不改变参数、阈值、边界条件或正式阶段文件。", "- 最后一层仍超出 60 秒时，保持 `INCONCLUSIVE`，不强行判 PASS。", ""]
    return "\n".join(lines)


def output_manifest() -> list[dict]:
    result = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name not in {"handoff.json", "manifest.json"}:
            result.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    np.random.seed(SEED)
    rows = existing_space_rows()
    specs = new_specs()
    failures: list[dict] = []
    with (OUT / "run.log").open("w", encoding="utf-8") as log:
        log.write(json.dumps({
            "command": " ".join(sys.argv), "python": sys.version,
            "python_executable": str(Path(sys.executable).resolve()),
            "platform": platform.platform(), "numpy": np.__version__, "seed": SEED,
            "threshold": THRESHOLD, "write_boundary": rel(OUT),
            "started_at": datetime.now(timezone.utc).astimezone().isoformat(),
        }, ensure_ascii=False) + "\n")
        log.write("SCOPE: spatial Z/W/V/U = 54/72/108/144, fixed dt=300 s, paired baseline/candidate; prior L/M/H/X/Y retained.\n")
        log.flush()
        for index, spec in enumerate(specs, start=1):
            for implementation, source_path in (
                ("prescribed-T-baseline", BASELINE_PATH),
                ("internal-temperature", CANDIDATE_PATH),
            ):
                log.write(f"START {index}/{len(specs)} {implementation} {json.dumps(spec, ensure_ascii=False)}\n")
                log.flush()
                try:
                    module = load_module(f"space_refine_{implementation}_{spec['question']}_{spec['level']}", source_path)
                    completion = load_completion_module()
                    summary, groups, run = completion.run_one(
                        module, implementation, spec, log, {}, save_artifacts=False, return_run=True
                    )
                    summary["source"] = "new-space-refinement-run"
                    rows.append(summary)
                    save_case(implementation, spec, summary, groups, run)
                    log.write("DONE " + json.dumps(summary, ensure_ascii=False, default=json_default) + "\n")
                except Exception as exc:
                    failure = {"implementation": implementation, "question": spec["question"],
                               "level": spec["level"], "error": repr(exc),
                               "traceback": traceback.format_exc(limit=12)}
                    failures.append(failure)
                    log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
                log.flush()
        log.write(json.dumps({"completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
                              "runtime_s": time.perf_counter() - started}, ensure_ascii=False) + "\n")

    ladder = ladder_rows(rows)
    checks = last_checks(ladder)
    write_csv(OUT / "space-convergence.csv", ladder)
    write_csv(OUT / "raw-results.csv", rows)
    write_csv(OUT / "failures.csv", failures)
    write_json(OUT / "checks.json", {"tolerance_s": REPORT_S, "checks": checks})
    (OUT / "refinement-report.md").write_text(render_report(ladder, checks, failures), encoding="utf-8")
    inputs = [{"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in (
        COMPLETION_SCRIPT, BASELINE_PATH, CANDIDATE_PATH,
        PREVIOUS_OUT / "space-convergence.csv",
        ROOT / "03-prototype" / "controller-temp-field-completion-20260912" / "handoff.json",
    ) if path.is_file()]
    write_json(OUT / "environment.json", {
        "python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(), "numpy": np.__version__, "seed": SEED,
        "threshold": THRESHOLD, "report_grid_s": REPORT_S,
        "write_boundary": rel(OUT), "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
    })
    outputs = output_manifest()
    handoff = {
        "schema_version": "1.0", "stage": "PROTOTYPE-CANDIDATE-SPACE-REFINEMENT",
        "status": "BLOCKED", "review_status": "PENDING_CANDIDATE_REVIEW",
        "scope": "continued Q3/Q4 spatial convergence for the internal-temperature candidate; no formal-stage writes",
        "inputs": inputs, "outputs": outputs,
        "assumptions": [
            "Prior L/M/H/X/Y results are retained and are the lower spatial ladder levels.",
            "New Z/W/V/U cases use the same equations, threshold, properties, geometry, and paired protocol.",
            "A numerical 60 s pass does not clear missing internal observations or physical closure.",
        ],
        "unknowns": ["The candidate has no internal-temperature observations.",
                     "Numerical convergence does not identify thermal properties or latent heat."],
        "claims": ["The extended spatial ladder is recorded with per-case raw outputs.",
                   "The final adjacent spatial change is reported honestly against the 60 s tolerance."],
        "warnings": ["Do not overwrite formal COMPUTE, EVIDENCE, FIGURE, PAPER, decisions, or workflow state.",
                     "Do not promote this candidate solely from numerical convergence."],
        "required_next_actions": ["Review refinement-report.md, space-convergence.csv, checks.json, and raw-results.csv.",
                                   "Keep the candidate at H2 review unless physical evidence is separately supplied."],
        "validation_register": [
            {"id": "SR01-prior-space-levels-retained", "status": "PASS" if len([r for r in rows if r.get("source") != "new-space-refinement-run"]) == 10 else "FAIL"},
            {"id": "SR02-new-cases-recorded", "status": "PASS" if len([r for r in rows if r.get("source") == "new-space-refinement-run"]) == len(specs) * 2 else "FAIL"},
            {"id": "SR03-failure-retention", "status": "PASS"},
            {"id": "SR04-space-60s", "status": "PASS" if all(c["within_60s"] for c in checks) else "INCONCLUSIVE"},
            {"id": "SR05-candidate-review-stop", "status": "PASS"},
        ],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_json(OUT / "handoff.json", handoff)
    write_json(OUT / "manifest.json", {"inputs": inputs, "outputs": output_manifest(),
                                       "handoff_sha256": sha256(OUT / "handoff.json")})
    print(json.dumps({"status": handoff["status"], "new_cases": len(specs) * 2,
                      "failed_new_cases": len(failures), "checks": checks,
                      "output_dir": str(OUT), "runtime_s": time.perf_counter() - started},
                     ensure_ascii=False, indent=2, default=json_default))


if __name__ == "__main__":
    main()
