---
name: seo-geo-file-diagnosis
description: >
  Performs file-based GEO/LLM citation-readiness diagnosis from uploaded crawl,
  content, schema, backlink, GSC and related exports. Evaluates answer fitness,
  extraction readiness, entity clarity, evidence readiness, technical accessibility
  and retrieval context only where supported by the available files. Adapts to
  the actual data present; no fixed filenames, fixed schemas, live AI-search checks
  or API calls are assumed.
user-invokable: true
argument-hint: "[data-foundation-artifacts]"
license: MIT
metadata:
  version: "1.1.0"
  category: seo-file-audit
---

# GEO / LLM Citation Readiness File Diagnosis

## Datenbasis: DuckDB + Kontext-Artefakte

### Stufe 0 — Qdrant SEO-Wissen abrufen

Rufe vor der Diagnose relevantes SEO-Wissen aus Qdrant ab.

```
qdrant-find: "GEO generative engine optimization LLM citation AI search answer extraction"
qdrant-find: "llms.txt structured answers entity clarity brand authority AI crawler accessibility"
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
GEO diagnosis blocked: seo-data-foundation artifacts not found in context.
Required: run seo-data-foundation first to produce file_inventory and analysis_readiness_report.
```

Wenn Technical SEO und Content Diagnosis bereits im Kontext vorhanden sind:
deren Findings für crawlability- und strukturabhängige GEO-Bewertungen referenzieren,
statt dieselben Checks erneut durchzuführen.

### Stufe 2 — DuckDB-Tabellen prüfen

Lies die relevanten Tabellennamen aus `file_inventory` (Feld `duckdb_table`).
Prüfe per SQL:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'main'
  AND table_name IN (<relevante Tabellen aus file_inventory für geo>);
```

Typisch relevante Tabellen für GEO:
`crawl_internal`, `crawl_structured_data`, `crawl_h1` (für Heading-Struktur),
`gsc_queries` (für Query-Intent), `gsc_pages`,
`ahrefs_referring_domains` (für Authority-Proxies),
`crawl_inlinks` (für Content Architecture)

Mindest-Anforderung: mindestens eine Tabelle mit URLs und page-level Evidence
(Headings, Titles, Directives oder Content-Felder).

### Stufe 3 — analysis_readiness_report Pre-Check

Lies den Readiness-Status für `geo` aus dem Kontext-Artefakt:
- `ready`: vollständige Diagnose.
- `partially_ready`: Diagnose mit dokumentierten Einschränkungen.
- `blocked_missing_data` oder `blocked_low_quality_data`:

```text
GEO diagnosis blocked: [reason from analysis_readiness_report].
Coverage: [n]% — not scored.
```

- `not_relevant`:

```text
GEO diagnosis skipped: area marked not_relevant in analysis_readiness_report.
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

Falls `join_key_report` im Kontext und Match-Rate ≥ 30%: Joins verpflichtend.

```sql
SELECT c.address, c."H1-1", c.indexability,
       g.impressions, g.clicks
FROM crawl_internal c
LEFT JOIN gsc_pages g ON lower(trim(c.address)) = lower(trim(g.page))
WHERE c.indexability = 'Indexierbar';
```

### Metric Coverage

Falls `metric_coverage_report` nicht im Kontext:
```text
metric_coverage_report not available. GEO diagnosis runs in descriptive mode.
```

## Purpose

Diagnose Generative Engine Optimization and LLM citation readiness from the data-foundation artifacts, including uploaded Semrush AI Visibility `.mhtml` exports and a live Screaming Frog crawl where available.

This skill evaluates whether the available data supports conclusions about how well pages are prepared to be:

- accessible to AI systems,
- understandable,
- extractable,
- trustworthy,
- supported by evidence,
- and likely to serve as useful citation candidates.

It does not query ChatGPT, Google AI Overviews, Perplexity or any live AI search engine.

It measures **GEO / LLM readiness**, not actual AI visibility, unless uploaded visibility data explicitly supports such a conclusion.

## What GEO Means Here

In this file-based framework, GEO covers:

- technical accessibility and indexability evidence,
- answer fitness and extraction readiness,
- query-answer alignment where query data exists,
- self-contained and quotable passages where content exists,
- entity clarity and trust signals,
- structured data support,
- evidence and source readiness,
- topical authority and external corroboration from uploaded data,
- internal architecture supporting answer pages,
- retrieval context where ranking or query-cluster data exists,
- multilingual and localization support where relevant data exists.

## Data-Adaptive Rule

Do not assume fixed filenames, fixed exports or fixed column names.

First determine:

