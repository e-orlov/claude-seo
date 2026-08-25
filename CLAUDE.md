# CLAUDE.md

## Mission

This project is a SEO, technical SEO, content, backlink, GEO / LLM Citation Readiness and performance audit framework for Claude Code, operating in a **mixed mode**: a live connection to Screaming Frog SEO Spider via its own MCP server for crawl/technical data — including GSC, GA4 and PageSpeed Insights/CrUX fields when those APIs are connected within Screaming Frog itself — plus uploaded file exports for everything else (Ahrefs for backlinks, Semrush AI Visibility `.mhtml` exports for GEO/AI-visibility, standalone GSC/GA4/WebPageTest/Lighthouse/HAR exports when not pulled via Screaming Frog).

The assistant must produce evidence-led diagnoses, scoring and recommendations from this mixed data basis — never from data that was neither uploaded, derived from an upload, nor pulled live via the sanctioned Screaming Frog MCP connection.

The goal is not to freely call arbitrary APIs, use OAuth, or orchestrate other live external services beyond the sanctioned Screaming Frog MCP connection. The goal is to transform uploaded exports/reports plus the live Screaming Frog crawl into a reliable decision basis with transparent data coverage, validated evidence, prioritized findings and practical recommendations.

## File Size Guideline

This file loads in full every session — keep it under ~400 lines. It should hold operating policy (mission, non-negotiable rules, ordering, pointers), not reference material. Field taxonomies, header signatures, and artifact schemas belong in skills (they load lazily, this file does not) — link to them from here instead of duplicating.

## Qdrant SEO Knowledge Base

See global `CLAUDE.md` for base Qdrant search/store mechanics. This project additionally has SEO background knowledge in the `claude_code_memory` collection:
- **The Art of SEO** 4th Edition — 265 chunks (Chapters 1–9)
- **Google Developer Docs** (Search Central Blog, Search docs, Crawling, PageSpeed) — 3104 chunks

Each diagnosis skill (technical, content, backlink, geo, performance) and the scoring skill runs `qdrant-find` at startup (Stufe 0) with topic-specific queries — automatic on every skill invocation.

On-demand, call `qdrant-find` immediately whenever the user asks to analyze an issue and wants recommendations, uses phrases like "mit SEO-Wissen" / "Qdrant-Wissen einbeziehen" (or equivalent in any language), asks for best-practice/background context, or asks why a finding matters or how to fix it. Formulate the query from the specific topic at hand, and use the retrieved chunks directly as evidence or reasoning.

## Non-Negotiable Operating Mode

This project runs in mixed mode: one sanctioned live MCP connection (Screaming Frog) plus file-based exports for everything else. It is not a general-purpose live-tooling project — the exception is scoped to exactly one source.

Allowed data basis:
- Uploaded files
- Local files explicitly present in the project workspace
- Derived intermediate artifacts created from those files
- A live connection to Screaming Frog SEO Spider via its own MCP server (`seospider`), for crawl/technical/on-page data

Disallowed unless the user explicitly changes the project rules:
- Live crawling or scraping outside the Screaming Frog MCP connection
- API calls (Google APIs, Ahrefs API, Sistrix API, Moz API, DataForSEO, Semrush API, etc.)
- OAuth flows
- Browser automation (chrome-devtools MCP) as part of the standard audit evidence pipeline — the user regulates its use themselves by explicitly prompting for a specific task; it is not invoked automatically as an audit data source and its output does not enter the evidence ledger unless the user asks for that
- Firecrawl or generic crawler orchestration
- Hidden background automation
- Claims based on data that was neither uploaded, derived from an upload, nor pulled live via the Screaming Frog MCP connection

If a source is missing, report the gap. Do not replace it with a live lookup beyond the sanctioned Screaming Frog MCP connection.

## Skill Invocation Rules

For larger SEO audits based on the mixed data basis (uploaded files plus the live Screaming Frog MCP connection), use the project skills in this order:

1. `seo-file-audit-orchestrator`
2. `seo-data-foundation`
3. `seo-url-clustering`
4. relevant diagnosis skills:
   - `seo-technical-file-diagnosis`
   - `seo-content-file-diagnosis`
   - `seo-backlink-file-diagnosis`
   - `seo-geo-file-diagnosis`
   - `seo-performance-file-diagnosis`
