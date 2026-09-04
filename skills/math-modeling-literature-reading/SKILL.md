---
name: math-modeling-literature-reading
description: Reads user-supplied literature after the H1 problem definition is approved, extracts traceable domain and modeling knowledge, and produces the required knowledge handoff for DESIGN. Use only for the LITERATURE stage between H1 and DESIGN; it does not search for papers or choose the final model route.
---

# Literature Reading

Turn the team's supplied literature into one traceable knowledge file that DESIGN can use. Read `../../shared/references/quality-principles.md` and `workflow-contract.md` before starting.

## Inputs and write boundary

- Require `decisions/H1-problem.json` with `gate: H1` and `status: TEAM_APPROVED`.
- Require at least one user-supplied file under `PROJECT_ROOT/literature/input/`. Treat these files as read-only.
- Read the approved H1 decision, original problem, `01-intake/赛题结构化说明.json`, and `01-intake/handoff.json` to judge relevance. Do not reopen or rewrite H1.
- Write only `PROJECT_ROOT/02-literature/`.
- Use the suite PDF tool for PDFs, including OCR when a scan has no usable text. Use the corresponding document tool for other supported formats.

## Reading method

1. Inventory every supplied file with a stable source ID (`L01`, `L02`, ...), path, type, size, SHA-256, page count when available, and extraction status.
2. Attempt every supplied file. Mark encrypted, corrupted, incomplete, or unreadable material explicitly; do not silently omit it.
3. For each usable source, verify bibliographic identity from the document itself or a DOI/publisher record. Separate verified metadata from uncertain metadata.
4. Extract only content relevant to the approved H1 problem: domain mechanisms, variable definitions, equations or algorithms, assumptions, data requirements, parameter ranges, evaluation metrics, empirical findings, limitations, and failure conditions.
5. Attach a locator to every substantive source-level claim: PDF page, section, theorem, table, or figure. Page numbers refer to PDF pages unless printed-page numbering is explicitly stated.
6. Synthesize agreements, contradictions, transferable methods, and evidence gaps across sources. Label cross-paper synthesis as analysis rather than as a direct claim from one paper.
7. Translate the synthesis into DESIGN implications without selecting the H2 route: credible baselines, candidate model families, necessary constraints, parameter priors or ranges, validation ideas, and methods that should be avoided or treated cautiously.

Never infer a paper's result from its title or abstract when full text is unavailable. Never present a literature method as suitable merely because it is popular. Preserve differences in population, scale, data regime, objective, and assumptions when transferring knowledge to the competition problem.

## Authoritative knowledge file

Write all reading results to `02-literature/文献阅读结果.md`. It must contain:

1. H1 scope and reading question;
2. source-status table with source IDs and metadata confidence;
3. one evidence card per source;
4. cross-source consensus and conflicts;
5. domain facts and mechanisms relevant to the problem;
6. reusable mathematical formulations and their assumptions;
7. data, parameter, and evaluation guidance;
8. DESIGN input matrix mapping each H1 subproblem to evidence, candidate implications, transfer risks, and source locators;
9. prohibited overclaims and unresolved gaps;
10. a compact list of source IDs DESIGN must cite when it uses the corresponding idea.

Use cautious language for weak, abstract-only, or single-source evidence. Quote sparingly; prefer faithful paraphrase with a locator.

## Required outputs

- `02-literature/文献清单.json`
- `02-literature/文献阅读结果.md`
- `02-literature/handoff.json`

The handoff must follow `../../shared/schemas/handoff.schema.json`, declare stage `LITERATURE`, hash every input and output, and freeze the approved H1 decision. Set `PASS` only when every supplied file was attempted and at least one relevant source was usable. Otherwise return `BLOCKED` with an exact reason.

Stop after the reading handoff. Do not design candidates, choose a model, implement code, or modify the user-supplied literature.
