---
name: math-modeling-figure
description: Creates traceable publication figures from approved workflow evidence, or produces one evidence-grounded draft figure before eliciting detailed preferences in a standalone plotting request. It never changes source data, metrics, or model results.
---

# Publication Figures

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, `resource-map.md`, and `../../tools/figure/SKILL.md`. Detailed chart guidance and scripts remain under `tools/figure/` and are loaded only as needed.

## Choose the mode

- **Workflow mode:** when `.workflow/` exists or the request names H3/FIGURE, require `decisions/H3-claims.json` with `TEAM_APPROVED`. Read verified results, evidence map, formal figure requirements, terminology, and official page dimensions. Write only `PROJECT_ROOT/06-figure/`.
- **Standalone mode:** require a readable dataset or result table and a discernible comparison, relationship, distribution, or trend. Preserve the source file. Write to the user-requested output directory, or `PROJECT_ROOT/figures/` when none is given.

## Standalone first-draft interaction

Do not begin with a questionnaire when the supplied data supports a defensible default. Profile the data, infer the most decision-relevant relationship, and generate exactly one clearly labelled draft figure with conservative defaults. Do not silently infer a causal claim, metric definition, aggregation rule, unit, or omitted category.

Show the draft and briefly state the inferred question, selected fields, transformations, aggregation, uncertainty treatment, and output size. Then ask only the detailed preferences that could materially improve the next version, such as the intended claim, audience or venue, dimensions, language, grouping, uncertainty display, annotations, palette, or output formats. Incorporate the reply into the revision; if the user gives no further preference, the first draft remains the deliverable.

If no safe first draft is possible because the data, field meaning, units, or requested comparison is missing or materially ambiguous, ask one focused blocking question before drawing. Never fabricate placeholder data unless the user explicitly asks for a mockup.

## Contract-first work

1. Create one contract per workflow figure using `../../shared/schemas/figure-contract.schema.json`; for a standalone draft, record the same fields in a compact sidecar JSON when practical.
2. Freeze each figure's source-data snapshot and hash before rendering.
3. Choose the chart from data shape and the approved question; offer alternatives when the visual choice can change interpretation.
4. Compute only plot-specific summaries declared in the contract. Never redefine a metric, remove failures, select only favorable parameters, or alter model output.
5. Use final publication size, readable typography, colorblind-safe redundant encodings, explicit uncertainty, SVG, and at least 300 DPI PNG unless current official rules differ.
6. Inspect color and grayscale previews at intended paper size; fix clipping, overlap, missing glyphs, misleading axes, or inconsistent panels.
7. Use no fixed minimum count for figures, categories, or chart types. Every retained figure must change understanding of an approved claim.

## Required workflow outputs

- `06-figure/contracts/`
- `06-figure/data-snapshots/`
- `06-figure/scripts/`
- `06-figure/figures/`
- `06-figure/previews/`
- `06-figure/图注.md`
- `06-figure/figure-manifest.json`
- `06-figure/visual-audit.md`
- `06-figure/handoff.json`

Request optional C1 when an axis transformation, normalization, omission, or layout could materially change interpretation. Stop after final figures; do not write the paper.
