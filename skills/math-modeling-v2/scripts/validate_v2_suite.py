#!/usr/bin/env python3
"""Validate the source structure of the v2 mathematical-modeling skill suite."""

from __future__ import annotations

import json
import re
from pathlib import Path


EXPECTED_SKILLS = [
    "math-modeling-workflow",
    "math-modeling-team-decision",
    "math-modeling-selection",
    "math-modeling-intake",
    "math-modeling-literature",
    "math-modeling-literature-reading",
    "math-modeling-design",
    "math-modeling-prototype",
    "math-modeling-compute",
    "math-modeling-evidence",
    "math-modeling-figure",
    "math-modeling-appendix",
    "math-modeling-paper",
    "math-modeling-audit",
]


def validate_suite(root: Path) -> list[str]:
    errors: list[str] = []

    for path in root.rglob("*.md"):
        if re.search(r"(?<![\w-])py\s+-3(?:\s|$)", path.read_text(encoding="utf-8", errors="replace")):
            errors.append(f"deprecated Windows py launcher command: {path.relative_to(root)}")

    initializer_text = (root / "scripts" / "init_v2_project.py").read_text(encoding="utf-8")
    for marker in ("def diagnose_python", "sys.executable", "MIN_PYTHON"):
        if marker not in initializer_text:
            errors.append(f"initializer lacks Python interpreter diagnostic: {marker}")
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
        "selection-score.schema.json",
    ]
    for name in expected_schemas:
        path = schemas / name
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            errors.append(f"missing schema: {path}")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON schema {path}: {exc}")

    for script_name in ("init_v2_project.py", "workflow_control.py", "install_v2_suite.py", "selection_score.py"):
        if not (root / "scripts" / script_name).is_file():
            errors.append(f"missing workflow script: {script_name}")

    figure_text = (root / "skills" / "math-modeling-figure" / "SKILL.md").read_text(encoding="utf-8")
    if "no fixed minimum count" not in figure_text.lower():
        errors.append("figure skill must reject fixed figure and chart-type quotas")
    figure_instruction_roots = (
        root / "tools" / "figure",
        root / "references" / "roles" / "编程手",
    )
    for instruction_root in figure_instruction_roots:
        for path in instruction_root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for forbidden in ("每类至少 3 张", "合计至少 9 张", "图型种类 ≥ 3"):
                if forbidden in text:
                    errors.append(
                        f"figure instructions contain a fixed quota: "
                        f"{path.relative_to(root)}: {forbidden}"
                    )

    for legacy_role in ("建模手", "编程手", "论文手"):
        legacy_root = root / "references" / "roles" / legacy_role
        if (legacy_root / "SKILL.md").exists():
            errors.append(f"legacy role remains discoverable as a skill: {legacy_root / 'SKILL.md'}")
        if not (legacy_root / "ROLE.md").is_file():
            errors.append(f"missing legacy role guide: {legacy_root / 'ROLE.md'}")

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

    # Markdown navigation is part of the skill interface. Broken links make
    # progressively disclosed instructions unreachable and waste context.
    markdown_link = re.compile(r"(?<!!)\[[^\]]*\]\(([^)#]+)")
    for base in (root / "skills", root / "shared", root / "references", root / "tools"):
        for path in base.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in markdown_link.finditer(text):
                target_text = match.group(1).strip().strip("<>")
                if "://" in target_text or target_text.startswith("#"):
                    continue
                target = (path.parent / target_text).resolve()
                if not target.exists():
                    line = text.count("\n", 0, match.start()) + 1
                    errors.append(
                        f"broken Markdown link: {path.relative_to(root)}:{line} -> {target_text}"
                    )

    paper_skill = (root / "skills" / "math-modeling-paper" / "SKILL.md").read_text(encoding="utf-8")
    paper_contract_markers = (
        "## Hard writing gate",
        "DESIGN, COMPUTE, EVIDENCE, FIGURE, and APPENDIX",
        "actual recorded runs",
        "Automatically inventory",
        "strengths, weaknesses, sensitivity or robustness, applicability, and failure boundaries",
        "formulas, notation, units, code implementation",
        "Only after the evidence and consistency checks pass",
    )
    for marker in paper_contract_markers:
        if marker not in paper_skill:
            errors.append(f"paper skill missing result-first writing contract: {marker}")

    workflow_skill = (root / "skills" / "math-modeling-workflow" / "SKILL.md").read_text(encoding="utf-8")
    for marker in ("WAITING_FOR_LITERATURE", "$math-modeling-literature-reading", "02-literature/", "$math-modeling-appendix", "07-appendix/"):
        if marker not in workflow_skill:
            errors.append(f"workflow skill missing literature checkpoint contract: {marker}")
    design_skill = (root / "skills" / "math-modeling-design" / "SKILL.md").read_text(encoding="utf-8")
    for marker in ("02-literature/handoff.json", "02-literature/文献阅读结果.md", "文献到模型映射.md"):
        if marker not in design_skill:
            errors.append(f"design skill missing literature input contract: {marker}")
    literature_reading = root / "skills" / "math-modeling-literature-reading"
    reading_text = (literature_reading / "SKILL.md").read_text(encoding="utf-8")
    for marker in ("prepare_literature_corpus.py", "query_literature_corpus.py", "--max-chars 18000", "caj-processing.md"):
        if marker not in reading_text:
            errors.append(f"literature-reading skill missing CAJ/token contract: {marker}")
    for relative in (
        "scripts/prepare_literature_corpus.py",
        "scripts/query_literature_corpus.py",
        "references/caj-processing.md",
    ):
        if not (literature_reading / relative).is_file():
            errors.append(f"missing literature-reading resource: {literature_reading / relative}")
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
