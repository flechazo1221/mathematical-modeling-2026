#!/usr/bin/env python3
"""Apply deterministic state transitions for a v2 modeling project."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
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
AFTER_STAGE = {
    "SELECTION": ("H0", "WAITING_FOR_TEAM"),
    "INTAKE": ("H1", "WAITING_FOR_TEAM"),
    "LITERATURE": ("DESIGN", "RUNNING"),
    "DESIGN": ("PROTOTYPE", "RUNNING"),
    "PROTOTYPE": ("H2", "WAITING_FOR_TEAM"),
    "COMPUTE": ("EVIDENCE", "RUNNING"),
    "EVIDENCE": ("H3", "WAITING_FOR_TEAM"),
    "FIGURE": ("PAPER", "RUNNING"),
    "PAPER": ("AUDIT", "RUNNING"),
    "AUDIT": ("H4", "WAITING_FOR_TEAM"),
}
AFTER_GATE = {"H0": "INTAKE", "H1": "LITERATURE", "H2": "COMPUTE", "H3": "FIGURE"}
GATE_FILES = {
    "H0": "H0-selection.json",
    "H1": "H1-problem.json",
    "H2": "H2-model.json",
    "H3": "H3-claims.json",
    "H4": "H4-submission.json",
}
SUPPORTED_LITERATURE_SUFFIXES = {".caj", ".pdf", ".docx", ".txt", ".md", ".html", ".htm"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_files(root: Path) -> tuple[Path, Path, Path, Path, Path]:
    workflow = root.resolve() / ".workflow"
    return (
        workflow / "config.json",
        workflow / "state.json",
        workflow / "threads.json",
        workflow / "workflow-log.json",
        workflow / "ai-usage-log.json",
    )


def append_event(log_path: Path, event: str, **details: object) -> None:
    log = load_json(log_path)
    log.setdefault("events", []).append({"event": event, "at": now_iso(), **details})
    save_json(log_path, log)


def authorize(root: Path, value: bool) -> None:
    config_path, _, _, log_path, _ = project_files(root)
    config = load_json(config_path)
    config["task_creation_authorized"] = value
    save_json(config_path, config)
    append_event(log_path, "TASK_CREATION_AUTHORIZATION_CHANGED", authorized=value)


def start_stage(root: Path, stage: str, thread_id: str, host_id: str | None) -> None:
    config_path, state_path, threads_path, log_path, _ = project_files(root)
    config = load_json(config_path)
    state = load_json(state_path)
    if not config.get("task_creation_authorized"):
        raise ValueError("independent task creation is not authorized")
    if state.get("next_stage") != stage:
        raise ValueError(f"expected next stage {state.get('next_stage')}, not {stage}")
    if state.get("active_thread_id"):
        raise ValueError(f"another task is active: {state['active_thread_id']}")
    if stage == "DESIGN":
        if "LITERATURE" not in state.get("completed_stages", []):
            raise ValueError("DESIGN requires a completed LITERATURE stage")
        validate_handoff(root, "LITERATURE")
    if stage == "LITERATURE":
        input_dir = root.resolve() / "literature" / "input"
        supplied = [
            path for path in input_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_LITERATURE_SUFFIXES
        ] if input_dir.is_dir() else []
        if not supplied:
            raise ValueError(
                "LITERATURE requires at least one supported user file under literature/input"
            )

    threads = load_json(threads_path)
    record = {"thread_id": thread_id, "started_at": now_iso(), "status": "RUNNING"}
    if host_id:
        record["host_id"] = host_id
    threads.setdefault("threads", {}).setdefault(stage, []).append(record)
    save_json(threads_path, threads)

    state.update(
        status="RUNNING",
        current_stage=stage,
        active_thread_id=thread_id,
        blocking_items=[],
        updated_at=now_iso(),
    )
    save_json(state_path, state)
    append_event(log_path, "STAGE_STARTED", stage=stage, thread_id=thread_id)


def validate_handoff(root: Path, stage: str) -> dict:
    handoff_path = root.resolve() / STAGE_DIRS[stage] / "handoff.json"
    handoff = load_json(handoff_path)
    if handoff.get("stage") != stage:
        raise ValueError(f"handoff stage mismatch: {handoff.get('stage')} != {stage}")
    if handoff.get("status") != "PASS":
        raise ValueError(f"handoff is not PASS: {handoff.get('status')}")
    if not handoff.get("completed_at"):
        raise ValueError("PASS handoff has no completion timestamp")
    if not handoff.get("outputs"):
        raise ValueError("PASS handoff has no declared outputs")
    for section in ("inputs", "outputs", "frozen_decisions"):
        seen_paths: set[str] = set()
        for item in handoff.get(section, []):
            candidate = Path(item["path"])
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError(f"handoff path must be PROJECT_ROOT-relative: {candidate}")
            normalized = candidate.as_posix().casefold()
            if normalized in seen_paths:
                raise ValueError(f"duplicate {section} path: {candidate}")
            seen_paths.add(normalized)
            path = (root.resolve() / candidate).resolve()
            if path != root.resolve() and root.resolve() not in path.parents:
                raise ValueError(f"handoff path escapes PROJECT_ROOT: {candidate}")
            if not path.is_file():
                raise ValueError(f"handoff file missing: {path}")
            actual = sha256(path)
            if actual.lower() != item["sha256"].lower():
                raise ValueError(f"handoff hash mismatch: {path}")
    return handoff


def finish_stage(root: Path, stage: str) -> None:
    _, state_path, threads_path, log_path, ai_log_path = project_files(root)
    state = load_json(state_path)
    if state.get("current_stage") != stage or not state.get("active_thread_id"):
        raise ValueError(f"stage {stage} is not the active task")
    validate_handoff(root, stage)
    if stage == "SELECTION":
        score_errors = validate_scorecard(root.resolve() / "00-selection" / "选题评分.json")
        if score_errors:
            raise ValueError("invalid selection scorecard: " + "; ".join(score_errors))
    ai_log = load_json(ai_log_path)
    if not any(item.get("stage") == stage for item in ai_log.get("entries", [])):
        raise ValueError(f"AI usage has not been recorded for {stage}")

    active_id = state["active_thread_id"]
    threads = load_json(threads_path)
    records = threads.get("threads", {}).get(stage, [])
    match = next((item for item in reversed(records) if item.get("thread_id") == active_id), None)
    if not match:
        raise ValueError(f"active task is not recorded for {stage}: {active_id}")
    match.update(status="PASS", finished_at=now_iso())
    save_json(threads_path, threads)

    completed = state.setdefault("completed_stages", [])
    if stage not in completed:
        completed.append(stage)
    next_stage, status = AFTER_STAGE[stage]
    state.update(
        status=status,
        current_stage=next_stage,
        active_thread_id=None,
        next_stage=next_stage,
        blocking_items=[],
        updated_at=now_iso(),
    )
    save_json(state_path, state)
    append_event(log_path, "STAGE_COMPLETED", stage=stage, next_stage=next_stage)


def advance_gate(root: Path, gate: str) -> None:
    _, state_path, _, log_path, _ = project_files(root)
    state = load_json(state_path)
    if state.get("current_stage") != gate or state.get("status") != "WAITING_FOR_TEAM":
        raise ValueError(f"workflow is not waiting at {gate}")
    decision_path = root.resolve() / "decisions" / GATE_FILES[gate]
    decision = load_json(decision_path)
    expected = "TEAM_APPROVED_FOR_SUBMISSION" if gate == "H4" else "TEAM_APPROVED"
    if decision.get("status") != expected:
        raise ValueError(f"{gate} requires {expected}")
    if not decision.get("confirmed_by") or not decision.get("confirmed_at"):
        raise ValueError(f"{gate} approval lacks named reviewers or timestamp")
    if not decision.get("selected_options"):
        raise ValueError(f"{gate} approval lacks a selected option")
    if not decision.get("reasons"):
        raise ValueError(f"{gate} approval lacks a team reason")
    if gate == "H0":
        selected = decision.get("selected_options")
        if not isinstance(selected, list) or len(selected) != 1:
            raise ValueError("H0 requires exactly one selected candidate id")
        if not decision.get("reasons"):
            raise ValueError("H0 requires at least one team reason")
        scorecard = load_json(root.resolve() / "00-selection" / "选题评分.json")
        candidate_ids = {
            item.get("id") for item in scorecard.get("candidates", []) if isinstance(item, dict)
        }
        if selected[0] not in candidate_ids:
            raise ValueError(f"H0 selected unknown candidate: {selected[0]}")

    if gate == "H4":
        state.update(
            status="COMPLETE",
            current_stage="COMPLETE",
            active_thread_id=None,
            next_stage=None,
            blocking_items=[],
            updated_at=now_iso(),
        )
        next_stage = None
    elif gate == "H1":
        next_stage = AFTER_GATE[gate]
        state.update(
            status="WAITING_FOR_LITERATURE",
            current_stage=next_stage,
            active_thread_id=None,
            next_stage=next_stage,
            blocking_items=[
                "等待用户将相关领域文献放入 literature/input/，然后启动 LITERATURE 阶段"
            ],
            updated_at=now_iso(),
        )
    else:
        next_stage = AFTER_GATE[gate]
        state.update(
            status="RUNNING",
            current_stage=gate,
            active_thread_id=None,
            next_stage=next_stage,
            blocking_items=[],
            updated_at=now_iso(),
        )
    save_json(state_path, state)
    append_event(log_path, "GATE_APPROVED", gate=gate, next_stage=next_stage)


def record_ai_use(
    root: Path,
    stage: str,
    tool_or_model: str,
    purpose: str,
    affected_files: list[str],
    human_review: str,
) -> None:
    _, _, _, workflow_log_path, ai_log_path = project_files(root)
    normalized: list[str] = []
    project_root = root.resolve()
    for raw in affected_files:
        candidate = Path(raw)
        path = candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
        if path != project_root and project_root not in path.parents:
            raise ValueError(f"affected file escapes PROJECT_ROOT: {raw}")
        if not path.exists():
            raise ValueError(f"affected file does not exist: {path}")
        normalized.append(path.relative_to(project_root).as_posix())

    log = load_json(ai_log_path)
    log.setdefault("entries", []).append(
        {
            "stage": stage,
            "tool_or_model": tool_or_model,
            "purpose": purpose,
            "affected_files": normalized,
            "human_review": human_review,
            "recorded_at": now_iso(),
        }
    )
    save_json(ai_log_path, log)
    append_event(workflow_log_path, "AI_USAGE_RECORDED", stage=stage, affected_files=normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)

    auth = commands.add_parser("authorize-tasks")
    auth.add_argument("--value", required=True, choices=("yes", "no"))
    start = commands.add_parser("start-stage")
    start.add_argument("--stage", required=True, choices=tuple(STAGE_DIRS))
    start.add_argument("--thread-id", required=True)
    start.add_argument("--host-id")
    finish = commands.add_parser("finish-stage")
    finish.add_argument("--stage", required=True, choices=tuple(STAGE_DIRS))
    gate = commands.add_parser("advance-gate")
    gate.add_argument("--gate", required=True, choices=tuple(GATE_FILES))
    ai_use = commands.add_parser("record-ai-use")
    ai_use.add_argument("--stage", required=True, choices=tuple(STAGE_DIRS))
    ai_use.add_argument("--tool-or-model", required=True)
    ai_use.add_argument("--purpose", required=True)
    ai_use.add_argument("--affected-file", action="append", required=True)
    ai_use.add_argument("--human-review", required=True)
    commands.add_parser("status")
    args = parser.parse_args()

    try:
        if args.command == "authorize-tasks":
            authorize(args.project_root, args.value == "yes")
        elif args.command == "start-stage":
            start_stage(args.project_root, args.stage, args.thread_id, args.host_id)
        elif args.command == "finish-stage":
            finish_stage(args.project_root, args.stage)
        elif args.command == "advance-gate":
            advance_gate(args.project_root, args.gate)
        elif args.command == "record-ai-use":
            record_ai_use(
                args.project_root,
                args.stage,
                args.tool_or_model,
                args.purpose,
                args.affected_file,
                args.human_review,
            )
        else:
            _, state_path, threads_path, _, ai_log_path = project_files(args.project_root)
            print(json.dumps({"state": load_json(state_path), "threads": load_json(threads_path)}, ensure_ascii=False, indent=2))
            return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"Applied: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
