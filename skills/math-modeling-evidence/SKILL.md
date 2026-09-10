---
name: math-modeling-evidence
description: Converts verified model outputs into a claim-evidence map, abstract fact set, publication-figure requirements, and paper evidence outline. Use after full computation to prepare H3 without deciding the team's final claims or narrative.
---

# Evidence Synthesis

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, and `human-decisions.md`.

## Inputs and write boundary

- Read H1 and H2 decisions, model contracts, compute handoff, real result tables, diagnostic plots, and reproducibility records.
- Write only `PROJECT_ROOT/05-evidence/`.

## Work

1. Map every subproblem to the conclusions it can and cannot support.
2. Separate observed facts, mathematical deductions, model-dependent inferences, and unsupported statements.
3. Bind each candidate claim to exact formulas, files, rows, metrics, figures, literature, or commands.
4. Check baselines, uncertainty, robustness, boundary failures, and selective reporting.
5. Produce an abstract fact set containing only verified values.
6. Specify publication-figure needs by question and claim, not by a quota or desired visual variety.
7. Prepare a neutral H3 package for claims, figures, limitations, and narrative.

## Required outputs

- `05-evidence/主张证据映射.json`
- `05-evidence/结果事实清单.json`
- `05-evidence/摘要事实清单.json`
- `05-evidence/正式图表需求.json`
- `05-evidence/论文证据大纲.md`
- `05-evidence/H3-选择包.md`
- `05-evidence/handoff.json`

Stop for H3. Do not decide the final claims, render publication figures, or draft the full paper.
