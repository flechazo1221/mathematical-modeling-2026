---
name: math-modeling-design
description: Produces a credible baseline, materially different candidate models, mathematical contracts, and validation plans from an approved problem definition. Use after H1; it offers choices but does not select the team's final model route.
---

# Model Design

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, and `resource-map.md`. Read `references/baseline-improvement-validation.md`. Load `../../references/算法索引.md` and only the algorithm references relevant to the problem.

## Inputs and write boundary

- Require `decisions/H1-problem.json` with `TEAM_APPROVED`.
- Read the original inputs and `01-intake/handoff.json`.
- Write only `PROJECT_ROOT/02-design/`.

## Work

1. Translate every approved subproblem into decision use, inputs, outputs, constraints, and evaluation criteria.
2. Define consistent symbols, units, indices, and data semantics.
3. Build at least one simplest credible baseline for every subproblem before proposing complexity. A baseline must be runnable within the competition budget and capable of answering the same decision question as its proposed improvement.
4. Diagnose the baseline before improving it. Use residuals, constraint violations, error decomposition, instability, missed mechanisms, or decision failure costs to identify a concrete defect; do not treat a more advanced algorithm name as a defect.
5. Propose only materially different candidate routes with explicit assumptions, identifiability, data needs, computational cost, strengths, and failure conditions. Admit extra complexity only when the data can support it, the defect is relevant, the expected gain is testable out of sample or by an equivalent independent check, and interpretability and reproducibility remain acceptable.
6. For each proposed improvement, record the chain `baseline → observed or testable defect → targeted change → expected evidence → rejection rule`. If the gain is small, unstable, or unexplained, recommend returning to the simpler model or rediagnosing the defect.
7. Pre-register a fair comparison using identical data, splits, metrics, constraints, and calculation conventions. Document and justify any unavoidable exception before prototyping.
8. Make sensitivity analysis the default priority for influential parameters. Add robustness analysis for data/environment shifts and ablation analysis for claimed modules when each is decision-relevant; keep their questions and conclusions distinct.
9. Treat problem-aware data processing, defensible assumptions, targeted model changes, and stronger validation as legitimate innovation. Do not label routine preprocessing or model substitution as innovation without a mechanism and comparative evidence.
10. Search and verify literature only for claims that require external support.

## Required outputs

- `02-design/题目分析报告.md`
- `02-design/术语表格.md`
- `02-design/候选模型方案.md`
- `02-design/H2-优化审计与方向.md`
- `02-design/contracts/model-*.json`
- `02-design/验证计划.json`
- `02-design/handoff.json`

Stop after producing implementable candidates. Do not choose the final route, write full solution code, or begin the paper.
