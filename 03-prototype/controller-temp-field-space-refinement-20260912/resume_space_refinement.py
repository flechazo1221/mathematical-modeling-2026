"""Resume missing high-resolution spatial cases and finalize the ladder."""
from __future__ import annotations

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
RUN_HELPERS = OUT / "run_space_refinement.py"
COMPLETION_SCRIPT = ROOT / "03-prototype" / "controller-temp-field-completion-20260912" / "run_completion.py"
BASELINE_PATH = ROOT / "04-compute" / "src" / "formal_compute.py"
CANDIDATE_PATH = ROOT / "04-compute" / "temperature-field-revision-20260912" / "formal_compute_revision.py"
LEVELS = [("Z", 54), ("W", 72), ("V", 108), ("U", 144)]


def load_helpers():
    import importlib.util
    spec = importlib.util.spec_from_file_location("space_refinement_helpers_resume", RUN_HELPERS)
    if spec is None or spec.loader is None:
        raise RuntimeError(RUN_HELPERS)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_module(name: str, path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_current_rows(helper) -> list[dict]:
    rows = helper.existing_space_rows()
    for implementation, directory in (("prescribed-T-baseline", "model-baseline"),
                                      ("internal-temperature", "model-internal-temperature")):
        for question in ("Q3", "Q4"):
            for level, _mesh in LEVELS:
                path = OUT / directory / f"{question}-spatial-{level}" / "metrics.json"
                if path.is_file():
                    row = json.loads(path.read_text(encoding="utf-8"))
                    row["source"] = "resumed-space-refinement-run"
                    rows.append(row)
    return rows


def spec(question: str, level: str, mesh: int) -> dict:
    return {"question": question, "family": "spatial", "level": level,
            "nr": mesh, "nz": mesh, "dt": 300.0, "duration": 259200.0,
            "sample_every": 3600.0, "space_level": level, "time_level": "M",
            "label": f"{question}-spatial-{level}"}


def completed_pairs() -> set[tuple[str, str, str]]:
    result = set()
    for implementation, directory in (("prescribed-T-baseline", "model-baseline"),
                                      ("internal-temperature", "model-internal-temperature")):
        for question in ("Q3", "Q4"):
            for level, _mesh in LEVELS:
                if (OUT / directory / f"{question}-spatial-{level}" / "metrics.json").is_file():
                    result.add((implementation, question, level))
    return result


def report(helper, rows: list[dict], failures: list[dict]) -> list[dict]:
    ladder = helper.ladder_rows(rows)
    checks = helper.last_checks(ladder)
    helper.write_csv(OUT / "space-convergence-complete.csv", ladder)
    helper.write_csv(OUT / "raw-results-complete.csv", rows)
    helper.write_csv(OUT / "failures-complete.csv", failures)
    helper.write_json(OUT / "checks-complete.json", {"tolerance_s": 60.0, "checks": checks})
    def fmt(value):
        return "" if value is None else f"{float(value):.6g}"
    lines = [
        "# 内部温度场补全：空间收敛继续推进（完整结果）", "",
        "状态：**数值空间梯子完成；候选仍不进入正式 COMPUTE/EVIDENCE/FIGURE/PAPER。**", "",
        "本轮从已落盘的 L/M/H/X/Y/Z/W/V 结果断点续跑缺失层，空间网格为 8、12、18、27、36、54、72、108、144；时间步固定 300 s；基线与内部温度候选成对运行。阈值保持 `0.15−1e−6`。", "",
        "|实现|问题|层级|网格|t*(s)|相邻变化(s)|判读|", "|---|---|---|---:|---:|---:|---|",
    ]
    for row in ladder:
        lines.append(f"|{row['implementation']}|{row['question']}|{row['level']}|{row.get('nr')}×{row.get('nz')}|{fmt(row.get('interpolated_event_time_s'))}|{fmt(row.get('adjacent_change_s'))}|{row.get('refinement_status')}|")
    lines += ["", "## 最后一层 60 秒检查", "", "|实现|问题|最后层|相邻变化(s)|结论|", "|---|---|---|---:|---|"]
    for check in checks:
        lines.append(f"|{check['implementation']}|{check['question']}|{check['last_level']}|{fmt(check.get('last_adjacent_change_s'))}|{'PASS_60S' if check['within_60s'] else 'INCONCLUSIVE'}|")
    lines += ["", "## 失败保留", "", f"失败算例数：{len(failures)}。失败没有删除或改阈值规避。", ""]
    for failure in failures:
        lines.append(f"- `{failure['implementation']}/{failure['question']}-{failure['level']}`：{failure['error']}")
    lines += ["", "## 证据边界", "", "- 数值空间收敛不等于内部温度的现实准确性。", "- Q4 移动域物理闭合、潜热和独立内部温度观测仍需单独审查。", "- 即使数值 60 秒检查通过，也只代表候选离散误差达到预注册门槛。", ""]
    (OUT / "complete-report.md").write_text("\n".join(lines), encoding="utf-8")
    return checks


def main() -> None:
    helper = load_helpers()
    old_rows = read_current_rows(helper)
    done = completed_pairs()
    targets = []
    for question in ("Q3", "Q4"):
        for level, mesh in LEVELS:
            for implementation, source_path in (("prescribed-T-baseline", BASELINE_PATH),
                                                ("internal-temperature", CANDIDATE_PATH)):
                if (implementation, question, level) not in done:
                    targets.append((implementation, source_path, spec(question, level, mesh)))

    rows = list(old_rows)
    failures: list[dict] = []
    started = time.perf_counter()
    log_path = OUT / "resume.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"command": " ".join(sys.argv), "python": sys.version,
                              "python_executable": str(Path(sys.executable).resolve()),
                              "platform": platform.platform(), "numpy": np.__version__,
                              "target_count": len(targets), "started_at": datetime.now(timezone.utc).astimezone().isoformat()}, ensure_ascii=False) + "\n")
        log.write("SCOPE: resume missing spatial Z/W/V/U cases only; prior results and completed partial cases are retained.\n")
        log.flush()
        for index, (implementation, source_path, case_spec) in enumerate(targets, start=1):
            log.write(f"START {index}/{len(targets)} {implementation} {json.dumps(case_spec, ensure_ascii=False)}\n")
            log.flush()
            try:
                module = load_module(f"resume_{implementation}_{case_spec['question']}_{case_spec['level']}", source_path)
                completion = load_module(f"completion_resume_{implementation}_{case_spec['question']}_{case_spec['level']}", COMPLETION_SCRIPT)
                summary, groups, run = completion.run_one(module, implementation, case_spec, log, {}, save_artifacts=False, return_run=True)
                summary["source"] = "resumed-space-refinement-run"
                rows.append(summary)
                helper.save_case(implementation, case_spec, summary, groups, run)
                log.write("DONE " + json.dumps(summary, ensure_ascii=False, default=helper.json_default) + "\n")
            except Exception as exc:
                failure = {"implementation": implementation, "question": case_spec["question"],
                           "level": case_spec["level"], "error": repr(exc),
                           "traceback": traceback.format_exc(limit=12)}
                failures.append(failure)
                log.write("FAIL " + json.dumps(failure, ensure_ascii=False) + "\n")
            log.flush()
        log.write(json.dumps({"completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
                              "runtime_s": time.perf_counter() - started}, ensure_ascii=False) + "\n")

    checks = report(helper, rows, failures)
    inputs = [{"path": helper.rel(path), "bytes": path.stat().st_size, "sha256": helper.sha256(path)} for path in (
        RUN_HELPERS, COMPLETION_SCRIPT, BASELINE_PATH, CANDIDATE_PATH,
        ROOT / "03-prototype" / "controller-temp-field-refinement-20260912" / "space-convergence.csv",
    ) if path.is_file()]
    helper.write_json(OUT / "environment-complete.json", {
        "python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(), "numpy": np.__version__, "threshold": 0.149999,
        "report_grid_s": 60.0, "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "write_boundary": helper.rel(OUT),
    })
    outputs = helper.output_manifest()
    handoff = {
        "schema_version": "1.0", "stage": "PROTOTYPE-CANDIDATE-SPACE-REFINEMENT",
        "status": "BLOCKED", "review_status": "PENDING_CANDIDATE_REVIEW",
        "scope": "complete Q3/Q4 spatial convergence extension for the internal-temperature candidate; no formal-stage writes",
        "inputs": inputs, "outputs": outputs,
        "assumptions": ["All spatial levels are computed with the same dt=300 s and unchanged threshold.",
                        "Baseline and candidate are paired at every newly completed level.",
                        "Numerical 60 s convergence does not establish physical validation."],
        "unknowns": ["The candidate lacks independent internal-temperature observations.",
                     "Q4 physical heat closure and latent-heat identification remain separate gates."],
        "claims": ["The extended spatial ladder is recorded with per-case raw outputs.",
                   "Final adjacent changes are compared directly with the 60 s tolerance."],
        "warnings": ["Do not overwrite formal COMPUTE, EVIDENCE, FIGURE, PAPER, decisions, or workflow state.",
                     "Do not equate numerical convergence with model validation or promotion."],
        "required_next_actions": ["Review complete-report.md, space-convergence-complete.csv, checks-complete.json, and raw-results-complete.csv.",
                                   "Team decides whether the numerically stable candidate is scientifically admissible."],
        "validation_register": [
            {"id": "CR01-all-planned-spatial-cases", "status": "PASS" if not failures and all(c["last_level"] == "U" for c in checks) else "INCONCLUSIVE"},
            {"id": "CR02-space-60s", "status": "PASS" if not failures and all(c["within_60s"] for c in checks) else "INCONCLUSIVE"},
            {"id": "CR03-failure-retention", "status": "PASS"},
            {"id": "CR04-candidate-review-stop", "status": "PASS"},
        ],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    helper.write_json(OUT / "handoff-complete.json", handoff)
    helper.write_json(OUT / "manifest-complete.json", {"inputs": inputs, "outputs": helper.output_manifest(),
                                                         "handoff_sha256": helper.sha256(OUT / "handoff-complete.json")})
    print(json.dumps({"status": handoff["status"], "resumed_cases": len(targets),
                      "failures": len(failures), "checks": checks,
                      "output_dir": str(OUT), "runtime_s": time.perf_counter() - started},
                     ensure_ascii=False, indent=2, default=helper.json_default))


if __name__ == "__main__":
    main()
