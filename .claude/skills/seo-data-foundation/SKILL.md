---
name: seo-data-foundation
description: >
  Builds the data foundation for file-based SEO audits: file inventory, source
  classification, encoding/delimiter detection, schema registry, column profiles,
  field mapping, URL normalization, data quality, source joining and metric coverage.
  Use before any final diagnosis or scoring.
user-invokable: true
argument-hint: "[folder-or-files]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# SEO Data Foundation

## Purpose

Create a reliable data foundation for SEO analysis from any source — MCP crawl, file upload or both.

This skill must run before final diagnosis, scoring or recommendations.

## Datenbasis: DuckDB

All raw data must be loaded into DuckDB before this skill runs.
This is handled by Phase 0 of `seo-file-audit-orchestrator` or manually before invoking this skill.

**Step 0 of this skill: discover available tables.**

```sql
SHOW TABLES;
```

Or more detail:
```sql
SELECT table_name, estimated_size
FROM duckdb_tables()
ORDER BY table_name;
```

Classify each table by inspecting its columns:
```sql
DESCRIBE <table_name>;
-- or
PRAGMA table_info('<table_name>');
```

Use the same column-signature heuristics defined in CLAUDE.md and this skill's
Source Classification Heuristics section to determine source type from column names —
the method is identical whether data came from a file or MCP.

**All subsequent steps read from DuckDB, not from files in context.**
Do not load raw file contents into the context window. Use SQL aggregates, filters and samples.

## Core Rules

- Classify every DuckDB table before analysis.
- Unknown tables must be classified before exclusion.
- Table names are hints, not truth — column signatures are authoritative.
- Missing expected tables reduce coverage, not health.
- Empty cells are observations, not automatic issues.
- Preserve original column names for evidence.
- Use normalized column names for computation.
- Do not load large result sets into context — use aggregations and filtered samples.

## Status Taxonomy

All status values used in this skill and referenced by diagnosis skills are organized into six typed families. Use the typed field name in structured outputs (e.g., `"source_status"`, not `"status"`).

### Family A — `source_status`

Describes availability of a data source.

| Value | Meaning |
|---|---|
| `available` | Source present and usable |
| `partially_available` | Source present but only partially usable (truncated, filtered, low coverage) |
| `missing` | Expected source not uploaded or not found |
| `not_relevant` | Source not required for this audit scope |

### Family B — `metric_status`

Describes computability of a metric.

| Value | Meaning |
|---|---|
| `computable` | Metric can be fully computed from available data |
| `partially_computable` | Metric can be computed for a subset only; state the subset |
| `not_computable_from_current_sources` | Required sources or fields are absent |
| `insufficient_data` | Data exists but volume or quality is too low for a reliable result |
| `rule_incomplete` | Metric definition requires context not available (e.g., device type unknown) |
| `unreliable` | Metric is technically computable but data quality prevents reliable conclusions |
| `field_data_only` | Metric requires field data (CrUX/RUM); lab proxy exists but is not equivalent |
| `experimental_only` | Signal may be reported but must not be included in health scores |

### Family C — `area_readiness_status`

Describes whether a diagnosis area can be analyzed. Used in `analysis_readiness_report`.

The table below shows which values are valid for which field. `readiness_label` and `area_readiness_status` are assigned by this skill and are never modified after assignment. `effective_readiness_label` and `effective_area_readiness_status` are set by the Orchestrator's Late Discovery Decision Gate and may be updated post-diagnosis.

| Value | Meaning | `readiness_label` / `area_readiness_status` | `effective_readiness_label` / `effective_area_readiness_status` |
|---|---|---|---|
| `ready` | Area can be fully diagnosed | yes | yes |
| `partially_ready` | Area can be partially diagnosed; some sub-areas are limited or blocked | yes | yes |
| `blocked_missing_data` | Area blocked because required sources are absent | yes | yes |
| `blocked_low_quality_data` | Area blocked because data quality is insufficient | yes | yes |
| `blocked_late_discovery` | Area was `ready` or `partially_ready` but found effectively blocked during diagnosis due to a late-discovered quality issue | **no — Orchestrator only** | yes |
| `not_relevant` | Area is outside the current audit scope | yes | yes |

### Family D — Field Utilization

Field utilization is tracked in two phases. Phase-1 Mapping Utilization is set during Step 4 and Step 12 (before diagnosis). Post-Diagnosis Final Utilization is added after the Orchestrator's Phase 3 issue register is complete.

#### Phase-1 `mapping_utilization_status`

Describes the analytical assignment of a field at the end of Data Foundation, before any diagnosis skill runs.

| Value | Meaning |
|---|---|
| `used_in_metric` | Field is mapped to a computable metric |
| `used_in_join` | Field serves as a join or normalization key |
| `profiled_only` | Field was recognized and profiled; no analytical use identified |
| `potentially_relevant_unassigned` | Field appears relevant but no clear metric or join mapping was found; requires post-diagnosis review |
| `duplicate_of_preferred_field` | Field is semantically redundant; preferred canonical field documented in `mapping_notes` |
| `intentionally_excluded` | Field deliberately excluded; `exclusion_reason` is mandatory |
| `not_applicable` | Field is not relevant for this audit scope |

#### Post-Diagnosis `final_utilization_roles` (array)

Populated after Orchestrator Phase 3 (`issue_register` complete). Contains all roles the field actually fulfilled across the full audit. A field may contribute to multiple roles simultaneously (e.g., a status code field may drive both a metric and appear as evidence in a finding).

Allowed values: `used_in_metric`, `used_in_join`, `used_in_finding`

If `final_utilization_roles` is empty after Post-Diagnosis Final Utilization Check, the field was not actually used.

#### Post-Diagnosis `final_gap_status`

Set during Post-Diagnosis Final Utilization Check for fields where `mapping_utilization_status` = `potentially_relevant_unassigned`.

| Value | Meaning |
|---|---|
| `unmapped_relevant_field` | Field was relevant but not used in any metric, join or finding across the full audit; constitutes a genuine utilization gap |
| `null` | Field was eventually used (appears in `final_utilization_roles`) or is genuinely not applicable |

