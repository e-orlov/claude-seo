---
name: seo-file-audit-orchestrator
description: >
  Orchestrates SEO audits in mixed mode: a live Screaming Frog MCP connection for
  crawl/technical data, plus uploaded exports for everything else (Ahrefs, Semrush
  AI Visibility mhtml, GSC, GA4, WebPageTest, Lighthouse, HAR). Use for full audits,
  multi-source SEO analysis, or when the user asks to analyze a Screaming Frog
  crawl (live or exported) together with other SEO exports. Does not call other
  APIs, use OAuth, or use browser automation as part of the standard pipeline.
user-invokable: true
argument-hint: "[audit-scope or uploaded-files-folder]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# SEO File Audit Orchestrator

## Purpose

Coordinate a complete SEO audit in mixed mode.

This skill does not call other APIs, use OAuth, or perform live external data collection beyond the one sanctioned source below.

It uses:
- a live connection to Screaming Frog SEO Spider via its own MCP server (`seospider`), for crawl/technical data
- uploaded files
- local project files explicitly provided
- derived intermediate artifacts

## When to Use

Use this skill when the user asks for:
- full SEO audit from a live Screaming Frog crawl, uploaded files, or both
- technical SEO audit from a Screaming Frog crawl (live MCP connection or exports)
- content audit from crawl/GSC/GA4 data
- backlink audit from Ahrefs exports
- GEO / AI-visibility audit from Semrush AI Visibility mhtml exports and other available data
- performance audit from WebPageTest/Lighthouse/HAR exports
- scoring across multiple SEO areas
- prioritized recommendations from the assembled data basis

## Inputs

Accept any combination of a live Screaming Frog MCP connection and uploaded files.

Expected but not required:
- Live Screaming Frog MCP connection (`seospider`), or Screaming Frog CSV/XLSX exports and reports
- GSC CSV/XLSX exports
- GA4 CSV/XLSX exports
- Ahrefs CSV exports
- Semrush AI Visibility `.mhtml` exports
- WebPageTest JSON, Requests CSV, HAR, Lighthouse JSON
- Additional manually prepared mapping, content, keyword or crawl files

Unknown files must be inventoried, not ignored.

## Operating Sequence

Run the audit in this order.

### Phase 0: Data Staging

Before any skill runs, all raw data must be loaded into DuckDB (the path
configured for the `duckdb` MCP server on this machine — see global `CLAUDE.md`).

This phase is identical for MCP sources and file uploads — after Phase 0, the rest of the
workflow is the same regardless of how the data arrived.

**MCP sources:**
1. Fetch data via the relevant MCP tool with all required export filters.
2. Export as NDJSON to the MCP server folder (the MCP tool handles this).
3. Load into DuckDB:
   ```sql
   CREATE OR REPLACE TABLE <table_name> AS
   SELECT * FROM read_json_auto('<path_to_ndjson>');
   ```
4. Confirm to the user: table name, row count, column names.

**File uploads (CSV / XLSX / JSON / NDJSON):**
1. Detect file format.
2. Load into DuckDB:
   ```sql
   CREATE OR REPLACE TABLE <table_name> AS
   SELECT * FROM read_csv_auto('<path>');   -- or read_json_auto / read_xlsx
   ```
3. Confirm to the user: table name, row count, column names.

Use the table naming conventions from CLAUDE.md. The actual name used is recorded in
`file_inventory` (produced in Phase 1).

Do not proceed to Phase 1 until all available data sources are staged in DuckDB.

### Phase 1: Data Foundation

Invoke or follow `seo-data-foundation`.

Produce:
1. `file_inventory` (includes source classification per record via `source_type` field)
2. `schema_registry`
3. `column_profiles`
4. `source_coverage_report`
5. `field_coverage_report`
6. `data_quality_report`
7. `normalized_url_map` — required when URL normalization or URL-level joins are performed; if no URL joins are needed, produce an artifact record with `artifact_status: not_applicable` and a reason
8. `join_key_report` — required when cross-source joins are performed; if no joins are performed, produce an artifact record with `artifact_status: not_applicable` and a reason
9. `metric_coverage_report`
10. source and field mapping coverage check (performed as Step 12 of `seo-data-foundation`; results are embedded in `file_inventory` via `source_mapping_status` and `mapped_to_areas` fields — not a separate artifact; `source_final_utilization_status` is populated by the Post-Diagnosis Final Utilization Check after Phase 3)
11. `analysis_readiness_report`

Artifacts 7 and 8 are conditional: they must either be produced with real content OR documented as an artifact record with `artifact_status: not_applicable` and a stated reason. Do not silently omit them. Do not proceed to final diagnosis before all 11 Phase-1 outputs / artifact records are present or explicitly accounted for.

