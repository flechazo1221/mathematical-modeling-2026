---
name: math-modeling-literature-reading
description: Reads user-supplied CAJ, PDF, or text literature after H1, using local conversion and bounded retrieval to minimize context use, then produces the traceable knowledge handoff required by DESIGN. Use only for the LITERATURE stage; it does not search for papers or choose the final model route.
---

# Literature Reading

Turn the team's supplied literature into one traceable knowledge file that DESIGN can use. Read `../../shared/references/quality-principles.md` and `workflow-contract.md` before starting.

## Inputs and write boundary

- Require `decisions/H1-problem.json` with `gate: H1` and `status: TEAM_APPROVED`.
- Require at least one user-supplied CAJ, PDF, DOCX, HTML, Markdown, or text file under `PROJECT_ROOT/literature/input/`. Treat these files as read-only.
- Read the approved H1 decision, original problem, `01-intake/赛题结构化说明.json`, and `01-intake/handoff.json` to judge relevance. Do not reopen or rewrite H1.
- Write only `PROJECT_ROOT/02-literature/`.
- Use the suite PDF tool for PDFs and the corresponding document tool for other supported formats.

## CAJ normalization and token budget

If any `.caj` file is present, read [references/caj-processing.md](references/caj-processing.md). Do not load CAJ binary data or an entire converted thesis into the model context.

First build a local corpus cache:

```powershell
py -3 "<SKILL_ROOT>/scripts/prepare_literature_corpus.py" --input-dir "<PROJECT_ROOT>/literature/input" --output-dir "<PROJECT_ROOT>/02-literature/corpus"
```

The script detects mislabeled PDFs, uses an available `caj2pdf` converter or a user-supplied same-stem PDF, checks the PDF text layer, optionally invokes local `ocrmypdf`, and writes page-aware chunks plus `corpus-manifest.json`. If it reports `needs_manual_conversion` or `ocr_required`, stop and request the exact missing conversion; do not compensate by sending every page image to the model.

Read the corpus manifest and H1 first. Form a small set of retrieval queries covering the H1 domain mechanism, each subproblem, relevant variables, methods, validation, and limitations. Retrieve all first-pass evidence in one bounded call:

```powershell
py -3 "<SKILL_ROOT>/scripts/query_literature_corpus.py" --chunks "<PROJECT_ROOT>/02-literature/corpus/chunks.jsonl" --query "<H1 topic>" --query "<method or mechanism>" --top-k 3 --max-chars 18000
```

Use a second call only for a specific unresolved claim, normally with `--top-k 2 --max-chars 6000`. Read a full normalized text file only when exact equation context, a table, or a contradiction cannot be resolved from targeted chunks. This retrieval budget is a default ceiling, not a quota.

## Reading method

1. Use the corpus manifest to inventory every supplied file with a stable source ID (`L01`, `L02`, ...), path, type, size, SHA-256, page count when available, conversion method, and extraction status.
2. Attempt every supplied file. Mark encrypted, corrupted, incomplete, or unreadable material explicitly; do not silently omit it.
3. For each usable source, verify bibliographic identity from the document itself or a DOI/publisher record. Separate verified metadata from uncertain metadata.
4. Extract only content relevant to the approved H1 problem: domain mechanisms, variable definitions, equations or algorithms, assumptions, data requirements, parameter ranges, evaluation metrics, empirical findings, limitations, and failure conditions.
5. Attach a locator to every substantive source-level claim: source ID plus PDF page, section, theorem, table, or figure. Page numbers refer to converted-PDF pages unless printed-page numbering is explicitly stated; preserve the CAJ-to-PDF page mapping recorded in the manifest.
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

`文献清单.json` may summarize `corpus/corpus-manifest.json`, but it must retain the original CAJ hash, conversion status, normalized-PDF path and hash when created, text path and hash, and whether evidence came from a text layer or OCR. The handoff must follow `../../shared/schemas/handoff.schema.json`, declare stage `LITERATURE`, hash every input and required output, and freeze the approved H1 decision. Set `PASS` only when every supplied file was attempted and at least one relevant source was usable. Otherwise return `BLOCKED` with an exact reason.

Stop after the reading handoff. Do not design candidates, choose a model, implement code, or modify the user-supplied literature.
