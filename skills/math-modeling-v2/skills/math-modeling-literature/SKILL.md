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

## CNKI-assisted acquisition

Use this interactive route when Chinese literature is relevant and the user can open CNKI in a controllable browser. It complements the OpenAlex + AnySearch collector; it does not weaken metadata verification or access-control rules.

### Step 1: prepare and pause

1. Add a `cnki` section to `literature/acquisition/search-plan.json` containing:
   - `professional_search_url`: `https://kns.cnki.net/kns8s/AdvSearch?type=expert&classid=WD0FTY92&rlang=CHINESE&language=CHS`;
   - 4–8 copy-ready professional-search expressions derived from H1;
   - for every expression, its purpose, H1 basis, preferred database/type/year filters, and a bounded screening target.
2. Use CNKI field syntax deliberately: `SU` for topic, `TKA` for title-keyword-abstract, `KY` for keywords, `TI` for title, and `AB` for abstract. Use the site's documented Boolean operators; do not invent unsupported syntax.
3. Create `literature/acquisition/CNKI-检索交接.md` with the clickable official URL, the expressions in execution order, inclusion/exclusion criteria, and the exact metadata to capture.
4. Present the link and queries to the user and stop. Ask them only to open the link and reply that the CNKI page is ready. Do not require or proactively request login: CNKI may expose ordinary search and download actions without authentication. The user's explicit ready confirmation establishes that the page is open for browser control; handle any actual access challenge only if it appears later.

### Step 2: resume in the user's ready tab

After the user explicitly reports that the CNKI page is open or ready:

1. Connect to the existing user-opened tab with the available browser-control tool; do not open a separate session when the ready tab is available.
2. Execute the planned expressions one at a time. Before every search, verify the input field contains the intended expression; after submission, record the visible result count and active filters.
3. Do not treat passive page labels such as `登录`, `个人登录`, or a download-link hint such as `未登录` as proof that access is blocked. When the user requested downloads and an ordinary visible download action is available with no stated charge, try that action once through normal GUI interaction.
4. If that action starts a download, verify the resulting file and continue. If CNKI instead presents an actual credential dialog, CAPTCHA, access warning, payment/charge confirmation, or permission denial, stop at that boundary. Ask the user to handle the challenge or decide whether to use their lawful access. Never solve a CAPTCHA, enter credentials, purchase content, or bypass access controls.
5. Screen results by H1 relevance, not merely ranking or citation count. Collapse duplicate titles and reject wrong population/material, wrong outcome, generic background, retracted work, and records that cannot support a named H1 need.
6. Write `literature/acquisition/cnki-results.json`. Each retained record must include the query ID, title, authors as displayed, venue, year, document type, stable CNKI detail URL when visible, relevance decision, `supports`, and metadata-verification status. Record excluded candidates with a brief reason when they were plausibly relevant.
7. Create `literature/acquisition/CNKI-下载清单.md`, grouped into `优先下载`, `备选`, and `仅题录/不可获取`. This is a reviewable acquisition queue, not a claim that every result should be downloaded.
8. Download a retained full text when the user-opened CNKI page exposes a normal download action and no extra payment, credential, CAPTCHA, or access-circumvention step is required. Save it under `PROJECT_ROOT/literature/input/` without overwriting existing files.
9. For each attempted download, update `literature/acquisition/cnki-download-manifest.json` with the record identity, outcome (`downloaded`, `user_action_required`, `no_authorized_access`, or `failed`), source URL, local relative path when downloaded, SHA-256, and PDF/CAJ signature/readability check. Never report a click as a successful download without validating the local file.
10. Stop after acquisition and let the user review/add/remove sources before literature reading. Report query, candidate, retained, downloaded, unavailable, and failed counts separately.

Do not promise an exhaustive search of CNKI. State the databases, filters, query set, result window, and screening limits so “complete” means complete within the declared reproducible scope.

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

When the CNKI-assisted route is used, also reconcile retained CNKI records into `selected-candidates.json` and `references.bib` after verification. Keep their `source: "CNKI"` and query provenance; do not label them OpenAlex/AnySearch cross-validated unless an actual metadata match was found.

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
- every CNKI download attempt appears in `cnki-download-manifest.json`, and every successful CNKI PDF/CAJ exists under `literature/input/` with matching SHA-256 and a readability/signature result;
- duplicate DOI/title records are collapsed;
- the review distinguishes downloaded full text from abstract-only evidence;
- failures and unavailable full texts remain visible in the manifest.

Report counts for queries, candidates, selected records, verified records, downloaded PDFs, unavailable PDFs, and failed downloads. Provide paths to the search review, bibliography, manifest, and `literature/input/`, then stop so the user can add or remove sources before the reading stage begins.
