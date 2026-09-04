---
name: math-modeling-team-decision
description: Prepares neutral option packages for human decisions in a mathematical-modeling workflow and validates team decision records. Use at H0 problem selection, H1 problem framing, H2 model selection, H3 claim and figure selection, or H4 submission approval; never decides on the team's behalf.
---

# Team Decision Support

Read `../../shared/references/human-decisions.md`, `quality-principles.md`, and the current stage handoff. Write only the current choice package and a blank or user-confirmed decision record under `PROJECT_ROOT/decisions/`.

## Decision package

Present:

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
- H2: primary model, baselines, metrics, weights, innovations, and required validation. The package must also tell the team which optimizations were actually designed or tested, what baseline defect each addresses, the current evidence status, which modules should be retained or rolled back, and which future optimization directions remain conditional. Never present an unimplemented direction as a completed optimization.
- H3: approved claims, conditional or prohibited claims, key figures, narrative, and limitations.
- H4: residual risks, AI declaration, human revision, official compliance, and submission approval.
- C1: optional confirmation of a high-risk visual choice.

## Approval boundary

Generate decision files with `status: DRAFT`. Only set an approval status when the user provides the team decision and responsible member names in the current turn. Never infer approval from silence or from the need to keep the workflow moving.

Validate approved records against `../../shared/schemas/decision.schema.json`. A changed decision must create a new version with `supersedes`; preserve the earlier record.

Stop after delivering the package or validating the team's decision. Do not perform the next AI stage.