5. `seo-scoring-recommendations`

`seo-url-clustering` is standalone and user-invocable (`/seo-url-clustering`) and recommended when cluster-scoped findings add value (large crawls, multiple locales, high page-type diversity) — not mandatory for smaller audits.

If the user asks for a single area only, still apply the relevant data-foundation logic before diagnosing that area.

Do not skip inventory, source classification, field mapping, data quality checks, URL normalization, metric coverage or evidence ledger for larger audits.

## No Live Tool Contamination

This project runs in mixed mode, with exactly one sanctioned live source: the Screaming Frog MCP connection (`seospider`). Data pulled through it is treated at parity with file-based evidence — same evidence ledger, same `E-NNN` IDs, no `live_external_source` special marking, because it is the regular path for crawl data, not an exception.

Do not use any other live APIs, MCPs, OAuth connections, crawlers or external SEO tools during an audit unless the user explicitly changes the rules for the current audit.

This applies even if tools are connected and visible in the environment, including but not limited to Sistrix, Google APIs, DataForSEO, Firecrawl, Ahrefs APIs, Moz APIs or any live crawler. chrome-devtools MCP falls under this too, with one carve-out: the user may explicitly prompt for a specific chrome-devtools task (e.g. a live rendering/layout check) outside the standard pipeline — that stays a one-off action the user directs, not a standing audit data source, and its output only enters the evidence ledger if the user asks for that.

If live data beyond the Screaming Frog MCP connection is explicitly enabled for a specific audit, separate it from uploaded-file evidence and label it as `live_external_source`.

## Core Principle

Do not produce final diagnoses before the available data has been inventoried, profiled, checked, normalized, linked, aggregated and evaluated.

Use this operating model:

```text
uploaded files + live Screaming Frog MCP connection
→ file inventory + source classification          [seo-data-foundation]
→ encoding / delimiter detection                  [seo-data-foundation]
→ schema registry + header normalization          [seo-data-foundation]
→ canonical field mapping                         [seo-data-foundation]
→ scope / freshness detection                     [seo-data-foundation]
→ column profiles + data quality checks           [seo-data-foundation]
→ URL normalization                               [seo-data-foundation]
→ source joining + join key report                [seo-data-foundation]
→ metric coverage                                 [seo-data-foundation]
→ source and field mapping coverage check         [seo-data-foundation]
→ analysis readiness report                       [seo-data-foundation]
→ area diagnosis + metric calculation             [diagnosis skills]
→ evidence ledger + issue register                [seo-file-audit-orchestrator Phase 3]
→ scoring                                         [seo-scoring-recommendations]
→ prioritized recommendations                     [seo-scoring-recommendations]
→ final report                                    [seo-file-audit-orchestrator Phase 5]
```

Do not load large raw datasets into the working context when structured inventory, aggregation, filtered examples and evidence IDs are more appropriate.

Golden rule:

```text
Do not load more context.
Load better context.
```

## Data Sources

Expected sources may include, but are not limited to:

### Screaming Frog
Supplied either as uploaded exports/reports, or as a live connection via Screaming Frog's own built-in MCP server (`seospider`, port 11435) — the sanctioned live source for this project (see Non-Negotiable Operating Mode). Both forms feed the same fields below and are treated at evidence parity.
- All exports and reports
- Internal / External
- Response Codes
- Page Titles
- Meta Descriptions
- H1 / H2
- Canonicals
- Directives
- Hreflang
- Structured Data
- Images
- Inlinks / Outlinks
- Redirect Chains
- Crawl Overview
- JavaScript rendered crawl exports if present
- Connector-enriched fields such as GSC, GA4, PSI, CrUX or URL Inspection fields if present inside Screaming Frog exports

### Google Search Console
Supplied either as uploaded exports, or as connector-enriched fields inside a
Screaming Frog crawl (live MCP connection or export) when the Search Console
API is connected within Screaming Frog itself — both forms feed the same fields.
- Pages
- Queries
- Query + Page combinations
- Countries
- Devices
- Dates
- Search appearance, if exported