1. which files and sources are available,
2. which fields and entities they contain,
3. which GEO analysis areas they can support,
4. which metrics are computable,
5. which metrics are only partially computable,
6. which areas are not computable from the current sources.

Examples:

- A crawl export may support indexability, headings, metadata and internal links.
- Full content exports may support citability and answer extraction.
- GSC exports may support query-page alignment and topic demand.
- Ahrefs exports may support external corroboration and authority proxies.
- Ranking exports may support retrieval context.
- New or unexpected files must be profiled before being ignored.

Missing data is not a negative result.

If a factor cannot be evaluated from the current sources, label it using Family B `metric_status` values:

- `not_computable_from_current_sources` — required data was not uploaded
- `insufficient_data` — data exists but volume or quality is too low
- `rule_incomplete` — factor definition requires context not available

Do not use `not_available` — it is not a valid status in any taxonomy family.

## Minimum Data

Minimum useful data:

- at least one uploaded source containing URLs plus some usable page-level evidence, such as headings, titles, content snippets, rendered content, full text, structured data, directives or equivalent fields.

Enhanced data may include:

- full text / content extracts,
- H1/H2/H3 fields,
- question headings,
- structured data exports,
- robots/directives exports,
- bot-crawl tests,
- backlink/refdomain data,
- GSC queries and page data,
- ranking / keyword-cluster data,
- internal linking data,
- hreflang / content parity data,
- brand or mention data,
- llms.txt if uploaded or present in exports.

If no data source can support a meaningful GEO diagnosis, report:

```text
For the analysis of GEO / LLM citation readiness, the required data basis is missing.
```

## Joined Analysis Rule

When GSC, backlink, or crawl data is available alongside content/heading/schema data, and the join key report shows a match rate of ≥ 30%, joining is mandatory for prioritization.

Do not treat cross-source analysis as optional when join-eligible data exists. Use joined data to identify answer pages with high query demand but weak GEO readiness, and pages with authority signals but poor extraction readiness.

If a join is technically possible but was skipped, document this as a coverage reduction:

```text
Join [source A] ↔ [source B] was available but not performed.
Coverage reduction: GEO opportunity ranking by search demand or authority cannot be performed.
```

If a mandatory join (match rate ≥ 30%) was available but skipped, additionally document this as a Late Discovery per the Late Amendment Rule in the Orchestrator.

If match rate is < 30%, joining may still be performed but must be flagged as low-coverage join.

**Rationale for 30% threshold:** below 30% match rate, cross-source claims risk being driven by the matched subset rather than the full population. At ≥30%, patterns in the joined set are suitable for prioritizing findings within the matched set; whether they represent the full unmatched population depends on the match selection mechanism. Exception: if the crawl was explicitly scoped to a curated URL list (e.g., top landing pages only), joins below 30% may still be informative — flag as `low-coverage join — targeted scope — interpret findings as sample, not population`.

## Important Rules

- Do not claim actual AI Overview, ChatGPT or Perplexity visibility without uploaded visibility evidence.
- Do not claim citation frequency unless such data is uploaded.
- Do not treat GEO readiness, retrieval context and actual AI visibility as the same thing.
- Do not treat search rankings as proof of citation readiness; use them as retrieval-context evidence only.
- Do not treat backlink metrics as actual AI visibility; use them as authority proxies only.
- Do not treat lack of `llms.txt` as a critical SEO defect.
- Do not treat missing AI-specific robots data as an issue unless bot access is part of the audit scope.
- Do not score unavailable factors as zero.
- GEO score confidence must be lower if full content is unavailable.
- Headings and metadata can indicate structure, but cannot fully prove passage citability without content body.
- Only compute metrics and scores when the available fields support them.
- If an uploaded source is unfamiliar, profile it and map usable fields semantically before deciding whether it is relevant.

## GEO Factor Model

Use the following factor groups as a diagnosis framework.

They are candidate factors, not mandatory checks.

### 1. Citation Fitness

Primary readiness factors:

- query-answer match,
- intent-format match,
- factual specificity,
- self-contained passages,
- explicit phrasing,
- answer near the top,
- AI-ready structure.

These factors are the core of GEO readiness where content and/or query data exists.

### 2. Technical Accessibility

Use available crawl, directive, bot or rendered-content data to assess:

- URL accessibility,
- indexability,
- canonicalization,
- robots restrictions,
- AI crawler access where data exists,
- visible / extractable main content,
- JavaScript dependency where supported by crawl/render data.

Technical accessibility may act as a gating factor: strong content should not receive a high readiness classification if the relevant content is not reliably accessible.

### 3. Machine Interpretability

Use available evidence to assess:

- structured data support,
- semantic heading hierarchy,
- lists,
- tables,
- definitions,
- FAQ-like blocks,
- comparison blocks,
- content block clarity.

Structured data is supportive evidence, not proof of citation readiness by itself.

### 4. Entity and Trust Signals

Use uploaded evidence to assess:

- brand / entity trust,
- organization clarity,
- author / person signals where relevant,
- entity consistency,
- sameAs / entity connections if present,
- About / Contact / Impressum / author pages if available,
- consistent naming across content and schema,
- external corroboration from uploaded authority data.

### 5. Evidence Readiness

Where content exists, assess:

- source-backed claims,
- direct references,
- factual specificity,
- original data,
- dates,
- expert attribution,
- case studies,
- examples,
- verifiable claims.

### 6. Retrieval Context

If ranking, keyword, topic-cluster or query-expansion data exists, assess separately:

- search rank,
- fan-out rank,
- topic-cluster ranking,
- query demand,
- organic visibility context.

Retrieval context is important, but should be shown separately from readiness by default.

### 7. Context Fit

If relevant data exists, assess:

- freshness,
- language match,
- localized content,
- content length relative to query intent.

Do not apply universal freshness or word-count rules without context.

### 8. Experimental Signals

If available, report separately:

- `llms.txt`,
- preview-control-related signals,
- other emerging conventions.

Do not include these in the main GEO score unless project-specific rules explicitly require it.

## Diagnosis Workflow

### 1. Data Coverage

Determine which evidence exists and what it can support:

- page URLs,
- content body or only metadata/headings,
- query data,
- ranking data,
- question headings,
- structured data types,
- robots/directives,
- AI crawler rules or bot tests,
- rendered-content evidence,
- internal linking,
- backlinks / refdomains / mentions,
- multilingual / hreflang data,
- content parity data,
- performance data if accessibility or rendering affects extraction,
- uploaded AI visibility reports, if any.

For each analysis area, mark:

- available,
- partially available,
- missing (source not uploaded or not found),
- not_computable_from_current_sources (source exists but required fields are absent or insufficient).

### 2. Factor-to-Data Mapping

Before scoring, map available data to GEO factors.

For each factor, determine:

- available source,
- usable fields,
- whether evidence is direct or proxy,
- whether the factor is applicable,
- whether it is computable,
- confidence level.

Each factor entry must use typed status fields from the correct taxonomy family — do not mix source, metric and scope statuses in a single untyped field:

- `source_status` (Family A) — describes whether the source required for this factor is available: `available`, `partially_available`, `missing`, `not_relevant`
- `factor_applicability` — **GEO-local field, not a global taxonomy family.** Describes whether the factor is in scope for this audit: `applicable`, `not_applicable` (e.g., multilingual factor on a single-language site), `unknown`. This field is not part of Families A–F; it is a scope qualifier specific to GEO factor mapping.
- `metric_status` (Family B) — describes computability once the factor is applicable and source is available: `computable`, `partially_computable`, `not_computable_from_current_sources`, `insufficient_data`, `rule_incomplete`, `experimental_only`

Do not use `missing` or `not_applicable` as metric_status values — they belong to Family A or factor_applicability, not Family B.

Example — source missing:
```json
{
  "factor": "llms_txt",
  "source_status": "missing",
  "factor_applicability": "applicable",
  "metric_status": "not_computable_from_current_sources",
  "confidence": "low",
  "reason": "No uploaded llms.txt file or crawl evidence for llms.txt."
}
```

Example — factor not applicable:
```json
{
  "factor": "multilingual_hreflang_geo",
  "source_status": "not_relevant",
  "factor_applicability": "not_applicable",
  "metric_status": null,
  "reason": "Audit scope is a single-language domestic site."
}
```

Example — source available but factor computable only partially:
```json
{
  "factor": "structured_answer_formats",
  "source_status": "available",
  "factor_applicability": "applicable",
  "metric_status": "partially_computable",
  "confidence": "medium",
  "reason": "Content headings and lists available; JSON-LD answer types not exported."
}
```

### 3. AI Crawler Accessibility

If robots.txt, directives, bot crawl tests, rendered content or crawl exports contain relevant information, check:

- pages blocked by robots,
- `noindex` on answer pages,
- canonicalization of answer pages,
- AI-specific crawler rules if robots data is present,
- blocked resources required for rendered content if data supports it,
- JavaScript-dependent content if crawl/render data supports it,
- content visible only after rendering if data supports that check.

Do not infer AI bot access without robots or bot-test evidence.

### 3b. llms.txt Assessment

If an `llms.txt` file is uploaded or available in the dataset, assess:

- whether it appears to describe the root domain or correct site,
- whether it contains a clear site title,
- whether it contains a concise description,
- whether it lists important content sections,
- whether listed URLs are absolute or reliably resolvable,
- whether listed URLs are indexable, if crawl data is available,
- whether listed URLs return 200, if status data is available,
- whether listed URLs are canonical, if canonical data is available,
- whether important answer pages are missing, if content/crawl data allows this check,
- whether it lists blocked, noindex, redirected or error URLs.

Important:

- `llms.txt` is an emerging GEO convention, not a confirmed general ranking factor.
- Treat findings as experimental AI-discoverability signals, not critical classic SEO defects.
- Do not include `llms.txt` in the main GEO score by default.

### 4. Answer Fitness and Extraction Readiness

Use headings, content and query data where available to assess:

- query-answer match,
- intent-format match,
- clear H1,
- descriptive H2/H3,
- question-based headings where relevant,
- concise answer sections,
- direct answers near section starts,
- self-contained passages,
- explicit definitions,
- factual specificity,
- lists and tables where useful,
- FAQ-like visible content,
- comparison structures,
- step-by-step sections,
- summary blocks.

If only headings or metadata are available, label the result as a structural proxy.

### 5. Citability and Evidence Readiness

Evaluate only where content text exists:

- factual, quotable sentences,
- specific numbers and statistics,
- source-backed claims,
- direct answer near the start of a section,
- original data or proprietary insights,
- named entities and unambiguous references,
- examples and case studies,
- dates and freshness indicators,
- visible citations or references.

If content text is absent, do not calculate a full citability score. Use `not_computable_from_current_sources` or a low-confidence structural proxy.

### 6. Entity Clarity and Trust

Use available data such as:

- organization schema,
- author / person schema,
- sameAs fields if exported or content is available,
- consistent brand mentions,
- page titles and H1s,
- About / Contact / Privacy / Impressum / author pages in crawl,
- external authority data,
- target URL structure,
- schema/content consistency.

Find:

- weak entity identity,
- inconsistent brand naming,
- missing organization/trust pages,
- missing author/entity signals where page type requires them,
- schema opportunities,
- contradictions between visible content and structured data.

### 7. Authority and External Corroboration

Use uploaded data only:

- referring-domain quality,
- authoritative refdomains,
- backlinks to answer pages,
- editorial or citable external sources where derivable,
- external source links if crawl/content provides them,
- citations/references in content if content exists,
- expert author data if available,
- GSC demand / query coverage as topical relevance support,
- mention or link-gap data if uploaded.

Do not substitute backlink DR for actual AI citation visibility. Treat it as an authority proxy only.

### 8. Retrieval Context

If GSC, ranking, keyword-cluster or similar data exists, assess separately:

- search rank,
- query demand,
- topic-cluster coverage,
- fan-out or related-query coverage if available,
- pages with clear answer readiness but weak retrieval context,
- pages with rankings but weak citation readiness.

Do not blend retrieval context into the main GEO readiness score unless the project explicitly defines such a combined score.

### 9. Content Architecture for GEO

Analyze where data supports it:

- answer pages with internal support,
- important pages lacking internal links,
- pages with GSC demand but weak structure,
- topic clusters if URL/query data supports them,
- hub/spoke opportunities,
- thin high-impression pages,
- duplicate content weakening entity clarity,
- backlink-supported answer pages,
- content gaps across clusters,
- multilingual parity if hreflang/content parity data exists.

### 10. Multilingual / International GEO

If hreflang or multilingual data exists, assess:

- content parity across language versions,
- localized title/meta/headings,
- missing language versions,
- stale translations if dates exist,
- schema localization,
- region/language consistency,
- culturally relevant adaptation only where content evidence supports it.

Do not perform cultural quality judgment from URLs alone.

## Non-Computable Metric Reporting

For every metric that cannot be computed, state this explicitly in the output using the standard format:

```text
Metric: [metric name]
Status: not_computable_from_current_sources
Reason: [missing field / missing source / insufficient rows / content body absent]
Required for computation: [field or source name]
```

Allowed status values:
- `not_computable_from_current_sources` — required data was not uploaded
- `insufficient_data` — data exists but volume or coverage is too low for a reliable result
- `partially_computable` — metric can be computed for a subset only; state the subset and what is missing
- `rule_incomplete` — metric definition requires context not available
- `unreliable` — data exists but quality checks indicate it cannot be trusted for this metric
- `experimental_only` — metric relates to experimental signals (e.g., `llms.txt`) and should not be included in main score

