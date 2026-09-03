# Content Recency Framework

## Source role

Use [Seer Interactive, "Study: Content Recency's Impact on AI Visibility in
2026"](https://www.seerinteractive.com/insights/study-content-recencys-impact-on-ai-visibility-in-2026),
published July 24, 2026, as an empirical supporting reference for recency and
maintenance analysis.

The Seer study is not normative Google guidance and is not evidence about the
audited site. It describes date patterns among pages already cited by three LLM
products during a particular four-month sample. Use it to structure observations
and review priorities, never to assign a Google quality rating, predict an LLM
citation, or turn page age into a pass/fail rule.

Google Search Central and the Search Quality Rater Guidelines remain the
normative sources for the helpful-content framework. Their governing principle
is that freshness is conditional on page purpose and user need: an old archival
page may remain useful, while stale time-sensitive information may be unhelpful
or harmful.

## What the study measured

The study examined pages cited in non-branded LLM answers for four brands in
four verticals: pet retail, travel, retail energy and commercial banking.

- Engines: ChatGPT, Gemini and Perplexity.
- Observation window: March through June 2026.
- Inclusion: pages cited at least three times after deduplication to unique
  conversations.
- Date sources: structured signals such as schema, XML sitemaps and HTTP
  headers.
- Dated set: 7,683 unique pages associated with 47,097 citations; roughly two
  thirds of the eligible pages could be dated.
- Both-dates subset: 4,124 pages for which both publication and update dates
  were readable.
- Weighting caveat: vertical sample sizes differed, so the article emphasizes
  percentages and says the headline was checked both pooled and equal-weighted.

The study reported these descriptive patterns:

| Slice | Observed distribution in the study |
|---|---|
| All dated cited pages | 75% updated within one year; 88% within two years |
| Pages with both dates | 72% updated within one year, while 42% were published within one year |
| Gemini | 78% updated within one year; 90% within two years |
| ChatGPT | 73% updated within one year; 87% within two years |
| Perplexity | 65% updated within one year; 83% within two years |

The study's one-year update shares by content type were 78% for marketplaces
and aggregators, 77% for comparison/review pages, 74% for reference pages, 72%
for brand/corporate pages, 67% for blogs/guides and 45% for news/editorial pages.
These are sample descriptions, not recommended thresholds.

The article defines **fresh-from-old** as a page updated within the last year
but originally published at least two years ago. This is a maintenance-pattern
label only. It does not establish that the update was substantive.

The study also separated pages by the number of months in which they were cited:

| Months cited in the four-month window | Pages | Updated within one year |
|---|---:|---:|
| 1 | 525 | 86% |
| 2 | 1,749 | 82% |
| 3 | 1,986 | 77% |
| 4 | 3,423 | 68% |

This association supports distinguishing a short citation spike from sustained
visibility. The audit cannot make that distinction because it does not collect
LLM citation histories.

## Limits on inference

Preserve all of these limits in analysis:

1. **Selection bias:** the sample contains already-cited pages, not all eligible
   pages on the web.
2. **No uncited control group:** the study does not estimate how update age
   changes the probability of being cited.
3. **No causal identification:** recently updated pages may differ in authority,
   usefulness, topic, format and promotion. The observations do not prove that
   changing a date or editing a page caused an LLM citation.
4. **Date claims are imperfect:** schema, sitemap and HTTP dates may represent
   publication, content editing, template deployment or server changes. A
   recent date does not prove substantive maintenance.
5. **Incomplete date coverage:** about one third of eligible pages were not in
   the dated set.
6. **Scope limits:** four brands, four verticals, three engines and four months
   do not support a universal cadence for other industries, languages, query
   types, engines or future model versions.
7. **Aggregation effects:** engine and vertical differences partly reflect the
   content-type mix and unequal sample sizes.
8. **No target-site visibility evidence:** without a separate citation dataset,
   this audit cannot state whether an audited URL is cited, whether its citations
   are rising or falling, or whether a refresh will improve AI visibility.

Phrase the study-level inference as an association: cited pages in this sample
skewed toward recent update dates, and maintained older pages were common.
Do not say that the study proved an LLM freshness ranking factor.

## Operational conclusions retained from the study

Formalize the article's strategy claims this way:

- **Maintenance versus publishing:** distinguish a maintained older page from a
  newly published page. Do not recommend replacement merely because publication
  age is high.
- **Content-type context:** group observed recency by content type, but let the
  inferred user task determine whether freshness is actually required.
- **Durability:** the study's one-month versus four-month citation observation
  cannot be applied without citation history. Record AI citation durability as
  `not_measured`, not as an inferred freshness outcome.
- **Site-specific cadence:** the article recommends deriving refresh triggers
  from a site's own citation history. This skill has no such dataset and must not
  invent a cadence from the study averages.
- **Owned versus earned:** internal pages are directly maintainable; third-party
  marketplaces, reviews and reference pages are not. The default internal crawl
  cannot measure the freshness of the wider earned-citation landscape. Do not
  extrapolate an internal-page distribution to external visibility.

## Per-page analysis

Create one structured freshness assessment for every included target URL.

### 1. Classify freshness demand

Infer freshness demand from the page's purpose, primary focus and likely user
task before looking at its age:

| Value | Use when |
|---|---|
| `high` | The task can become wrong or unsafe quickly: current prices, availability, schedules, deadlines, laws, financial rates, medical guidance, current product versions or live comparisons |
| `medium` | Currency materially affects usefulness, but change is normally slower: reviews, commercial offer details, travel planning, statistics or operational guidance |
| `low` | The subject is mostly durable, though facts, examples or recommendations may occasionally change |
| `none` | The intended value is historical, archival, artistic or based on a stable fact for which age does not reduce usefulness |
| `not_verifiable` | The purpose or temporal dependency cannot be established from the crawl |

Page type informs this classification but never determines it alone. A news
archive may have `none`; a corporate page containing current fees may have
`high`.

### 2. Map the study content type

Map each page to exactly one analytical value:

- `marketplace_aggregator`
- `comparison_review`
- `reference`
- `brand_corporate`
- `blog_guide`
- `news_editorial`
- `other`
- `not_verifiable`

This mapping exists only to group the site's observed recency profile against
the study's descriptive categories. It does not set the freshness demand or
outcome.

### 3. Collect and reconcile date signals

Collect all available claims separately:

- visible publication and update labels in rendered HTML;
- JSON-LD or other structured `datePublished` and `dateModified` values;
- XML sitemap `lastmod` values exposed by Screaming Frog;
- HTTP `Last-Modified` when exposed;
- crawl date, used only as the age reference date;
- explicit temporal statements in main content, such as years, deadlines,
  prices, model versions, season names and "current as of" labels.

Store the original value, source locator and parsed value. Never silently replace
one signal with another. Reconcile publication claims separately from
modification claims. Assign both `publication_date_status` and
`modification_date_status` from the same vocabulary:

| Value | Meaning |
|---|---|
| `consistent_multiple` | Two or more claims for the same date type support the same calendar date, allowing a one-day timezone difference |
| `single_claim` | Exactly one usable claim exists for that date type |
| `conflicting` | Claims for the same date type disagree materially and the difference cannot be explained from page evidence |
| `invalid_future` | After timezone normalization, a claimed date is later than the crawl date |
| `unavailable` | No usable claim exists for that date type |

Do not treat a publication date and a later modification date as conflicting;
they describe different events. Assign `date_relationship_status` as
`consistent`, `modified_before_published` or `not_verifiable` after the two date
types have been reconciled.

Use a single `modified_date` for a `consistent_multiple` or `single_claim`
modification status. For `invalid_future`, preserve the selected claimed value
so the error remains auditable, assign the `future_date` bucket and do not treat
it as a valid update. For `conflicting`, leave it null. If page evidence clearly
distinguishes a technical deployment date from a content-modification claim,
exclude the technical signal from the content-date candidate set, document why,
and then recompute the modification status.

Prefer `modified_date` for `effective_update_date`. If modification status is
`unavailable` but a usable publication date exists, the publication date may be
used as the recency baseline with
`effective_update_basis = 'published_fallback'`. This means only that the page
existed by that date; never describe the fallback as an observed update. Do not
use a publication fallback to hide a conflicting or invalid modification claim.

### 4. Derive age and maintenance labels

Calculate age relative to `helpful_content_runs.crawl_date`, never relative to
the model's current date. Assign one `update_recency_bucket`:

- `le_3_months`
- `gt_3_months_le_1_year`
- `gt_1_le_2_years`
- `gt_2_le_3_years`
- `gt_3_le_5_years`
- `gt_5_years`
- `future_date`
- `not_verifiable`

Set `fresh_from_old = true` only when both conditions are met relative to the
crawl date:

1. a modification claim, not a publication fallback, is within the previous
   year; and
2. publication date is at least two years old; and
3. both date types are usable and their relationship is `consistent`.

Otherwise use `false` only when both date types are usable, their relationship
is `consistent` and one of the two age conditions is not met. Use `null` when a
date is unavailable, conflicting or invalid, or when the date relationship is
not consistent.

### 5. Inspect substantive currency

Age is not the outcome. Inspect the rendered main content for evidence that
matters to the inferred task:

- expired dates or deadlines presented as current;
- superseded year, version, product, plan or offer labels;
- internally inconsistent prices, terms, statistics or temporal claims;
- current-season or current-year promises contradicted by the body;
- a visible update claim without corresponding substantive change when a known
  older crawl version is available;
- stable evergreen content whose usefulness does not depend on recent change.

A comparison with an older crawl is optional and may use only stored Screaming
Frog evidence for the same URL. Do not infer unchanged content merely from an old
publication date or a recent modification date.

### 6. Assign the outcome

Use one `freshness_outcome`:

| Value | Use when |
|---|---|
| `current_supported` | Direct temporal evidence supports current usefulness for the inferred task; qualify any unverified factual claims |
| `verified_stale` | Direct page evidence shows expired, superseded or internally contradictory information material to the task |
| `artificial_freshness_concern` | Direct comparison or contradiction shows a newer date without a corresponding substantive update |
| `maintenance_review_candidate` | Age, date conflict or missing maintenance evidence warrants review, but staleness is not proven |
| `evergreen_no_refresh_need_observed` | The purpose is stable and no material temporal dependency is observed |
| `mixed_evidence` | Material signals point in different directions |
| `not_verifiable` | Available crawl evidence cannot support a freshness conclusion |
| `not_applicable` | Freshness does not reasonably apply to the page purpose |

Pair the outcome with the skill's normal evidence status. `verified_stale` and
`artificial_freshness_concern` require `verified_concern` and direct evidence.
`maintenance_review_candidate` is normally `supported_inference`. A recent date
alone cannot justify `verified_positive` or `current_supported`.

Use `freshness_outcome = 'not_applicable'` with `freshness_demand = 'none'`.
Reserve `evergreen_no_refresh_need_observed` for a `low`-demand page whose stable
purpose and content support that inference. Pair `not_applicable`,
`not_verifiable` and `mixed_evidence` outcomes with their identically named
evidence statuses.

## Domain aggregations

Compute from raw target rows and retain exact denominators:

- date-signal coverage and conflict rate;
- update-recency distribution overall and by mapped content type;
- share updated within one and two years;
- fresh-from-old share among targets with both usable dates;
- freshness-demand distribution;
- outcome distribution;
- high/medium-demand URLs with `verified_stale`,
  `artificial_freshness_concern` or `maintenance_review_candidate` outcomes.

Do not compare these rates to Seer's percentages as a pass/fail benchmark. The
study values may be included as clearly labeled external context only; the
audited site's own rates, denominator and date coverage must remain separate.

## Recommendation rules

- Recommend a substantive review, not a date-only change.
- State the specific facts, sections or temporal promises that must be checked.
- For verified staleness, require correction or removal of the obsolete claim
  and validation against the updated rendered HTML.
- For a maintenance candidate, label the recommendation as a review trigger,
  not as proof that the page is stale.
- Prioritize time-sensitive YMYL and task-critical pages before low-demand
  evergreen pages.
- Never prescribe a universal annual refresh cadence from the Seer study.
- Never forecast citation gains or claim an AI-visibility defect without actual
  citation-history evidence, which this skill does not collect.
