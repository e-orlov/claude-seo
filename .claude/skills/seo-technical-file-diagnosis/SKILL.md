---
name: seo-technical-file-diagnosis
description: >
  Performs file-based technical SEO diagnosis from uploaded exports. Covers crawlability,
  indexability, status codes, redirects, canonicals, directives, internal links, hreflang,
  images and structured data. Uses only available files and reports missing data as coverage gaps.
user-invokable: true
argument-hint: "[data-foundation-artifacts]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# Technical SEO File Diagnosis

## Purpose

Diagnose technical SEO issues from the data-foundation artifacts (built from a live Screaming Frog MCP crawl and/or uploaded exports).

This skill covers:
- crawlability
- indexability
- status codes
- redirects
- canonicals
- robots directives
- sitemap evidence if available
- internal linking
- hreflang
- images
- structured data / schema
- technical signals relevant to GEO and performance when present in crawl data

## Datenbasis: DuckDB + Kontext-Artefakte

### Stufe 0 — Qdrant SEO-Wissen abrufen

Rufe vor der Diagnose relevantes SEO-Wissen aus Qdrant ab.

```
qdrant-find: "technical SEO crawlability indexability canonicals redirects directives"
qdrant-find: "robots meta noindex canonical hreflang structured data internal linking"
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
Technical SEO diagnosis blocked: seo-data-foundation artifacts not found in context.
Required: run seo-data-foundation first to produce file_inventory and analysis_readiness_report.
```

### Stufe 2 — DuckDB-Tabellen prüfen

Lies die relevanten Tabellennamen aus `file_inventory` (Feld `duckdb_table`).
Prüfe dann per SQL ob die Tabellen vorhanden sind:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'main'
  AND table_name IN (<relevante Tabellen aus file_inventory für technical>);
```

Typisch relevante Tabellen für Technical SEO:
`crawl_internal`, `crawl_redirects`, `crawl_canonicals`, `crawl_hreflang`,
`crawl_structured_data`, `crawl_images`, `crawl_inlinks`, `crawl_outlinks`,
`gsc_pages` (optional, für Traffic-Priorisierung)

Fehlende Tabellen → als Coverage Gap dokumentieren, nicht als harte Blockierung
(es sei denn, `crawl_internal` fehlt — dann ist kein technisches Audit möglich).

### Stufe 3 — analysis_readiness_report Pre-Check

Lies den Readiness-Status für `technical` aus dem Kontext-Artefakt:
- `ready`: vollständige Diagnose durchführen.
- `partially_ready`: Diagnose durchführen; limitierte Sub-Areas dokumentieren. Confidence-Cap `medium` nur für Findings, die ausschließlich von blockierten Sub-Areas oder Quellen mit `scope_unknown` abhängen.
- `blocked_missing_data` oder `blocked_low_quality_data`: keine Score-Ausgabe. Ausgabe:

```text
Technical SEO diagnosis blocked: [reason from analysis_readiness_report].
Required to unblock: [list from readiness report].
Coverage: [n]% — not scored.
```

- `not_relevant`: Bereich außerhalb des Audit-Scopes. Ausgabe:

```text
Technical SEO diagnosis skipped: area marked not_relevant in analysis_readiness_report.
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

Caps gelten per Quelle, nicht area-wide. Nur Findings, die von der gecappten Quelle abhängen, werden gecappt.

### Empty Cell Handling

Fehlende oder NULL-Werte in DuckDB-Feldern sind nicht automatisch SEO-Probleme.
Prüfe anhand der 5-Bedingungen aus `seo-data-foundation` Step 8, ob ein leeres Feld
ein echtes Problem ist oder nur eine Beobachtung.

### Joins

Falls `join_key_report` im Kontext vorhanden und Match-Rate ≥ 30%:
Joins sind verpflichtend für Priorisierung. SQL-Join gegen GSC/GA4-Tabellen:

```sql
SELECT c.address, c.status_code, c.indexability,
       g.clicks, g.impressions
FROM crawl_internal c
LEFT JOIN gsc_pages g ON lower(trim(c.address)) = lower(trim(g.page))
WHERE c.status_code = 200 AND c.indexability = 'Indexierbar';
```