Do not silently skip a metric. Every metric listed under "Possible metrics" that is not computed must appear in the "Non-Computable Metrics" output section with its status and reason.

## Metrics

Possible metrics include:

- GEO data coverage,
- factor coverage,
- answer structure coverage,
- question-heading rate,
- indexable answer page rate,
- structured-data support rate,
- self-contained passage coverage,
- direct-answer coverage,
- factual-specificity coverage,
- evidence-readiness score,
- entity-clarity score,
- internal support score,
- backlink-supported answer-page share,
- multilingual parity score if data exists,
- retrieval-context score if ranking/query data exists,
- actual AI visibility metrics only if uploaded visibility data exists.

Only compute metrics if the available fields support them.

## Suggested GEO Score Components

Use only computable components.

Recommended readiness components:

- Technical accessibility
- Citation fitness / answer readiness
- Machine interpretability
- Entity and trust signals
- Authority and evidence readiness
- Context fit where relevant

Recommended separate scores:

- **GEO Readiness Score**: direct readiness factors only
- **Retrieval Context Score**: rankings, topic-cluster visibility and related retrieval proxies where available
- **AI Citation Visibility Score**: only if uploaded platform-visibility data exists

If a component is not computable:

- exclude it from the score,
- reduce coverage/confidence,
- state why it is not computable.

Do not assign automatic zero points for missing data.

### Scoring Guidance

Use evidence tiers as weighting priors:

| Factor Group | Default Treatment |
|---|---|
| Query-answer fit, AI-ready structure, factual specificity, intent-format match, self-contained passages | core readiness factors |
| Answer near the top, explicit phrasing, structured data | supporting readiness factors |
| Search rank, fan-out rank, topic-cluster ranking | retrieval-context factors, separate by default |
| Brand/entity trust, entity consistency, citations, known-source indicators | trust / corroboration factors |
| Freshness and language | context-dependent factors |
| `llms.txt`, preview control | experimental / report-only by default |

If score coverage is low, label the score as:

- `partial`
- `provisional`
- or `blocked`

as appropriate.

## Output Structure

```markdown
## GEO / LLM Citation Readiness Diagnosis

### Data Coverage
### Factor Coverage
### GEO Score Inputs
#### GEO Readiness Score
#### Retrieval Context Score
#### AI Citation Visibility Score
### AI Crawler and Indexability Evidence
### llms.txt Assessment
### Answer Fitness and Extraction Readiness
### Citability and Evidence Readiness
### Entity Clarity and Trust
### Authority and External Corroboration
### Retrieval Context
### Content Architecture
### Multilingual / International GEO
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
- `candidate_id`: prefix `RGEO` + three-digit number, e.g. `RGEO001`
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
- Always state count AND percentage together: `34 (7,5 % von 452 URLs)`
- The percentage must be exactly count ÷ baseline. State the baseline explicitly above the table.
- Do not add explanatory percentage comments — fix the baseline instead.

## Cluster Naming Rule

In issue tables, name clusters by URL pattern or page type, not by individual URLs.

Correct: `/antwort-seiten/`, `answer-page template`, `Produktdetailseiten`
Wrong: individual exact URLs in the cluster column.

## Recommendation Examples

Low Hanging Fruit:

- Add concise answer blocks under high-impression question headings.
- Improve H2/H3 headings to better match query intent.
- Add visible source references to factual claims.
- Clarify ambiguous entity references in key answer sections.
- Fix accessibility or indexability blockers on answer pages.

Mid Term:

- Create or improve hub pages for query clusters.
- Add relevant structured data to entity-heavy pages where appropriate.
- Improve internal links to high-value answer pages.
- Enrich weak pages with self-contained, factual answer passages.
- Improve external corroboration for strategically important topics.

Long Term / Strategic:

- Build original data, studies or case-study assets.
- Strengthen author/entity/trust framework.
- Build authoritative mentions and citations in relevant external sources.
- Develop topic clusters that combine retrieval context with strong citation fitness.
- Establish measurement for actual AI citation visibility if strategically relevant.

## Evidence Requirements

Each GEO finding must state whether it is based on:

- direct content evidence,
- heading/metadata proxy,
- structured-data evidence,
- crawl/indexability evidence,
- rendered-content evidence,
- bot-access evidence,
- backlink authority proxy,
- GSC demand proxy,
- ranking / retrieval-context proxy,
- multilingual evidence,
- joined multi-source evidence,
- uploaded AI-visibility evidence.

Always label confidence.

For every score, state:

- which components were included,
- which components were excluded,
- why excluded components were not computable,
- score coverage,
- confidence,
- whether the score represents readiness, retrieval context or actual visibility.