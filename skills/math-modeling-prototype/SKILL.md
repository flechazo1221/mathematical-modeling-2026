---
name: math-modeling-prototype
description: Builds small, isolated, and fairly evaluated prototypes for approved candidate models. Use after model design to produce evidence for H2 without committing the project to a final route.
---

# Candidate Prototyping

Read `../../shared/references/quality-principles.md` and `workflow-contract.md`.

## Inputs and write boundary

- Require `02-design/handoff.json`, model contracts, and validation plan.
- Read original data without modifying it.
- Write only `PROJECT_ROOT/03-prototype/`.

## Fair comparison

1. Implement the smallest end-to-end slice for each genuinely viable candidate.
2. Use the same data split, metrics, resource budget, and stopping rule unless a documented model requirement makes this impossible.
3. Record environment, command, random seed, runtime, convergence, constraint violations, and failures.
4. Do not give an AI-preferred candidate extra tuning or hide unsuccessful runs.
5. Compare feasibility, preliminary evidence, interpretability, data fit, cost, and failure modes.
6. If prototypes would be materially expensive, pause with a costed experiment proposal instead of consuming an unapproved budget.

## Required outputs

- `03-prototype/model-*/` minimal code and outputs
- `03-prototype/原型结果.csv`
- `03-prototype/候选方案对比.md`
- `03-prototype/H2-选择包.md`
- `03-prototype/handoff.json`

Stop for H2. Do not set model weights, select the final model, or start full computation.