Falls kein `join_key_report` oder Match-Rate < 30%: Join als Coverage Reduction dokumentieren.

### Metric Coverage

Falls `metric_coverage_report` im Kontext nicht vorhanden:
- Keine Metric-Completeness-Claims
- Keine coverage-basierten Score-Inputs
- Descriptive Mode dokumentieren:

```text
metric_coverage_report not available. Technical SEO diagnosis runs in descriptive mode.
```

## Joined Analysis Rule

When GSC, GA4 or backlink data is available and the join key report shows a match rate of ≥ 30%, joining is mandatory for prioritization of findings.

Do not treat joining as optional when join-eligible data exists. Use the joined data to rank and prioritize issues by search, traffic or link impact.

If a join is technically possible but was skipped, document this as a coverage reduction:

```text
Join [source A] ↔ [source B] was available but not performed.
Coverage reduction: priority ranking for [area] based on traffic/search impact is not possible.
```

If a mandatory join (match rate ≥ 30%) was available but skipped, additionally document this as a Late Discovery per the Late Amendment Rule in the Orchestrator.

If match rate is < 30%, joining may still be performed but must be flagged as low-coverage join. Do not derive strong cross-source claims from low-coverage joins.

**Rationale for 30% threshold:** below 30% match rate, cross-source claims risk being driven by the matched subset rather than the full population. At ≥30%, patterns in the joined set are suitable for prioritizing findings within the matched set; whether they represent the full unmatched population depends on the match selection mechanism. Exception: if the crawl was explicitly scoped to a curated URL list (e.g., top landing pages only), joins below 30% may still be informative — flag as `low-coverage join — targeted scope — interpret findings as sample, not population`.

## Minimum Data

Minimum useful source:
- Screaming Frog internal-like export with URL and at least status or indexability.

Enhanced sources:
- response codes
- canonicals
- directives
- hreflang export
- structured data export
- images export
- inlinks/outlinks export
- redirect chains
- crawl overview
- sitemap export
- GSC/GA4 connector fields inside Screaming Frog if present

If minimum data is missing, report:

```text
For the analysis of technical SEO, the required data basis is missing.
```

## Diagnosis Workflow

### 1. Scope Definition

Determine:
- total crawled URLs
- indexable HTML URLs
- non-indexable URLs
- status code distribution
- content type distribution
- host/protocol variants
- subdomains if present
- crawl depth distribution
- directory structure if derivable

### 2. Crawlability

Check if data exists for:
- robots.txt blocked URLs
- crawl depth
- orphan pages if available
- inlinks / unique inlinks
- outlinks
- crawl budget waste candidates
- non-HTML assets in crawl
- internal nofollow

Metrics:
- indexable URL count
- non-indexable URL count
- crawl depth buckets
- URLs with zero or low internal inlinks
- important URLs deeper than 3 clicks if crawl depth exists
- internal links to blocked/non-indexable URLs if fields exist

### 3. Indexability

Check:
- `Indexability`
- `Indexability Status`
- `Meta Robots`
- `X-Robots-Tag`
- `Canonical Link Element`
- HTTP status

Findings:
- 200 OK but non-indexable
- indexable URL with noindex directives contradiction
- canonicalized pages that still receive internal links
- canonical target missing, redirected, non-200 or non-indexable
- indexable pages with canonical mismatch
- duplicated or conflicting robots directives
- Google-selected canonical conflicts if URL Inspection fields exist

Do not infer Google indexation unless GSC URL Inspection data is available.

### 4. Status Code Health

Check:
- 4xx internal URLs (broken pages)
- 5xx URLs (server errors)
- non-200 internal URLs that are not intentional redirects
- backlink target URLs returning 4xx or 5xx if joined

Prioritize by:
- inlinks
- clicks/impressions if available
- GA4 sessions/conversions if available
- backlink equity flowing to broken URLs if joined

### 4b. Redirect Handling

Check:
- 3xx internal URLs
- redirect chains
- redirect loops
- mixed HTTP/HTTPS
- www/non-www variants
- internal links to redirects
- internal links to broken URLs

Prioritize by:
- indexable/internal HTML pages
- inlinks
- clicks/impressions if available

### 5. Canonicals

