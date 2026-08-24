---
name: seo-content-file-diagnosis
description: >
  Performs file-based content SEO diagnosis from uploaded crawl, GSC, GA4 and
  related exports. Covers metadata, headings, content depth, duplicates, page type,
  search demand, E-E-A-T evidence and content opportunities. No live SERP/API use.
user-invokable: true
argument-hint: "[data-foundation-artifacts]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# Content SEO File Diagnosis

## Purpose

Diagnose content SEO issues and opportunities from uploaded files only.

This skill covers:
- title tags
- meta descriptions
- H1/H2 headings
- content depth / word count
- readability if available
- duplicate and near-duplicate signals
- search demand and performance if GSC data exists
- engagement and conversion if GA4 data exists
- page type fit if derivable
- E-E-A-T evidence where supported by data
- content opportunities from query/page data

## Datenbasis: DuckDB + Kontext-Artefakte

### Stufe 0 — Qdrant SEO-Wissen abrufen

Rufe vor der Diagnose relevantes SEO-Wissen aus Qdrant ab.

```
qdrant-find: "content SEO title meta description H1 duplicate content word count"
qdrant-find: "E-E-A-T content quality search intent keyword optimization GSC"
```

Verwende die abgerufenen Ergebnisse als Hintergrundwissen für:
- Schwellenwerte und Best Practices bei der Befundinterpretation
- Begründung von Handlungsempfehlungen
- Einordnung von Findings in übergeordnete SEO-Prinzipien

Die Abfragen werden immer ausgeführt — unabhängig davon, ob der Nutzer explizit danach fragt.

### Stufe 1 — Kontext-Artefakte prüfen

Prüfe ob im aktuellen Kontext vorhanden:
- `file_inventory` (mit `duckdb_table`-Feld je Quelle) — produziert von `seo-data-foundation`
- `analysis_readiness_report` — produziert von `seo-data-foundation`

Falls nicht vorhanden:
```text
Content diagnosis blocked: seo-data-foundation artifacts not found in context.
Required: run seo-data-foundation first to produce file_inventory and analysis_readiness_report.
```

### Stufe 2 — DuckDB-Tabellen prüfen

Lies die relevanten Tabellennamen aus `file_inventory` (Feld `duckdb_table`).
Prüfe per SQL:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'main'
  AND table_name IN (<relevante Tabellen aus file_inventory für content>);
```

Typisch relevante Tabellen für Content:
`crawl_internal`, `crawl_titles`, `crawl_meta_desc`, `crawl_h1`,
`crawl_near_dupes`, `crawl_exact_dupes`,
`gsc_pages`, `gsc_queries` (optional),
`ga4_landing_pages` (optional)

Fehlende Tabellen → als Coverage Gap dokumentieren.
Wenn `crawl_internal` fehlt und kein anderes Crawl-Export → Content-Diagnose nicht möglich.

### Stufe 3 — analysis_readiness_report Pre-Check

Lies den Readiness-Status für `content` aus dem Kontext-Artefakt:
- `ready`: vollständige Diagnose durchführen.
- `partially_ready`: Diagnose durchführen; limitierte Sub-Areas dokumentieren.
- `blocked_missing_data` oder `blocked_low_quality_data`: keine Score-Ausgabe.

```text
Content diagnosis blocked: [reason from analysis_readiness_report].
Required to unblock: [list from readiness report].
Coverage: [n]% — not scored.
```

- `not_relevant`:

```text
Content diagnosis skipped: area marked not_relevant in analysis_readiness_report.
```

### Source Scope und Confidence Cap

Aus `file_inventory`: wenn eine Quelle `scope_unknown` oder `date_unknown` ist:

| Scope Status | Maximum Confidence |
|---|---|
| `scope_known` | high |
| `scope_partial` | medium |
| `scope_unknown` | medium |
| `date_unknown` | medium |
| `scope_unknown` + `date_unknown` | low |

### Empty Cell Handling

NULL-Werte in DuckDB-Feldern sind nicht automatisch SEO-Probleme.
Prüfe anhand der 5-Bedingungen aus `seo-data-foundation` Step 8.

### Joins

Falls `join_key_report` im Kontext vorhanden und Match-Rate ≥ 30%: Joins verpflichtend.

```sql
SELECT c.address, c."Titel 1", c."Meta Description 1",
       g.clicks, g.impressions, g.position
