---
name: seo-performance-file-diagnosis
description: >
  Performs file-based performance diagnosis from uploaded WebPageTest, Lighthouse,
  HAR and request-level exports. Covers TTFB, LCP, TBT, CLS, request waterfalls,
  third parties, render-blocking resources, caching, fonts and images. No live tests.
user-invokable: true
argument-hint: "[data-foundation-artifacts]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# Performance File Diagnosis

## Datenbasis: DuckDB + Kontext-Artefakte

### Stufe 0 — Qdrant SEO-Wissen abrufen

Rufe vor der Diagnose relevantes SEO-Wissen aus Qdrant ab.

```
qdrant-find: "Core Web Vitals LCP CLS INP TTFB page speed performance"
qdrant-find: "render blocking resources third party scripts caching CDN fonts image optimization"
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
Performance diagnosis blocked: seo-data-foundation artifacts not found in context.
Required: run seo-data-foundation first to produce file_inventory and analysis_readiness_report.
```

### Stufe 2 — DuckDB-Tabellen prüfen

Lies die relevanten Tabellennamen aus `file_inventory` (Feld `duckdb_table`).
Prüfe per SQL:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'main'
  AND table_name IN (<relevante Tabellen aus file_inventory für performance>);
```

Typisch relevante Tabellen für Performance:
`wpt_requests`, `lighthouse`, `har`,
`crawl_internal` (optional, für URL-Join),
`gsc_pages` (optional, für Traffic-Kontext)

Mindest-Anforderung: mindestens eine Tabelle aus
`wpt_requests`, `lighthouse` oder `har`.

Performance-Daten sind typisch 1–10 URLs (kein großes Dataset).
Standard Match-Rate-Schwellwert (30%) gilt nur bei großen URL-Sets (z.B. PSI/CrUX Connector).
Bei 1–10 Test-URLs: URL-level Join per Exact Match, ohne Match-Rate-Anforderung.

### Stufe 3 — analysis_readiness_report Pre-Check

Lies den Readiness-Status für `performance` aus dem Kontext-Artefakt:
- `ready`: vollständige Diagnose.
- `partially_ready`: Diagnose mit dokumentierten Einschränkungen.
- `blocked_missing_data` oder `blocked_low_quality_data`:

```text
Performance diagnosis blocked: [reason from analysis_readiness_report].
Coverage: [n]% — not scored.
```

- `not_relevant`:

```text
Performance diagnosis skipped: area marked not_relevant in analysis_readiness_report.
```

### Source Scope und Confidence Cap

Aus `file_inventory`:

| Scope Status | Maximum Confidence |
|---|---|
| `scope_known` | high |
| `scope_partial` | medium |
| `scope_unknown` | medium |
| `date_unknown` | medium |
| `scope_unknown` + `date_unknown` | low |

### Joins (Performance-spezifisch)

Performance-Tests decken typisch 1–10 URLs ab. Join-Logik:

```sql
-- URL-level exact join (kein Match-Rate-Schwellwert nötig)
SELECT w.full_url, w.load_ms, w.ttfb_ms,
       c.status_code, c.indexability,
       g.clicks, g.impressions
