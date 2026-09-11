---
name: math-modeling-prototype
description: Builds small, isolated, and fairly evaluated prototypes for approved candidate models. Use after model design to produce evidence for H2 without committing the project to a final route.
---

# Candidate Prototyping

Read `../../shared/references/quality-principles.md` and `workflow-contract.md`.

## Inputs and write boundary

- Require `02-design/handoff.json`, model contracts, validation plan, and `02-design/H2-优化审计与方向.md`.
- Read original data without modifying it.
- Write only `PROJECT_ROOT/03-prototype/`.

## Fair comparison

1. Implement the smallest end-to-end slice for each genuinely viable candidate.
2. Use the same data split, metrics, resource budget, and stopping rule unless a documented model requirement makes this impossible.
3. Record environment, command, random seed, runtime, convergence, constraint violations, and failures.
4. Do not give an AI-preferred candidate extra tuning or hide unsuccessful runs.
5. Compare feasibility, preliminary evidence, interpretability, data fit, cost, and failure modes.
6. Evaluate each proposed improvement against its own baseline and pre-registered retention threshold. Mark the evidence as supported, inconclusive, or unsupported; do not equate a numerically higher score with a meaningful or stable gain.
7. Prioritize sensitivity experiments for influential parameters; run robustness or ablation experiments when required by the design plan. Report failed and near-null improvements instead of hiding them.
8. In `H2-选择包.md`, include a concise section named “已进行的优化与后续优化方向”. Separate implemented/tested changes from unimplemented directions, and give each item its target defect, evidence status, cost, risk, and retain/rollback recommendation.
9. If prototypes would be materially expensive, pause with a costed experiment proposal instead of consuming an unapproved budget.

## Required outputs

- `03-prototype/model-*/` minimal code and outputs
- `03-prototype/原型结果.csv`
- `03-prototype/候选方案对比.md`
- `03-prototype/H2-选择包.md`
- `03-prototype/handoff.json`

Stop for H2. Do not set model weights, select the final model, or start full computation.
