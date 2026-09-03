---
name: math-modeling-figure
description: Creates traceable publication figures, captions, frozen plot-data snapshots, and visual audits from team-approved claims and verified results. Use after H3 or for a standalone modeling-paper figure task; it never changes the model, metrics, or source results.
---

# Publication Figures

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, `resource-map.md`, and `../../tools/figure/SKILL.md`. Detailed chart guidance and scripts remain under `tools/figure/` and are loaded only as needed.

## Inputs and write boundary

- Require `decisions/H3-claims.json` with `TEAM_APPROVED` in the complete workflow.
- Read verified results, evidence map, formal figure requirements, terminology, and official page dimensions.
- Write only `PROJECT_ROOT/06-figure/`.

## Contract-first work

1. Create one contract per figure using `../../shared/schemas/figure-contract.schema.json`.
2. Freeze each figure's source-data snapshot and hash before rendering.
3. Choose the chart from data shape and the approved question; offer alternatives when the visual choice can change interpretation.
4. Compute only plot-specific summaries declared in the contract. Never redefine a metric, remove failures, select only favorable parameters, or alter model output.
5. Use final publication size, readable typography, colorblind-safe redundant encodings, explicit uncertainty, SVG, and at least 300 DPI PNG unless current official rules differ.
6. Inspect color and grayscale previews at intended paper size; fix clipping, overlap, missing glyphs, misleading axes, or inconsistent panels.
7. Use no fixed minimum count for figures, categories, or chart types. Every retained figure must change understanding of an approved claim.

## Required outputs

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