`unmapped_relevant_field` is only valid as a `final_gap_status` value, never as a `mapping_utilization_status` value. This distinction preserves the difference between a provisional assessment (Phase 1) and a confirmed gap (post-diagnosis).

### Family E — Source Utilization

Source utilization is tracked in two phases, mirroring the Field Utilization model (Family D).

#### Phase-1 `source_mapping_status`

Set during Step 12 (Phase 1 — before any diagnosis skill runs). Describes whether the source has been analytically assigned.

| Value | Meaning |
|---|---|
| `mapped` | At least one field from this source has `mapping_utilization_status` = `used_in_metric` or `used_in_join` |
| `tentatively_mapped` | All assigned fields have `mapping_utilization_status` = `potentially_relevant_unassigned` — relevant but not yet tied to a specific metric or join |
| `unmapped` | No fields assigned to any analysis purpose |
| `excluded` | Source intentionally excluded; document reason |
| `not_applicable` | Source is structural metadata, not analyzable content |

#### Post-Diagnosis `source_final_utilization_status`

Set during the Post-Diagnosis Final Utilization Check after Orchestrator Phase 3. Describes whether the source was actually used across the full audit.

| Value | Meaning |
|---|---|
| `used` | At least one field used AND no fields with `final_gap_status` = `unmapped_relevant_field` |
| `partially_used` | At least one field used AND at least one field with `final_gap_status` = `unmapped_relevant_field` |
| `not_used` | No field from this source appears in any `final_utilization_roles` |
| `excluded` | Source intentionally excluded; no final utilization check required |
| `not_applicable` | Source is structural metadata; not assessable |

Starts as `null` at Phase 1; set by Orchestrator Post-Diagnosis Final Utilization Check only.

### Family F — `artifact_status`

Describes the production state of conditional pipeline artifacts (currently `normalized_url_map` and `join_key_report`). These artifacts are either produced with real content, or documented as not applicable with a reason.

| Value | Meaning |
|---|---|
| `produced` | Artifact was created with real content |
| `not_applicable` | Artifact was not needed for this audit; reason documented |
| `blocked` | Artifact could not be produced due to a data quality or prerequisite failure |
| `missing` | Artifact was expected but not produced and no reason was documented |

`artifact_status` is used only for conditional artifacts in the pipeline — artifacts that must either be produced OR explicitly documented as `not_applicable`. It is not a synonym for `source_status` and must not be used in `file_inventory`.

### Cross-family note on `not_relevant`

`source_status = not_relevant` and `area_readiness_status = not_relevant` are both valid uses of the same label. They are not ambiguous because the family is always explicit from the field name.

## Step 1: File Inventory

For each file, record:

```json
{
  "file_id": "F001",
  "file_name": "",
  "duckdb_table": "",
  "extension": "",
  "detected_encoding": "",
  "detected_delimiter": "",
  "file_type": "",
  "source_type": "",
  "source_status": "available | partially_available | missing | not_relevant",
  "row_count": null,
  "column_count": null,
  "sheet_names": [],
  "json_top_level_keys": [],
  "primary_entities": [],
  "date_range": "",
  "export_date": "",
  "scope_status": "scope_known | scope_partial | scope_unknown",
  "date_status": "date_known | date_unknown",
  "likely_analysis_areas": [],
  "source_of_truth_role": "",
  "limitations": [],
  "recommended_access": [],
  "source_mapping_status": "mapped | tentatively_mapped | unmapped | excluded | not_applicable",
  "mapped_to_areas": [],
  "source_final_utilization_status": null
}
```

### File Types to Detect

- CSV / TSV / TXT table
- XLSX / spreadsheet
- JSON
- HAR
- XML
- HTML
- PDF
- Markdown
- plain text log
- unknown / binary / unsupported

## Step 2: Encoding and Delimiter Detection

For CSV-like files, detect:
- encoding
- delimiter
- quote character
- header row
- empty trailing columns
- row count
- column count

Known patterns:
- Screaming Frog examples: UTF-8-SIG, comma
- Ahrefs examples: UTF-16, tab
- WebPageTest Requests examples: UTF-8-SIG, comma

Potential delimiters:
- comma
- tab
- semicolon
- pipe

Do not assume one delimiter globally.

## Step 3: Source Classification

Classify by structural signatures.

### Screaming Frog Internal-like Export

Signals:
- `Address`
- `Status Code`
- `Indexability`
- `Indexability Status`
- `Title 1`
- `Meta Description 1`
- `H1-1`
- `Word Count`
- `Crawl Depth`
- `Inlinks`

May also include:
- GSC fields: `Clicks`, `Impressions`, `CTR`, `Position`
- GA4 fields: `GA4 Sessions`, `GA4 Views`, `GA4 Engagement rate`
- PSI/Lighthouse fields: `Performance Score`, `Largest Contentful Paint Time (ms)`
- CrUX fields: `CrUX Largest Contentful Paint Time (ms)`, `CrUX Interaction to Next Paint (ms)`
- URL Inspection fields: `URL Inspection API Status`, `Coverage`, `Google-Selected Canonical`

### Screaming Frog Hreflang

Signals:
- `Address`
- `HTML hreflang 1`
- `HTML hreflang 1 URL`
- `HTTP hreflang 1`
- `Sitemap hreflang 1`
- `Indexability`

Pattern fields:
- `HTML hreflang [n]`
- `HTML hreflang [n] URL`
- `HTTP hreflang [n]`
- `HTTP hreflang [n] URL`
- `Sitemap hreflang [n]`
- `Sitemap hreflang [n] URL`

### Screaming Frog Structured Data

Signals:
- `Address`
- `Errors`
- `Warnings`
- `Rich Result Errors`
- `Rich Result Warnings`
- `Total Types`
- `Unique Types`
- `Type-1`

Pattern fields:
- `Feature-[n]`
- `Type-[n]`


### Google Search Console Standalone Export

Signals:
- `Query`
- `Top queries`
- `Suchanfragen`
- `Page`
- `Top pages`
- `Seite`
- `URL`
- `Clicks`
- `Klicks`
- `Impressions`
- `Impressionen`
- `CTR`
- `Position`
- `Date`
- `Datum`
- `Country`
- `Land`
- `Device`
- `Gerät`
- `Search type`

