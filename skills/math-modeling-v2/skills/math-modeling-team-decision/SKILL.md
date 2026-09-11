---
name: math-modeling-team-decision
description: Reviews an upstream mathematical-modeling choice package for neutrality and records an explicit team decision at H0–H4, L1, or C1. It never authors the stage package, decides for the team, or advances the workflow.
---

# Team Decision Support

Read `../../shared/references/human-decisions.md`, `quality-principles.md`, the current stage handoff, and the choice package produced by that stage. Treat the package and all stage outputs as read-only. If they are incomplete, biased, or inconsistent, return exact findings to the owning stage; do not rewrite them.

Write only a new DRAFT or explicitly user-confirmed decision record under `PROJECT_ROOT/decisions/`. Never write into a stage output directory or advance workflow state.

## Review and presentation

Review the upstream package and present:

1. The exact question requiring a team decision.
2. Facts that do not depend on a model choice.
3. Unknowns and evidence limitations.
4. Two or more materially different options when they genuinely exist.
5. The same comparison dimensions for every option.
6. Assumptions, data needs, expected benefit, cost, and failure conditions.
7. Existing evidence and additional experiments that could distinguish options.
8. A separately labelled, non-binding AI recommendation.

Do not bias the package through unequal detail, loaded wording, unfair experiments, or presenting an AI preference as a fact. If evidence cannot distinguish options, say so.

## Gate scope

- H0: candidate-problem scores, hard-stop risks, uncertainty, and the team's final problem choice.
- H1: problem meaning, objectives, hard constraints, error costs, and accepted assumptions.
- L1: searched/downloaded literature scope, source relevance, synthesis quality, evidence gaps, transfer limits, exclusions, and the source set permitted as DESIGN input. It does not approve a model route.
- H2: primary model, baselines, metrics, weights, innovations, and required validation. The package must also tell the team which optimizations were actually designed or tested, what baseline defect each addresses, the current evidence status, which modules should be retained or rolled back, and which future optimization directions remain conditional. Never present an unimplemented direction as a completed optimization.
- H3: approved claims, conditional or prohibited claims, key figures, narrative, and limitations.
- H4: residual risks, AI declaration, human revision, official compliance, and submission approval.
- C1: optional confirmation of a high-risk visual choice.

## Approval boundary

When no decision has been supplied, a new record must use `status: DRAFT`, empty `selected_options`, empty `reasons`, empty `confirmed_by`, and `confirmed_at: null`. Only set an approval or rejection status when the user provides the team decision, reasons, and responsible member names in the current turn. Never infer approval from silence or from the need to keep the workflow moving.

Validate approved records against `../../shared/schemas/decision.schema.json`. A changed decision must create a new version with `supersedes`; preserve the earlier record.

Stop after reviewing the package, creating a DRAFT, or validating the team's explicit decision. Do not repair the package, perform the next AI stage, or update `.workflow/`.
