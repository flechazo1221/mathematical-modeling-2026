"""Finalize the recoverable evidence after a cost-bounded interruption."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
RUN_SCRIPT = OUT / "run_space_refinement.py"


def load_run_module():
    spec = importlib.util.spec_from_file_location("space_refinement_helpers", RUN_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(RUN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    module = load_run_module()
    rows = module.existing_space_rows()
    partial_new = []
    for implementation, directory in (
        ("prescribed-T-baseline", "model-baseline"),
        ("internal-temperature", "model-internal-temperature"),
    ):
        for question in ("Q3", "Q4"):
            for level in ("Z", "W", "V", "U"):
                path = OUT / directory / f"{question}-spatial-{level}" / "metrics.json"
                if path.is_file():
                    row = json.loads(path.read_text(encoding="utf-8"))
                    row["source"] = "partial-space-refinement-run"
                    rows.append(row)
                    partial_new.append({"implementation": implementation, "question": question, "level": level})

    ladder = module.ladder_rows(rows)
    checks = module.last_checks(ladder)
    module.write_csv(OUT / "space-convergence-partial.csv", ladder)
    module.write_csv(OUT / "raw-results-partial.csv", rows)
    module.write_json(OUT / "checks-partial.json", {"tolerance_s": module.REPORT_S, "checks": checks})

    planned = [
        {"question": q, "level": level, "mesh": mesh}
        for q in ("Q3", "Q4")
        for level, mesh in (("Z", 54), ("W", 72), ("V", 108), ("U", 144))
    ]
    completed = {(item["question"], item["level"], item["implementation"]) for item in partial_new}
    report = [
        "# 内部温度场补全：空间继续加密（部分完成）", "",
        "状态：**BLOCKED / PARTIAL；候选仍停留在 H2 复审。**", "",
        "本轮因 108×108 内部温度候选单个算例持续约 12 分钟且后续 144×144 代价更高，按成本边界中止。已完成的 Z/W 层和 Q3 基线 V 层均保留；未完成算例没有被当作 PASS。", "",
        "## 已完成的关键变化", "",
        "- Q3 基线：36→54 为 %.3f s，54→72 为 %.3f s，72→108 为 %.3f s。" % (
            next(r["adjacent_change_s"] for r in ladder if r["implementation"] == "prescribed-T-baseline" and r["question"] == "Q3" and r["level"] == "Z"),
            next(r["adjacent_change_s"] for r in ladder if r["implementation"] == "prescribed-T-baseline" and r["question"] == "Q3" and r["level"] == "W"),
            next(r["adjacent_change_s"] for r in ladder if r["implementation"] == "prescribed-T-baseline" and r["question"] == "Q3" and r["level"] == "V"),
        ),
        "- 108×108 基线相对 72×72 的变化仍超过 60 s，因此空间收敛尚未通过；不能用未完成的内部温度 V/U 层补齐。", "",
        "## 中止记录", "",
        "- 计划新算例：%d 个；已完成：%d 个；未完成：%d 个。" % (len(planned) * 2, len(partial_new), len(planned) * 2 - len(partial_new)),
        "- 中止位置：`internal-temperature / Q3 / spatial / V / 108×108`。", "- 原始过程日志：`run.log`；已完成算例目录含 `raw-result.json`、`metrics.json`、`trajectory.csv` 和 `state-arrays.npz`。", "",
        "## 结论", "",
        "- 时间梯子已在上一轮达到 60 s：Q3/Q4 两种实现最后相邻变化约 59.7/44.5 s。", "- 空间梯子仍为 `INCONCLUSIVE`，当前不能宣称整体 60 s 收敛。", "- 本轮不修改正式 COMPUTE、EVIDENCE、FIGURE、PAPER、decisions 或 workflow state。", "",
    ]
    (OUT / "partial-report.md").write_text("\n".join(report), encoding="utf-8")
    write_json(OUT / "partial-status.json", {
        "status": "BLOCKED", "reason": "cost-bounded interruption after partial spatial refinement",
        "planned_new_cases": len(planned) * 2, "completed_new_cases": len(partial_new),
        "completed_cases": partial_new,
        "interrupted_case": {"implementation": "internal-temperature", "question": "Q3", "level": "V", "mesh": "108x108"},
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    })
    inputs = []
    for path in (RUN_SCRIPT, OUT / "run.log", ROOT / "03-prototype" / "controller-temp-field-refinement-20260912" / "space-convergence.csv"):
        if path.is_file():
            inputs.append({"path": module.rel(path), "bytes": path.stat().st_size, "sha256": module.sha256(path)})
    outputs = module.output_manifest()
    handoff = {
        "schema_version": "1.0", "stage": "PROTOTYPE-CANDIDATE-SPACE-REFINEMENT",
        "status": "BLOCKED", "review_status": "PENDING_CANDIDATE_REVIEW",
        "scope": "partial Q3/Q4 spatial convergence extension; cost-bounded stop; no formal-stage writes",
        "inputs": inputs, "outputs": outputs,
        "assumptions": ["All completed Z/W/V results are real solver outputs and remain auditable.",
                        "Missing V/U cases are not inferred from a trend and are not counted as PASS."],
        "unknowns": ["Full spatial 60 s convergence for both implementations remains unresolved.",
                     "The candidate has no internal-temperature observations."],
        "claims": ["Time convergence passed the pre-registered 60 s adjacent-change check in the previous refinement package.",
                   "Spatial convergence remains INCONCLUSIVE after partial extension."],
        "warnings": ["Do not promote this candidate or overwrite formal-stage files.",
                     "Do not use extrapolated values for missing high-resolution cases."],
        "required_next_actions": ["Review partial-report.md, space-convergence-partial.csv, checks-partial.json, and raw-results-partial.csv.",
                                   "If strict spatial PASS is required, resume only with an explicitly accepted compute budget."],
        "validation_register": [
            {"id": "PS01-completed-results-retained", "status": "PASS" if len(partial_new) == 5 else "FAIL"},
            {"id": "PS02-no-inferred-cases", "status": "PASS"},
            {"id": "PS03-space-60s", "status": "INCONCLUSIVE"},
            {"id": "PS04-candidate-review-stop", "status": "PASS"},
        ],
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_json(OUT / "handoff.json", handoff)
    write_json(OUT / "manifest.json", {"inputs": inputs, "outputs": module.output_manifest(),
                                       "handoff_sha256": module.sha256(OUT / "handoff.json")})
    print(json.dumps({"status": "BLOCKED", "completed_new_cases": len(partial_new),
                      "planned_new_cases": len(planned) * 2,
                      "output_dir": str(OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