Classify the aggregation level:
- query only
- page only
- query + page
- date segmented
- country segmented
- device segmented
- search appearance / search type segmented

Important:
- GSC is search-performance evidence, not crawlability evidence.
- Do not join GSC to crawl data until URL fields are normalized.
- If a GSC export contains paths or relative URLs only, require a hostname before URL joins.

### GA4 Standalone Export

Signals:
- `Landing page`
- `Landing page + query string`
- `Page path`
- `Page path and screen class`
- `Page title`
- `Sessions`
- `Users`
- `Total users`
- `Active users`
- `Engaged sessions`
- `Engagement rate`
- `Average engagement time`
- `Key events`
- `Conversions`
- `Event count`
- `Revenue`
- `Session source / medium`
- `Default channel group`

Important:
- GA4 often exports paths, not absolute URLs.
- If only paths are available, require a known hostname before joining to crawl URLs.
- GA4 is behavioral/business-impact evidence, not indexability evidence.
- Empty conversion fields are not automatically errors; they may indicate zero events, export scope, tracking configuration or non-applicability.

### Ahrefs Backlinks

Signals:
- `Referring page URL`
- `Target URL`
- `Anchor`
- `Domain rating`
- `UR`
- `Nofollow`
- `UGC`
- `Sponsored`
- `First seen`
- `Last seen`
- `Lost`

### Ahrefs Referring Domains

Signals:
- `Domain`
- `DR`
- `Links to target`
- `Dofollow links`
- `First seen`
- `Lost`

Normalize trailing spaces such as `Traffic ` and `Keywords `.

### Ahrefs Link Intersect

Signals:
- `Domain`
- `Domain rating`
- `Domain traffic`
- `Intersect`
- dynamic domain-like competitor columns

Treat all non-fixed domain-like columns as competitor columns.

### WebPageTest Requests CSV

Signals:
- `full_url`
- `host`
- `responseCode`
- `request_type`
- `load_ms`
- `ttfb_ms`
- `bytesIn`
- `objectSize`
- `cacheControl`
- `contentType`
- `protocol`
- `initiator`
- `renderBlocking`
- `cpuTime`

### WebPageTest JSON

Signals:
- top-level `data`
- `data.testUrl`
- `data.runs`
- `data.medians`
- nested `firstView.steps`
- nested request objects

### Lighthouse JSON

Signals:
- `lighthouseVersion`
- `requestedUrl`
- `finalUrl`
- `fetchTime`
- `audits`
- `categories`

### HAR

Signals:
- top-level `log`
- `log.entries`
- `log.pages`

## Step 4: Header Normalization and Schema Registry Entry

For each column, create a `schema_registry` entry using the following structure:

```json
{
  "original_field": "",
  "normalized_field": "",
  "source_file": "",
  "semantic_family": "",
  "datatype": "",
  "metric_family": "",
  "source_of_truth_role": "primary | supplementary | integrated_connector | conflict_resolved_by_[rule]",
  "aliases": [],
  "caveats": [],
  "mapping_utilization_status": "used_in_metric | used_in_join | profiled_only | potentially_relevant_unassigned | duplicate_of_preferred_field | intentionally_excluded | not_applicable",
  "mapping_notes": "",
  "final_utilization_roles": [],
  "final_gap_status": null,
  "used_by": [],
  "exclusion_reason": null
}
```

Field definitions:
- `mapping_utilization_status`: Phase-1 assignment from Family D; set during Step 4 / Step 12; never includes `used_in_finding` or `unmapped_relevant_field`, which are Post-Diagnosis values only
- `mapping_notes`: optional notes on the mapping logic; mandatory when `mapping_utilization_status` = `duplicate_of_preferred_field` (state the preferred field)
- `final_utilization_roles`: array populated after Orchestrator Phase 3; records all actual uses: `used_in_metric`, `used_in_join`, `used_in_finding`; a field may appear in multiple roles simultaneously
- `final_gap_status`: set during Post-Diagnosis Final Utilization Check; `unmapped_relevant_field` if a `potentially_relevant_unassigned` field was never used; `null` otherwise
- `used_by`: array of references; populated when the field is used; each entry is `{"type": "metric | finding | join", "id": "[metric_id or issue_id or join_id]"}`
- `exclusion_reason`: plain-language reason if `mapping_utilization_status` = `intentionally_excluded`; `null` otherwise

Field Utilization Rule: every field with `final_gap_status` = `unmapped_relevant_field` after the Post-Diagnosis Final Utilization Check must be documented as a confirmed utilization gap. Do not silently leave relevant fields unmapped.

Normalization:
1. strip whitespace
2. remove BOM
3. lowercase
4. replace spaces and punctuation with `_`
5. collapse repeated underscores
6. remove leading/trailing underscores

Examples:
- `Status Code` → `status_code`
- `Traffic ` → `traffic`
- `GA4 Engaged sessions` → `ga4_engaged_sessions`
- `CrUX Interaction to Next Paint (ms)` → `crux_interaction_to_next_paint_ms`

## Step 5: Canonical Field Mapping

Map fields into canonical families.

### URL

| Canonical Field | Aliases |
|---|---|
| `page_url` | `Address`, `Page`, `Landing page`, `URL` |
| `target_url` | `Target URL` |
| `source_url` | `Referring page URL`, `Source URL` |
| `request_url` | `full_url`, `url` in request tables |
| `document_url` | `documentURL`, `doc_url` |
| `final_url` | `finalUrl`, `finalDisplayedUrl`, `mainDocumentUrl` |
| `canonical_url` | `Canonical Link Element 1`, `Google-Selected Canonical` |

### Crawl / Indexability

| Canonical Field | Aliases |
|---|---|
| `status_code` | `Status Code`, `responseCode`, `Referring page HTTP code` |
| `status_text` | `Status` |
| `indexability` | `Indexability` |
| `indexability_status` | `Indexability Status` |
| `meta_robots` | `Meta Robots 1` |
| `x_robots_tag` | `X-Robots-Tag 1` |

### Metadata / Content

