---
name: math-modeling-literature
description: Finds, verifies, and downloads legally available literature from a team-approved H1 problem definition. Use during the post-H1 acquisition pause when the user asks for paper search or open-access download; do not use to synthesize supplied full text, choose the competition problem, or bypass publisher access controls.
---

# Literature Search and Download

Use this skill after the team has fixed the problem interpretation at H1. It is an optional acquisition assistant for the user-facing literature pause: its goal is a small, relevant, reproducible collection that can be supplied to `$math-modeling-literature-reading`, not a large unscreened download.

`SKILL_ROOT` is this skill's directory. Resolve bundled script paths from it; commands must not depend on the current working directory.

## Authority and boundary

- `PROJECT_ROOT` is the mathematical-modeling project directory.
- Require `PROJECT_ROOT/decisions/H1-problem.json` with `gate: H1`, `status: TEAM_APPROVED`, and at least one `selected_options` entry. Stop and report the missing approval if these conditions are not met.
- Read the H1 decision, `01-intake/赛题结构化说明.json`, `01-intake/H1-选择包.md`, and the selected problem statement or attachments when available. Treat the approved H1 interpretation and assumptions as authoritative.
- Write search metadata only under `PROJECT_ROOT/literature/acquisition/` and downloaded PDFs under `PROJECT_ROOT/literature/input/`. Preserve any files the user already placed in `literature/input/`. Do not alter decisions, stage handoffs, or model-route choices.
- Download only openly and legally available copies. Do not use Sci-Hub, leaked mirrors, credential sharing, CAPTCHA bypass, or publisher-access circumvention.

## Search plan

Create `literature/acquisition/search-plan.json` before searching. Derive queries from the actual H1 scope and include:

1. one domain-mechanism query for the real-world phenomenon;
2. one method query for each plausible model family named or implied by H1, without choosing the H2 route;
3. one validation, uncertainty, or evaluation query;
4. English queries and Chinese queries when both bodies of literature are relevant.

Each query record must contain `query`, `purpose`, `h1_basis`, and optional year or field filters. Prefer 4–8 precise queries over one broad query. Combine domain nouns, mechanism terms, model names, and measurable outcomes. Do not add a topic that cannot be traced to H1.

## Candidate discovery

Run the bundled collector once with all approved queries:

```powershell
python "<SKILL_ROOT>/scripts/search_literature.py" --query "<QUERY 1>" --query "<QUERY 2>" --limit-per-query 12 --output "<PROJECT_ROOT>/literature/acquisition/candidates.json"
```

The collector uses the suite's OpenAlex + AnySearch search implementation, merges DOI and title duplicates, and retains source and query provenance. If one engine is unavailable, record the degraded search in the report; never label single-source results as cross-validated.

Search results are candidates only. Inspect titles and abstracts, then verify shortlisted records against DOI, publisher, or repository pages. Reject records that match only generic method words, concern the wrong system or scale, are retracted, or do not support a concrete H1/H2 need. Citation count is context, not evidence of correctness.

Write:

- `literature/acquisition/selected-candidates.json`, preserving candidate metadata and adding `selection_reason`, `supports`, `metadata_verified`, and `verification_url`;
- `literature/acquisition/search-review.md`, grouping selected work by the H1 subproblem or evidence need, with explicit gaps and contradictions;
- `literature/acquisition/references.bib`, using verified metadata only.

Set `metadata_verified` to true only after checking author, title, year, venue, and DOI or stable repository identifier. Do not infer a paper's findings from its title or invent missing metadata.

## Download open-access PDFs

After screening, download the selected set:

```powershell
python "<SKILL_ROOT>/scripts/download_open_access.py" --input "<PROJECT_ROOT>/literature/acquisition/selected-candidates.json" --output-dir "<PROJECT_ROOT>/literature/input" --manifest "<PROJECT_ROOT>/literature/acquisition/download-manifest.json"
```

The downloader resolves DOI/title records through OpenAlex, accepts only public HTTP(S) PDF responses, validates the PDF signature, uses stable filenames, and records SHA-256 values. A paywalled record is not a failure: keep its verified citation and record `no_open_access_pdf`. Do not silently substitute a different paper.

## Completion checks

Before reporting completion:

- every selected record traces to at least one search query and one H1 need;
- every cited record has verified metadata;
- every downloaded file opens as a PDF and appears in `download-manifest.json` with its source URL and SHA-256;
- duplicate DOI/title records are collapsed;
- the review distinguishes downloaded full text from abstract-only evidence;
- failures and unavailable full texts remain visible in the manifest.

Report counts for queries, candidates, selected records, verified records, downloaded PDFs, unavailable PDFs, and failed downloads. Provide paths to the search review, bibliography, manifest, and `literature/input/`, then stop so the user can add or remove sources before the reading stage begins.