### GA4
Supplied either as uploaded exports, or as connector-enriched fields inside a
Screaming Frog crawl (live MCP connection or export) when the Analytics API is
connected within Screaming Frog itself — both forms feed the same fields.
- Landing pages
- Sessions
- Users
- Engagement
- Conversions / key events
- Source / medium / channel, if exported

### Ahrefs
- Backlinks
- Referring domains
- Anchors
- Link intersect
- Best by links
- Lost / new links, if exported

### Semrush AI Visibility (GEO / AI performance)
- Saved `.mhtml` exports of the Semrush AI Visibility report for the domain
- Read as rendered content (tables, scores, mention/citation figures), not as a structured data export — extract figures conservatively and only cite what is actually legible in the saved page
- Feeds the GEO / LLM Citation Readiness area (`seo-geo-file-diagnosis`) alongside crawl- and content-based GEO signals

### WebPageTest / Lighthouse / HAR
PageSpeed Insights (PSI) and CrUX fields can additionally arrive as
connector-enriched fields inside a Screaming Frog crawl (live MCP connection or
export) when the PSI API is connected within Screaming Frog itself. Standalone
WebPageTest exports and HAR files remain file-only, no Screaming Frog connector
for those.
- WebPageTest JSON
- WebPageTest Requests CSV
- Lighthouse JSON
- Lighthouse logs
- HAR files
- Waterfall / request-level data
- Filmstrip / visual progress data if available

### Additional Files
Additional uploaded files may contain relevant data even if not listed above. Never ignore an unknown file. Inventorize and classify it first.

## Variable Input Rule

Files may differ from audit to audit.

Therefore:
- File names are hints, not truth.
- Headers are stronger evidence than file names.
- Encodings and delimiters may differ.
- Column counts may differ.
- Columns may be missing, additional, renamed, empty or partially populated.
- Sheet names may differ.
- JSON structures may differ.
- Empty cells are observations, not automatic findings.
- Missing files are coverage gaps, not negative SEO signals.


## Data Freshness Rule

For every source, detect or infer:
- export date
- test date
- crawl date
- date range
- file modification date, if available
- source-specific timestamp fields such as crawl timestamp, fetch time, first seen, last seen or test run time

If no date is available, mark the source as `date_unknown`.

If the source is older than the freshness expectation for its category, mark it as a caveat in `analysis_readiness_report`. Do not automatically treat old data as a website defect.

Default freshness expectations:
- WebPageTest / Lighthouse / HAR: ideally ≤ 30 days for current-state performance diagnosis
- Screaming Frog crawl: ideally ≤ 30–60 days for current technical diagnosis
- GSC / GA4: the date range must be explicit; older historical ranges can still be valid if the question is historical
- Ahrefs backlinks: export date should be explicit; older exports can still support structural backlink analysis but lower freshness confidence

## Missing Data Rule

Missing expected data is not a defect in the website.

Missing data affects:
- Data coverage
- Metric coverage
- Evidence confidence
- Audit completeness

Missing data does not directly reduce the health score.

Use the typed status families defined in `seo-data-foundation` Status Taxonomy. Do not mix values across families or use unlisted values.

**`source_status` (Family A)** — for data sources in `file_inventory`:
- `available`
- `partially_available`
- `missing`
- `not_relevant`

**`metric_status` (Family B)** — for metrics in `metric_coverage_report`:
- `computable`
- `partially_computable`
- `not_computable_from_current_sources`
- `insufficient_data`
- `rule_incomplete`
- `unreliable`
- `field_data_only`
- `experimental_only`

**`area_readiness_status` (Family C)** — for areas in `analysis_readiness_report`:
- `ready`
- `partially_ready`
- `blocked_missing_data`
- `blocked_low_quality_data`
- `blocked_late_discovery` — valid **only** for `effective_readiness_label` / `effective_area_readiness_status` (set by the Orchestrator). Never use for the initial `readiness_label` / `area_readiness_status` produced by `seo-data-foundation`.
- `not_relevant`

**`mapping_utilization_status` / `final_gap_status` (Family D)** — for fields in `schema_registry`:
See `seo-data-foundation` Status Taxonomy Family D for full definitions.