| Canonical Field | Aliases |
|---|---|
| `title` | `Title 1` |
| `title_length` | `Title 1 Length` |
| `meta_description` | `Meta Description 1` |
| `meta_description_length` | `Meta Description 1 Length` |
| `h1` | `H1-1` |
| `h2` | `H2-1` |
| `word_count` | `Word Count` |
| `readability` | `Readability`, `Flesch Reading Ease Score` |

### GSC

| Canonical Field | Aliases |
|---|---|
| `gsc_clicks` | `Clicks` |
| `gsc_impressions` | `Impressions` |
| `gsc_ctr` | `CTR` |
| `gsc_position` | `Position` |
| `query` | `Query`, `Search Query`, `Top queries`, `Suchanfragen` |
| `gsc_page` | `Page`, `Top pages`, `Seite`, `URL` |
| `gsc_date` | `Date`, `Datum` |
| `gsc_country` | `Country`, `Land` |
| `gsc_device` | `Device`, `Gerät` |
| `gsc_search_type` | `Search type` |

### GA4

| Canonical Field | Aliases |
|---|---|
| `ga4_landing_page` | `Landing page`, `Landing page + query string`, `Page path`, `Page path and screen class` |
| `ga4_page_title` | `Page title` |
| `ga4_sessions` | `GA4 Sessions`, `Sessions` |
| `ga4_views` | `GA4 Views`, `Views` |
| `ga4_engaged_sessions` | `GA4 Engaged sessions`, `Engaged sessions` |
| `ga4_engagement_rate` | `GA4 Engagement rate`, `Engagement rate` |
| `ga4_avg_engagement_time` | `Average engagement time`, `Average engagement time per session` |
| `ga4_key_events` | `GA4 Key events`, `Key events`, `Conversions` |
| `ga4_event_count` | `Event count` |
| `ga4_revenue` | `Revenue`, `Total revenue` |
| `ga4_total_users` | `GA4 Total users`, `Users`, `Total users`, `Active users` |
| `ga4_source_medium` | `Session source / medium`, `Source / medium` |
| `ga4_channel` | `Default channel group`, `Session default channel group` |

### Backlinks

| Canonical Field | Aliases |
|---|---|
| `referring_domain` | derived from `Referring page URL`, `Domain` |
| `referring_page_url` | `Referring page URL` |
| `target_url` | `Target URL` |
| `anchor_text` | `Anchor` |
| `domain_rating` | `Domain rating`, `DR` |
| `url_rating` | `UR` |
| `domain_traffic` | `Domain traffic`, `Traffic` |
| `is_spam` | `Is spam` |
| `nofollow` | `Nofollow` |
| `ugc` | `UGC` |
| `sponsored` | `Sponsored` |
| `first_seen` | `First seen` |
| `last_seen` | `Last seen` |
| `lost` | `Lost`, `Lost status` |

### Performance

| Canonical Field | Aliases |
|---|---|
| `ttfb_ms` | `TTFB`, `ttfb_ms`, `timeToFirstByte` |
| `fcp_ms` | `FCP`, `firstContentfulPaint`, `First Contentful Paint` |
| `lcp_ms` | `LCP`, `largestContentfulPaint`, `Largest Contentful Paint` |
| `tbt_ms` | `TBT`, `TotalBlockingTime`, `totalBlockingTime` |
| `cls` | `CLS`, `CumulativeLayoutShift`, `cumulativeLayoutShift` |
| `speed_index_ms` | `SpeedIndex`, `speedIndex` |
| `request_count` | derived from request rows |
| `transfer_bytes` | `bytesIn`, `transferSize` |
| `resource_type` | `request_type`, `req_type` |
| `mime_type` | `contentType`, `cnt_type` |
| `cache_control` | `cacheControl`, `c_ctrl` |
| `cdn_provider` | `cdn_provider`, `cdn` |
| `render_blocking` | `renderBlocking`, `is_blk`, `blk_type` |
| `cpu_time_ms` | `cpuTime`, `cpu_t` |

## Step 6: Source Scope and Freshness Detection

For every source, identify where possible:
- entity scope: domain, subdomain, path, URL list, page, query, request, backlink, referring domain
- date range
- export date / test date / crawl date
- file modification date if available
- export mode: crawl, list mode, sitemap crawl, UI export, connector export, report export
- filters: device, country, search type, channel, segment, first view/repeat view, run number
- aggregation level: URL, query, query+URL, date, country, device, landing page, event, request, domain
- source scope: domain/subdomain/path/exact URL for backlink and visibility files

If the source scope cannot be determined, mark it as `scope_unknown` and apply the following confidence reduction rule:

| Scope Status | Maximum Allowed Confidence |
|---|---|
| `scope_known` | high |
| `scope_partial` | medium |
| `scope_unknown` | medium (cap — cannot be high regardless of data quality) |
| `date_unknown` | medium (cap — age of data is unverifiable) |
| `scope_unknown` + `date_unknown` | low |

Document the scope limitation in the `file_inventory` and `analysis_readiness_report`. Do not suppress findings from scope-unknown sources; include them with the reduced confidence label.

Freshness expectations:
- WPT / Lighthouse / HAR: ideally ≤ 30 days for current-state performance diagnosis
- Screaming Frog: ideally ≤ 30–60 days for current technical diagnosis
- GSC / GA4: date range must be explicit
- Ahrefs: export date should be explicit; older exports can still support structural analysis

### Integrated Screaming Frog Connector Fields

When a Screaming Frog export contains connector-derived fields from GSC, GA4, PSI, CrUX or URL Inspection, treat these as equivalent to standalone source exports for coverage purposes.

Rules:
- Integrated GSC fields (`Clicks`, `Impressions`, `CTR`, `Position`) count as GSC coverage for that audit.
- Integrated GA4 fields (`GA4 Sessions`, `GA4 Views`, `GA4 Engaged sessions`, etc.) count as GA4 coverage.
- Integrated PSI/Lighthouse fields (`Performance Score`, `Largest Contentful Paint Time (ms)`, etc.) count as lab performance coverage at the page level.
- Integrated CrUX fields (`CrUX Largest Contentful Paint Time (ms)`, `CrUX Interaction to Next Paint (ms)`, etc.) count as field data coverage.
- Integrated URL Inspection fields (`URL Inspection API Status`, `Coverage`, `Google-Selected Canonical`) count as indexation/crawl coverage.