Check:
- missing canonical if expected
- canonical to different URL
- canonical to non-200 URL
- canonical to non-indexable URL
- canonical to redirected URL
- canonical conflicts with hreflang
- canonical conflicts with GSC selected canonical if available
- duplicate canonical targets

Do not treat missing self-canonical as automatically critical unless the project rules or CMS context make it required.

### 6. Hreflang

Use hreflang exports or hreflang fields if available.

Check:
- self-referencing hreflang
- return tags if full alternate set is available
- x-default if international setup is evident
- invalid language codes
- invalid region codes
- mixed protocols
- trailing slash mismatches
- hreflang URLs that are non-canonical
- hreflang URLs that return non-200
- hreflang URLs blocked/noindex
- inconsistent implementation sources: HTML vs sitemap vs HTTP header

If no hreflang data exists:
- do not mark as issue automatically.
- state not computable unless the site is known to be multilingual from URL/language data.

### 7. Images

Use image export, internal crawl fields or WPT request data if available.

Check:
- missing alt text
- empty alt text
- oversized images
- non-modern formats where relevant
- missing width/height if exported
- lazy-loaded above-the-fold/LCP image if evidence exists
- images causing transfer size issues
- image URLs returning non-200
- indexable pages with many image issues

Thresholds are heuristics:
- thumbnail target <50 KB
- content image target <100 KB
- hero image target <200 KB
- warning/critical thresholds depend on context and visual role

Do not classify an image as LCP-critical unless Lighthouse/WPT/page evidence supports that role.

### 8. Structured Data / Schema

Use structured data export or crawl fields.

Check:
- URLs with structured data
- structured data errors
- warnings
- rich result errors
- rich result warnings
- total types
- unique types
- schema types found
- schema coverage by page type if page types are derivable
- schema on non-indexable pages
- structured data errors on important pages

### 9. Sitemap Quality

Use sitemap exports, sitemap-derived crawl data, crawl overview or sitemap fields if available.

Check:
- sitemap URLs returning non-200 status codes
- sitemap URLs that redirect
- sitemap URLs marked non-indexable
- sitemap URLs with `noindex`
- sitemap URLs canonicalizing to another URL
- sitemap URLs blocked by robots.txt if such data is available
- HTTP/HTTPS inconsistencies
- hostname inconsistencies
- trailing slash inconsistencies
- important indexable URLs missing from sitemap if both crawl and sitemap data are available
- orphan or very low-inlink sitemap URLs if crawl/inlink data allows this

Do not penalize sitemap quality if no sitemap data is available. Mark sitemap analysis as `insufficient_data`.


If only Screaming Frog structured data summary is available:
- do not pretend property-level JSON-LD validation.
- limit conclusions to detected types, errors and warnings.

Rules:
- Do not recommend HowTo rich result markup as a Google rich-result opportunity.
- FAQ markup should be treated cautiously and only recommended where appropriate for current Google support and site type.
- Visible FAQ content can still be recommended even when FAQPage markup is not.

### 10. Internal Linking

If link data exists, check:
- orphan candidates
- low inlink important pages
- excessive crawl depth
- internal links to redirects
- internal links to 4xx/5xx
- non-descriptive anchors if anchor data exists
- important pages not linked from main hubs
- pages with high impressions/clicks but weak internal support

If link data is absent, mark internal linking as partially or not computable.

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
- technical health issue rate
- indexable page rate
- 200 indexable HTML rate
- non-indexable 200 URL count
- 4xx_error_rate (status_code_health sub-area)
- 5xx_error_rate (status_code_health sub-area)
- canonical integrity rate
- redirect waste rate
- broken internal link target count
- hreflang validity rate
- structured data error rate
- image issue rate
- internal support score if inlink + traffic data exists

Only compute metrics when required fields exist.

## Evidence

Each finding needs evidence:
- source file
- field names
- filters
- example URLs
- affected count
- joined traffic/search/link data if available
- confidence

Example evidence filter:

```text
source=Screaming Frog Internal
filter=Status Code=200 AND Indexability=Non-Indexable
fields=Address, Status Code, Indexability, Indexability Status, Canonical Link Element 1
```

## Output Structure