**`source_mapping_status` / `source_final_utilization_status` (Family E)** — for sources in `file_inventory`:
See `seo-data-foundation` Status Taxonomy Family E for full definitions.

**`artifact_status` (Family F)** — for conditional pipeline artifacts (`normalized_url_map`, `join_key_report`):
Values: `produced | not_applicable | blocked | missing`. See `seo-data-foundation` Status Taxonomy Family F for full definitions.

Do not use `available`, `missing` or `not_relevant` as metric status values. Do not use `derivable`, `partially_derivable` or `out_of_scope` — these are not defined in any taxonomy family.

If a section cannot be analyzed, state:

```text
For the analysis of [area], the required data basis is missing.
```

Then list what would be needed.

## Empty Cell Rule

Null, blank or missing values in data files are not automatically SEO problems.

A missing value becomes a negative finding only if:
1. the field is semantically required for the source type,
2. the row is applicable,
3. the page type or entity type requires the value,
4. the metric definition requires the value,
5. the source is reliable enough for that conclusion.

Examples:
- Empty meta description on an indexable HTML page can be an on-page issue.
- Empty hreflang columns on a single-language site are not an issue.
- Empty GA4 conversions can mean zero conversions, missing tracking, export filtering or non-applicability.
- Empty backlink anchors can indicate image links, redirects, export limitations or missing data.
- Empty Lighthouse details can be an audit limitation, not a performance issue.

## Required Audit Artifacts

For every larger audit, create or maintain these 12 artifacts internally and show them when useful:

`file_inventory`, `schema_registry`, `column_profiles`, `source_coverage_report`, `field_coverage_report`, `metric_coverage_report`, `normalized_url_map`, `join_key_report`, `data_quality_report`, `evidence_ledger`, `issue_register`, `analysis_readiness_report`.

Full field definitions and schemas for all 12 artifacts: see `seo-data-foundation` skill (Steps 1–12). `evidence_ledger` and `issue_register` are specifically produced by `seo-file-audit-orchestrator` Phase 3 (including the full `record_type` / `verified_issue` / `unverified_hypothesis` field-requirements table).

## Global Evidence ID Rule

Every piece of evidence cited in any audit — across all clients, domains, and date slugs — receives a globally unique `E-NNN` identifier.

### How to assign a new evidence ID

1. **Before assigning any evidence ID**, read `clients/evidence_registry.md`.
2. Find the highest existing `E-NNN` number in the registry.
3. Increment by 1 for each new evidence entry.
4. Write the new entry (or entries) to `clients/evidence_registry.md` immediately — before using the ID in any audit output.
5. Use the assigned ID in the `evidence_ledger`, `issue_register`, and all report tables.

Do not assign evidence IDs from memory. Always read the registry first.

### Registry file format

`clients/evidence_registry.md` uses this row format:

```
| E-NNN | client_domain | date_slug | issue_id | description |
```

Example:
```
| E-023 | example.de | 2026-07 | ITCH-001 | Title duplicate — /page-a vs /page-b |
```

If multiple evidence entries are created in one session, write all of them to the registry in a single update before returning any IDs to the audit output.

### ID format

- Format: `E-` followed by a zero-padded three-digit number, e.g. `E-001`, `E-042`, `E-123`.
- When the counter exceeds 999, continue with four digits: `E-1000`.
- Never reuse an ID. Never assign the same ID to two entries.
- Do not use client-specific prefixes (`SRC`, `SITE`, etc.) for new evidence entries. Those are legacy and remain as-is in their existing files.

### Retroactive legacy IDs

Evidence IDs from audits completed before this rule was introduced are preserved as-is in their original files. They are listed in `clients/evidence_registry.md` under their original identifiers for traceability.

### Automation requirement

This rule applies automatically — no user prompt is required. Whenever the audit pipeline reaches the `evidence_ledger` step, read the registry and assign the next available IDs.

---

## CSV / Table Reading Rules

See `seo-data-foundation` skill for the full CSV/table detection checklist (encoding, delimiter, quote handling, header detection/normalization) and known source-specific quirks (e.g. Screaming Frog UTF-8-SIG, Ahrefs UTF-16 tab-delimited).

## Header Normalization Rules

See `seo-data-foundation` skill for normalization steps. Always preserve the original header name in `schema_registry`.

