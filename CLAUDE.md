# CLAUDE.md

## Mission

This project is an SEO, technical SEO, content, GEO / LLM Citation Readiness and migration (redirect) framework for Claude Code. Work runs through a small set of standalone skills (see Skill Invocation Rules). Each skill has its own closed data contract.

The assistant produces evidence-led diagnoses and recommendations — never from data that was neither uploaded, derived from an upload, nor pulled through a source the invoked workflow sanctions. The goal is not to call arbitrary APIs or orchestrate unrelated live services, but to turn the authorized source set into a decision basis with transparent coverage, validated evidence and practical recommendations.

## File Size Guideline

This file loads in full every session — keep it under ~400 lines. It holds operating policy (mission, non-negotiable rules, pointers), not reference material. Field taxonomies, schemas and method details belong in the skills (they load lazily, this file does not); link to them instead of duplicating.

The eight legacy shared-workflow skills (data-foundation, orchestrator, five diagnosis skills, scoring) are archived unchanged on branch `archive/legacy-file-audit-skills`. They are not part of this project's active workflow.

## Non-Negotiable Operating Mode

Allowed data basis:
- Uploaded files and local files explicitly present in the project workspace
- Derived intermediate artifacts created from those files
- Live connection to Screaming Frog SEO Spider via its MCP server (`seospider`)
- Within an explicitly invoked `/seo-geo-audit` only: SISTRIX MCP for the six `SX-*` source codes defined in `.claude/geo-audit/contracts/source-catalog.yaml`

Disallowed unless the user explicitly changes the rules for the current task:
- Live crawling or scraping outside the Screaming Frog MCP connection
- Other APIs or MCPs (Google APIs, Ahrefs, Moz, DataForSEO, Semrush, other SISTRIX endpoints, Firecrawl, generic crawlers) — even if connected and visible in the environment
- OAuth flows, except connector-managed authentication for the sanctioned SISTRIX MCP
- Browser automation (chrome-devtools MCP) as an audit data source. The user may explicitly prompt for a specific chrome-devtools task (e.g. a live rendering check); it stays a one-off action, and its output enters an evidence ledger only if the user asks
- Hidden background automation
- Claims based on data that was neither uploaded, derived from an upload, nor pulled through a sanctioned source

If a source is missing, report the gap. Do not replace it with a live lookup. If live data beyond the sanctioned sources is explicitly enabled, keep it separate and label it `live_external_source`.

## Skill Invocation Rules

Active skills (all user-invocable; none runs another automatically unless stated):

| Skill | Purpose | Data basis |
|---|---|---|
| `seo-helpful-content-audit` | People-first content audit of a URL, URL list or domain | Screaming Frog MCP only; own DuckDB tables `helpful_content_*`; run-local evidence `HC-E####` |
| `seo-geo-audit` | GEO analysis package (129 factors) | Closed 18-source catalog; explicit invocation only |
| `seo-geo-report-generator` | Scores and renders a GEO analysis package (DOCX + PDF) | Only the analysis package and `.claude/geo-audit/contracts/`; explicit invocation only |
| `seo-url-clustering` | Vertical and horizontal URL clusters from a staged crawl table | DuckDB crawl table; has a "GEO Run Mode" used by `seo-geo-audit` |
| `seo-report-generator` | Renders confirmed findings as landscape A4 `.docx` | Findings already confirmed in the conversation |
| `redirect-map-builder` | Redirect map for a migration or URL restructuring | Screaming Frog MCP + DuckDB |

Boundaries that must hold:
- `seo-helpful-content-audit` ends with a SQL-validated `run_id` in skill-local DuckDB tables. It never invokes `seo-report-generator`, `seo-url-clustering` or any other skill, and writes neither to `clients/evidence_registry.md` nor to other skills' tables. The user may start `seo-report-generator` manually afterwards; that task then follows the report generator's own contract.
- `seo-geo-audit` invokes `seo-url-clustering` automatically through its GEO Run Mode and never invokes the report skill. `seo-geo-report-generator` is started manually and reads only the analysis package. Semrush AI Visibility is not a source for this workflow.
- Analytical skills never invoke `seo-report-generator` automatically.

For ad hoc audits outside these skills, stage the data in DuckDB first (see Data Staging Rule) and apply the Evidence Discipline below.

## Evidence Discipline

- File names are hints, headers are stronger evidence. Encodings, delimiters, sheet names and columns differ between audits — inspect before mapping.
- Missing data affects coverage and confidence, not the website's score. A missing export is a coverage gap, not a negative SEO signal.
- An empty cell is an observation. It becomes a negative finding only if the field is required for the source type, the row is applicable, the page type requires it and the source is reliable enough.
- Record a date for every source (crawl, export, test, date range). If none exists, mark it `date_unknown` and treat age as a caveat, not as a website defect.
- If an area cannot be analyzed, state "For the analysis of [area], the required data basis is missing." and list what would be needed.

