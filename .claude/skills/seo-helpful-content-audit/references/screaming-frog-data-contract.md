# Screaming Frog Data Contract

## Scope

The official Screaming Frog MCP server (`seospider`) is the only audited-site
data source for this skill. It can load or run crawls, export crawl datasets and
return stored URL content. Its API and available filters may change between
versions, so discover the live schema before requesting data.

Primary product documentation:

- [Screaming Frog MCP configuration and API](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/#mcp-server)
- [Screaming Frog tab and field reference](https://www.screamingfrog.co.uk/seo-spider/user-guide/tabs/)

## Crawl preflight

1. Call `sf_list_crawls` and identify completed crawls for the requested host.
2. Prefer a currently loaded, completed matching crawl when its scope and date
   satisfy the request.
3. If one unambiguous stored crawl matches, load it with `sf_load_crawl`.
4. If several plausible crawls match, present their crawl IDs, dates and scopes
   and ask the user to select one.
5. If no crawl exists and the user supplied a domain or URL to audit, starting a
   crawl with `sf_crawl` is within scope. Use an existing approved configuration
   file when one is available. Do not invent a config path.
6. Poll `sf_crawl_progress` until crawl processing, crawl analysis and connected
   audit processing are complete. Do not treat URL-crawl completion alone as
   proof that Accessibility or connector data is ready.

Record:

- crawl ID and name;
- start URL/host;
- crawl date;
- completion state;
- URL count;
- rendering/storage configuration when exposed;
- whether Content, Accessibility, Mobile and Structured Data results populated.

## Rendered-HTML requirement

Rendered HTML is mandatory for this audit.

The crawl must have JavaScript rendering and "Store rendered HTML" enabled for
the HTML to be described as rendered. The stored DOM represents the page after
JavaScript processing. If configuration state is not exposed, inspect a known URL
with `sf_url_content` and record `html_render_state: unconfirmed`; do not silently
call ordinary source HTML rendered.

Use:

- `sf_bulk_export_page_content` with `page_content_type: RAW_HTML` for domain or
  URL-list structural extraction;
- `sf_bulk_export_page_content` with `page_content_type: VISIBLE_TEXT` for a
  content-text corpus;
- `sf_url_content` with `show_visible_content_for_html_url: false` for a single
  page's stored HTML when bulk export would be disproportionate;
- `sf_url_content` with `show_visible_content_for_html_url: true` for that page's
  visible text.

Write large returns to files inside the MCP allowed directory instead of sending
them into conversation context. Resolve the directory first with
`sf_list_allowed_base_directory`.

Do not use `sf_get_url_screenshot`, `sf_open_url_in_browser`, chrome-devtools or
another renderer for this workflow.

## Dynamic field discovery

Before each `sf_export_seo_element_urls` call:

1. Call `sf_list_available_filters_for_seo_element`.
2. Select the broadest applicable filter from the returned live list.
3. Call `sf_list_available_data_fields_for_seo_element_and_filter`.
4. Request fields by the exact returned names.

Never guess a filter or field name. Filter and value labels can be localized or
change across Screaming Frog versions. Preserve the original field name beside
the canonical meaning used in analysis.

Fields with `null` mean unavailable. Do not infer their values.

## Required collection map

| Need | Preferred MCP path | Evidence use |
|---|---|---|
| URL universe and core on-page data | `sf_export_seo_element_urls` for `Internal`, HTML filter | URL, status, indexability, content type, title, meta description, H1/H2, canonical, word count, crawl depth and available content fields |
| Full rendered DOM | `sf_bulk_export_page_content` `RAW_HTML`, or `sf_url_content` for one URL | Lists, tables, semantic containers, DOM order, bylines, disclosures, citations, dates and schema fallback extraction |
| Visible content | `sf_bulk_export_page_content` `VISIBLE_TEXT`, or visible `sf_url_content` | Purpose, audience, focus, user task and qualitative content assessment |
| Content metrics | `sf_export_seo_element_urls` for `Content` | Flesch score, average words per sentence, readability class, spelling/grammar, exact/near duplicates when exposed |
| Structured data | `sf_export_seo_element_urls` for `Structured Data`, plus rendered JSON-LD parsing | Page/entity type, headline/name, author/reviewer, dates, about/keywords, citations and publisher claims |
| Accessibility | `sf_export_seo_element_urls` for `Accessibility`; use discovered bulk export/report for details when available | Confirmed axe run, counts, WCAG rule, exact affected element/location and contrast violations |
| Text-size legibility | `sf_export_seo_element_urls` for `Mobile` and, if needed, `PageSpeed` | `Illegible Font Size` result only; never substitute the font-resource `Font Size` field |
| Link relationships | `sf_url_links` for selected targets, or discovered inlink/outlink exports | Author/profile, source, contact and context-page relationships |
| URL detail | `sf_url_info` | Single-URL cross-check and available field inventory |

Use `sf_list_available_bulk_exports` and `sf_list_available_reports` before
generating detailed Accessibility or duplicate reports. Select a returned
category; never invent category strings.

## Minimum field groups

Map live field names to these canonical meanings when present:

### Identity and eligibility

- `page_url`
- `content_type`
- `status_code`
- `indexability`
- `indexability_status`
- `canonical_url`
- `crawl_depth`
- `unique_inlinks`

### Focus and structure

- `title`
- `meta_description`
- `h1`
- `h2`
- `word_count`
- `rendered_html`
- `visible_text`
- `structured_data_types`
- `structured_data_payload`

### Content quality support

- `flesch_reading_ease`
- `average_words_per_sentence`
- `readability_class`
- `spelling_errors`
- `grammar_errors`
- `exact_duplicate_signal`
- `closest_similarity_match`
- `near_duplicate_count`

### Automated accessibility and legibility

- `accessibility_run_status`
- `all_accessibility_violations`
- `wcag_aa_violations`
- `contrast_rule_result`
- `contrast_violation_details`
- `illegible_font_size_result`

Do not require every field to exist before continuing. Track availability per
URL and use `not_verifiable` for the affected criterion.

## Standalone staging

Large exports must be stored as files and staged before analysis. Use skill-local
names so this audit neither depends on nor overwrites shared pipeline tables:

| Suggested table | Contents |
|---|---|
| `helpful_content_internal` | Internal HTML export |
| `helpful_content_raw_html` | RAW_HTML page-content NDJSON |
| `helpful_content_visible_text` | VISIBLE_TEXT page-content NDJSON |
| `helpful_content_dom_signals` | Output of `extract_rendered_html_signals.py` |
| `helpful_content_metrics` | Content/Flesch/duplicate fields |
| `helpful_content_structured_data` | Structured Data export |
| `helpful_content_accessibility` | Accessibility summary/details |
| `helpful_content_mobile` | Mobile text-size results |

These are suggested names, not a contract with `seo-data-foundation`. Record the
actual names in the standalone scope artifact.

Run the included extractor:

```bash
python .claude/skills/seo-helpful-content-audit/scripts/extract_rendered_html_signals.py \
  <raw-html.ndjson> <dom-signals.ndjson>
```

For a single saved HTML file:

```bash
python .claude/skills/seo-helpful-content-audit/scripts/extract_rendered_html_signals.py \
  <page.html> <dom-signals.ndjson> --url https://example.com/page
```

The extractor uses only Python's standard library. Inspect its stderr summary,
stage its NDJSON output and verify input/output row counts. Any record with an
`extraction_error` remains visible and makes rendered-DOM criteria
`not_verifiable` for that URL.

## Required evidence locators

Every direct observation needs a compact locator:

- Crawl field: `SEO element > filter > original field name > URL`.
- Accessibility: `rule name > impact > affected selector/location > URL`.
- Rendered HTML: `URL > element/attribute or selector > extracted value/count`.
- Structured data: `URL > format > @type > property path`.
- Link evidence: `source URL > direction > destination URL > anchor/relationship`.
- Derived rate: source record IDs plus exact numerator and denominator.

Do not paste large HTML blocks into the evidence ledger. Store a short
paraphrase, count or minimal excerpt and point to the saved raw artifact.

## Data-specific interpretation rules

### Accessibility and contrast

A contrast statement is verified only when:

1. Accessibility extraction ran for the URL;
2. the relevant axe/WCAG contrast rule has a result;
3. a violation claim includes the rule and affected location, or a no-violation
   claim is based on a confirmed completed rule evaluation.

Phrase a clean result as "Screaming Frog's automated axe audit reported no
violations for [rule]", not "the page has accessible contrast".

### Font size

Use `Illegible Font Size` from the Mobile/Lighthouse audit. The PageSpeed
overview metric called `Font Size` is the transferred size of font resources and
does not measure rendered text size. If `Illegible Font Size` was not run, text
size is `not_verifiable`.

### Flesch readability

Report:

- exact Flesch Reading Ease score;
- Screaming Frog readability class;
- average words per sentence when available;
- detected/page-declared language;
- intended audience inferred by the audit.

The metric result itself is verified data. Whether it is suitable for the
audience is an interpretation. Do not call specialized text poor merely because
it receives a difficult classification.

### Rendered DOM

DOM tag counts are facts, not quality scores. `ul_count = 0` does not mean a list
is needed; `table_count > 0` does not mean the page is helpful. Use a structural
element only when it supports or impedes the page's inferred task.

### Dates

A publication or modification date is a displayed/marked-up claim. Do not infer
artificial freshness from a recent date alone. A verified freshness concern
requires contradictory page evidence, unchanged duplicated content across known
versions, or another direct signal available in the crawl.

## Failure handling

- MCP unavailable: stop and state that the `seospider` connection is required.
- No matching crawl and crawl cannot be started: stop and state the exact blocker.
- Crawl incomplete: wait or return a resumable partial status; do not analyze as
  complete.
- Rendered HTML absent: do not substitute chrome-devtools. Continue only with
  explicitly reduced scope and mark DOM-dependent criteria `not_verifiable`.
- Accessibility/Flesch/Mobile fields absent: continue, but do not make positive or
  negative claims for those checks.
- Tool output too large: write it to a file, paginate exports or use `start_index`
  and `max_rows`; do not truncate silently.