## Canonical Field Families

Map fields semantically, not by exact name only. Families: URL Fields, Status / Indexability, GSC, GA4, Ahrefs, Performance Requests. Full alias lists per family: see `seo-data-foundation` skill.

## Source Classification Heuristics

Classify files by header signature and structure. Covered source types: Screaming Frog Internal, Screaming Frog Hreflang, Screaming Frog Structured Data, Google Search Console Standalone Export, GA4 Standalone Export, Ahrefs Backlinks, Ahrefs Referring Domains, Ahrefs Link Intersect, WebPageTest Requests CSV, WebPageTest JSON, Lighthouse JSON, HAR. Full header-signature lists per source: see `seo-data-foundation` skill.

## Analysis Areas

Create diagnoses in these areas:

1. Technical SEO
   - Crawlability
   - Indexability
   - Status codes
   - Redirects
   - Canonicals
   - Directives
   - Internal links
   - Hreflang
   - Images
   - Schema / structured data
   - Sitemap if data available

2. Content
   - Titles
   - Meta descriptions
   - H1/H2
   - Word count
   - Duplicate / near-duplicate content
   - Readability if fields available
   - Search intent fit if query/SERP/page-type data available
   - E-E-A-T signals if data supports them
   - Content gap and query/page opportunities if GSC data available

3. Backlinks
   - Referring domains
   - Link quality
   - Anchor distribution
   - Target URL distribution
   - Link type distribution
   - Follow/nofollow/UGC/sponsored
   - Lost/new links if available
   - Spam indicators
   - Link intersect / competitor opportunities if available

4. GEO / LLM Citation Readiness
   - AI crawler accessibility if robots/bot data available
   - llms.txt if uploaded or present in crawl exports
   - citability of answer passages if content data available
   - entity clarity
   - source/evidence readiness
   - brand/entity authority signals from backlinks and mentions if available
   - structured answer formats such as questions, lists, tables, definitions

5. Performance
   - WebPageTest lab metrics
   - Lighthouse metrics
   - HAR/request waterfall
   - TTFB
   - LCP
   - TBT / main-thread blocking
   - CLS
   - request count
   - transfer size
   - third-party hosts
   - render-blocking CSS/JS
   - cache policy
   - fonts
   - images
   - CDN/protocol usage

## Cross-Area Priority Matrix

Use this shared matrix across ALL diagnosis skills to determine finding priority consistently.

Priority is determined by two dimensions: **Search/Business Impact** and **Affected Scope**.

| Impact \ Scope | Widespread (>20% of indexable pages or high-traffic URLs) | Moderate (5–20% or mid-traffic URLs) | Limited (<5% or low-traffic URLs) |
|---|---|---|---|
| **Blocks indexing / ranking / conversion** | Critical | High | High |
| **Significantly harms performance, visibility or authority** | High | High | Medium |
| **Likely improvement opportunity** | High | Medium | Low |
| **Best-practice deviation** | Medium | Low | Low |

Apply this matrix before assigning severity in the `issue_register`. Overrides are allowed but must be explained in `score_rationale`.

Prioritization signals to use (in order of relevance):
1. GSC clicks and impressions (strongest search impact signal)
2. GA4 sessions and conversions (strongest business impact signal)
3. Backlink equity flowing to affected pages
4. Crawl depth and internal inlinks
5. Page type importance (money pages, entry points, hub pages)
6. Absolute affected URL count as secondary signal only

If no traffic or search signals are available, fall back to structural signals (page type, crawl depth, inlinks) and document the lower confidence.

## Scoring Principles

Scoring details, penalty bands, recommendation format, evidence ledger fields and
final report structure are defined in the relevant skills:
- `seo-scoring-recommendations` — scores, penalties, recommendation format, validation plan
- `seo-file-audit-orchestrator` — final report structure, evidence ledger, phase sequence

Core principles that apply everywhere:

- Missing data reduces coverage and confidence, not health score.
- Do not output a precise numeric score when the data basis is too weak.
- Priority labels are always in German: **Kritisch / Hoch / Mittel / Niedrig**
- All output tables must have an **Evidenz** column as the last column.
- URL cluster names in tables use patterns, not individual URLs (e.g. `index.php?page=`, not `index.php?page=18`).
- Percentages must match their numerator/denominator exactly. State the baseline explicitly above every table. Parameter URLs (`?`) and no-parameter URLs are disjoint sets — never express one as a share of the other's baseline.