### Phase 2: Area Diagnostics

Run only areas with sufficient or partially sufficient data.

Recommended execution order within the diagnosis phase:

1. `seo-technical-file-diagnosis` — no dependencies on other diagnosis skills
2. `seo-content-file-diagnosis` — no dependencies on other diagnosis skills
3. `seo-backlink-file-diagnosis` — no dependencies on other diagnosis skills
4. `seo-performance-file-diagnosis` — no dependencies on other diagnosis skills
5. `seo-geo-file-diagnosis` — benefits from Technical and Content output; runs last

The GEO skill must reference Technical indexability findings and Content structure findings when assessing AI crawler accessibility and answer-passage citability. If Technical and Content diagnosis have not been completed, the GEO skill proceeds with seo-data-foundation artifacts only and documents:

```text
GEO diagnosis completed without Technical/Content cross-reference.
Confidence reduced to: medium for crawlability-dependent GEO findings.
```

If an area lacks data, report:

```text
For the analysis of [area], the required data basis is missing.
```

Do not punish health score for missing data.

### Phase 2b: Source and Field Mapping Coverage Check

The Source and Field Mapping Coverage Check is performed by `seo-data-foundation` as its final step before producing the `analysis_readiness_report`. It verifies that all inventoried sources have been assigned to at least one analysis area (including tentative assignments via `potentially_relevant_unassigned` fields). The Post-Diagnosis Final Utilization Check — which updates `source_final_utilization_status` — runs after Phase 3 once the `issue_register` is complete.

If `seo-data-foundation` was not re-run but a diagnosis skill discovers an unmapped source, document the gap here, flag it for the next data-foundation pass, and apply the Late Amendment Rule to append it to the `analysis_readiness_report`.

### Phase 3: Evidence and Issue Register

The `evidence_ledger` and `issue_register` are produced by the Orchestrator by aggregating across all completed diagnosis skill outputs in this phase. The `## Evidence` section at the end of each diagnosis skill output is the direct source material for the `evidence_ledger`. Both artifacts must be complete before `seo-scoring-recommendations` is invoked.

**Producing the `evidence_ledger`:** For every `## Evidence` section in each diagnosis skill output, assign a unique `evidence_id` using the format `E[area_prefix][nnn]` (e.g., `ETECH001`, `ECONT001`, `EBACK001`, `EPERF001`, `EGEO001`). Record for each entry all 10 mandatory fields:

| Field | Description |
|---|---|
| `evidence_id` | unique ID per entry, format `E[area_prefix][nnn]` |
| `source_file` | filename of the source export used |
| `sheet_table_json_path` | sheet name, table name, or JSON path within the source file |
| `filter_used` | filter applied to derive the evidence (e.g., `Status Code=200, Indexability=Indexierbar`) |
| `row_ids_or_ranges` | row IDs or row ranges when possible; use `n/a` if not applicable |
| `example_urls` | 1–3 representative example URLs, domains, queries or requests |
| `metric_values` | numeric values or counts that support the finding |
| `calculation_method` | direct field / derived / joined; formula if derived |
| `confidence` | high / medium / low |
| `limitations` | known constraints on the evidence (scope, date, sampling, join coverage) |

**Producing the `issue_register`:** Every entry must declare its `record_type` first: `verified_issue` (backed by `evidence_ledger` entries) or `unverified_hypothesis` (plausible suspicion without direct evidence). The two types share most fields but differ in what is mandatory.

| Field | `verified_issue` | `unverified_hypothesis` | Notes |
|---|---|---|---|
| `record_type` | mandatory | mandatory | `verified_issue` or `unverified_hypothesis` |
| `issue_id` | mandatory | mandatory | Format: `I[area_prefix][nnn]` |
| `area` | mandatory | mandatory | technical / content / backlinks / performance / geo |
| `severity` | mandatory | optional — `potential_severity` | Critical / High / Medium / Low — from Cross-Area Priority Matrix; for hypotheses use `potential_severity` field instead if severity cannot be determined without evidence |
| `affected_entity_type` | mandatory | mandatory | URL / query / domain / request / etc. |
| `affected_count` | mandatory | optional — estimated range | numeric or range; for hypotheses use an estimated range (e.g., "unknown — possibly 5–50 URLs") if exact count not determinable |
| `traffic_impact` | if available | if available | clicks / impressions / sessions / links / performance value |
| `evidence_ids` | mandatory | `[]` / `null` | verified issues must link to `evidence_ledger` entries |
| `confidence` | mandatory | mandatory | high / medium / low |
| `observation` | mandatory | mandatory | one sentence: what the data shows or suggests |
| `interpretation` | mandatory | mandatory | one sentence: why this matters for SEO |
| `candidate_action` | if actionable | optional | one sentence: what could be done |
| `recommendation_logic` | mandatory if `candidate_action` present | optional | one sentence: why this action addresses the interpretation |
| `validation_method` | mandatory | optional | how to confirm the issue is resolved |
| `verification_requirement` | not applicable | mandatory | one sentence: what data or analysis is needed to confirm or reject this hypothesis |
| `status` | `verified` | `unverified` | |

