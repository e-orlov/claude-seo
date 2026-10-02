# Deterministic on-page observations

Profile ID: `geo-on-page-observables-v1`.

Read this specification before analysing the mapped factors. Extract observations
from the existing RAW/REN artifacts and SF fields. Keep the 129-factor inventory,
canonical metrics, source gate and frozen scoring policy as defined in the
contracts. These observations describe markup and text; they do not estimate
citation probability or establish required content lengths.
Use each owning factor's existing applicable URL universe and record the reason
for every inapplicable observation.

## Contents

1. [Factor ownership](#factor-ownership)
2. [Shared extraction rules](#shared-extraction-rules)
3. [ToC](#toc)
4. [H2 count and form](#h2-count-and-form)
5. [Editorial summary](#editorial-summary)
6. [Author blocks](#author-blocks)
7. [Title and H1](#title-and-h1)
8. [List types](#list-types)
9. [Native details](#native-details)
10. [Evidence and aggregation](#evidence-and-aggregation)
11. [Verification examples](#verification-examples)

## Factor ownership

| Observation | Owning factor | Permitted reuse within existing factors |
|---|---|---|
| ToC, H2 count/form, H1 structure, list types | C03 | C09 for ordered steps; C26 for scanability |
| Explicit editorial summary | C02 | C26 for scanability |
| Author block, name and profile link | C17 | C18 for attribution and expertise |
| Author photo and biography | C18 | C17 for the same author identity |
| Title characteristics and title/H1 equality | C04 | C03 for the observed H1 |
| Native `<details>` structure and initial DOM content | T15 | C10 only for blocks inside an evidenced FAQ scope |

Use one measurement per URL/source/profile and cite the same observation when
reused. Dependent observations never increase evidence independence. Do not
create new factors or overwrite canonical factor metrics with these fields.

## Shared extraction rules

1. Use the saved initial DOM after the crawl's configured render wait, before
   any click, expansion, hover or scroll. Process RAW and REN separately; record
   source code, artifact hash and parser name/version. Do not fetch extra pages.
2. Bind a content root for each template before extraction. An explicit selector
   must resolve to exactly one element; zero/multiple matches are a gap and do
   not trigger a fallback. Without that binding, use exactly one `main` or
   `[role="main"]` (deduplicate the same element), otherwise exactly one
   `article`, otherwise `body` with `body_fallback`. Multiple candidates at the
   first nonempty preference level are `not_determined`.
3. Exclude `script`, `style`, `template`, `noscript`, `aside`, `footer`,
   `[role="complementary"]`, `[role="contentinfo"]` and recorded template
   boilerplate selectors from content observations. Preserve article headers.
   Inspect navigation containers for ToC before excluding other `nav` and
   `[role="navigation"]` subtrees. Title extraction always uses `head > title`.
4. Freeze selector bindings for roots, summaries, author blocks and author
   fields in the run's derived extraction settings. Record their literal CSS
   selectors and supporting DOM locators. Do not add undocumented fields to
   `audit.yaml`. A selector must behave identically for every URL in its declared
   template scope; unresolved binding is a gap, not absence of a page feature.
5. Traverse descendant text nodes in DOM order. Preserve adjacency across inline
   elements. Emit one space for `br` and before/after each `p`, `div`, `section`,
   `article`, `header`, `main`, `h1` through `h6`, `li`, `dt`, `dd`, `ul`, `ol`,
   `dl`, `tr`, `td`, `th`, `blockquote`, `figure`, `figcaption`, `details` and
   `summary`. Skip excluded subtrees. Apply Unicode NFC, replace every Unicode
   White_Space run with one ASCII space and trim. Preserve case and punctuation.
   Do not add image alt text, JSON-LD values or CSS-generated text.
6. Count characters as Unicode code points of normalized text, including spaces
   and punctuation. Count words as maximal runs of Unicode letter/number
   characters, with combining marks attached to them; retain an internal ASCII
   hyphen, straight apostrophe or U+2019 only when surrounded by letter/number
   characters. Record the Unicode database version. Do not count punctuation
   alone as a word.
7. For question form, record the number of ASCII `?` characters and a boolean
   `ends_with_question_mark`. Calculate the latter after stripping whitespace
   and terminal closing quotes/brackets (U+0022, U+0027, U+00BB, U+2019, U+201D,
   U+0029, U+005D, U+007D). Set form to `empty`, `question_mark` or `other`.
   This is a punctuation observation, not an LLM judgement of interrogative intent.
8. Treat DOM presence and initial visibility as separate facts. Record visibility
   as `visible`, `not_visible` or `unknown` only from captured rendered evidence;
   saved HTML alone does not prove computed CSS visibility. Counts below are DOM
   counts and may include content inside a closed native disclosure.
9. Use states `measured`, `not_determined`, `not_applicable`. For an unavailable
   artifact, ambiguous root or unresolved required selector, set affected values
   to `null` and name the reason. Use zero/false only after complete extraction
   within the declared scope. A valid empty element has normalized text `""`.
10. Compare RAW/REN values only for the same normalized URL, run and equivalent
    root/selector scope. Different scopes are `not_comparable`; keep both
    observations without attributing their difference to JavaScript.

## ToC

Detect a structural table of contents from links to headings in the content
root. Resolve links against the document's recorded base URL. A qualifying link
must point to the same document (same resolved URL except fragment), have a
nonempty percent-decoded fragment, and resolve to exactly one eligible H2-H6
heading with that `id`. Duplicate IDs are unresolved targets.

Automatic candidate containers are `nav`, `[role="doc-toc"]`, `ul` and `ol`.
A recorded ToC selector may supply another container type. Require at least two
distinct resolved heading targets and no targeted heading inside the container.
Prefer the outermost qualifying navigation/`doc-toc` container; ignore qualifying
descendant lists. Outside such containers, use outermost qualifying lists and
ignore their qualifying descendants. Merge candidates matching the same DOM
element. Keep all accepted containers in DOM order.

Record `toc_detected`, `toc_count` and, per container, its locator, unique target
count, ordered link labels/targets and unresolved fragment links. Set detection
to false only when the complete candidate universe was inspected. A single
"back to top" link or repeated links to one heading do not qualify. The rule
detects this explicit structural form; it does not infer an unmarked visual ToC.

## H2 count and form

Select every eligible `h2` in the content root in DOM order. Count elements,
including empty and duplicate headings; do not deduplicate heading text.

Record `h2_count`, `h2_nonempty_count`, `h2_empty_count`,
`h2_question_mark_count`, `h2_other_nonempty_count` and `h2_at_least_5`.
For each heading record locator, normalized text, word/character counts, number
of `?` characters and the form defined above. The question-mark count counts
headings with form `question_mark`, not individual punctuation characters.

Calculate question-heading share over nonempty H2s only. With zero nonempty H2s,
record a null share and `zero_denominator`. Preserve numerator and denominator.
The five-heading flag is descriptive; it does not determine C03 status.

## Editorial summary

Detect an explicitly marked editorial summary through recorded selectors or
an eligible H2-H6 whose normalized, casefolded label, after removing a trailing
colon, is exactly one of:

- German: `zusammenfassung`, `kurzfassung`, `kurz und knapp`, `das wichtigste`,
  `das wichtigste in kuerze`, `das wichtigste in kürze`, `fazit`.
- English: `summary`, `executive summary`, `in brief`, `key takeaways`, `tldr`,
  `tl;dr`, `conclusion`.
- Russian: `кратко`, `краткое содержание`, `главное`, `выводы`, `итоги`.

For a heading marker, take following content up to the next heading of equal or
higher rank, or the end of the content root. Exclude the marker itself. For a
bound container, use its content minus its bound label/heading. If both methods
identify the same content span, retain one block. Record detection method and
DOM boundaries so overlapping blocks are reproducible.

Record `summary_detected`, `summary_count`, `summary_nonempty_count`, and each
block's text, word/character counts, marker and location in DOM order. Retain
empty marked blocks. Exclude native `<summary>` children of `<details>` from
editorial-summary detection. An unlabelled opening paragraph can satisfy the
existing C02 direct-answer rubric, but this extractor does not relabel it a
summary. Absence of an explicit summary is not a C02 failure by itself.

## Author blocks

Use recorded author-block selectors or explicit `[itemprop~="author"]` /
`[data-author]` wrappers. Deduplicate the same element and process blocks in DOM
order. Do not expand an author link to an arbitrary ancestor to collect a nearby
portrait or biography. An isolated `a[rel~="author"]` is an author-link marker,
not proof of an author box. If neither explicit markers nor a confirmed template
binding defines the author-block universe, record `not_determined`.

Bind fields inside each block using explicit microdata or recorded field
selectors. Accept name from `[itemprop~="name"]` or a bound name element; profile
link from `a[rel~="author"]` or a bound profile link; biography from
`[itemprop~="description"]` or a bound biography element. Accept a portrait only
from an author-specific image selector, `[itemprop~="image"]` within that author
entity, or an `img` whose resolved URL exactly matches that author's declared
Person image. Do not infer portraits from faces or count every nearby image.

Record `author_block_count`, isolated author-link locators, and per block:
locator, name text(s), profile URL(s), `name_present`, `profile_link_present`,
`portrait_present`, `biography_present`, biography text and word count, portrait
URLs/locators, field-binding method and initial visibility state. A field is
present only with nonempty normalized text or a resolved nonempty URL, as
appropriate. An unresolved field binding produces null, not false. An `img` is
one portrait candidate even when wrapped in `picture` or supplied via `srcset`.
Use captured `currentSrc`, otherwise `src`; keep unselected `srcset` candidates
as declared URLs without claiming that they loaded.

Use JSON-LD only to confirm an exact author/image association. It does not prove
that a biography, name, portrait or author block appears in page content.
Presence records do not establish expertise, portrait authenticity or a bio's
factual correctness; retain the existing C17/C18 evaluation rules.

## Title and H1

Record every `head > title` and every eligible content-root `h1` in DOM order,
including empty/duplicate elements. For each record locator, normalized text,
word/character counts and question form. Record `title_count` and `h1_count`;
never silently choose the first of multiple elements.

When exactly one nonempty title/H1 exists, record the descriptive flags
`title_chars_at_least_45`, `h1_chars_at_least_40`, `h1_words_at_least_5` for the
corresponding element. Otherwise set that element's flags to null and state
`missing`, `empty` or `multiple`. Set `title_equals_h1` only when both singular
nonempty values exist; compare exact normalized text, retaining case and
punctuation. Otherwise record null with the reason.

Extract four-ASCII-digit year tokens from 1900 through 2099 in title text; require
boundaries that are neither Unicode letters, numbers nor combining marks, and
retain duplicates in encounter order. Use the run's immutable `created_at` as
the evaluation timestamp and its UTC year as `evaluation_year`. Record
`title_years`, `has_current_year`,
`has_older_year` and `has_future_year` per title. Absence of years gives an empty
array and false flags after successful extraction. Multiple year categories
may coexist. Do not treat an older year as outdated facts or require the current
year in a title.

## List types

Count content-root `ul`, `ol` and `dl` separately after excluding accepted ToC
containers and author blocks. Native nesting creates distinct list records.
Record `unordered_list_count`, `ordered_list_count`, `description_list_count`
and a locator/type for every list. Count only direct `li` children of `ul`/`ol`,
and direct `dt`/`dd` children of `dl`; record these counts and empty-list flags.
Record `start`, `reversed` and `type` attributes of ordered lists, including
their absence. A boolean `reversed` attribute is true when present.

Keep `[role="list"]` with direct `[role="listitem"]` children as a separate
ARIA-list observation, excluding native list elements to prevent double counts.
Do not classify paragraphs, CSS bullets or newline-separated text as semantic
lists. DOM counts do not prove that a numbered list describes a valid process;
C09 still evaluates its steps, prerequisites and outcomes.

## Native details

Select actual `<details>` elements in the content root, including nested ones.
Do not interpret a `<detail>` typo, a custom accordion or an ARIA disclosure as
this native element. Record `details_count`, `details_open_count`,
`details_closed_count` and, per element, its locator, direct-child summary count,
first direct `<summary>` text, and normalized body text excluding that first
summary subtree. Keep later summary elements as body content and record the
multiple-summary condition. Record `body_dom_nonempty`, body word count and
initial visibility separately. Do not sum nested body word counts sitewide.

Treat the `open` attribute as a boolean by presence, so `open="false"` is open.
Record this native open/closed state independently of CSS visibility. A closed
block with nonempty body text in the initial DOM has `body_dom_nonempty=true`;
do not label it interaction-loaded, absent or a T15 blocker because it is closed.
If its body is empty, record that observed absence; do not speculate about what
a later click would load. Compare RAW/REN body text only under the shared parity
rules. [HTML details semantics](https://html.spec.whatwg.org/multipage/interactive-elements.html#the-details-element)
defines native disclosure behaviour; it does not establish AI citation uplift.

## Evidence and aggregation

Store these structured details in `geo_evidence_drafts.observed_value_json`, then
`geo_evidence.observed_value_json` and package `evidence[].observed_value` under
the owning factor. Use its existing lowercase method ID, such as
`geo_factor_c03_v1`. Include
the profile ID, normalized URL, source-specific root/element locators, extraction
state/reasons and settings. Calculate the method fingerprint over canonical
JSON (the project's canonical-json-v1 algorithm) containing the reference-file
SHA-256, profile ID, parser/Unicode versions,
evaluation timestamp and selector settings. Keep the source artifact hash in
its existing evidence field. This profile's states belong inside observed_value;
factor_result statuses continue to use the contract enums.

Reuse observations only when the profile/settings/reference hashes match.
Recompute them after a method change even if config/source hashes are unchanged;
create a new run revision instead of editing a completed analysis package.

For one-URL observations set evidence numerator/denominator to null unless the
observation is an actual proportion. For proportions use measured eligible
units only, preserve counts, exclude unknown/inapplicable units, and record a
null rate for zero denominator. Aggregate over distinct normalized URLs in one
source/snapshot/template scope. Never add RAW and REN counts together or sum
overlapping parent/child clusters. Report coverage alongside every aggregate.

Connect evidence IDs to existing factor results. Keep descriptive flags separate
from the frozen canonical metrics and rubric scores. A missing ToC, summary,
portrait, question heading, list or length cutoff is not an automatic issue.
Create a finding/recommendation only when existing factor criteria and evidence
support it. Never turn conference percentages into weights or promised effects.
Before completing the analysis, check that every applicable mapped factor links
to the profile observations for its analysed URL scope, or records specific
extraction gaps and observation coverage. Keep gaps in evidence/factor limitations;
do not conceal them behind false presence flags or passing rubric values.

## Verification examples

Use these cases to check the definitions before finalising observations.

| Stored input / condition | Required observation |
|---|---|
| One ToC container links to distinct eligible IDs `a`, `b` | `toc_count=1`, unique targets=2 |
| Two links both target heading `a` | Does not qualify as a ToC |
| A fragment resolves to two headings with the same ID | Target is unresolved; exclude it from valid target count |
| H2 texts: `Warum?`, empty, `Kosten` | total=3, nonempty=2, question-mark headings=1, share=1/2 |
| H2 text: `Warum?` followed by a closing quote | Form is `question_mark` |
| `<details><summary>Summary</summary><p>Body</p></details>` | Native summary only; closed; body is present in DOM |
| `<details open="false"><summary>FAQ</summary><p>Body</p></details>` | Native state is open |
| An author name exists only in JSON-LD | Does not establish a DOM author block/name |
| A logo occurs near an author link without a portrait binding | Does not establish an author portrait |
| Two H1 elements contain identical text | `h1_count=2`; title/H1 equality and singular H1 flags are null |
| Title `Guide 2025/2026`, evaluation year 2026 | years=[2025,2026], older=true, current=true |
| `ul` contains one direct `li` with a nested `ol` and two `li` | One unordered list with one item; one ordered list with two items |
| REN HTML or a required content-root binding is unavailable | `not_determined` and null affected values, not zero/false |
