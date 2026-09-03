---
name: math-modeling-design
description: Produces a credible baseline, materially different candidate models, mathematical contracts, and validation plans from an approved problem definition. Use after H1; it offers choices but does not select the team's final model route.
---

# Model Design

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, and `resource-map.md`. Load `../../references/算法索引.md` and only the algorithm references relevant to the problem.

## Inputs and write boundary

- Require `decisions/H1-problem.json` with `TEAM_APPROVED`.
- Read the original inputs and `01-intake/handoff.json`.
- Write only `PROJECT_ROOT/02-design/`.

## Work

1. Translate every approved subproblem into decision use, inputs, outputs, constraints, and evaluation criteria.
2. Define consistent symbols, units, indices, and data semantics.
3. Build the simplest credible baseline before proposing complexity.
4. Propose only materially different candidate routes with explicit assumptions, identifiability, data needs, computational cost, strengths, and failure conditions.
5. For every retained model, state what defect it addresses and how an experiment could prove the gain.
6. Design sample-out, boundary, sensitivity, ablation, baseline, or external validation appropriate to the problem type.
7. Search and verify literature only for claims that require external support.

## Required outputs

- `02-design/题目分析报告.md`
- `02-design/术语表格.md`
- `02-design/候选模型方案.md`
- `02-design/contracts/model-*.json`
- `02-design/验证计划.json`
- `02-design/handoff.json`

Stop after producing implementable candidates. Do not choose the final route, write full solution code, or begin the paper.
