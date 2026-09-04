---
name: math-modeling-intake
description: Inventories a modeling problem, attachments, data quality, current competition rules, and AI-disclosure requirements. Use as the first independent stage of a modeling workflow; it prepares H1 but does not decide the problem interpretation.
---

# Intake and Compliance

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, `ai-disclosure.md`, and `resource-map.md`.

## Inputs and write boundary

- Require an approved `decisions/H0-selection.json` and read the selected candidate's `00-selection/` handoff and score evidence.
- Read only the selected problem and its attachments under `PROJECT_ROOT/input/`, the H0 decision, selection handoff, and controller configuration. Do not silently intake a higher-ranked but unapproved candidate.
- Write only `PROJECT_ROOT/01-intake/`.
- Use the suite PDF and spreadsheet tools when relevant.

## Work

1. Inventory every input with path, type, size, and SHA-256.
2. Extract all subquestions, requested outputs, deadlines, and stated constraints.
3. Profile data fields, units, missingness, ranges, grouping, and time or spatial order without silently changing data.
4. Identify ambiguities, unknowns, potential leakage, measurement error, selection bias, and inconsistent definitions.
5. Verify the target competition, year, region, official template, submission rules, and AI policy from current official sources. Mark unverified items explicitly.
6. Prepare a neutral H1 package covering problem interpretation, objectives, hard constraints, error costs, and candidate assumptions.

## Required outputs

- `01-intake/赛题结构化说明.json`
- `01-intake/附件清单.json`
- `01-intake/数据审计报告.md`
- `01-intake/官方规则与AI合规.md`
- `01-intake/H1-选择包.md`
- `01-intake/handoff.json`

The handoff must follow `../../shared/schemas/handoff.schema.json` and contain hashes for every declared input and output. Stop after preparing H1. Do not select a model or create `TEAM_APPROVED`.
