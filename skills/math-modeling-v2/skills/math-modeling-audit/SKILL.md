---
name: math-modeling-audit
description: Independently audits a completed mathematical-modeling project for problem alignment, numerical reproducibility, evidence integrity, figure honesty, paper consistency, official compliance, and AI disclosure. Use as a fresh read-only final task before H4.
---

# Independent Final Audit

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, `human-decisions.md`, `ai-disclosure.md`, and `resource-map.md`.

## Independence and write boundary

- Run in a fresh task that did not author or repair the inspected artifacts.
- Treat all project files as read-only except `PROJECT_ROOT/09-audit/`.
- Do not receive an expected verdict or the author's confidence assessment.

## Audit order

1. Verify the paper follows H1 problem interpretation, H2 model route, and H3 approved claims.
2. Reproduce the minimum decisive computations and compare key values, units, constraints, and hashes.
3. Look for leakage, proxy-target mismatch, non-identifiability, weak baselines, causal overreach, hidden failures, and unsupported generalization.
4. Trace every core paper claim to formulas, real outputs, figures, or verified literature.
5. Check publication figures against frozen data snapshots and contracts; detect misleading axes, selective presentation, or missing uncertainty.
6. Check the canonical LaTeX project and its compiled PDF for structure, citations, source/PDF hash consistency, rendering, and official-rule compliance. If an official platform required a derived DOCX, verify that it was exported from the frozen LaTeX source and has no substantive drift.
7. Compare the AI declaration with the actual usage log and affected files.

## Required outputs

- `09-audit/审查报告.md`
- `09-audit/问题清单.json`
- `09-audit/修复路由.json`
- `09-audit/handoff.json`

The verdict is `PASS`, `FAIL`, or `BLOCKED`. Classify findings by correctness/compliance, reproducibility/evidence, and non-blocking improvement. Do not edit upstream artifacts and do not approve H4.