Document the integrated source origin in `schema_registry`:
- field `source_of_truth_role` = `integrated_connector`
- note the parent file and column name

Do not require a standalone GSC/GA4/PSI export to be present before treating these fields as valid evidence. Reduce no coverage score for their absence when integrated equivalents exist.

### Source of Truth Conflict Resolution

When both an integrated connector export (e.g., GSC fields inside Screaming Frog) and a standalone export (e.g., standalone GSC CSV) exist for the same source:

Priority order:
1. Standalone export with explicit date range and full field set — highest priority
2. Integrated connector fields with known connector configuration — second priority
3. Integrated connector fields with unknown configuration — lowest priority

Rules:
- If the standalone export has a wider date range or more rows, use it as the primary source.
- If the standalone export has a narrower scope but the same date range, use it to supplement.
- Never merge values from both sources for the same URL/query combination without documenting the merge logic.
- Document in `schema_registry`:
  - `source_of_truth_role: primary | supplementary | conflict_resolved_by_[rule]`
- If conflict cannot be resolved, use the standalone export and flag:

```text
Source conflict: [integrated field] vs. [standalone field] — standalone preferred by default.
```

### GSC Aggregation Level Rule

Before joining GSC data, determine aggregation level:
- **Query-level**: one row per query; no URL information — use for query analysis only
- **Page-level**: one row per URL — use for page-level joins with crawl data
- **Query+Page**: one row per query/URL combination — use for CTR opportunity analysis

Join rules:
- For URL joins (crawl ↔ GSC): use Page-level or Query+Page collapsed to Page-level.
- For query analysis: use Query-level or Query+Page.
- Never join Query-level GSC to crawl URLs and treat per-URL values as representative.
- If only Query+Page is available, deduplicate to Page-level before crawl join:
  `page_level = Query+Page grouped by URL, summing Clicks/Impressions, averaging Position`
- Document in `join_key_report`:

```text
GSC aggregation level used: [query | page | query+page | collapsed_from_query+page]
```

## Step 7: Column Profiling

For each relevant field:
- null count
- null rate
- distinct count
- sample values
- min/max for numeric values
- parse errors
- suspicious values
- whether it can be used as a join key
- whether it is required for any metric

Do not treat high null rate as an issue until field applicability is known.

## Step 8: Data Quality Checks

### Empty Cell Rule — Mandatory Pre-Check

Before treating any empty or null value as a finding, apply the following 5-condition checklist. All 5 conditions must be true for the empty cell to become a negative finding:

1. **Field is semantically required for this source type.** (e.g., `Title 1` is required on an HTML page; `Anchor` on a backlink row may legitimately be empty for image links)
2. **Row is applicable.** (e.g., the page is an HTML document, not a PDF, image or redirect target)
3. **Page type or entity type requires this value.** (e.g., meta description is required on indexable HTML landing pages; not on noindex or redirect pages)
4. **Metric definition requires this value.** (e.g., a duplicate-title analysis requires `Title 1` to be populated)
5. **Source is reliable enough for this conclusion.** (e.g., a truncated or filtered export may have systematically empty fields that are populated in the full export)

If any condition is not met, classify the empty cell as `observation_not_finding` and do not raise it as a data quality issue.

Examples:
- Empty `Meta Description` on a `noindex` page → condition 3 fails → `observation_not_finding`
- Empty `Anchor` where the link type is image → condition 1 fails → `observation_not_finding`
- Empty `GA4 Key events` → may be zero events, filtering, tracking gap or non-applicability → all 5 conditions must be verified before flagging

Perform source-appropriate checks.

### Generic
- duplicate rows
- duplicate entity keys
- malformed URLs
- mixed hostnames
- mixed protocols
- inconsistent trailing slash
- inconsistent query parameters
- invalid dates
- numeric parse failures
- percentage parse failures
- empty headers
- unexpected row counts
- truncated files
- stale exports
- multiple devices/countries/date ranges mixed unintentionally

### Screaming Frog
- duplicate `Address`
- missing `Status Code`
- missing `Indexability`
- non-URL values in `Address`
- inconsistent host/protocol
- unusually many empty metadata fields
- connector fields present but sparse
- crawl timestamp range if available

### GSC
- mixed date ranges
- mixed countries/devices
- page/query aggregation ambiguity
- missing query or page fields
- CTR/Position parse issues

### GA4
- landing page path vs full URL mismatch
- mixed date ranges
- missing conversion fields
- metric naming ambiguity
- sampled or filtered reports if indicated

### Ahrefs
- UTF-16/tab parsing issues
- trailing spaces in headers
- missing target URLs
- missing source URLs
- domain extraction failures
- lost link fields interpreted correctly
- boolean fields normalized

### WPT / Lighthouse / HAR
- test URL vs final URL mismatch
- lab run count
- first view vs repeat view distinction
- device/emulation context
- missing metrics
- request rows without host/type/timing
- sensitive headers/cookies in HAR

## Step 9: URL Normalization

Determine whether URL normalization is needed before producing `normalized_url_map`.

**When URL joins or URL-level reconciliation are needed:** produce `normalized_url_map` with full content (see below).

**When no URL joins or URL-level reconciliation are needed** (e.g., single-source audit, no cross-source URL matching required): produce a structured `not_applicable` record instead:

```json
{
  "artifact": "normalized_url_map",
  "artifact_status": "not_applicable",
  "reason": "[e.g., single source — no cross-source URL joins required]",
  "produced_by": "seo-data-foundation Step 9"
}
```

Do not omit the record entirely. If `normalized_url_map` is absent without a documented `not_applicable` record, diagnosis skills must treat this as a missing prerequisite.

**Full `normalized_url_map` content when produced:**

Default normalization:
- trim whitespace
- decode obvious entities only when safe
- lowercase hostname
- preserve path case unless project rule says otherwise
- remove fragment
- normalize default ports
- keep query parameters unless analysis requires queryless grouping
- create both `normalized_full_url` and `normalized_url_without_query`
- record trailing slash variant
- record canonical URL if available
- record final URL if available

