---
name: seo-backlink-file-diagnosis
description: >
  Performs file-based backlink diagnosis from uploaded Ahrefs exports. Covers
  referring domains, backlink quality, anchors, target URLs, follow/nofollow/UGC/sponsored,
  lost links, spam indicators and link intersect opportunities. No API or live backlink lookup.
user-invokable: true
argument-hint: "[data-foundation-artifacts]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# Backlink File Diagnosis

## Purpose

Analyze backlink profile quality and opportunities from the data-foundation artifacts built from uploaded backlink files (Ahrefs exports).

This skill uses:
- Ahrefs backlinks exports
- Ahrefs referring domains exports
- Ahrefs anchors exports if provided
- Ahrefs link intersect exports
- Screaming Frog URL data for joining backlink targets if available
- GSC/GA4 data for prioritizing target URLs if available

No live backlink APIs, no DataForSEO, no Moz, no Bing Webmaster, no Common Crawl.

## Datenbasis: DuckDB + Kontext-Artefakte

### Stufe 0 — Qdrant SEO-Wissen abrufen

Rufe vor der Diagnose relevantes SEO-Wissen aus Qdrant ab.

```
qdrant-find: "backlink link building referring domains anchor text link quality"
qdrant-find: "nofollow sponsored UGC link spam disavow domain rating link intersect"
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
Backlink diagnosis blocked: seo-data-foundation artifacts not found in context.
Required: run seo-data-foundation first to produce file_inventory and analysis_readiness_report.
```

### Stufe 2 — DuckDB-Tabellen prüfen

Lies die relevanten Tabellennamen aus `file_inventory` (Feld `duckdb_table`).
Prüfe per SQL:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'main'
  AND table_name IN (<relevante Tabellen aus file_inventory für backlinks>);
```

Typisch relevante Tabellen für Backlinks:
`ahrefs_backlinks`, `ahrefs_referring_domains`, `ahrefs_anchors`, `ahrefs_link_intersect`,
`crawl_internal` (optional, für Target-URL-Join),
`gsc_pages` (optional, für Traffic-Priorisierung)

Wenn weder `ahrefs_backlinks` noch `ahrefs_referring_domains` vorhanden:
```text
For the analysis of backlinks, the required data basis is missing.
```

### Stufe 3 — analysis_readiness_report Pre-Check

Lies den Readiness-Status für `backlinks` aus dem Kontext-Artefakt:
- `ready`: vollständige Diagnose durchführen.
- `partially_ready`: Diagnose durchführen; limitierte Sub-Areas dokumentieren.
- `blocked_missing_data` oder `blocked_low_quality_data`:

```text
Backlink diagnosis blocked: [reason from analysis_readiness_report].
Coverage: [n]% — not scored.
```

- `not_relevant`:

```text
Backlink diagnosis skipped: area marked not_relevant in analysis_readiness_report.
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

### Empty Cell Handling

NULL-Werte in DuckDB-Feldern sind nicht automatisch Issues.
Prüfe anhand der 5-Bedingungen aus `seo-data-foundation` Step 8.

### Joins

Falls `crawl_internal` oder `gsc_pages` vorhanden und Match-Rate ≥ 30%: Joins verpflichtend.

```sql
SELECT b."Referring page URL", b."Target URL", b."Domain rating",
       c.status_code, c.indexability
FROM ahrefs_backlinks b
LEFT JOIN crawl_internal c ON lower(trim(b."Target URL")) = lower(trim(c.address));
```

### Metric Coverage

Falls `metric_coverage_report` nicht im Kontext:
```text
metric_coverage_report not available. Backlink diagnosis runs in descriptive mode.
```

## Minimum Data

Minimum useful data:
- backlinks export with `Referring page URL` and `Target URL`
or
- referring domains export with `Domain` and link counts

Enhanced data:
- `Anchor`
- `Domain rating` / `DR`
- `UR`
- `Domain traffic`
- `Page traffic`
- `Nofollow`
- `UGC`
- `Sponsored`
- `Is spam`
- `First seen`
- `Last seen`
- `Lost`
- `Page type`
- `Page category`
- link intersect competitor columns

If minimum data is missing, report:

```text
For the analysis of backlinks, the required data basis is missing.
```

Do not reduce SEO health score for absent backlink files.

