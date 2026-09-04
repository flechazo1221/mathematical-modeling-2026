#!/usr/bin/env python3
"""Validate v2 project state, decisions, stage handoffs, and declared hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from selection_score import validate_scorecard


STAGE_DIRS = {
    "SELECTION": "00-selection",
    "INTAKE": "01-intake",
    "LITERATURE": "02-literature",
    "DESIGN": "02-design",
    "PROTOTYPE": "03-prototype",
    "COMPUTE": "04-compute",
    "EVIDENCE": "05-evidence",
    "FIGURE": "06-figure",
    "PAPER": "07-paper",
    "AUDIT": "08-audit",
}

REQUIRED_GATES = {
    "INTAKE": ("H0-selection.json", {"TEAM_APPROVED"}),
    "LITERATURE": ("H1-problem.json", {"TEAM_APPROVED"}),
    "DESIGN": ("H1-problem.json", {"TEAM_APPROVED"}),
    "PROTOTYPE": ("H1-problem.json", {"TEAM_APPROVED"}),
    "COMPUTE": ("H2-model.json", {"TEAM_APPROVED"}),
    "EVIDENCE": ("H2-model.json", {"TEAM_APPROVED"}),
    "FIGURE": ("H3-claims.json", {"TEAM_APPROVED"}),
    "PAPER": ("H3-claims.json", {"TEAM_APPROVED"}),
    "AUDIT": ("H3-claims.json", {"TEAM_APPROVED"}),
}

STAGE_PREREQUISITES = {
    "DESIGN": ("LITERATURE",),
    "PAPER": ("DESIGN", "COMPUTE", "EVIDENCE", "FIGURE"),
}


def load_json(path: Path, errors: list[str]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path}")
        return None
    return value


def resolve_project_path(root: Path, relative: str, errors: list[str]) -> Path | None:
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        errors.append(f"path escapes PROJECT_ROOT: {relative}")
        return None
    return candidate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_decision(path: Path, allowed: set[str], errors: list[str]) -> None:
    decision = load_json(path, errors)
    if decision is None:
        return
    if decision.get("status") not in allowed:
        errors.append(f"decision not approved: {path}")
    if not decision.get("confirmed_by"):
        errors.append(f"approved decision has no team member: {path}")
    if not decision.get("confirmed_at"):
        errors.append(f"approved decision has no timestamp: {path}")
    if not decision.get("selected_options"):
        errors.append(f"approved decision has no selected option: {path}")
    if not decision.get("reasons"):
        errors.append(f"approved decision has no team reason: {path}")


def validate_selection_decision(root: Path, errors: list[str]) -> None:
    decision_path = root / "decisions" / "H0-selection.json"
    scorecard_path = root / "00-selection" / "选题评分.json"
    decision = load_json(decision_path, errors)
    scorecard = load_json(scorecard_path, errors)
    if decision is None or scorecard is None:
        return
    selected = decision.get("selected_options")
    if not isinstance(selected, list) or len(selected) != 1:
        errors.append(f"H0 must select exactly one candidate id: {decision_path}")
        return
    if not decision.get("reasons"):
        errors.append(f"H0 approval has no team reason: {decision_path}")
    candidate_ids = {
        item.get("id") for item in scorecard.get("candidates", []) if isinstance(item, dict)
    }
    if selected[0] not in candidate_ids:
        errors.append(f"H0 selected unknown candidate {selected[0]}: {decision_path}")


def validate_handoff(root: Path, stage: str, errors: list[str]) -> None:
    handoff_path = root / STAGE_DIRS[stage] / "handoff.json"
    handoff = load_json(handoff_path, errors)
    if handoff is None:
        return
    if handoff.get("schema_version") != "1.0":
        errors.append(f"unsupported handoff schema: {handoff_path}")
    if handoff.get("stage") != stage:
        errors.append(f"handoff stage mismatch: {handoff_path}")
    if handoff.get("status") != "PASS":
        errors.append(f"completed stage is not PASS: {handoff_path}")
    if not handoff.get("completed_at"):
        errors.append(f"PASS handoff has no completion timestamp: {handoff_path}")
    if not handoff.get("outputs"):
        errors.append(f"PASS handoff has no declared outputs: {handoff_path}")

    for group in ("inputs", "outputs", "frozen_decisions"):
        records = handoff.get(group, [])
        if not isinstance(records, list):
            errors.append(f"{group} must be a list: {handoff_path}")
            continue
        seen_paths: set[str] = set()
        for record in records:
            if not isinstance(record, dict) or "path" not in record or "sha256" not in record:
                errors.append(f"invalid file record in {handoff_path}: {record!r}")
                continue
            declared_path = str(record["path"])
            normalized = declared_path.replace("\\", "/").casefold()
            if normalized in seen_paths:
                errors.append(f"duplicate {group} path in {handoff_path}: {declared_path}")
                continue
            seen_paths.add(normalized)
            path = resolve_project_path(root, declared_path, errors)
            if path is None:
                continue
            if not path.is_file():
                errors.append(f"declared file missing: {path}")
                continue
            actual = sha256(path)
            if actual.lower() != str(record["sha256"]).lower():
                errors.append(f"hash mismatch: {path}")


def validate_workspace(project_root: Path, require_complete: bool = False) -> list[str]:
    root = project_root.resolve()
    errors: list[str] = []
    required_dirs = ["input", "literature/input", ".workflow", "decisions", *STAGE_DIRS.values()]
    for directory in required_dirs:
        if not (root / directory).is_dir():
            errors.append(f"missing directory: {root / directory}")

    state = load_json(root / ".workflow" / "state.json", errors)
    load_json(root / ".workflow" / "threads.json", errors)
    ai_usage = load_json(root / ".workflow" / "ai-usage-log.json", errors)
    if state is None:
        return errors

    completed = state.get("completed_stages", [])
    if not isinstance(completed, list):
        errors.append("completed_stages must be a list")
        completed = []
    for stage in completed:
        if stage not in STAGE_DIRS:
            errors.append(f"unknown completed stage: {stage}")
            continue
        gate = REQUIRED_GATES.get(stage)
        if gate:
            validate_decision(root / "decisions" / gate[0], gate[1], errors)
            if stage == "INTAKE":
                validate_selection_decision(root, errors)
        for prerequisite in STAGE_PREREQUISITES.get(stage, ()):
            if prerequisite not in completed:
                errors.append(f"{stage} completed before required stage: {prerequisite}")
        validate_handoff(root, stage, errors)
        if stage == "SELECTION":
            errors.extend(validate_scorecard(root / "00-selection" / "选题评分.json"))
        if ai_usage is not None and not any(
            isinstance(item, dict) and item.get("stage") == stage
            for item in ai_usage.get("entries", [])
        ):
            errors.append(f"completed stage has no AI usage record: {stage}")

    if require_complete:
        if state.get("status") != "COMPLETE":
            errors.append("workflow state is not COMPLETE")
        missing = [stage for stage in STAGE_DIRS if stage not in completed]
        if missing:
            errors.append(f"incomplete stages: {', '.join(missing)}")
        validate_decision(
            root / "decisions" / "H4-submission.json",
            {"TEAM_APPROVED_FOR_SUBMISSION"},
            errors,
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    errors = validate_workspace(args.project_root, args.require_complete)
    if errors:
        print("Workspace validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Workspace validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