```markdown
## Technical SEO Diagnosis

### Data Coverage
### Technical Score Inputs
### Key Findings
### Crawlability
### Indexability
### Status Code Health
### Redirect Handling
### Canonicals and Directives
### Hreflang
### Images
### Structured Data
### Sitemap Quality
### Internal Linking
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
- `candidate_id`: prefix `RTECH` + three-digit number, e.g. `RTECH001`
- `what`: one sentence — what could be done
- `why`: one sentence — why the current state is harmful (linked to the finding)
- `affected_urls`: count or URL pattern
- `confidence`: high / medium / low
- `priority`: Kritisch / Hoch / Mittel / Niedrig — from Cross-Area Priority Matrix
- `evidence_ref`: reference to the finding/evidence section this candidate is based on

The Orchestrator assigns final `evidence_id` and `recommendation_id` in Phase 3.
Final recommendations with effort, validation method and definitive priority are produced
exclusively by `seo-scoring-recommendations` in Phase 4/5.
Section 10 of the final report is the single authoritative recommendation list.

If a potential action has no supporting evidence, do not include it as an action candidate.
Note it as an evidence-needed observation in the diagnosis section.
The Orchestrator decides in Phase 3 whether it becomes an `unverified_hypothesis` or
a `discarded_action_candidate`.

Do not recommend large migrations or canonical rewrites without strong data.

## robots.txt and noindex Rule

Never recommend `Disallow` in robots.txt and `noindex` simultaneously for the same URLs.

- `Disallow` blocks the crawler entirely — Googlebot cannot read the `noindex` tag on a blocked page.
- Use `Disallow` when the URL type should never be crawled (e.g. Ajax endpoints, session URLs, internal tool pages).
- Use `noindex` when the page should be crawled but excluded from the index (e.g. thank-you pages, parameter variants with canonical already set).
- Choose one mechanism per URL type. Document the choice and rationale in the recommendation.

## canonical and noindex Rule

Never describe `canonical + noindex` as "doubly secured" or a stronger signal. It is a configuration error.

- A canonical tag tells Google: "the canonical URL is the authoritative version — index that instead."
- A `noindex` tag tells Google: "do not index this URL."
- Together they send contradictory signals: index the canonical target, but also do not index this page. Google must choose one — behavior is undefined and inconsistent across crawls.
- The correct single mechanism depends on intent:
  - If the URL should not be indexed and a canonical target should be: use **canonical only**. The canonical consolidates signals to the target; noindex on the source is redundant and contradictory.
  - If the URL should simply not be indexed and there is no canonical target: use **noindex only**.
- When diagnosing URLs that carry both signals simultaneously, classify this as a **directive conflict** — a verified issue, not a double protection.
- Do not use "canonicalized + noindex" as a positive quality indicator. Flag it as an issue requiring cleanup.

## Issue Table Output Rule

Every issue table in this skill's output must include an **Evidenz** column as the last column.

Format for every evidence cell:
```
<issue_id> | <source_file> | <field or filter>
```

Example: `ITECH001 | internal_all.csv | Status Code=200, Indexability=Non-Indexable`

Never leave the Evidenz cell blank.

## Percentage and Baseline Rules

When reporting affected URL counts and percentages:
- Always state the absolute count AND the percentage in the same cell: `439 (34,2 % von 1.285 URLs)`
- The percentage must be exactly count ÷ baseline. Never use a different base for the percentage than for the count.
- Declare the baseline explicitly above or below every table that uses percentages, e.g.: *Basis: 1.285 indexierbare HTML-URLs mit Status 200*
- URLs with parameters (`?`) are a disjoint set from no-parameter URLs. Never express parameter URLs as a share of the no-parameter baseline or vice versa.
- Do not add explanatory comments like "140 % bedeutet …" — if the ratio seems unusual, fix the baseline.

## Cluster Naming Rule

In issue tables and recommendation candidates, name URL clusters by their URL pattern, not by individual URLs.

Correct: `index.php?page=`, `ajaxLoader.php?`, `/kategorie/`
Wrong: `index.php?page=18`, `ajaxLoader.php?context=artikel&method=checkLagerbestand`

Individual URLs may appear as examples in the evidence section, not in the cluster column.
