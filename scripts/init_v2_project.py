#!/usr/bin/env python3
"""Initialize a non-destructive project workspace for the v2 skill suite."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


STAGE_DIRS = [
    "00-selection",
    "01-intake",
    "02-literature",
    "02-design",
    "03-prototype",
    "04-compute",
    "05-evidence",
    "06-figure",
    "07-paper",
    "08-audit",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_new_json(path: Path, value: object) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def decision_template(gate: str, question: str) -> dict:
    return {
        "schema_version": "1.0",
        "gate": gate,
        "status": "DRAFT",
        "question": question,
        "selected_options": [],
        "reasons": [],
        "accepted_assumptions": [],
        "rejected_options": [],
        "required_validations": [],
        "prohibited_changes": [],
        "delegations": [],
        "confirmed_by": [],
        "confirmed_at": None,
        "supersedes": None,
    }


def initialize(project_root: Path, contest: str, year: int, project_id: str | None = None) -> list[Path]:
    root = project_root.resolve()
    suite_root = Path(__file__).resolve().parent.parent
    if root == suite_root or suite_root in root.parents:
        raise ValueError("PROJECT_ROOT must be outside the skill-suite source tree")

    root.mkdir(parents=True, exist_ok=True)
    for directory in ["input", "literature/input", ".workflow", "decisions", *STAGE_DIRS]:
        (root / directory).mkdir(parents=True, exist_ok=True)

    timestamp = now_iso()
    pid = project_id or f"{contest.lower().replace(' ', '-')}-{year}"
    created: list[Path] = []

    documents = {
        root / ".workflow" / "config.json": {
            "schema_version": "1.0",
            "project_id": pid,
            "competition": contest,
            "year": year,
            "task_creation_authorized": False,
            "project_execution": "same-local-directory",
            "created_at": timestamp,
        },
        root / ".workflow" / "state.json": {
            "schema_version": "1.0",
            "project_id": pid,
            "status": "NEW",
            "current_stage": "NEW",
            "completed_stages": [],
            "active_thread_id": None,
            "next_stage": "SELECTION",
            "blocking_items": [],
            "updated_at": timestamp,
        },
        root / ".workflow" / "threads.json": {
            "schema_version": "1.0",
            "threads": {},
        },
        root / ".workflow" / "ai-usage-log.json": {
            "schema_version": "1.0",
            "competition": contest,
            "year": year,
            "rule_status": "UNVERIFIED",
            "official_sources": [],
            "entries": [],
        },
        root / ".workflow" / "workflow-log.json": {
            "schema_version": "1.0",
            "events": [{"event": "PROJECT_INITIALIZED", "at": timestamp}],
        },
        root / "decisions" / "H0-selection.json": decision_template(
            "H0", "确认候选题评分、关键风险和最终选题"
        ),
        root / "decisions" / "H1-problem.json": decision_template(
            "H1", "确认题意、目标、硬约束、错误代价和关键假设"
        ),
        root / "decisions" / "H2-model.json": decision_template(
            "H2", "确认主模型、基线、评价指标、权重和验证要求"
        ),
        root / "decisions" / "H3-claims.json": decision_template(
            "H3", "确认核心结论、正式图表、局限和论文叙事"
        ),
        root / "decisions" / "H4-submission.json": decision_template(
            "H4", "确认最终论文、AI使用声明、残余风险和提交批准"
        ),
        root / "decisions" / "C1-figure.json": decision_template(
            "C1", "仅在视觉表达可能改变解释时确认核心图表"
        ),
    }

    for path, value in documents.items():
        if write_new_json(path, value):
            created.append(path)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--contest", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--project-id")
    args = parser.parse_args()

    try:
        created = initialize(args.project_root, args.contest, args.year, args.project_id)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"Initialized: {args.project_root.resolve()}")
    print(f"Created JSON files: {len(created)}")
    if not created:
        print("Existing state was preserved; no JSON file was overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
