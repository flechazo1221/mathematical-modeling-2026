---
name: math-modeling-paper
description: Writes and builds a mathematical-modeling paper from frozen team decisions, verified evidence, and approved publication figures. Use after H3 and the figure stage to create Word and optionally LaTeX/PDF plus a truthful AI-use declaration.
---

# Paper Production

Read `../../shared/references/quality-principles.md`, `workflow-contract.md`, `ai-disclosure.md`, `resource-map.md`, and `writing-style-profile.md` for Chinese papers.

## Inputs and write boundary

- Require approved H1, H2, and H3 decisions.
- Read evidence outputs, verified results, publication figures, captions, official rules, writing guidance, and `.workflow/ai-usage-log.json`.
- Write only `PROJECT_ROOT/07-paper/`.

## Work

1. Verify every planned claim has an exact evidence path before drafting.
2. Use the official current-year structure and template; built-in templates are only fallbacks.
3. Write one coherent source of truth for methods, values, figures, limitations, and references.
4. State formulas with definitions and explain why each method answers the approved problem.
5. Describe experiments through setup, comparison, result, interpretation, uncertainty, and failure boundary.
6. Use only frozen publication figures; request a FIGURE rerun instead of redrawing or modifying data.
7. Verify literature against original publication pages.
8. Generate Word by default and LaTeX/PDF only when requested or required. Keep formats substantively identical.
9. Generate the AI-use declaration from current official rules and the actual usage log.
10. Run document-specific structural, equation, reference, rendering, page, font, and image checks.

## Required outputs

- `07-paper/完整论文.docx`
- `07-paper/完整论文-LaTeX/` and `完整论文.pdf` when required
- `07-paper/AI使用声明.md` when required or requested
- `07-paper/构建记录.json`
- `07-paper/handoff.json`

The paper is a reviewable draft. Do not mark it approved for submission or alter frozen team decisions.