Rules:
- `unverified_hypothesis` entries must NOT contribute to health score deductions.
- `unverified_hypothesis` entries must NOT appear in the prioritized Recommendation Plan.
- `unverified_hypothesis` entries appear only in Section 10.4 (Unverified Hypotheses) of the final report and in the Data Gaps section.
- A `verified_issue` with no `evidence_ids` is an error, not an `unverified_hypothesis`. If evidence cannot be found, downgrade to `unverified_hypothesis` and set `verification_requirement`.
- An issue that initially has `record_type: unverified_hypothesis` may be upgraded to `verified_issue` if subsequent data provides evidence — update `evidence_ids`, `status`, remove `verification_requirement`, add `validation_method`.

#### analysis_readiness_report — Late Amendment Rule

If a diagnosis skill discovers a data gap, field mapping error or join failure that was not documented in the `analysis_readiness_report` produced by `seo-data-foundation`, it must append the finding to the report under:

```text
Late Discovery — [Skill Name]:
- Source: [file]
- Gap: [description]
- Affected sub-areas: [list, e.g. hreflang, canonicalization — or "area-wide" if no specific sub-area]
- Impact: [area blocked / coverage reduced / confidence reduced]
- Recommendation: [re-run data foundation step / accept gap / document as caveat]
```

The original `analysis_readiness_report` must never be silently replaced. Late discoveries are additive.

#### Late Discovery Decision Gate

After all diagnosis skills have completed, review all Late Discovery entries appended to the `analysis_readiness_report`. Apply the following decision rules before proceeding to Phase 4.

For each decision outcome, update the `effective_readiness_label` field in the corresponding `analysis_readiness_report` record. **Do not change `readiness_label`.**

- **Coverage reduction only** (confidence reduced, findings still valid): proceed to Phase 4. Set `effective_readiness_label` = original `readiness_label` (no change). Document the gap in Section 12 of the final report.
- **Join failure discovered late** (a planned join could not be performed): re-evaluate affected findings. If findings depended on the failed join, downgrade their evidence confidence. Proceed to Phase 4 with reduced confidence. Set `effective_readiness_label` = `partially_ready` if original label was `ready`; otherwise keep original label. Document confidence reduction in `score_rationale`.
- **Unmapped source discovered** (a source was in `file_inventory` but no fields were mapped): determine whether the source can materially affect a scored in-scope area:
  - **Blocking re-pass** (material impact possible): the source type matches an in-scope area, the area is currently `ready` or `partially_ready`, and the source appears to contain fields not covered by any other source. Trigger a targeted Data Foundation re-pass for that source **before proceeding to Phase 4**. Set `effective_readiness_label` = `partially_ready`; add `late_discovery_repass_status: pending` as a separate note field (not a status family value) until the re-pass completes; then update to the result (`partially_ready`, `ready`, or `blocked_late_discovery`). Document as:
  ```text
  Data Foundation re-pass triggered after Phase 2 (blocking).
  Reason: [Late Discovery description]
  Scope: [source / area affected]
  ```
  - **Non-blocking documentation** (no material impact): the source type maps to a `not_relevant` area, all fields from the source type are already covered by another mapped source, or the source is too small/low-quality to change any scored finding. Proceed to Phase 4 without re-pass. Document the gap in Section 12 and record a `late_discovery` entry with `type: unmapped_source`. Set `effective_readiness_label` = original `readiness_label` (no change).

- **Blocked area discovered late** (an area that was `ready` **or** `partially_ready` is now effectively `blocked` due to a late-discovered quality issue): exclude the area from the health score and proceed to Phase 4. Set `effective_readiness_label` = `blocked_late_discovery`.

#### Sub-area readiness propagation

When a Late Discovery entry has a non-empty `affected_sub_areas` list, apply the same decision rules to `effective_area_readiness_status` for each named sub-area in `sub_area_readiness`:

- **Coverage reduction only**: `effective_area_readiness_status` = original `area_readiness_status` (no change). Document the gap in Section 12.
- **Join failure discovered late**: `effective_area_readiness_status` = `partially_ready` if original was `ready`; otherwise no change. Document confidence reduction in `score_rationale`.
- **Blocking quality issue**: `effective_area_readiness_status` = `blocked_late_discovery`. Keep the sub-area in the area coverage denominator at 0% covered. Only `not_relevant` sub-areas exit the denominator. Do not re-raise as area-level `blocked_late_discovery` unless all in-scope sub-areas are now blocked.

After updating all affected `effective_area_readiness_status` values, reassess the area-level `effective_readiness_label`:
- If all in-scope sub-areas are now `blocked_late_discovery` (or were already `blocked_missing_data` / `blocked_low_quality_data`), elevate the area to `blocked_late_discovery`.
- If at least one in-scope sub-area is blocked (any blocked status), set the area to at least `partially_ready`. The area level can only be `ready` when all in-scope sub-areas are `ready` (no blocked sub-areas of any kind).

If `affected_sub_areas` is empty (`[]`), treat as area-wide and apply the decision rules only to the area-level `effective_readiness_label` without updating individual sub-area entries.

After updating all `effective_readiness_label` values, document a summary:

```text
Late Discovery Decision Gate — Summary:
- [Area]: effective_readiness_label set to [value] — reason: [decision outcome]
- [Area] / [sub_area]: effective_area_readiness_status set to [value] — reason: [decision outcome]
- ...
```

### Phase 4: Scoring

Invoke or follow `seo-scoring-recommendations`.

Produce:
- area health scores
- area coverage scores
- area confidence
- overall score — name depends on exclusions:
  - `SEO Health Score` if all relevant areas are scored (Case 1)
  - `Scope-adjusted Health Score` if areas are excluded as `not_relevant` only (Case 2)
  - `Observed Health Score` if in-scope areas are excluded due to missing data or late discovery (Case 3)
- overall Audit Coverage Score
- overall Confidence

Each area score must include a `score_rationale` in the structured format defined in `seo-scoring-recommendations` (Starting score → Deductions → Total deductions → Final score → Non-computable metrics → Coverage → Confidence).

Do not produce precise numeric scores where the data basis is insufficient.

### Phase 5: Recommendation Plan

Apply the Recommendation Consolidation Rule defined below. Final output is Section 10 of the Final Report, which supersedes all skill-level recommendation sections.

For each area, group actions into:
- Low Hanging Fruit
- Mid Term
- Long Term / Strategic

Every recommendation must include:
- current-state problem
- negative impact
- evidence
- affected volume
- expected effect
- effort
- priority
- validation method

## Required Final Report

Use this default structure:

```markdown
# SEO Audit Report

## 1. Executive Summary
- Top 3-7 issues
- Most important opportunities
- Overall score summary
- Important caveats

## 2. Data Basis and Audit Coverage
- File inventory summary
- Available sources
- Missing sources
- Coverage by area
- Confidence by area

## 3. Scores
| Area | Health Score | Data Coverage | Confidence | Status |
|---|---:|---:|---|---|

## 4. Critical Findings
| Priority | Area | Finding | Impact | Evidence | Confidence |
|---|---|---|---|---|---|

## 5. Technical SEO Diagnosis
## 6. Content Diagnosis
## 7. Backlink Diagnosis
## 8. GEO / LLM Citation Readiness Diagnosis
## 9. Performance Diagnosis

## 10. Prioritized Recommendation Plan
### 10.1 Low Hanging Fruit
### 10.2 Mid Term
### 10.3 Long Term / Strategic
### 10.4 Unverified Hypotheses / Evidence Needed

Plausible but unverified audit observations that require additional data before they can become findings or recommendations. These are **not** recommendations — they are open questions. For each hypothesis, state:
- what data would confirm or reject it
- the expected impact if confirmed
- confidence: low
- these items are excluded from scoring, health score deductions and the prioritized Recommendation Plan

## 11. Evidence Ledger
## 12. Data Gaps and Non-Computable Metrics
## 13. Validation Plan
```

## Recommendation Consolidation Rule

Individual diagnosis skills produce **action candidates**, not final recommendations.

Each action candidate from a diagnosis skill carries a `candidate_id` with area prefix:
- Technical: `RTECH001`, `RTECH002`, …
- Content: `RCONT001`, `RCONT002`, …
- Backlinks: `RBACK001`, `RBACK002`, …
- Performance: `RPERF001`, `RPERF002`, …
- GEO: `RGEO001`, `RGEO002`, …

