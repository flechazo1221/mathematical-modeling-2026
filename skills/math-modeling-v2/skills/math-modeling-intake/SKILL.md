---
name: math-modeling-intake
description: Structures an approved modeling problem into knowns, subquestions, constraints, deliverables, data readiness, and provisional method families while checking current competition and AI rules. Use after H0 to prepare the H1 problem-definition decision; it does not choose the final model route.
---

# Intake and Compliance

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, `ai-disclosure.md`, and `resource-map.md`. Read [references/problem-method-constraint.md](references/problem-method-constraint.md) for the required problem decomposition, method-family screening, and constraint audit.

## Inputs and write boundary

- Require an approved `decisions/H0-selection.json` and read the selected candidate's `00-selection/` handoff and score evidence.
- Read only the selected problem and its attachments under `PROJECT_ROOT/input/`, the H0 decision, selection handoff, and controller configuration. Do not silently intake a higher-ranked but unapproved candidate.
- Write only `PROJECT_ROOT/01-intake/`.
- Use the suite PDF and spreadsheet tools when relevant.

## Work

1. Inventory every input with path, type, size, and SHA-256.
2. Decompose the statement into four auditable inventories: known information, requested questions, constraints, and mandatory deliverables. Preserve source locations and distinguish quoted facts from interpretation.
3. Number every explicit and implicit subquestion. For each one, record action keywords, target object, output form, granularity, evaluation criterion, and its consistency, difference, dependency, or trade-off relationship with other subquestions.
4. Profile data fields, units, missingness, ranges, grouping, sample size, class balance, and time or spatial order without silently changing data.
5. Audit explicit, data, practical-domain, temporal, and physical constraints. Translate each usable constraint into a checkable mathematical or programmatic form; flag conflicts, missing bounds, unit mismatches, and constraints unsupported by the available data.
6. Map each subquestion to one primary task type and, only when needed, a secondary type. Screen plausible method families against data readiness, assumptions, constraints, output needs, validation paths, and failure conditions. Recommend a provisional family and a simple baseline, not a final algorithm or model route.
7. Identify ambiguities, unknowns, potential leakage, measurement error, selection bias, and inconsistent definitions. Never fabricate predictive information, causal identification, or unavailable labels.
8. Verify the target competition, year, region, official template, submission rules, and AI policy from current official sources. Mark unverified items explicitly.
9. Prepare a neutral H1 package covering problem interpretation, objectives, hard constraints, error costs, candidate assumptions, provisional method-family mappings, rejected families with reasons, and questions requiring team approval.

## Required outputs

- `01-intake/赛题结构化说明.json`
- `01-intake/附件清单.json`
- `01-intake/数据审计报告.md`
- `01-intake/问题方法约束矩阵.md`
- `01-intake/官方规则与AI合规.md`
- `01-intake/H1-选择包.md`
- `01-intake/handoff.json`

`赛题结构化说明.json` must make the four inventories and numbered subquestion relationships machine-readable. `问题方法约束矩阵.md` must show evidence for every provisional method-family recommendation and every rejected family; a keyword match alone is insufficient.

The handoff must follow `../../shared/schemas/handoff.schema.json` and contain hashes for every declared input and output. Stop after preparing H1. Do not choose a final algorithm, tune a model, create `TEAM_APPROVED`, or write into `02-design/`.