FROM crawl_internal c
LEFT JOIN gsc_pages g ON lower(trim(c.address)) = lower(trim(g.page))
WHERE c.status_code = 200 AND c.indexability = 'Indexierbar';
```

Falls kein `join_key_report` oder Match-Rate < 30%: als Coverage Reduction dokumentieren.

### Metric Coverage

Falls `metric_coverage_report` nicht im Kontext:
```text
metric_coverage_report not available. Content diagnosis runs in descriptive mode.
```

## Minimum Data

Minimum useful data:
- URL list with at least one of title, meta description, headings, word count or text/content fields.

If minimum data is missing, report:

```text
For the analysis of content, the required data basis is missing.
```

## Joined Analysis Rule

When GSC or GA4 data is available and the join key report shows a match rate of ≥ 30%, joining is mandatory for prioritization.

Do not treat joining as optional when join-eligible data exists. Use joined data to rank metadata, content depth, and opportunity findings by impression, click, session or conversion impact.

If a join is technically possible but was skipped, document this as a coverage reduction:

```text
Join [source A] ↔ [source B] was available but not performed.
Coverage reduction: priority ranking for content findings based on search/traffic impact is not possible.
```

If a mandatory join (match rate ≥ 30%) was available but skipped, additionally document this as a Late Discovery per the Late Amendment Rule in the Orchestrator.

If match rate is < 30%, joining may still be performed but must be flagged as low-coverage join. Do not derive strong cross-source claims from low-coverage joins.

**Rationale for 30% threshold:** below 30% match rate, cross-source claims risk being driven by the matched subset rather than the full population. At ≥30%, patterns in the joined set are suitable for prioritizing findings within the matched set; whether they represent the full unmatched population depends on the match selection mechanism. Exception: if the crawl was explicitly scoped to a curated URL list (e.g., top landing pages only), joins below 30% may still be informative — flag as `low-coverage join — targeted scope — interpret findings as sample, not population`.

Enhanced sources for joining and enrichment:
- GSC query/page exports or integrated Screaming Frog GSC fields
- GA4 engagement/conversion exports or integrated fields
- duplicate/near-duplicate fields
- readability fields
- page type or template information
- content extracts, if uploaded

## Important Rules

- Word count thresholds are coverage heuristics, not direct ranking-factor claims.
- Empty metadata fields are issues only when the row is an applicable indexable page.
- Do not infer search intent without query/SERP/page-type evidence.
- Do not infer E-E-A-T quality from metadata alone.
- Do not claim conversions or business value without GA4/conversion data.
- Do not punish missing GSC/GA4 data; reduce coverage/confidence.

## Diagnosis Workflow

### 1. Scope Definition

Determine:
- indexable content URLs
- HTML pages
- page templates/directories if derivable
- pages with search data
- pages with GA4 data
- pages with duplicate/near-duplicate data
- pages with content metrics

### 2a. Metadata — Titles

Analyze applicable indexable HTML pages.

Title checks:
- missing title
- duplicate title
- too short / too long as heuristic
- title not unique
- title mismatch with H1 if data exists
- important pages with weak titles based on GSC opportunity

Assess `metadata_titles` sub-area readiness separately from meta descriptions.

### 2b. Metadata — Meta Descriptions

Meta description checks:
- missing meta description
- duplicate meta description
- too short / too long as heuristic
- important pages lacking description
- descriptions on non-indexable pages should not be over-prioritized

Assess `metadata_descriptions` sub-area readiness separately from titles.

Length heuristics for reproducible audits:

Title:
- `<30 characters`: likely too short / underdescriptive
- `30–60 characters`: usually acceptable
- `>60 characters`: truncation or dilution risk

Meta description:
- `<70 characters`: likely too short
- `70–160 characters`: usually acceptable
- `>160 characters`: truncation risk

Treat these as SERP-snippet and clarity heuristics, not hard ranking factors. Prioritize length issues by indexability, GSC impressions/clicks, page importance and duplication.

Prioritize using:
- GSC impressions/clicks
- GA4 sessions/conversions
- indexability
- crawl depth
- inlinks
- business page type if known

### 3. Headings and Structure

Check:
- missing H1
- multiple H1s
- duplicate H1s
- H1/title mismatch where meaningful
- missing H2 structure on long pages
- heading hierarchy issues if levels are available
- question-based headings for GEO if relevant
- thin heading structure on high-impression pages

Do not overstate multiple H1 as critical if HTML5/component context is unknown; prioritize by actual page importance.

### 4. Content Depth and Coverage

Use word count, sentence count, text ratio and readability if present.

Heuristic floors by page type:
- Homepage: 500 words
- Service / feature page: 800 words
- Blog post: 1,500 words
- Product page: 300-400+ words depending complexity
- Category page: 400 words
- Location page: 500-600 words
- FAQ page: 800 words

Treat these as topical coverage floors, not rigid ranking targets.

Find:
- thin important indexable pages
- pages with high impressions but low content depth
- pages with traffic but weak structure
- pages with low text ratio
- pages where content depth is not computable

### 5. Duplicates and Near-Duplicates

If duplicate fields exist, analyze:
- exact duplicate titles
- exact duplicate meta descriptions
- duplicate H1
- duplicate content hash
- near-duplicate similarity
- canonical handling of duplicates
- duplicate pages receiving impressions/clicks
- duplicate pages indexable without consolidation

If only metadata duplicates exist, do not claim body-content duplication.

### 6. Search Performance Opportunities

If GSC exists:
- pages with high impressions and low CTR
- pages with average position 4-15 and strong impression volume
- queries with high impressions and low CTR
- pages with many queries but weak metadata
- query cannibalization candidates if multiple URLs rank for same query
- pages losing clicks if date comparison exists
- low-click pages with strong impressions
- zero-click pages with crawl/indexability issues

Do not compare periods unless date data supports it.

### 7. GA4 Engagement and Conversion

If GA4 exists:
- landing pages with sessions but low engagement
- high-traffic pages with low conversion/key events
- SEO pages with engagement problems
- pages with organic search performance but poor engagement if source/medium is available
- conversion impact prioritization

Do not infer channel-specific SEO impact if GA4 export is not filtered or does not include channel/source.

### 8. Page Type and Intent Fit

If enough evidence exists:
- classify pages by URL pattern, metadata, headings, schema and content fields
- identify page type mismatch
- identify informational queries leading to commercial pages
- identify commercial queries leading to informational pages
- identify pages lacking required elements for their type

Page type examples:
- homepage
- service page
- product page
- category page
- blog post
- location page
- comparison page
- tool / interactive page
- hybrid service + content

If no SERP or query evidence exists, label intent findings as lower confidence.

### 9. E-E-A-T Evidence

Assess only what data supports:
- author/byline fields if present
- dates if present
- schema Person/Organization/Article if present
- external references if content extracts exist
- original data/case-study indicators if content fields exist
- trust pages if crawl contains contact/privacy/about URLs
- reviews/testimonials if crawl/content data supports it

Do not claim E-E-A-T failure solely from missing author data unless page type/topic requires it and data confirms absence.

### 10. Content Opportunity Register

Create opportunities:
- metadata improvement
- content expansion
- consolidation/canonicalization
- content refresh
- query intent alignment
- internal linking to high-opportunity pages
- GEO/citability formatting
- E-E-A-T trust signal additions

## Non-Computable Metric Reporting

For every metric that cannot be computed, state this explicitly in the output using the standard format:

```text
Metric: [metric name]
Status: not_computable_from_current_sources
Reason: [missing field / missing source / insufficient rows / low join coverage]
Required for computation: [field or source name]
```

Allowed status values:
- `not_computable_from_current_sources` — required data was not uploaded
- `insufficient_data` — data exists but volume or coverage is too low for a reliable result
- `partially_computable` — metric can be computed for a subset of pages only; state the subset
- `rule_incomplete` — metric definition requires context not available (e.g., page type classification needed)
- `unreliable` — data exists but quality checks indicate it cannot be trusted for this metric

Do not silently skip a metric. Every metric listed under "Possible metrics" that is not computed must appear in the "Non-Computable Metrics" output section.

## Metrics

Possible metrics:
- title coverage rate
- meta description coverage rate
- duplicate title rate
- duplicate meta description rate
- H1 coverage rate
- thin indexable page rate
- content opportunity count
- high-impression low-CTR URL count
- striking-distance query/page count
- metadata opportunity weighted by impressions
- content score by template/directory
- content confidence by data source coverage

Only compute metrics when fields exist.

## Output Structure

```markdown
## Content Diagnosis

