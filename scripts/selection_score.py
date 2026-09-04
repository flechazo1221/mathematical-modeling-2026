#!/usr/bin/env python3
"""Validate fixed-weight mathematical-modeling problem-selection scorecards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


WEIGHTS = {
    "problem_understanding": 0.25,
    "data_processability": 0.15,
    "result_verifiability": 0.20,
    "model_feasibility": 0.15,
    "ai_reliability": 0.25,
}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}


def validate_scorecard(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"missing selection scorecard: {path}"]
    except json.JSONDecodeError as exc:
        return [f"invalid selection scorecard JSON {path}: {exc}"]

    if data.get("schema_version") != "1.0":
        errors.append("selection scorecard schema_version must be 1.0")
    if data.get("criteria_weights") != WEIGHTS:
        errors.append("selection criteria weights must be exactly 25/15/20/15/25")
    if data.get("score_scale") != {"min": 0, "max": 10, "higher_is_better": True}:
        errors.append("selection score scale must be 0-10 with higher_is_better=true")

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("selection scorecard must contain at least one candidate")
        return errors

    ids: list[str] = []
    totals: dict[str, float] = {}
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            errors.append(f"candidate {index} must be an object")
            continue
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            errors.append(f"candidate {index} has no valid id")
            continue
        ids.append(candidate_id)
        criteria = candidate.get("criteria")
        if not isinstance(criteria, dict) or set(criteria) != set(WEIGHTS):
            errors.append(f"candidate {candidate_id} must contain exactly the five fixed criteria")
            continue

        expected_total = 0.0
        valid_scores = True
        for criterion_id, weight in WEIGHTS.items():
            record = criteria.get(criterion_id)
            if not isinstance(record, dict):
                errors.append(f"candidate {candidate_id} criterion {criterion_id} must be an object")
                valid_scores = False
                continue
            score = record.get("score")
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 10:
                errors.append(f"candidate {candidate_id} criterion {criterion_id} score must be 0-10")
                valid_scores = False
            else:
                expected_total += float(score) * weight * 10
            if record.get("confidence") not in CONFIDENCE:
                errors.append(f"candidate {candidate_id} criterion {criterion_id} has invalid confidence")
            evidence = record.get("evidence")
            if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item.strip() for item in evidence):
                errors.append(f"candidate {candidate_id} criterion {criterion_id} needs non-empty evidence")
            risks = record.get("risks")
            if not isinstance(risks, list) or not all(isinstance(item, str) for item in risks):
                errors.append(f"candidate {candidate_id} criterion {criterion_id} risks must be a string list")

        if not isinstance(candidate.get("hard_stops"), list):
            errors.append(f"candidate {candidate_id} hard_stops must be a list")
        if not isinstance(candidate.get("unknowns"), list):
            errors.append(f"candidate {candidate_id} unknowns must be a list")
        reported_total = candidate.get("weighted_total")
        if valid_scores:
            expected_total = round(expected_total, 2)
            if not isinstance(reported_total, (int, float)) or isinstance(reported_total, bool):
                errors.append(f"candidate {candidate_id} weighted_total must be numeric")
            elif abs(float(reported_total) - expected_total) > 0.01:
                errors.append(
                    f"candidate {candidate_id} weighted_total mismatch: {reported_total} != {expected_total}"
                )
            else:
                totals[candidate_id] = expected_total

    if len(ids) != len(set(ids)):
        errors.append("candidate ids must be unique")
    ranking = data.get("ranking")
    expected_ranking = sorted(totals, key=lambda item: (-totals[item], item))
    if ranking != expected_ranking or len(expected_ranking) != len(candidates):
        errors.append(f"ranking must list every candidate by weighted total: {expected_ranking}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scorecard", type=Path)
    args = parser.parse_args()
    errors = validate_scorecard(args.scorecard)
    if errors:
        print("Selection scorecard validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Selection scorecard validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