Action candidates also carry a preliminary `priority` (Kritisch / Hoch / Mittel / Niedrig) and
`evidence_ref` from the diagnosis skill. The Orchestrator assigns the final `evidence_id` from
the `evidence_ledger` in Phase 3. The final `recommendation_id` and definitive priority are
assigned by `seo-scoring-recommendations` in Phase 5.

Action candidates are processed in two distinct phases:

**Phase 3 — Classification (happens during evidence ledger and issue register construction):**

For each action candidate, the Orchestrator links it to available `evidence_ledger` entries and classifies it as one of three outcomes:

- **`verified_for_recommendation_planning`** — candidate has at least one `evidence_id`; record as `verified_issue` with `candidate_action` in the `issue_register`. This makes it *eligible* for final recommendation planning, not a finished recommendation. Priority, effort, `recommendation_id` and final wording are assigned later in Phase 5.
- **`converted_to_unverified_hypothesis`** — candidate has no `evidence_id` but expresses a plausible, testable audit suspicion tied to a specific observable signal; add to `issue_register` as `unverified_hypothesis` with a `verification_requirement`; list in Section 10.4.
- **`discarded_action_candidate`** — candidate has no `evidence_id` and is not a plausible testable hypothesis (e.g., generic best-practice suggestion without any signal from the available data); exclude from `issue_register` and from all sections of the final report; note it only in internal audit notes if needed.

**Phase 5 — Final Recommendation Plan (happens after Phase 4 scoring):**

`verified_issue` entries from Phase 3 are:
1. **Deduplicated** — if two skills proposed the same action, merge into one entry with combined `evidence_ids`.
2. **Cross-referenced** — if a Technical action resolves a GEO issue as a side effect, document the cross-area benefit.
3. **Re-prioritized** — final priority uses the Cross-Area Priority Matrix from CLAUDE.md, not any skill-level estimate.
4. **Consolidated** — `seo-scoring-recommendations` produces the final `recommendation_id`, effort rating and validation method. Section 10 of the final report is the single authoritative Recommendation Plan.

Individual skill candidate sections remain in the diagnosis output as area context. Section 10 supersedes them.

## Audit Area Readiness

### Technical SEO
Minimum useful data:
- Screaming Frog internal-like export with URL, status, indexability or equivalent.

Enhanced data:
- canonicals
- directives
- redirects
- hreflang
- structured data
- images
- inlinks/outlinks
- sitemap/crawl overview

### Content
Minimum useful data:
- URLs and at least one of title, meta description, headings, word count or content fields.

Enhanced data:
- GSC clicks/impressions/queries
- GA4 engagement/conversions
- duplicate/near-duplicate fields
- readability fields
- page type mapping

### Backlinks
Minimum useful data:
- Ahrefs backlinks or referring domains export.

Enhanced data:
- anchors
- target URLs
- link types
- DR/UR
- spam flags
- first seen / lost
- link intersect

### GEO
Minimum useful data:
- content/crawl structure data, headings, schema, robots/bot access data or evidence-bearing content fields.

Enhanced data:
- backlinks/mentions
- structured data
- FAQ/question headings
- GSC query intent
- llms.txt if present
- AI crawler access information if exported

### Performance
Minimum useful data:
- WebPageTest JSON, Lighthouse JSON, HAR or WPT Requests CSV.

Enhanced data:
- request-level timings
- render-blocking flags
- CPU times
- cache headers
- LCP/FCP/CLS/TBT/TTFB
- resource summaries
- filmstrip/visual progress

## Source Priority

When sources overlap:
- Use Screaming Frog for crawl/indexability/on-page URL-level data.
- Use GSC for search demand, clicks, impressions, CTR and position.
- Use GA4 for engagement and conversion/business impact.
- Use Ahrefs for backlink/refdomain/anchor data.
- Use WebPageTest/Lighthouse/HAR for lab performance and network data.
- Use integrated Screaming Frog connector fields when separate files are absent, but mark their origin and coverage.

## Safety Rules

- Do not mutate raw input files.
- Do not delete user data.
- Do not expose secrets if they appear in HAR or exports.
- If HAR files are present, treat them as potentially sensitive.
- Do not quote cookies, authorization headers, session tokens, personal identifiers, private query parameters or request bodies containing sensitive values from HAR data.
- Use HAR data for aggregated diagnostics such as host, resource type, status code, timing, transfer size, cache behavior, initiator, render-blocking pattern and third-party impact.
- If HAR contains cookies, authorization headers or personal data, mention the sensitivity and avoid quoting secrets.
- Do not recommend destructive SEO actions without strong evidence.
- Do not recommend disavow except under strong spam/manual-action evidence.