### Data Coverage
### Content Score Inputs
### Key Findings
### Metadata
### Headings and Structure
### Content Depth
### Duplicates and Cannibalization
### Search Performance Opportunities
### Engagement / Conversion Signals
### Page Type and Intent Fit
### E-E-A-T Evidence
### Recommendation Candidates
#### Low Hanging Fruit
#### Mid Term
#### Long Term / Strategic
### Non-Computable Metrics
### Evidence
```

## Recommendation Candidates Rule

This skill produces **action candidates**, not final recommendations.

Each action candidate must include:
- `candidate_id`: prefix `RCONT` + three-digit number, e.g. `RCONT001`
- `what`: one sentence — what could be done
- `why`: one sentence — why the current state is harmful (linked to the finding)
- `affected_urls`: count or URL pattern
- `confidence`: high / medium / low
- `priority`: Kritisch / Hoch / Mittel / Niedrig — from Cross-Area Priority Matrix
- `evidence_ref`: reference to the finding/evidence section this candidate is based on

The Orchestrator assigns final `evidence_id` and `recommendation_id` in Phase 3.
Final recommendations are produced exclusively by `seo-scoring-recommendations` in Phase 4/5.
Section 10 of the final report is the single authoritative recommendation list.

If a potential action has no supporting evidence, do not include it as an action candidate.
The Orchestrator decides in Phase 3 whether it becomes an `unverified_hypothesis` or
a `discarded_action_candidate`.

## Issue Table Output Rule

Every issue table in this skill's output must include an **Evidenz** column as the last column.

Format for every evidence cell:
```
<issue_id> | <source_file> | <field or filter>
```

Never leave the Evidenz cell blank.

## Percentage and Baseline Rules

When reporting affected URL counts and percentages:
- Always state count AND percentage together: `385 (85,2 % von 452 URLs)`
- The percentage must be exactly count ÷ baseline.
- Declare the baseline explicitly above every table that uses percentages.
- URLs with parameters (`?`) are a disjoint set from no-parameter URLs — never mix bases.
- Do not add explanatory percentage comments — fix the baseline instead.

## Cluster Naming Rule

In issue tables and recommendation candidates, name URL clusters by their URL pattern.

Correct: `/weihnachtskarten/`, `/kategorie/`
Wrong: individual exact URLs in the cluster column.

## Recommendation Examples

Low Hanging Fruit:
- Rewrite duplicate or missing titles on high-impression indexable pages.
- Add missing meta descriptions to high-impression pages.
- Fix missing H1 on important indexable pages.

Mid Term:
- Expand thin service/category/location pages with unique, useful content.
- Consolidate near-duplicate indexable pages.
- Create missing content sections for important query clusters.

Long Term / Strategic:
- Build content architecture around query clusters.
- Establish author/entity/trust framework.
- Rework templates that systematically create thin or duplicate pages.

## Evidence Requirements

Every major finding must include:
- source file
- filter
- affected count
- examples
- joined GSC/GA4 values when used
- confidence
