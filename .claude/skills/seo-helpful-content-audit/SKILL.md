---
name: seo-helpful-content-audit
description: >
  Audits one URL, a URL list, or an entire domain for helpful, reliable,
  people-first content using only Screaming Frog MCP crawl data and stored
  rendered HTML. Infers each page's purpose, audience, focus topic and likely
  user task from on-page evidence, applies Google Search Central guidance and
  the Search Quality Rater Guidelines as a conceptual framework, and writes
  validated evidence, assessments and findings to skill-local DuckDB tables.
  Does not generate reports or use chrome-devtools, live SERP research, other
  SEO skills or the shared audit scoring/reporting pipeline.
user-invocable: true
argument-hint: "[url-or-domain]"
license: MIT
compatibility: Requires Claude Code with the Screaming Frog seospider MCP server and a local DuckDB MCP server.
metadata:
  version: "1.2.0"
  category: seo-content-audit
---

# Helpful, Reliable, People-First Content Audit

## Purpose

Evaluate whether the content available at the requested URL scope is supported
by observable evidence of usefulness, reliability and a people-first purpose.
Use Screaming Frog as the sole website-data source. The audit may cover one
page, an explicit URL list, or all eligible pages in a domain crawl.

This is a standalone analytical skill. It owns its data collection and analysis
and ends with a validated DuckDB run. It does not own report generation.
It must not invoke or require:

- `seo-file-audit-orchestrator`
- `seo-data-foundation`
- `seo-content-file-diagnosis`
- `seo-scoring-recommendations`
- `seo-report-generator`
- `seo-url-clustering`

Do not write to their artifacts, evidence registries, issue registers, scores,
tables or report scripts. Never invoke `seo-report-generator` automatically.
The user may start that skill manually as a separate task after this analysis is
complete. Do not add this skill's findings to a full-audit score unless the user
later requests a separate integration task.

## Required References

For an actual audit, read all three references before collecting data:

1. [Google quality framework](references/google-quality-framework.md) - the
   assessment criteria, applicability rules and limits on what the sources mean.
2. [Screaming Frog data contract](references/screaming-frog-data-contract.md) -
   the MCP workflow, required collection and evidence boundaries.
3. [Standalone DuckDB analysis contract](references/output-contract.md) - table
   schemas, optional exports and completion checks.

For a question about the method rather than an audit, read only the reference
needed to answer that question.

## Authoritative Basis

Use only these normative sources for the quality framework:

- [Google Search Central: Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Google Search Quality Rater Guidelines](https://guidelines.raterhub.com/searchqualityevaluatorguidelines.pdf), September 11, 2025 edition

The Search Central document is direct publisher guidance. The Quality Rater
Guidelines are a conceptual self-assessment lens, not a list of ranking factors.
Never claim that this audit reproduces Google's algorithms, predicts rankings,
or assigns an official Google Page Quality rating. Search quality raters do not
directly control rankings, and E-E-A-T is not a single ranking factor.

Do not use, cite or reproduce the Photowant guide. It is deliberately excluded.

## Accepted Scope

Resolve the argument into one of these modes:

| Mode | Input | Assessment scope |
|---|---|---|
| `single_url` | One full URL | The target page plus a small domain-context set |
| `url_list` | Several explicit URLs | Every target URL plus shared domain context |
| `domain` | Origin, host or homepage URL | Every eligible internal HTML page in the loaded crawl |

For `single_url` and `url_list`, domain context is still required to interpret
site purpose, responsibility and trust signals. Select, when present in the same
crawl:

- the homepage;
- About, contact, customer-service, editorial-policy or equivalent pages;
- author/profile pages linked from a target;
- up to three same-type peer pages per target.

Context pages inform the target assessment but are not silently converted into
additional target-page findings. Label each URL as `target` or `context`.

For `domain` mode, assess every eligible page. Do not silently sample. Process
large crawls in bounded batches and persist results after each batch. If the run
stops early, return exact completed and remaining counts and resume from the
saved `helpful_content_page_assessments` rows in DuckDB.

## Eligibility

The default page-level baseline is internal HTML URLs that:

- returned HTTP 200;
- are indexable;
- have a stored rendered-HTML record.

Also inventory excluded URLs by reason. Non-indexable pages may be included when
the user explicitly asks for them or when they are necessary domain-context
pages, but do not mix them into the default baseline.

Utility pages whose purpose is primarily functional, such as login, cart,
faceted search or account pages, may be marked `not_applicable` for editorial
criteria. They still qualify for purpose, trust and usability observations where
those criteria apply.

## Non-Negotiable Data Boundary

Use website evidence only from the official Screaming Frog MCP server attached
to this project (`seospider`). This includes crawl fields, exports, URL details,
links, visible text and stored rendered HTML.

Do not use:

- chrome-devtools MCP;
- browser automation or manual browser rendering;
- live SERP or keyword tools;
- general web search for the audited site's facts or reputation;
- other crawler or SEO APIs;
- supplied target keywords as a prerequisite.

The source documents above may be cited as methodology. They are not evidence
about the audited site.

## Evidence Status

Every criterion-level assessment must use exactly one status:

| Status | Meaning |
|---|---|
| `verified_positive` | Direct crawl, field or rendered-DOM evidence supports the criterion |
| `verified_concern` | Direct crawl, field or rendered-DOM evidence demonstrates a concrete problem |
| `supported_inference` | A stated interpretation is supported by cited page evidence but cannot be proven as fact |
| `mixed_evidence` | Direct observations materially point in different directions |
| `not_verifiable` | Available Screaming Frog evidence cannot establish the claim |
| `not_applicable` | The criterion does not reasonably apply to this page type or purpose |

Never convert `not_verifiable` into a positive result. Missing or null data is
not evidence of absence. A zero count is usable only when the corresponding
Screaming Frog analysis is confirmed to have run successfully for that URL.

Keep three layers separate in both working data and prose:

1. **Observation** - what Screaming Frog or the rendered DOM contains.
2. **Interpretation** - what the observation may mean for the page's purpose.
3. **Recommendation** - what to change and how to validate the change.

## Focus and Topic Inference

Do not ask the user to supply keywords or topics. Infer them from page evidence.

For each target page:

1. Extract candidate topics from the title, meta description, H1, ordered H2/H3
   outline, JSON-LD properties, URL slug, breadcrumbs and opening main-content
   passage.
2. Give greatest weight to agreement among title, H1, structured data and the
   opening passage. Use meta description and URL only as supporting signals.
3. Exclude navigation, footer, cookie text and repeated boilerplate from topic
   inference.
4. Merge lexical variants that clearly refer to the same entity or task.
5. Record one inferred primary focus, secondary topics, the likely user task,
   evidence fields and confidence.
6. If strong signals conflict, return `focus_ambiguous` and explain the conflict.
   Do not force a keyword.

This is content-focus inference, not keyword-volume research. Do not claim
search demand, rankings, competitiveness or canonical query wording from it.
Never use keyword-density thresholds as a quality criterion.

## Audit Workflow

### 1. Resolve and verify the crawl

Follow the preflight in the Screaming Frog data contract.

- Identify or load the crawl matching the requested host.
- Confirm the crawl is complete before exporting.
- Confirm whether JavaScript rendering and stored rendered HTML are available.
- Determine which Content, Structured Data, Accessibility and Mobile fields
  actually exist before requesting them.
- Record crawl identity, date, scope and configuration evidence.

If several crawls match and the correct one cannot be determined from host,
date and status, ask the user to select one. Do not merge crawls silently.

### 2. Collect and stage standalone evidence

Use the exact MCP discovery and export sequence in the data contract. At minimum
collect:

- Internal HTML URL data;
- rendered HTML for target/in-scope URLs;
- visible page text;
- Content metrics, including Flesch data when available;
- structured data;
- Accessibility results and violation details when available;
- Mobile `Illegible Font Size` evidence when available;
- internal duplicate/near-duplicate signals when available;
- URL-level inlinks/outlinks only where needed to resolve author, source or
  domain-context relationships.

Stage every Screaming Frog result in DuckDB before analysis. Use only skill-local
tables prefixed with `helpful_content_`; this is direct use of the project's
DuckDB infrastructure, not an invocation of `seo-data-foundation`.

Read rendered HTML from the staged `helpful_content_raw_html` rows. Extract the
needed page facts yourself and write each auditable observation directly to
`helpful_content_evidence`. Normal Screaming Frog columns do not expose every
structural fact, so explicitly inspect the stored rendered HTML when the audit
needs counts or locations for `ul`, `ol`, `li`, tables, blockquotes,
definition lists, semantic containers, bylines, citations or disclosures. Do
not introduce a second parser or intermediate evidence file as another source
of truth.

### 3. Establish domain context

Before judging individual pages, determine from observed pages:

- apparent primary site purpose and topical focus;
- major page types or repeated templates;
- ownership, publisher and contact signals;
- author/reviewer infrastructure;
- visible editorial, review or content-production policies;
- internal exact/near-duplicate patterns;
- sitewide accessibility, readability and production-quality patterns.

Do not infer off-site reputation from the site's own claims or testimonials.
Assess external reputation only if independent external-source URLs are already
included in the selected Screaming Frog crawl and their content is available.

### 4. Assess every target page

For each target, in order:

1. Determine page type and beneficial purpose.
2. Infer audience, primary focus, secondary topics and likely user task.
3. Classify YMYL applicability as `clear`, `possible`, `unlikely` or
   `not_verifiable`, with a short reason.
4. Identify main content and distinguish it from supplementary content,
   navigation, monetization and boilerplate using rendered HTML.
5. Apply only the relevant criteria in the Google quality framework.
6. Record the strongest direct evidence for every result. Prefer selectors,
   element names, source fields and short paraphrases over long quotations.
7. Separate page-specific issues from template-wide or domain-wide patterns.
8. Create actions only for concrete concerns or well-supported improvement
   opportunities.

Absence of lists, tables, FAQ markup, video, images, a byline or a specific word
count is not automatically a defect. Judge each element against page purpose.

### 5. Aggregate without hiding page-level variation

Group recurring findings by verified common template or structural pattern.
Store the exact numerator, denominator and percentage for every domain-level
rate.
Do not extrapolate a finding from a sample to unsampled pages.

Preserve a `helpful_content_page_assessments` row for every target URL,
including pages with no verified concerns and pages whose evidence is
insufficient. Domain-level summaries must remain traceable through DuckDB joins
to page rows and evidence records.

### 6. Prioritize recommendations

Use these factors, in order:

1. potential harm or trust failure, especially on clear YMYL pages;
2. inability to achieve the page's apparent user purpose;
3. affected scope across target pages;
4. importance of the affected page type to the site's stated purpose;
5. confidence and directness of evidence.

Store the stable values `critical`, `high`, `medium` or `low`. Do not assign
`critical` solely for absent optional markup or a poor Flesch classification.
Explain every priority. Do not claim traffic or conversion impact without
corresponding data.

### 7. Validate and finalize the DuckDB analysis

Follow the DuckDB analysis contract. Treat DuckDB as the only working source of
truth.
Run every SQL completion check there and correct failures before setting
`run_status = 'validated'`.

Do not generate Markdown, DOCX or another client-facing report. Never invoke
`seo-report-generator` automatically. Report generation begins only when the
user later invokes that skill as a separate task.

CSV or NDJSON snapshots are optional and may be produced only when the user
explicitly requests them. Generate them directly from one validated `run_id`;
never maintain them as parallel working state or use them to resume analysis.

End with a concise operational handoff containing the `run_id`, domain, mode,
target baseline, completed count, source-coverage summary, table map, assessment
and finding counts, validation status and any material analytical limitations.
This handoff is not a report and must not prescribe report structure or layout.

## Explicit Verification Boundaries

The following can be verified when their named Screaming Frog data is present
and successfully populated:

- rendered-DOM structure;
- metadata, headings, structured data and visible authorship/source links;
- internal duplicate and near-duplicate signals;
- automated axe/WCAG accessibility violations, including contrast;
- Lighthouse/Mobile `Illegible Font Size` results;
- Flesch Reading Ease, average words per sentence and Screaming Frog's
  readability classification;
- spelling/grammar issue fields;
- HTTP, indexability, canonical and link facts.

Qualify these claims:

- Flesch measures textual reading difficulty, not visual legibility or factual
  quality. Interpret it in light of page language and intended audience.
- An automated accessibility pass does not prove full WCAG compliance.
- `Font Size` in PageSpeed overview is font-resource transfer size, not text
  legibility. Use `Illegible Font Size` for the latter.
- A byline or credential claim proves only that the page displays it.
- First-person language or original images can support an experience inference;
  they do not prove that the claimed experience occurred.

Normally not verifiable from this data alone:

- the creator's true motive for publishing;
- complete factual accuracy or expert consensus;
- actual user satisfaction;
- external originality or comparative value against unseen competitors;
- independent reputation when external evidence was not crawled;
- the authenticity of credentials, testimonials or claimed experience;
- full visual hierarchy, intrusive overlays or layout quality;
- full accessibility conformance.

Use `supported_inference` or `not_verifiable` for these. Never phrase them as
established facts.

## Completion Gate

Do not call the audit complete until all of the following are true:

- target scope and denominator are explicit;
- every target URL has one and only one `helpful_content_page_assessments` row;
- rendered HTML was inspected for every assessed URL, or the exact uncovered count
  is stated;
- inferred focus includes evidence and confidence for every target;
- every concern points to at least one evidence record;
- contrast, font-size and Flesch statements name the exact source field/audit;
- no `not_verifiable` criterion is presented as passed;
- findings do not claim official Google ratings or ranking-factor status;
- Photowant is absent from sources and reasoning;
- the DuckDB SQL completion gate passes;
- `run_status` is `validated` and the final handoff identifies the validated
  `run_id` and its table map;
- no report was generated and `seo-report-generator` was not invoked.