FROM wpt_requests w
LEFT JOIN crawl_internal c ON lower(trim(w.full_url)) = lower(trim(c.address))
LEFT JOIN gsc_pages g ON lower(trim(w.full_url)) = lower(trim(g.page))
WHERE w.request_type = 'Document';
```

Falls keine Test-URL im Crawl gefunden:
```text
Crawl join not possible: tested URL(s) not found in crawl_internal.
Coverage reduction: performance findings cannot be contextualized by indexability or search impact.
```

### Metric Coverage

Falls `metric_coverage_report` nicht im Kontext:
```text
metric_coverage_report not available. Performance diagnosis runs in descriptive mode.
```

## Purpose

Diagnose page performance from the data-foundation artifacts built from uploaded WebPageTest/Lighthouse/HAR files.

Supported sources:
- WebPageTest JSON
- WebPageTest Requests CSV
- Lighthouse JSON
- Lighthouse CLI logs
- HAR files
- Screaming Frog PSI/CrUX/Lighthouse connector fields if present

No live PageSpeed, Lighthouse, WebPageTest, browser or API calls.

## Minimum Data

Minimum useful data:
- Lighthouse JSON with `audits` and `categories`
or
- WebPageTest JSON with `data.runs`
or
- WebPageTest Requests CSV with request timings
or
- HAR with request entries

If minimum data is missing, report:

```text
For the analysis of performance, the required data basis is missing.
```

Do not reduce SEO health score for missing performance files. Reduce coverage/confidence.

## Joined Analysis Rule

When Screaming Frog crawl or GSC data is available and tested URLs can be matched to crawl/search data, joining is mandatory for contextualizing performance findings.

Do not treat cross-source joining as optional when join-eligible data exists. Use joined data to show which tested pages have high organic traffic, missing indexability, or canonicalization issues that compound performance impact.

If a join is technically possible but was skipped, document this as a coverage reduction:

```text
Join [source A] ↔ [source B] was available but not performed.
Coverage reduction: performance findings cannot be contextualized by search or traffic impact.
```

If a mandatory join (match rate ≥ 30%) was available but skipped for a large URL set (e.g., PSI/CrUX connector fields in Screaming Frog covering many pages), additionally document this as a Late Discovery per the Late Amendment Rule in the Orchestrator.

### Performance-Specific Join Rule

Performance tests typically cover 1–10 URLs. Standard dataset-level match-rate thresholds do not apply.

Instead:
- If tested URLs can be matched to crawl/GSC data by exact URL or canonical URL, the join is mandatory regardless of overall dataset match rate.
- If no tested URL matches the crawl, document as:

```text
Crawl join not possible: tested URL(s) not found in crawl data.
Coverage reduction: performance findings cannot be contextualized by indexability or search impact.
```

- If 1 or more tested URLs match the crawl, perform the join and annotate results as:

```text
Partial join — [n] of [total tested] URLs matched in crawl data.
```

The 30% match-rate threshold applies only when performance data covers a large URL set (e.g., PSI/CrUX connector fields in Screaming Frog covering many pages). In those cases, joins below 30% may still be performed but must be flagged as a low-coverage join. For standard performance tests (1–10 URLs), the Performance-Specific Join Rule above applies exclusively. Do not apply the 30% dataset threshold to single-URL or small-URL-set performance tests.

## Critical Distinction

Separate:
- Lab data from Lighthouse/WebPageTest/HAR
- Field data from CrUX/PSI/GSC if present

Do not call lab results "real user data."

If CrUX fields are present in Screaming Frog or PSI export:
- label them as field data proxy
- record source and URL/origin level
- distinguish page-level and origin-level if available

## Diagnosis Workflow

### 1. Test Context

Extract:
- tested URL
- final URL
- fetch time / test date
- device/emulation
- browser
- location if available
- connection profile
- CPU slowdown
- first view vs repeat view
- number of runs
- median run selection
- Lighthouse version if present
- WebPageTest test ID if present

Do not compare tests if conditions differ unless normalized.

### 2. Core Metrics

Extract where available:
- TTFB
- FCP
- LCP
- CLS
- TBT
- Speed Index
- render start
- fully loaded
- document complete
- request count
- transfer size
- total bytes
- main-thread/CPU metrics if available

Use conventional thresholds as heuristics:
- LCP good ≤ 2.5s
- INP field data good ≤ 200ms when available
- CLS good ≤ 0.1
- TTFB target < 800ms as diagnostic heuristic
- TBT lower is better in lab; high TBT suggests main-thread blocking

If INP is not present, do not infer it from TBT. State INP unavailable.

### 3. LCP Diagnosis

Use available data:
- Lighthouse LCP audit
- LCP element details if present
- WPT visual timing
- request waterfall
- image/font/CSS/JS timing
- render start vs LCP
- TTFB contribution
- resource load delay
- resource load time
- element render delay if Lighthouse subparts exist
- critical request chain

Classify likely LCP bottleneck:
- server / TTFB
- render-blocking CSS
- render-blocking JS
- delayed LCP resource discovery
- slow LCP resource download
- font delay / FOIT
- client-side rendering
- third-party blocking
- consent/CMP/banner
- large hero image
- element render delay

Only assert LCP element if available in Lighthouse/WPT evidence.

### 4. TBT / Main Thread

Use:
- Lighthouse TBT
- script treemap if available
- request CPU fields
- WPT `cpuTime`, `cpu_t`, `cpu.EvaluateScript`, `cpu.FunctionCall`
- third-party scripts
- long tasks if present

Identify:
- heavy third-party JS
- A/B testing / personalization scripts
- tag managers
- consent management
- webfont loaders
- unused JS opportunities
- render-blocking scripts
- expensive hydration if framework evidence exists

Do not claim INP failure without field INP data.

### 5. CLS

Use:
- Lighthouse CLS
- WPT CLS
- layout shift details if available
- image dimension fields if available
- font loading evidence
- ad/embed/iframe evidence

Find:
- missing image dimensions if exported
- late injected banners
- font swaps causing shift
- embeds/iframes without reserved space

### 6. Request Waterfall

Use WPT Requests CSV, WPT JSON requests or HAR.

Analyze:
- total requests
- total transfer
- requests by resource type
- transfer by resource type
- third-party hosts
- slowest requests by total time
- slowest TTFB
- largest resources
- render-blocking resources
- critical request chain
- DNS/connect/SSL overhead
- protocol usage HTTP/2/HTTP/3
- CDN provider
- cacheability
- compression
- duplicate resources
- fonts
- image sizes and formats
- scripts with high CPU time
- CSS blocking

### 7. Third Parties

Group by host/domain:
- request count
- bytes
- total blocking or CPU time if available
- render-blocking status
- timing before LCP
- purpose if inferable from host

Common categories:
- analytics
- tag manager
- consent management
- A/B testing / personalization
- fonts
- CDN assets
- chat widgets
- advertising
- social embeds
- maps/video

Avoid moralizing third parties; recommend defer/condition/self-host/remove only with evidence.

### 8. Caching and Compression

Use headers/fields:
- `cacheControl`
- `expires`
- `cache_time`
- `score_cache`
- `contentEncoding`
- `score_gzip`
- `objectSize`
- `objectSizeUncompressed`

Find:
- static assets with short or missing cache lifetime
- uncompressed text resources
- large uncompressed responses
- immutable assets with good caching
- HTML cache caveats

### 9. Fonts

Use requests:
- Google Fonts CSS
- font files
- webfont loaders
- preload evidence if available
- font-display if Lighthouse details or CSS text available

Find:
- external font CSS blocking
- multiple font families/weights
- late font discovery
- render-blocking webfont loader
- missing preload for critical font if evidence supports it
- excessive preloads if causing contention

Do not recommend preloading all fonts. Recommend only proven critical fonts.

### 10. Images

Use request data, Lighthouse image audits and crawl image data:
- large images
- non-modern formats
- missing responsive sizes if available
- LCP image optimization
- lazy-loaded LCP image if evidence exists
- offscreen images loaded early
- AVIF/WebP opportunities
- intrinsic dimensions/CLS if available

## Non-Computable Metric Reporting

For every metric that cannot be computed, state this explicitly in the output using the standard format:

```text
Metric: [metric name]
Status: not_computable_from_current_sources
Reason: [missing field / missing source / lab vs field distinction / insufficient test runs]
Required for computation: [field or source name]
```

Allowed status values:
- `not_computable_from_current_sources` — required data was not uploaded
- `insufficient_data` — data exists but insufficient runs or URLs for a reliable result
- `partially_computable` — metric can be computed for a subset of pages/runs; state the subset
- `rule_incomplete` — metric requires test context not available (e.g., device type unknown)
- `unreliable` — data exists but test conditions prevent reliable conclusion
- `field_data_only` — metric requires field data (CrUX/RUM) which was not uploaded; lab proxy is available but not equivalent

Do not silently skip a metric. Every metric listed under "Possible metrics" that is not computed must appear in the "Non-Computable Metrics" output section with its status and reason.

## Metrics

Possible metrics:
- performance lab score
- LCP status
- TTFB status
- TBT status
- CLS status
- total requests
- total transfer bytes
- third-party request share
- third-party byte share
- render-blocking request count
- JS transfer bytes
- CSS transfer bytes
- image transfer bytes
- font transfer bytes
- uncached static asset count
- slow request count
- high-CPU script count
- performance coverage score

Only compute where data exists.

## Output Structure

```markdown
## Performance Diagnosis