## Joined Analysis Rule

When Screaming Frog crawl, GSC, or GA4 data is available and the join key report shows a match rate of ≥ 30% against backlink target URLs, joining is mandatory for prioritization.

Do not treat joining as optional when join-eligible data exists. Use joined data to identify backlink targets with technical issues, prioritize link reclamation by page importance, and flag high-value pages lacking backlink support.

If a join is technically possible but was skipped, document this as a coverage reduction:

```text
Join [source A] ↔ [source B] was available but not performed.
Coverage reduction: prioritization of backlink findings by page health/traffic impact is not possible.
```

If a mandatory join (match rate ≥ 30%) was available but skipped, additionally document this as a Late Discovery per the Late Amendment Rule in the Orchestrator.

If match rate is < 30%, joining may still be performed but must be flagged as low-coverage join.

**Rationale for 30% threshold:** below 30% match rate, cross-source claims risk being driven by the matched subset rather than the full population. At ≥30%, patterns in the joined set are suitable for prioritizing findings within the matched set; whether they represent the full unmatched population depends on the match selection mechanism. Exception: if the crawl was explicitly scoped to a curated URL list (e.g., top landing pages only), joins below 30% may still be informative — flag as `low-coverage join — targeted scope — interpret findings as sample, not population`.

## Important Rules

- Do not recommend disavow unless the user has confirmed a manual action for unnatural links in Google Search Console. A high spam share alone is not sufficient grounds — Google's algorithm already filters typical spam link patterns.
- Weak links are not automatically toxic.
- Nofollow links are not toxic by default.
- Sponsored/UGC attributes are not issues by default.
- Lost links are not automatically negative if low quality or irrelevant.
- Ahrefs `Is spam` is a signal, not proof.
- Backlink data should be interpreted as exported sample/snapshot, not the full web unless export scope confirms it.
- Missing backlink data reduces coverage and confidence, not health.

## Diagnosis Workflow

### 1. Source and Coverage

Determine:
- backlink rows
- referring domains
- target URLs
- export type
- date fields available
- lost/new status available
- DR/UR/traffic fields available
- anchor data available
- link attributes available
- link intersect available
- joined target URLs in crawl/GSC/GA4 data

### 2. Profile Overview

Calculate where possible:
- total backlinks
- unique referring pages
- unique referring domains
- unique target URLs
- dofollow vs nofollow
- UGC count/share
- sponsored count/share
- lost link count/share
- spam-flagged count/share
- DR distribution
- domain traffic distribution
- language distribution if available
- platform distribution if available

### 3. Referring Domain Quality

Analyze:
- DR buckets
- domain traffic buckets
- spam-flagged domains
- irrelevant or suspicious TLDs if derivable
- language mismatch if target market known or inferable
- high external-link pages
- domains with many links to target
- domains linking sitewide or repeatedly if pattern exists
- lost domains

Do not classify as toxic solely from low DR.

### 4. Anchor Text Distribution

If `Anchor` exists:
- branded anchors
- URL/naked anchors
- generic anchors
- exact-match commercial anchors
- partial-match anchors
- empty anchors
- image/unknown anchors if inferable
- over-optimized anchors
- suspicious repeated exact-match anchors across unrelated domains

Anchor classification should be heuristic and transparent.

If brand name is not known:
- infer from target domain when possible
- otherwise state brand anchor classification is limited

### 5. Target URL Distribution

Analyze:
- homepage vs deep links
- links to non-200 target URLs if crawl joined
- links to redirected URLs if crawl joined
- links to non-indexable pages if crawl joined
- high-value pages with few/no backlinks if joined to GSC/GA4
- pages with backlinks but poor indexability
- content assets attracting links
- link equity concentration

### 6. Lost Links

If `Lost`, `Lost status`, `Drop reason` or date fields exist:
- lost link count
- lost referring domain count
- lost high-DR/high-traffic domains
- lost links to important URLs
- lost links due to target 404/redirect if data supports it
- lost links requiring reclamation

Do not recommend reclaiming weak/spam links.

### 7. Spam and Toxic Risk Review

Use toxic indicators as a review queue, not automatic disavow.

