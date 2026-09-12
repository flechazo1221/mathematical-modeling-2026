---
name: math-modeling-figure
description: Creates traceable publication figures from approved workflow evidence, or produces one evidence-grounded draft figure before eliciting detailed preferences in a standalone plotting request. It never changes source data, metrics, or model results.
---

# Publication Figures

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, `resource-map.md`, and `../../tools/figure/SKILL.md`. Detailed chart guidance and scripts remain under `tools/figure/` and are loaded only as needed.

## Choose the mode

- **Workflow mode:** when `.workflow/` exists or the request names H3/FIGURE, require `decisions/H3-claims.json` with `TEAM_APPROVED`. Read verified results, evidence map, formal figure requirements, terminology, and official page dimensions. Write only `PROJECT_ROOT/06-figure/`.
- **Standalone mode:** require a readable dataset or result table and a discernible comparison, relationship, distribution, or trend. Preserve the source file. Write to the user-requested output directory, or `PROJECT_ROOT/figures/` when none is given.

For a revision after COMPUTE/EVIDENCE/H3/FIGURE already passed, treat the existing
manifest, handoff, frozen snapshots, and approved claim list as the legacy baseline.
Do not silently replace them. Create a versioned revision directory, rebuild only
figures whose evidence dependencies changed, and require a new H3 approval before
the revised figures become formal deliverables.

## Standalone first-draft interaction

Do not begin with a questionnaire when the supplied data supports a defensible default. Profile the data, infer the most decision-relevant relationship, and generate exactly one clearly labelled draft figure with conservative defaults. Do not silently infer a causal claim, metric definition, aggregation rule, unit, or omitted category.

Show the draft and briefly state the inferred question, selected fields, transformations, aggregation, uncertainty treatment, and output size. Then ask only the detailed preferences that could materially improve the next version, such as the intended claim, audience or venue, dimensions, language, grouping, uncertainty display, annotations, palette, or output formats. Incorporate the reply into the revision; if the user gives no further preference, the first draft remains the deliverable.

If no safe first draft is possible because the data, field meaning, units, or requested comparison is missing or materially ambiguous, ask one focused blocking question before drawing. Never fabricate placeholder data unless the user explicitly asks for a mockup.

## Contract-first work

### Phase 3: confirm every figure

Before formal rendering, create a complete figure register from `assets/figure-register-template.json`. Include figures and tables. For every item record its stable ID and subproblem; exact claim or question; source data and model/result version; evidence class and visual family; axes, units, groups, uncertainty, annotations, and expected reading; generation tool and format; body or appendix placement; provenance, privacy, and license; limitations and prohibited interpretations.

Before confirming individual items, perform a **paper-argument coverage audit**. For a modeling paper, explicitly decide whether the retained set needs: (a) a model-domain/coordinate/boundary schematic, (b) a model hierarchy or mechanism schematic, (c) an input-data processing figure showing raw observations and every interpolation, extension, masking, or threshold operation that materially affects results, (d) core result figures, and (e) validation/robustness evidence. Mark each role as `required`, `not_applicable`, or `covered`, with a reason. If a required role is absent, the register must fail even when every listed item is individually complete. Do not treat an exemplar's subject matter as instructions; use it only to identify a communicative role and rebuild that role from the current project's contracts and data.

Apply an **information-gain gate** before retaining an item. Record `information_gain` and `render_or_table_reason`. A standalone figure is normally rejected when it contains only one scalar, two nearly identical scalars, a PASS/FAIL record without structure, or information already readable more clearly in a table or sentence. Merge it into a validation table, annotation, or related panel unless spatial structure, scale contrast, a failure boundary, or a decision threshold makes the graphic materially easier to understand. Never satisfy a frozen count mechanically. If the approved H3 list contains low-value figures or omits a required modeling/data-processing role, stop formal rendering and return a proposed H3 revision instead of drawing the defective list.

Route by evidence type, not appearance:

- Quantitative data, fitted results, numerical fields, optimization results, sensitivity, uncertainty, residuals, and diagnostics: MATLAB by default in mathematical-modeling workflow mode. Another deterministic statistical renderer is allowed only when the approved environment or upstream contract requires it.
- Deterministic workflows, dependencies, algorithms, geometry, boundary conditions, and exact schematics: Mermaid, Graphviz, SVG, TikZ, or programmatic drawing.
- Modeling-domain, coordinate, boundary-condition, model-hierarchy, moving-boundary, and workflow schematics: render in black/white or grayscale by default. Use solid/dashed/dotted lines, hatching, arrows, labels, and line weight as the primary encodings; color is not a required semantic channel. A color version may be supplied only as an optional preview when it does not carry unique meaning.
- For textbook-style modeling schematics, prefer a clean line-art composition: white background, thin black/gray strokes, no large filled color blocks, paired state panels when a state changes, explicit reference line/axis, dimension arrows, and a separate flux/interaction panel. Rebuild the geometry and labels from the current model; never copy an exemplar's unrelated object or notation.
- For the textbook-style modeling schematic specifically, use a deterministic vector backend (SVG/TikZ/Graphviz or equivalent programmatic vector drawing) as the authoritative source. Do not use MATLAB's default `annotation` arrows, automatic layout, or a generic plotting canvas for the final schematic; MATLAB remains appropriate for quantitative curves and diagnostics. The schematic must expose the model's actual geometry and notation through controlled paths: white background; black/gray strokes; paired initial/reference and moving/final states when the domain changes; explicit coordinate axes and reference/sea-level lines; dimension arrows with visible arrowheads; boundary labels; and a separate force/flux or boundary-exchange panel when those quantities enter the model. Export both editable vector output and a >=300 DPI raster preview, then inspect the preview at publication size for arrowhead placement, dashed-line continuity, text collisions, and panel alignment. A schematic is not accepted if it is merely a recolored generic plot or if its arrows/labels cannot be traced to the current model contract.
- Conceptual or contextual illustration: an image model only after explicit user consent; mark it `DRAFT—NON-EVIDENTIAL` in the image and register.
- Mixed figures: generate any non-evidential artwork separately, then deterministically rebuild labels, arrows, geometry, scales, axes, and evidence overlays. Never ask an image model to reproduce quantitative values or exact scientific geometry.

Run `scripts/validate_figure_register.py <register.json>` and fix every routing or completeness error. Never relabel a quantitative figure as conceptual to pass validation. Present the full validated register and one global visual specification covering fonts, labels, color semantics, grayscale behavior, accessibility, physical dimensions, and formats. Obtain explicit user confirmation before formal rendering. Reconfirm an individual item only if its scientific meaning, data transformation, evidence class, or structure later changes; cosmetic revisions that preserve the approved contract do not reopen confirmation.

After confirmation:

1. Create one contract per workflow figure using `../../shared/schemas/figure-contract.schema.json`; for a standalone draft, record the same fields in a compact sidecar JSON when practical.
2. Freeze each figure's source-data snapshot and hash before rendering.
3. Choose the chart from data shape and the approved question; offer alternatives when the visual choice can change interpretation.
4. Compute only plot-specific summaries declared in the contract. Never redefine a metric, remove failures, select only favorable parameters, or alter model output.
5. Use final publication size, readable typography, colorblind-safe redundant encodings for quantitative plots, explicit uncertainty, SVG, and at least 300 DPI PNG unless current official rules differ. Schematics follow the black/white rule above.
6. Inspect color and grayscale previews at intended paper size; fix clipping, overlap, missing glyphs, misleading axes, or inconsistent panels.
7. Use no fixed minimum count for figures, categories, or chart types. Every retained figure must change understanding of an approved claim.
8. Produce a contact sheet grouped by argument role—not file order—and audit whether the sequence reads as problem/data → model → computation → result → validation. A technically valid but narratively incoherent set is not PASS.

## CUMCM publication profile

When working in a CUMCM project's `06-figure/`, apply the following project
profile in addition to the general rules:

- Keep data curves high-contrast and colorblind-tolerant. Use black for axes,
  grid, title, legend, ticks, and explanatory text. Keep one curve family on a
  consistent solid-line convention and use color plus markers to distinguish
  time or scenario when needed; verify grayscale separability.
- Prefer Songti (or a verified equivalent) for Chinese publication text and keep
  variable names, units, ticks, legends, and captions typographically consistent.
  Remove redundant subtitles, decorative notes, and repeated explanations;
  place limitations and conditions in the caption or paper text.
- A visual revision may change layout, typography, annotation, or display-only
  units, but must not change the source data, frozen snapshot, axis range,
  sampled points, units, metric definition, failure cases, or claim category.
  Never smooth, interpolate, delete, or recompute a curve merely to make it look
  better. If the data shape is scientifically suspect, route the issue back to
  COMPUTE/EVIDENCE.
- Formal delivery uses SVG, PDF, and PNG. For this profile, PNG should be at
  least 600 DPI unless an official rule requires another value, with both color
  and grayscale previews. Check PDF font embedding when PDF is delivered.
- Complete three QA layers: visual (clipping, overlap, glyphs, axes, legend,
  panel consistency), programmatic (format, dimensions, DPI, font and JSON
  validity), and data (source/snapshot hashes, output hashes, and claim-to-file
  mapping). Record all warnings rather than hiding them.
- Before cleaning a figure directory, compare the current manifest, contracts,
  captions, paper/appendix references, and user-selected scope. Move clearly
  superseded files to a recoverable archive; do not permanently delete files
  solely because they are not in one manifest. Preserve historical revision
  directories and never alter upstream evidence.
- Render a batch with one controlled process. Do not launch overlapping renderers
  that can race on the same output files; verify the final batch after rendering.
  If Windows `python` resolves to the WindowsApps placeholder, use the bundled
  runtime rather than changing the environment for a one-off figure task.

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