## Anti-Hallucination Rules

- Do not infer unavailable metrics from unrelated data.
- Do not claim rankings or traffic without GSC/SISTRIX/ranking data, conversion impact without GA4/conversion data, or real-user performance from lab data only.
- Do not claim field data / CrUX if only lab data is available.
- Do not treat missing backlink data as toxic backlinks; do not recommend disavow without very strong evidence.
- Do not treat missing hreflang fields as an issue unless the site is known to be multilingual.
- Do not invent source files, rows, columns, URLs, metrics or examples.

## Evidence ID Rule (shared workflow and report generator)

Every piece of evidence used in a report built with `seo-report-generator` receives a globally unique `E-NNN` identifier. Registry: `clients/evidence_registry.md` (local only — `clients/` is in `.gitignore`).

1. Before assigning any ID, read the registry and take the highest existing `E-NNN` (the counter line at the top can lag — check the rows).
2. Increment by 1 per new entry and write all new entries to the registry in one update before using the IDs anywhere.
3. Row format: `| E-NNN | client_domain | date_slug | issue_id | description |`
4. Never reuse an ID, never assign it from memory, no client-specific prefixes. IDs from before this rule (`SRC…`, `SITE-…`) stay as they are.
5. Format `E-` + three digits (`E-001`); beyond 999, four digits.

The `seo-helpful-content-audit` run is an exception: it uses its own run-local `HC-E####` records.

### Evidenz cell and Issue ID format

- In report tables the Evidenz cell is `E-NNN | <source_file> | <field or calculation>`; several entries are comma-separated (`E-318, E-319 | …`). The Issue ID is not written into the cell — it lives in the registry row of the cited E-NNN.
- New Issue IDs use `<AREA>-NNN` with a hyphen (`TECH-001`, `RANK-003`; sub-findings `RANK-003a`). Older rows without a hyphen and legacy rows stay unchanged.

## Data Staging Rule

See global `CLAUDE.md` for the base DuckDB staging rule (stage before analyze). Table names describe the source, e.g. `crawl_internal`, `crawl_titles`, `crawl_redirects`, `crawl_inlinks`, `gsc_pages`, `ga4_landing_pages`, `ahrefs_backlinks`, `ahrefs_referring_domains`, `wpt_requests`, `lighthouse`. These are conventions, not mandatory names.

The DuckDB database is persistent and shared across clients: before using any table, check its host column against the audited domain.

### Moving to another computer

`main.duckdb` is not in the repo (it holds client data) and does not move with a `git clone`. Whenever the user mentions moving to a new machine, setting one up, or onboarding (see `SETUP.md`), say this before anything else:

> Export the DuckDB database and give me the export folder (zipped). Run this query via the `duckdb` MCP (or in the DuckDB CLI), then zip the folder:
>
> `EXPORT DATABASE 'C:\Users\<user>\duckdb-data\export' (FORMAT PARQUET);`

On the new machine, after unzipping to `<USERPROFILE>\duckdb-data\export`, load it with `IMPORT DATABASE '<USERPROFILE>\duckdb-data\export';`, then check the table count and a few row counts against the old machine. Do not copy `main.duckdb` itself between machines or versions.

Also ask for `clients/evidence_registry.md` (the evidence counter; otherwise numbering restarts and IDs collide). Client data, the export and the registry travel out-of-band (zip, drive) and never go into the git repo, which is public and holds instructions only.

## Reporting Rules

- Priority labels in client-facing reports are German: **Kritisch / Hoch / Mittel / Niedrig**. Analytical tables may keep stable English codes.
- Every client-facing report table has an **Evidenz** column as its last column. DuckDB tables and machine-readable exports are exempt.
- URL cluster names in tables use patterns, not individual URLs (`index.php?page=`, not `index.php?page=18`).
- Percentages must match numerator/denominator exactly; state the baseline above every table. Parameter URLs and no-parameter URLs are disjoint sets — never express one as a share of the other's baseline.
- Do not output a precise numeric score when the data basis is too weak.

### Report infrastructure

Rendering lives in `.claude/skills/seo-report-generator/` (`report_renderer.py`, `docx_helpers.py`, `report_config.py`). Always use it for `.docx` reports; do not re-implement rendering. Before generating a report, read any example file the user provides (column names, cluster naming, table conventions).

Report scripts are saved to `clients/<domain>/<date_slug>/work/`, generated `.docx` files to `clients/<domain>/<date_slug>/output/`.

### Report content

These rules apply to every generated `.docx` report.
- **No unvalidatable hypotheses.** Leave out explanations, observations or interpretations that cannot be proven from the available data — do not mention them, flag them or park them in a "limitations" section.
- **No "missing data" or "data gaps" sections** and no advice to acquire further tools or sources. If a finding cannot be made because data is missing, do not make it.
- **No sparse tables.** Do not include a table whose majority of cells are "k. A.", "n/a" or similar; use a short prose summary or omit it.
