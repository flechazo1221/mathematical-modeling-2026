---
name: math-modeling-compute
description: Implements the team-approved model route, runs full computations and robustness checks, and produces reproducible numerical evidence plus diagnostic figures. Use after H2; it does not create publication figures or change frozen model decisions.
---

# Full Computation

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, and `resource-map.md`.

## Inputs and write boundary

- Require `decisions/H2-model.json` with `TEAM_APPROVED`.
- Read original data, approved model contracts, prototype evidence, and validation plan.
- Write only `PROJECT_ROOT/04-compute/`.

## Work

1. Implement the approved route exactly; record any necessary deviation before running it.
2. Execute real commands from `PROJECT_ROOT`; no numerical claim may come from invented or unrun output.
3. Run the approved baseline, full solution, and validations relevant to prediction, optimization, evaluation, mechanism, or policy claims.
4. Report failed runs, uncertainty, boundary behavior, and the pressure test most likely to change the conclusion.
5. Create only diagnostic plots needed for data or model checking. Save publication-ready source tables separately.
6. Generate a reproducibility manifest with inputs, hashes, seeds, environment, parameters, commands, and key values.
7. If the approved model is structurally infeasible, return `FAIL` with `REQUEST_REOPEN_H2`; do not silently substitute another model.

## Required outputs

- `04-compute/src/`
- `04-compute/results/`
- `04-compute/diagnostic-figures/`
- `04-compute/logs/`
- `04-compute/复现清单.json`
- `04-compute/证据索引.json`
- `04-compute/handoff.json`

Stop after reproducible computation. Do not make final publication figures or write the paper.