Potential risk signals:
- `Is spam` true
- source HTTP not 200
- excessive external links
- suspicious platform/page category
- exact-match anchors repeated across unrelated domains
- unrelated language/country at scale
- very low traffic domains at scale
- sitewide-like patterns
- links to money pages with commercial exact-match anchors
- sponsored/UGC attribute missing where expected

**Disavow requires a confirmed manual GSC action.**

A disavow recommendation is only appropriate when the user has explicitly confirmed that a manual action for unnatural links is present in Google Search Console. Without a confirmed manual action, Google's algorithm is already filtering the spam — no disavow file is warranted.

If no manual action exists:
- Recommend GSC monitoring (check the Manual Actions report monthly)
- Document the spam domains as a contingency basis for a future disavow file
- Do not recommend creating or submitting a disavow file

A disavow recommendation may only be made when all of the following are true:
1. User has confirmed a manual action in GSC for unnatural links
2. The relevant spam domains are clearly identified in the data
3. No other remediation path exists

Default action for spam-flagged links (no manual action confirmed):
- monitor
- review
- ignore
- reclaim if relevant
- remove if controllable
- disavow: only after confirmed manual GSC action — never preemptively

### 8. Link Intersect

If link intersect export exists:
- identify domains linking competitors but not target
- prioritize domains intersecting multiple competitors
- prioritize high DR/high traffic domains
- classify opportunity types if possible
- create prospect list
- mark dynamic competitor columns
- avoid assuming all opportunities are relevant

### 9. Joined Analysis

If crawl/GSC/GA4 can be joined:
- backlink target status/indexability
- organic performance of linked pages
- conversion value of linked pages
- link equity to important pages
- backlink-supported pages with technical problems
- high-opportunity pages lacking backlinks

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
- `partially_computable` — metric can be computed for a subset of links only; state the subset
- `rule_incomplete` — metric definition requires context not available (e.g., brand name unknown for anchor classification)
- `unreliable` — data exists but quality checks indicate it cannot be trusted for this metric

Do not silently skip a metric. Every metric listed under "Possible metrics" that is not computed must appear in the "Non-Computable Metrics" output section.

## Metrics

Possible metrics:
- referring domain count
- backlink count
- dofollow share
- nofollow share
- sponsored share
- UGC share
- spam-flagged share
- lost link share
- branded anchor share
- exact-match anchor share
- homepage link share
- deep link share
- links to non-200 targets
- links to non-indexable targets
- high-DR referring domain count
- link intersect opportunity count
- backlink coverage confidence

Only compute when data exists.

## Output Structure

```markdown
## Backlink Diagnosis

### Data Coverage
### Backlink Score Inputs
### Profile Overview
### Referring Domain Quality
### Anchor Text Distribution
### Target URL Distribution
### Lost Links and Reclamation
### Spam / Toxic Risk Review
### Link Intersect Opportunities
### Joined SEO Impact
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
- `candidate_id`: prefix `RBACK` + three-digit number, e.g. `RBACK001`
- `what`: one sentence — what could be done
- `why`: one sentence — why the current state is harmful (linked to the finding)
- `affected_scope`: count, domain count or URL pattern
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

When reporting counts and percentages:
- Always state count AND percentage together: `47 (18,3 % von 257 Referring Domains)`
- The percentage must be exactly count ÷ baseline. State the baseline explicitly above the table.
- Do not add explanatory percentage comments — fix the baseline instead.

## Cluster Naming Rule

In issue tables, name link clusters by domain pattern or category, not by individual URLs.

Correct: `low-DR-domains (<10)`, `spam-flagged domains`, `lost links to /kategorie/`
Wrong: individual exact source or target URLs in the cluster column.

## Recommendation Examples

Low Hanging Fruit:
- Reclaim lost high-quality links pointing to 404/redirected important URLs.
- Fix technical issues on backlink target pages.
- Review spam-flagged links instead of disavowing immediately.

Mid Term:
- Improve internal linking from strongly linked pages to strategic pages.
- Build links to high-impression pages with weak backlink support.
- Convert competitor link intersect domains into outreach targets.

Long Term / Strategic:
- Build linkable assets.
- Diversify referring domains.
- Improve brand/entity mentions for GEO and authority.

## Evidence Requirements

Each backlink finding must include:
- source file
- row filters
- referring domains or source URLs
- target URLs
- counts
- DR/traffic/anchor values if used
- joined technical/search data if used
- confidence
