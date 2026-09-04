#!/usr/bin/env python3
"""Validate the source structure of the v2 mathematical-modeling skill suite."""

from __future__ import annotations

import json
import re
from pathlib import Path


EXPECTED_SKILLS = [
    "math-modeling-workflow",
    "math-modeling-team-decision",
    "math-modeling-intake",
    "math-modeling-design",
    "math-modeling-prototype",
    "math-modeling-compute",
    "math-modeling-evidence",
    "math-modeling-figure",
    "math-modeling-paper",
    "math-modeling-audit",
]


def validate_suite(root: Path) -> list[str]:
    errors: list[str] = []
    for name in EXPECTED_SKILLS:
        skill_file = root / "skills" / name / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"missing skill: {skill_file}")
            continue
        text = skill_file.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not match:
            errors.append(f"invalid frontmatter: {skill_file}")
            continue
        declared = re.search(r"^name:\s*([^\n]+)$", match.group(1), re.MULTILINE)
        description = re.search(r"^description:\s*(.+)$", match.group(1), re.MULTILINE)
        if not declared or declared.group(1).strip() != name:
            errors.append(f"name mismatch: {skill_file}")
        if not description or not description.group(1).strip():
            errors.append(f"missing description: {skill_file}")
        openai_yaml = root / "skills" / name / "agents" / "openai.yaml"
        if not openai_yaml.is_file():
            errors.append(f"missing UI metadata: {openai_yaml}")
        else:
            ui_text = openai_yaml.read_text(encoding="utf-8")
            if f"${name}" not in ui_text:
                errors.append(f"default prompt does not name ${name}: {openai_yaml}")

    schemas = root / "shared" / "schemas"
    expected_schemas = [
        "workflow-state.schema.json",
        "handoff.schema.json",
        "decision.schema.json",
        "figure-contract.schema.json",
        "ai-usage.schema.json",
    ]
    for name in expected_schemas:
        path = schemas / name
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            errors.append(f"missing schema: {path}")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON schema {path}: {exc}")

    for script_name in ("init_v2_project.py", "workflow_control.py", "install_v2_suite.py"):
        if not (root / "scripts" / script_name).is_file():
            errors.append(f"missing workflow script: {script_name}")

    figure_text = (root / "skills" / "math-modeling-figure" / "SKILL.md").read_text(encoding="utf-8")
    if "no fixed minimum count" not in figure_text.lower():
        errors.append("figure skill must reject fixed figure and chart-type quotas")
    legacy_figure_text = (root / "tools" / "figure" / "SKILL.md").read_text(encoding="utf-8")
    for forbidden in ("每类至少 3 张", "合计至少 9 张", "图型种类 ≥ 3"):
        if forbidden in legacy_figure_text:
            errors.append(f"legacy figure instructions still contain a fixed quota: {forbidden}")

    paper_library = root / "skills" / "math-modeling-paper" / "references" / "paper-template-2026"
    for relative in (
        "INTEGRATION.md",
        "SOURCE.md",
        "LICENSE",
        "00_LaTeX基础模板与排版/数学建模论文通用LaTeX模板.tex",
        "01_通用写作规范/提交前检查清单.md",
        "02_优化类/摘要范例.md",
        "03_预测类/摘要范例.md",
        "04_评价类/摘要范例.md",
        "05_分类类/摘要范例.md",
        "06_统计分析类/摘要范例.md",
        "07_机理建模类/摘要范例.md",
    ):
        if not (paper_library / relative).is_file():
            errors.append(f"missing paper-stage resource: {paper_library / relative}")
    if (paper_library / "INTEGRATION.md").is_file():
        integration = (paper_library / "INTEGRATION.md").read_text(encoding="utf-8")
        for required in ("权威顺序", "渐进式加载", "示例数据", "62f2c84dba41a491cb31ea915dc2db2957bd0f5b"):
            if required not in integration:
                errors.append(f"paper integration contract missing: {required}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    errors = validate_suite(root)
    if errors:
        print("V2 suite validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("V2 suite validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
