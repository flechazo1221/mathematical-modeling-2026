---
name: math-modeling-design
description: Produces a credible baseline, materially different candidate models, mathematical contracts, and validation plans from an approved H1 problem definition and a validated literature-reading handoff. Use after LITERATURE; it offers choices but does not select the team's final model route.
---

# Model Design

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, and `resource-map.md`. Read `references/baseline-improvement-validation.md`. Load `../../references/算法索引.md` and only the algorithm references relevant to the problem.

## Inputs and write boundary

- Require `decisions/H1-problem.json` with `TEAM_APPROVED`.
- Require `02-literature/handoff.json` with stage `LITERATURE` and status `PASS`; verify its declared hashes.
- Read the original inputs, `01-intake/handoff.json`, `02-literature/文献清单.json`, and the complete `02-literature/文献阅读结果.md` before proposing models.
- Write only `PROJECT_ROOT/02-design/`.

## Work

1. Translate every approved subproblem into decision use, inputs, outputs, constraints, and evaluation criteria.
2. Define consistent symbols, units, indices, and data semantics.
3. Map literature source IDs and locators to the H1 subproblems they can inform. Distinguish direct literature support, cross-paper synthesis, and the designer's own inference.
4. Build at least one simplest credible baseline for every subproblem before proposing complexity. A baseline must be runnable within the competition budget and capable of answering the same decision question as its proposed improvement.
5. Diagnose the baseline before improving it. Use residuals, constraint violations, error decomposition, instability, missed mechanisms, or decision failure costs to identify a concrete defect; do not treat a more advanced algorithm name as a defect.
6. Propose only materially different candidate routes with explicit assumptions, identifiability, data needs, computational cost, strengths, and failure conditions. Admit extra complexity only when the data can support it, the defect is relevant, the expected gain is testable out of sample or by an equivalent independent check, and interpretability and reproducibility remain acceptable. For every literature-derived element, cite its source ID and locator and explain whether its original data regime and assumptions transfer to this problem.
7. For each proposed improvement, record the chain `baseline → observed or testable defect → targeted change → expected evidence → rejection rule`. If the gain is small, unstable, or unexplained, recommend returning to the simpler model or rediagnosing the defect.
8. Pre-register a fair comparison using identical data, splits, metrics, constraints, and calculation conventions. Document and justify any unavoidable exception before prototyping.
9. Design sample-out, boundary, sensitivity, ablation, baseline, or external validation appropriate to the problem type, incorporating validated literature guidance where applicable. Make sensitivity analysis the default priority for influential parameters. Add robustness analysis for data/environment shifts and ablation analysis for claimed modules when each is decision-relevant; keep their questions and conclusions distinct.
10. Treat problem-aware data processing, defensible assumptions, targeted model changes, and stronger validation as legitimate innovation. Do not label routine preprocessing or model substitution as innovation without a mechanism and comparative evidence.
11. Preserve contradictions, transfer risks, and evidence gaps from the reading result. Do not turn a literature suggestion into an approved H2 choice.
12. Verify literature only for claims that require external support. If a recorded evidence gap requires additional literature, stop and return that need to the user or acquisition stage. Any new full text must be supplied under `literature/input/` and LITERATURE rerun before DESIGN relies on it.

## Required outputs

- `02-design/题目分析报告.md`
- `02-design/术语表格.md`
- `02-design/候选模型方案.md`
- `02-design/H2-优化审计与方向.md`
- `02-design/文献到模型映射.md`
- `02-design/contracts/model-*.json`
- `02-design/验证计划.json`
- `02-design/handoff.json`

Stop after producing implementable candidates. Do not choose the final route, write full solution code, or begin the paper.