## Anti-Hallucination Rules

- Do not infer unavailable metrics from unrelated data.
- Do not treat missing exports as bad performance.
- Do not treat missing backlink data as toxic backlinks.
- Do not treat missing hreflang fields as an issue unless the site is known to be multilingual or hreflang is expected.
- Do not recommend disavow unless evidence is very strong.
- Do not claim field data / CrUX if only lab data is uploaded.
- Do not claim real user performance if only Lighthouse/WebPageTest lab data is uploaded.
- Do not claim rankings or traffic if GSC/Sistrix/ranking data is absent.
- Do not claim conversion impact if GA4/conversion data is absent.
- Do not invent source files, rows, columns, URLs, metrics or examples.

## Data Staging Rule

See global `CLAUDE.md` for the base DuckDB staging rule (stage before analyze, MCP/file-upload loading mechanics). This project additionally uses a fixed table naming convention:

### Table naming convention
Use descriptive names that identify the source type:

| Table name | Source |
|---|---|
| `crawl_internal` | Screaming Frog Intern HTML |
| `crawl_titles` | Page Titles Export |
| `crawl_meta_desc` | Meta Descriptions Export |
| `crawl_h1` | H1 Export |
| `crawl_near_dupes` | Near Duplicate Content |
| `crawl_exact_dupes` | Exact Duplicate Content |
| `crawl_redirects` | Redirect Chains |
| `crawl_canonicals` | Canonicals Export |
| `crawl_hreflang` | Hreflang Export |
| `crawl_structured_data` | Structured Data Export |
| `crawl_images` | Images Export |
| `crawl_inlinks` | Inlinks Export |
| `crawl_outlinks` | Outlinks Export |
| `gsc_pages` | GSC Pages Export |
| `gsc_queries` | GSC Queries Export |
| `ga4_landing_pages` | GA4 Landing Pages |
| `ahrefs_backlinks` | Ahrefs Backlinks |
| `ahrefs_referring_domains` | Ahrefs Referring Domains |
| `ahrefs_anchors` | Ahrefs Anchors |
| `ahrefs_link_intersect` | Ahrefs Link Intersect |
| `wpt_requests` | WebPageTest Requests CSV |
| `lighthouse` | Lighthouse JSON |
| `har` | HAR entries |

These are conventions, not mandatory names. The actual name used is recorded in `file_inventory`.

## Report Infrastructure

The report rendering infrastructure lives in `.claude/skills/seo-report-generator/`:
- `report_renderer.py` — generic renderer
- `docx_helpers.py` — colors, helpers, document setup
- `report_config.py` — output path resolution

Always use this infrastructure for `.docx` report generation. Do not re-implement rendering.
Before generating a report, read any example file the user provides — for column names,
cluster naming and table conventions.

Generated report scripts are saved to `clients/<domain>/<date_slug>/work/`.
Generated `.docx` files are saved to `clients/<domain>/<date_slug>/output/`.

## Report Content Rules

These rules apply to every generated `.docx` report, without exception.

### No unvalidatable hypotheses

Do not include hypotheses, observations, or interpretations that cannot be directly validated
from the available data sources. If an explanation cannot be proven with the uploaded files,
leave it out entirely — do not mention it, flag it, or put it in a "limitations" section.

This rule extends to:
- "Possible explanations" that lack evidence
- Sections framed as "what we could not confirm"
- Caveats about missing data that have no actionable implication

### No "missing data" or "data gaps" sections in reports

Do not add sections advising the user to upload additional data sources, acquire new tools,
or extend the data basis. Such sections do not belong in a client-facing report.

If a finding cannot be made because data is missing, simply do not make the finding.
The report covers only what the available data supports.

### No sparse tables

Do not include a table if the majority of cells contain "k. A.", "n/a", "not available",
or equivalent placeholders. A table where most cells lack data adds no value and reduces
report quality. Replace sparse tables with a prose summary of what is known, or omit the
information entirely if it cannot be stated substantively.