Do not merge URLs destructively unless the chosen normalization mode is documented.

## Step 10: Joining Sources

Determine whether cross-source joins are possible before building `join_key_report`.

**When joins are possible** (multiple sources share a joinable key): produce `join_key_report` with full content (see below).

**When no cross-source joins are possible or required** (e.g., single-source audit, no overlapping join keys, all potential join partners are absent): produce a structured `not_applicable` record instead:

```json
{
  "artifact": "join_key_report",
  "artifact_status": "not_applicable",
  "reason": "[e.g., only one data source available — no cross-source joins possible]",
  "produced_by": "seo-data-foundation Step 10"
}
```

Do not omit the record entirely. If `join_key_report` is absent without a documented `not_applicable` record, diagnosis skills must treat this as a missing prerequisite for any join they attempt.

**Full `join_key_report` content when produced:**

Common joins:
- Screaming Frog `Address` ↔ GSC `Page`
- Screaming Frog `Address` ↔ GA4 landing page URL/path
- Screaming Frog `Address` ↔ Ahrefs `Target URL`
- Screaming Frog `Address` ↔ WPT/Lighthouse tested/final URL
- WPT Requests `documentURL` ↔ WPT JSON test URL
- HAR request URLs ↔ WPT Requests `full_url`

For each join:
- count left rows
- count right rows
- match count
- unmatched left
- unmatched right
- match rate
- duplicate keys
- join confidence

Never make strong cross-source claims if join coverage is poor.

## Step 11: Metric Coverage

Before calculating metrics, state coverage for each relevant metric using `metric_status` from Family B of the Status Taxonomy. `calculation_mode` is orthogonal to `metric_status`:
- `direct`: metric value is read directly from a source field without calculation
- `derived`: metric is calculated from one or more other fields

A `computable` metric may use `calculation_mode: derived`. A `partially_computable` metric may also use `calculation_mode: derived`. Do not treat `derived` as implying reduced computability.

Example (partially computable, derived — subset of rows):

```json
{
  "metric": "indexable_answer_page_rate",
  "metric_status": "partially_computable",
  "calculation_mode": "derived",
  "required_fields": ["page_url", "indexability", "status_code", "word_count"],
  "available_fields": ["Address", "Indexability", "Status Code", "Word Count"],
  "subset": "indexable HTML pages with word_count populated",
  "limitations": ["word_count missing for 12% of rows — excluded from rate calculation"]
}
```

Example (computable, derived — all rows available):

```json
{
  "metric": "non_indexable_200_rate",
  "metric_status": "computable",
  "calculation_mode": "derived",
  "required_fields": ["page_url", "status_code", "indexability"],
  "available_fields": ["Address", "Status Code", "Indexability"],
  "limitations": []
}
```

Example (not computable):

```json
{
  "metric": "backlink_anchor_distribution",
  "metric_status": "not_computable_from_current_sources",
  "required_fields": ["anchor_text"],
  "available_fields": [],
  "needed_source": "Ahrefs backlinks export with Anchor column"
}
```

Example (computable, direct):

```json
{
  "metric": "canonical_integrity_rate",
  "metric_status": "computable",
  "calculation_mode": "direct",
  "required_fields": ["page_url", "canonical_url", "status_code", "indexability"],
  "available_fields": ["Address", "Canonical Link Element 1", "Status Code", "Indexability"],
  "limitations": []
}
```

Do not use `status: derivable`, `partially_derivable`, or `out_of_scope`. Do not use unlisted `metric_status` values.

## Step 12: Phase-1 Source and Field Mapping Coverage Check

This step runs last in Data Foundation, immediately before producing the `analysis_readiness_report`. It checks whether sources and fields have been **assigned** to analysis purposes. It does not yet verify whether they were **actually used** — that is the Post-Diagnosis Final Utilization Check performed by the Orchestrator after Phase 3.

### Source-level mapping

For every source in `file_inventory` with `source_status` = `available` or `partially_available`, check whether the source has been assigned to analysis purposes. A source is considered assigned if at least one of its fields in `schema_registry` has `mapping_utilization_status` = `used_in_metric`, `used_in_join`, **or** `potentially_relevant_unassigned`. The question of whether the source was **actually used** is answered in the Post-Diagnosis Final Utilization Check, not here.

If a source has no assigned fields of any kind, flag as:

```text
Source unassigned: [source]
Required action: revisit field mapping for this source before issuing analysis_readiness_report.
```

Do not silently drop inventoried sources. Every source must have a documented mapping outcome. If a source is intentionally excluded, document the reason.

Record the Phase-1 outcome in `file_inventory` per source:
- `source_mapping_status`: one of `mapped | tentatively_mapped | unmapped | excluded | not_applicable`
  - `mapped`: at least one field has `used_in_metric` or `used_in_join`
  - `tentatively_mapped`: all assigned fields are `potentially_relevant_unassigned` (relevant but not yet tied to a specific metric or join)
  - `unmapped`: no fields assigned to any analysis purpose
  - `excluded`: source intentionally excluded; document reason
  - `not_applicable`: source is structural metadata, not analyzable content
- `mapped_to_areas`: list of analysis areas to which at least one field from this source was mapped (e.g., `["technical", "content"]`); may be provisional for `tentatively_mapped` sources
- `source_final_utilization_status`: leave `null` at Phase 1; set during Post-Diagnosis Final Utilization Check

### Field-level mapping

For every entry in `schema_registry`, confirm `mapping_utilization_status` has been assigned. This value represents the analytical intent at this point in the pipeline.

Apply the following rules:
- Field mapped to a metric → `mapping_utilization_status` = `used_in_metric`
- Field used as a join or normalization key → `mapping_utilization_status` = `used_in_join`
- Field recognized and profiled but no analytical use identified → `mapping_utilization_status` = `profiled_only`
- Field appears relevant but no clear metric or join mapping was found → `mapping_utilization_status` = `potentially_relevant_unassigned`; document:

```text
Mapping unresolved: [original_field] in [source_file] → potentially_relevant_unassigned.
Reason: [field recognized as possibly relevant but no metric or join mapping identified at this stage]
```

- Field is semantically equivalent to a preferred field already mapped → `mapping_utilization_status` = `duplicate_of_preferred_field`; record the preferred canonical field in `mapping_notes`. Do not map both; use the preferred field for all metrics and joins.
- Field is not relevant for this audit scope (e.g., belongs to a source only present for structural reasons, or is a column whose data category is out of scope for this audit) → `mapping_utilization_status` = `not_applicable`; record reason in `mapping_notes`.
- Field deliberately excluded for analytical reasons beyond the above → `mapping_utilization_status` = `intentionally_excluded`; record `exclusion_reason`

After completing this check, every `schema_registry` entry must have a non-null `mapping_utilization_status`. Fields still null at this step are errors, not gaps.

Do not set `final_utilization_roles`, `final_gap_status` or finding-related `used_by` entries in this step. These are Post-Diagnosis values only.

## Post-Diagnosis Final Utilization Check

Performed by the Orchestrator after Phase 3 (`issue_register` is complete). Updates `schema_registry` with actual utilization evidence.

### Field-level final utilization

For every field with `mapping_utilization_status` = `potentially_relevant_unassigned`:
- If the field appears in any finding's evidence or in any `used_by` reference → add `used_in_finding` to `final_utilization_roles`; set `final_gap_status` = `null`
- If the field was not referenced in any metric, join or finding → set `final_gap_status` = `unmapped_relevant_field`; document:

```text
Final utilization gap: [original_field] in [source_file] → unmapped_relevant_field.
Confirmed after full audit: field was available but not used in any metric, join or finding.
```

For all other fields:
- Populate `final_utilization_roles` to reflect all roles the field actually fulfilled (e.g., `["used_in_metric", "used_in_finding"]` if the field drove both)
- `final_gap_status` = `null` for all non-`potentially_relevant_unassigned` fields

After completing this check, every `schema_registry` entry must have non-null `mapping_utilization_status`. Fields with `final_gap_status` = `unmapped_relevant_field` are confirmed utilization gaps and must be listed in Section 12 of the final report under "Field Utilization Gaps".

### Source-level final utilization

After the field-level check is complete, update each source's `source_final_utilization_status` in `file_inventory`:

| `source_final_utilization_status` | Meaning |
|---|---|
| `used` | At least one field from this source appears in `final_utilization_roles` **and** no field from this source has `final_gap_status` = `unmapped_relevant_field` |
| `partially_used` | At least one field from this source appears in `final_utilization_roles` **and** at least one field from this source has `final_gap_status` = `unmapped_relevant_field` |
| `not_used` | No field from this source appears in any `final_utilization_roles` — constitutes a confirmed source utilization gap |
| `excluded` | Source was intentionally excluded; no final utilization check required |
| `not_applicable` | Source is structural metadata; not assessable |

**Precedence rule**: when determining the status, evaluate in this order and assign the first matching value:

1. `excluded` — if `source_mapping_status` = `excluded`
2. `not_applicable` — if `source_mapping_status` = `not_applicable`
3. `partially_used` — if ≥ 1 field is in `final_utilization_roles` AND ≥ 1 field has `final_gap_status` = `unmapped_relevant_field`
4. `used` — if ≥ 1 field is in `final_utilization_roles` AND no fields have `final_gap_status` = `unmapped_relevant_field`
5. `not_used` — otherwise

This means `partially_used` takes precedence over `used`. A source with one utilized field and one confirmed gap is always `partially_used`, never `used`.

Sources with `source_final_utilization_status` = `not_used` or `partially_used` that had `source_mapping_status` = `mapped` or `tentatively_mapped` must be documented as source utilization gaps in Section 12 of the final report alongside field gaps.

## Output

The result of this skill is not the final audit. It is the data foundation.

Produce:

```markdown
# Data Foundation Summary

## File Inventory
### Source Classification
## Schema Registry Summary
## Column Profiles
## Source Coverage
## Field Coverage
## Data Quality Issues
## URL Normalization Summary
## Join Key Report
## Metric Coverage
## Source and Field Mapping Coverage Check
## Analysis Readiness
```

## Readiness Labels

Use:
- `ready`
- `partially_ready`
- `blocked_missing_data`
- `blocked_low_quality_data`
- `not_relevant`

A full audit may proceed only for areas that are `ready` or `partially_ready`.

## analysis_readiness_report Schema

The `analysis_readiness_report` must be produced as a structured record per analysis area using the following schema:

```json
{
  "area": "",
  "readiness_label": "ready | partially_ready | blocked_missing_data | blocked_low_quality_data | not_relevant",
  "effective_readiness_label": "ready | partially_ready | blocked_missing_data | blocked_low_quality_data | not_relevant | blocked_late_discovery",
  "reason": "",
  "missing_data": [],
  "coverage_estimate_pct": null,
  "confidence_caps": [],
  "sub_area_readiness": [],
  "late_discoveries": []
}
```

Field definitions:
- `area`: one of `technical`, `content`, `backlinks`, `performance`, `geo`
- `readiness_label`: the label assigned by this skill at the end of Phase 1; **never modified after assignment**
- `effective_readiness_label`: the label used by `seo-scoring-recommendations` for scoring decisions; starts equal to `readiness_label`; updated exclusively by the Orchestrator's Late Discovery Decision Gate after Phase 2; may become `blocked_late_discovery` if an area that was `ready` or `partially_ready` is found to be effectively blocked during diagnosis
- `reason`: plain-language explanation of why this label was assigned
- `missing_data`: list of missing files, fields or joins that affect this area
- `coverage_estimate_pct`: estimated data coverage for this area (0–100); use `null` if not derivable
- `confidence_caps`: array of per-source or per-sub-area confidence cap entries; empty array if no caps apply; use `null` for the array only if `file_inventory` was not produced. Each entry:

```json
{
  "source_or_sub_area": "",
  "cap": "high | medium | low",
  "reason": "",
  "affected_findings": ""
}
```

  - `source_or_sub_area`: the source file ID (e.g., `F003`) or sub-area name (e.g., `hreflang`) the cap applies to
  - `cap`: the maximum allowed confidence for findings that depend exclusively on this source or sub-area
  - `reason`: the condition that triggered the cap (e.g., `scope_unknown`, `date_unknown`, `blocked_sub_area`)
  - `affected_findings`: plain-language description of which findings are capped (e.g., `"all hreflang findings"`, `"findings derived from F003 only"`)

  The cap applies **only** to findings that depend exclusively on the named source or sub-area. Findings from fully adequate sources in the same area retain their own confidence level. Do not apply the lowest entry as an area-wide cap.

- `sub_area_readiness`: array of sub-area readiness entries — see standard sub-area lists below; every sub-area in the standard list must be explicitly listed with its status; do not omit sub-areas to indicate they are ready; `effective_area_readiness_status` is updated by the Orchestrator when a Late Discovery names this sub-area in `affected_sub_areas` — see Late Discovery propagation rule in `seo-file-audit-orchestrator`
- `late_discoveries`: array of late-discovery entries appended by diagnosis skills; each entry uses this structure (matching the Late Amendment Rule format in the Orchestrator):

```json
{
  "skill": "",
  "source": "",
  "gap": "",
  "impact": "",
  "recommendation": "",
  "affected_sub_areas": []
}
```

`affected_sub_areas` is an optional list of sub-area names from the standard sub-area list. Use a list when the gap affects more than one sub-area (e.g., `["hreflang", "canonicalization"]`). Use `[]` when no specific sub-area can be identified or the gap is area-wide.

The `late_discoveries` array starts empty and is populated only if a diagnosis skill discovers a gap not documented in the original report. The original `readiness_label` and all other Phase 1 fields must not be overwritten; late discoveries are additive. Only `effective_readiness_label` (area-level) and `sub_area_readiness[].effective_area_readiness_status` (sub-area-level) may be updated after initial assignment, and only by the Orchestrator.

### Sub-area entry structure

Each entry in `sub_area_readiness` uses:

```json
{
  "sub_area": "",
  "area_readiness_status": "ready | partially_ready | blocked_missing_data | blocked_low_quality_data | not_relevant",
  "effective_area_readiness_status": "ready | partially_ready | blocked_missing_data | blocked_low_quality_data | not_relevant | blocked_late_discovery",
  "reason": ""
}
```

Field definitions:
- `area_readiness_status`: assigned by `seo-data-foundation` at Phase 1; **never modified after assignment**
- `effective_area_readiness_status`: starts equal to `area_readiness_status`; updated exclusively by the Orchestrator when a Late Discovery entry names this sub-area in `affected_sub_areas`; follows the same decision rules as the area-level `effective_readiness_label` (coverage reduction → no change; join failure → `partially_ready` if was `ready`; blocking quality issue → `blocked_late_discovery`)

### Standard sub-area lists per area

Every sub-area below must be explicitly listed in `sub_area_readiness`. Status `ready` is not assumed by omission. Sub-areas marked `not_relevant` are excluded from the area's coverage denominator.

Not every output section in a diagnosis skill is a sub-area. Some sections aggregate across sub-areas (`Joined SEO Impact`, `Key Findings`) or provide cross-cutting context (`Data Coverage`, `Score Inputs`). These are `output_only_section` entries — they are not assessed for readiness and do not contribute to coverage calculations. The lists below contain **only** assessable sub-areas.

**technical** (10 sub-areas):
`crawlability`, `indexability`, `status_code_health`, `canonicalization`, `redirect_handling`, `hreflang`, `structured_data`, `internal_linking`, `images`, `sitemap_quality`

Notes:
- `crawlability` and `indexability` are listed separately because they can be independently blocked. `crawlability` requires robots/depth/link data; `indexability` requires indexability fields and directives.
- `status_code_health` covers HTTP response code issues (4xx errors, 5xx errors, unexpected 200s) independently from redirect handling and crawlability. 4xx/5xx problems are not always redirect problems or crawl-budget problems; they warrant a distinct sub-area.

**content** (9 sub-areas):
`metadata_titles`, `metadata_descriptions`, `headings_structure`, `content_depth`, `duplicates_cannibalization`, `page_type_intent_fit`, `search_performance_opportunities`, `engagement_conversion`, `eeeat_signals`

**backlinks** (7 sub-areas):
`profile_overview`, `referring_domain_quality`, `anchor_distribution`, `target_url_distribution`, `lost_links_reclamation`, `spam_toxic_review`, `link_intersect`

Note: `joined_seo_impact` is an `output_only_section` — it reflects the join output across sub-areas, not a separate assessable sub-area.

**performance** (9 sub-areas):
`core_metrics`, `lcp_diagnosis`, `tbt_main_thread`, `cls_diagnosis`, `request_waterfall`, `third_parties`, `caching_compression`, `fonts`, `images`

**geo** (9 sub-areas):
`ai_crawler_accessibility`, `llms_txt`, `answer_fitness`, `citable_structure`, `entity_clarity`, `evidence_readiness`, `retrieval_context`, `content_architecture`, `multilingual_international_geo`

Note: `authority_corroboration` is covered as part of `evidence_readiness` and `citable_structure` in this model. `authority_and_external_corroboration` in the GEO skill's output is an `output_only_section` that draws from multiple sub-areas.

### Sub-area coverage weighting

Within each area, sub-areas receive **equal weight by default** for coverage calculation purposes. If `n` sub-areas are in scope (i.e., not `not_relevant`), each contributes `100/n` percent to the area's coverage score.

**Important**: Equal weighting is a readiness-coverage rule, not an SEO-importance rule. It determines how much of the area's planned analytical surface is covered. It does not imply that all sub-areas have equal SEO impact or business value. SEO importance is determined by the Cross-Area Priority Matrix and issue severity, not by sub-area count.

If a sub-area is `not_relevant`, it is excluded from the denominator before calculating the coverage share. If a sub-area is `blocked_missing_data` or `blocked_low_quality_data`, it counts as 0% covered within the area.

Sub-area weights may be explicitly overridden in `score_rationale` when the area structure justifies a different distribution. Document the override reason.