### Data Coverage
### Test Context
### Performance Score Inputs
### Core Metrics
### LCP Diagnosis
### TBT / Main Thread Diagnosis
### CLS Diagnosis
### Request Waterfall
### Third Parties
### Caching and Compression
### Fonts
### Images
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
- `candidate_id`: prefix `RPERF` + three-digit number, e.g. `RPERF001`
- `what`: one sentence — what could be done
- `why`: one sentence — why the current state is harmful (linked to the finding)
- `affected_scope`: tested URL, resource type or host pattern
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
<issue_id> | <source_file> | <metric or resource>
```

Never leave the Evidenz cell blank.

## Percentage and Baseline Rules

When reporting counts and percentages:
- Always state count AND percentage together: `12 (40,0 % von 30 Requests)`
- The percentage must be exactly count ÷ baseline. State the baseline explicitly above the table.
- Do not add explanatory percentage comments — fix the baseline instead.

## Recommendation Examples

Low Hanging Fruit:
- Defer or delay non-critical third-party scripts before LCP.
- Fix cache headers for static assets.
- Remove duplicate font or script requests.
- Optimize proven LCP image.

Mid Term:
- Split/defer heavy JS bundles.
- Refactor render-blocking CSS.
- Improve font loading strategy.
- Reduce third-party dependency cost.

Long Term / Strategic:
- Rework template architecture causing client-side rendering delay.
- Replace heavy personalization/tag stack.
- Build performance budget and regression testing process.

## Evidence Requirements

Every finding must include:
- source file
- metric values
- request URLs or hosts when applicable
- test context
- affected resource type
- timing/bytes/CPU values
- confidence

## HAR Sensitivity

HAR files may contain cookies, authorization headers, query strings and personal data.

Do not quote sensitive values. Redact:
- cookies
- authorization headers
- API keys
- session IDs
- personal identifiers
