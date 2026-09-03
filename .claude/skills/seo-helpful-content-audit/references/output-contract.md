# Standalone DuckDB Analysis Contract

## Source of truth

DuckDB is the only working source of truth for this skill. Write scope, source
coverage, target URLs, extracted observations, assessments, evidence links and
findings there as the audit progresses. Do not maintain parallel working JSON,
NDJSON or CSV files and do not use output files to resume a run.

The skill remains standalone by owning tables prefixed with
`helpful_content_`. It uses the project's DuckDB MCP infrastructure directly but
does not invoke, depend on or write to the contracts of `seo-data-foundation`,
the orchestrator, diagnosis, clustering, scoring or reporting skills.

Every row must contain `run_id`. Never mix two audit runs in a query merely
because they cover the same domain. Use UTC timestamps.

## Minimum DuckDB model

Equivalent physical types are acceptable, but preserve these logical tables and
fields. Record actual table names in `helpful_content_runs.table_map_json`.

### `helpful_content_runs`

One row per invocation:

```text
run_id                    primary key
skill_version
domain
mode                      single_url | url_list | domain
requested_scope_json
crawl_id
crawl_date
crawl_complete
html_render_state         confirmed_rendered | unconfirmed | unavailable
target_baseline
target_completed
source_availability_json
table_map_json
run_status                collecting | assessing | partial | validated
started_at
completed_at
```

`source_availability_json` may use only `available`, `partial`, `unavailable`
or `failed`. These values are skill-local and do not extend repository-wide
taxonomies.

### `helpful_content_targets`

One row per target or context URL:

```text
run_id
url
scope_role                target | context
eligibility_status        included | excluded | context_only
exclusion_reason
assessment_status         pending | completed | not_assessable
```

Enforce uniqueness on `(run_id, url, scope_role)`. `target_baseline` is the
count of rows with `scope_role = 'target'` and `eligibility_status = 'included'`.

### `helpful_content_page_assessments`

One row per included target URL:

```text
run_id
url
page_type
purpose
audience
primary_focus
focus_status              resolved | focus_ambiguous | not_verifiable
focus_confidence          high | medium | low
secondary_topics_json
likely_user_task
ymyl                      clear | possible | unlikely | not_verifiable
ymyl_reason
overall_outcome
highest_priority          critical | high | medium | low | none
completed_at
```

Allowed `overall_outcome` values:

- `no_material_verified_concerns`
- `verified_improvement_opportunities`
- `material_verified_concerns`
- `serious_verified_trust_or_harm_concerns`
- `insufficient_evidence`

### `helpful_content_freshness_assessments`

One row per included target URL, including pages for which freshness is not
applicable or not verifiable:

```text
run_id
url
seer_content_type         marketplace_aggregator | comparison_review |
                          reference | brand_corporate | blog_guide |
                          news_editorial | other | not_verifiable
freshness_demand          high | medium | low | none | not_verifiable
demand_reason
publication_date_status   consistent_multiple | single_claim | conflicting |
                          invalid_future | unavailable
modification_date_status  consistent_multiple | single_claim | conflicting |
                          invalid_future | unavailable
date_relationship_status  consistent | modified_before_published |
                          not_verifiable
published_date
modified_date
effective_update_date
effective_update_basis    modified_claim | published_fallback | not_verifiable
age_since_publish_days
age_since_update_days
update_recency_bucket     le_3_months | gt_3_months_le_1_year |
                          gt_1_le_2_years | gt_2_le_3_years |
                          gt_3_le_5_years | gt_5_years | future_date |
                          not_verifiable
fresh_from_old            true | false | null
freshness_outcome         current_supported | verified_stale |
                          artificial_freshness_concern |
                          maintenance_review_candidate |
                          evergreen_no_refresh_need_observed | mixed_evidence |
                          not_verifiable | not_applicable
status                    verified_positive | verified_concern |
                          supported_inference | mixed_evidence |
                          not_verifiable | not_applicable
observation
interpretation
confidence                high | medium | low
```

Enforce uniqueness on `(run_id, url)`. Keep the raw date values and their source
locators in `helpful_content_evidence` or the staged freshness-signal table, not
in this normalized assessment row. `effective_update_date` may use a reconciled
publication date as a fallback only when `modification_date_status =
'unavailable'`; record `published_fallback` so it is not presented as an
observed update. Never use the fallback for a conflicting or invalid
modification claim.

`verified_stale` and `artificial_freshness_concern` require
`status = 'verified_concern'`. `maintenance_review_candidate` normally uses
`supported_inference`. A recent date alone cannot support `verified_positive`.

### `helpful_content_criterion_assessments`

One row per applicable criterion and target URL:

```text
run_id
url
criterion_id              HC01 ... HC18
status
observation
interpretation
confidence                high | medium | low
```

Allowed `status` values:

- `verified_positive`
- `verified_concern`
- `supported_inference`
- `mixed_evidence`
- `not_verifiable`
- `not_applicable`

Enforce uniqueness on `(run_id, url, criterion_id)`.

### `helpful_content_evidence`

Store observations, never recommendations:

```text
run_id
evidence_id               HC-E0001, HC-E0002, ...
url
source_type
source_locator
observation
raw_value
collected_at
confidence                high | medium | low
limitations
```

Allowed `source_type` values:

- `sf_field`
- `rendered_html`
- `visible_text`
- `structured_data`
- `accessibility`
- `mobile_lighthouse`
- `link_data`
- `derived_aggregate`
- `external_page_in_selected_crawl`

Evidence IDs are monotonically increasing and unique within a run. Keep raw
HTML in the source table, not in `raw_value`; use a compact value, count or
excerpt plus a locator.

### `helpful_content_findings`

```text
run_id
finding_id                HC-F001, HC-F002, ...
scope
observation
why_it_matters
affected_pages_count
eligible_pages_count
affected_pages_pct
priority                  critical | high | medium | low
recommendation
validation
```

Each finding must state a concrete observation, the affected scope, why it
matters for the inferred page purpose, a specific action and a validation
method. Avoid generic actions such as "improve E-E-A-T", "add more content" or
"make the page helpful" unless they are converted into a concrete change tied
to verified evidence.

### `helpful_content_finding_pages`

One row per finding/affected-URL pair:

```text
run_id
finding_id
url
```

### `helpful_content_evidence_links`

Use a normalized link table instead of copying evidence-ID arrays between
working artifacts:

```text
run_id
subject_type              page_assessment | criterion | freshness | finding
subject_key               URL | URL#HC01 | HC-F001
evidence_id
```

Also allow `subject_type = 'freshness'` with the URL as `subject_key` for links
to `helpful_content_freshness_assessments`.

Subject-key mapping is exact:

- `page_assessment` -> URL
- `criterion` -> `URL#HC01` through `URL#HC18`
- `freshness` -> URL
- `finding` -> `HC-F001`, `HC-F002`, and so on

Enforce uniqueness on `(run_id, subject_type, subject_key, evidence_id)`.

## Persistence and resume

Insert evidence and assessments directly in DuckDB. Commit each bounded batch
before starting the next. On resume, select included targets whose
`assessment_status != 'completed'`; do not reconstruct state from an export or
other file.

Mark a target `completed` only after its page assessment, applicable criterion
rows and freshness assessment have been persisted and linked to their evidence.

Derive `target_completed` from completed included target rows before the
completion gate. If work stops early, set `run_status = 'partial'` and return
the exact completed and remaining counts.

## Analytical completion

No file output is required. The completed analytical result is the validated
DuckDB run identified by `run_id`, together with its `helpful_content_*` tables.
Set `run_status = 'validated'` only after the SQL completion gate passes.

End the invocation with a concise operational handoff containing:

- `run_id`, skill version, domain and mode;
- target baseline, completed and remaining counts;
- crawl ID/date and rendered-HTML state;
- source availability and material analytical limitations;
- actual table names from `table_map_json`;
- page-assessment, freshness-assessment, criterion, evidence and finding row
  counts;
- the SQL-gate result and final `run_status`.

This handoff is a run-completion notice, not a client-facing report. Do not add a
report title, report sections, formatted finding tables or presentation rules.
Do not generate Markdown or DOCX and never invoke `seo-report-generator`.
Report generation is a separate task that begins only when the user manually
invokes that skill after this analysis has ended.

## Optional exports

Create exports only when the user explicitly requests them. If no destination
is supplied, use:

```text
clients/<domain>/<YYYY-MM-helpful-content-audit>/work/exports/
```

Supported analytical snapshots:

| File | Purpose |
|---|---|
| `helpful-content-url-matrix.csv` | One row per included target URL |
| `helpful-content-evidence.ndjson` | Direct export of the run's evidence rows |
| `helpful-content-page-assessments.ndjson` | One object per page assembled from page, freshness and criterion rows |

Export only from a validated `run_id`. These files are immutable snapshots, not
working stores, resume sources or reports. If regeneration is needed, overwrite
them from the same run; never patch them independently. Export creation does not
change `run_status`.

Do not write to `clients/evidence_registry.md`. This standalone audit uses
`HC-*` IDs and is not part of the shared evidence/scoring pipeline.

### Optional URL matrix

Export these columns in order:

```text
URL
Page Type
Inferred Purpose
Inferred Primary Focus
Focus Confidence
Likely User Task
YMYL
Freshness Demand
Observed Publication Date
Observed Modification Date
Effective Update Date
Effective Update Basis
Update Recency Bucket
Fresh From Old
Freshness Outcome
Overall Outcome
Verified Strengths
Verified Concerns
Supported Inferences
Not Verifiable
Highest Priority
Evidence IDs
```

Build the values from validated assessment, criterion and evidence-link rows.
Use semicolon-separated lists inside a cell. Preserve exactly one row per
included target, including pages with no verified concern.

## Analytical calculation rules

- Store numerator, denominator and percentage together for every rate.
- Store percentages from raw rows at full available precision. An explicitly
  requested human-readable export may round its displayed value to one decimal
  place.
- Do not average Flesch across different languages without separate groups.
- Do not aggregate `not_applicable` with passes or concerns.
- Do not convert missing fields to zero.
- For a criterion rate, use only URLs for which that criterion was verifiable
  and store that criterion-specific denominator.
- Do not calculate a 0-100 helpful-content score.
- Calculate all page ages from `helpful_content_runs.crawl_date`.
- Keep publication age and update age separate. Never replace an unavailable
  modification date with a publication date without recording
  `effective_update_basis = 'published_fallback'`.
- Use the recency buckets and `fresh_from_old` definition exactly as specified
  in the content recency framework.
- Seer study percentages are external descriptive context. Do not use them as a
  pass/fail threshold, expected domain distribution or imputed value.

## SQL completion gate

Run the checks below for the current `run_id`. Adapt only physical table or
column names recorded in `table_map_json`; do not weaken the invariants.

### Scope and uniqueness

1. The included target count equals `helpful_content_runs.target_baseline`.
2. Every included target has exactly one page-assessment row.
3. Every included target has exactly one freshness-assessment row.
4. No duplicate `(run_id, url, criterion_id)`, freshness `(run_id, url)`,
   evidence ID, finding ID or evidence-link tuple exists.
5. `target_completed` equals the count of included targets marked `completed`.

Representative queries; each duplicate/missing-row query must return zero rows:

```sql
WITH counts AS (
  SELECT
    r.run_id,
    r.target_baseline,
    count(*) FILTER (
      WHERE t.scope_role = 'target'
        AND t.eligibility_status = 'included'
    ) AS included_targets,
    r.target_completed,
    count(*) FILTER (
      WHERE t.scope_role = 'target'
        AND t.eligibility_status = 'included'
        AND t.assessment_status = 'completed'
    ) AS completed_targets
  FROM helpful_content_runs r
  LEFT JOIN helpful_content_targets t ON t.run_id = r.run_id
  WHERE r.run_id = '<run_id>'
  GROUP BY r.run_id, r.target_baseline, r.target_completed
)
SELECT *
FROM counts
WHERE target_baseline <> included_targets
   OR target_completed <> completed_targets;

SELECT t.url
FROM helpful_content_targets t
LEFT JOIN helpful_content_page_assessments a
  ON a.run_id = t.run_id AND a.url = t.url
WHERE t.run_id = '<run_id>'
  AND t.scope_role = 'target'
  AND t.eligibility_status = 'included'
GROUP BY t.url
HAVING count(a.url) <> 1;

SELECT t.url
FROM helpful_content_targets t
LEFT JOIN helpful_content_freshness_assessments f
  ON f.run_id = t.run_id AND f.url = t.url
WHERE t.run_id = '<run_id>'
  AND t.scope_role = 'target'
  AND t.eligibility_status = 'included'
GROUP BY t.url
HAVING count(f.url) <> 1;

SELECT evidence_id, count(*)
FROM helpful_content_evidence
WHERE run_id = '<run_id>'
GROUP BY evidence_id
HAVING count(*) <> 1;
```

### Domain values and evidence integrity

6. Criterion IDs are only `HC01` through `HC18`; statuses and outcomes use only
   the enumerations above.
7. Each `verified_positive`, `verified_concern`, `supported_inference` and
   `mixed_evidence` criterion has at least one evidence link.
8. Each freshness assessment with `verified_positive`, `verified_concern`,
   `supported_inference` or `mixed_evidence` has at least one freshness evidence
   link.
9. Every evidence link resolves to an evidence row in the same run.
10. Every finding has at least one affected URL and at least one evidence link;
   its stored affected-page count equals the joined distinct URL count, and its
   denominator and percentage reproduce from stored rows.
11. A resolved or ambiguous primary focus has supporting evidence.

```sql
SELECT l.*
FROM helpful_content_evidence_links l
LEFT JOIN helpful_content_evidence e
  ON e.run_id = l.run_id AND e.evidence_id = l.evidence_id
WHERE l.run_id = '<run_id>' AND e.evidence_id IS NULL;

SELECT c.url, c.criterion_id
FROM helpful_content_criterion_assessments c
WHERE c.run_id = '<run_id>'
  AND c.status IN (
    'verified_positive', 'verified_concern',
    'supported_inference', 'mixed_evidence'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM helpful_content_evidence_links l
    WHERE l.run_id = c.run_id
      AND l.subject_type = 'criterion'
      AND l.subject_key = c.url || '#' || c.criterion_id
  );

SELECT f.url, f.freshness_outcome
FROM helpful_content_freshness_assessments f
WHERE f.run_id = '<run_id>'
  AND f.status IN (
    'verified_positive', 'verified_concern',
    'supported_inference', 'mixed_evidence'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM helpful_content_evidence_links l
    WHERE l.run_id = f.run_id
      AND l.subject_type = 'freshness'
      AND l.subject_key = f.url
  );

WITH finding_counts AS (
  SELECT
    f.finding_id,
    f.affected_pages_count,
    f.eligible_pages_count,
    f.affected_pages_pct,
    count(DISTINCT p.url) AS linked_pages,
    count(DISTINCT l.evidence_id) AS linked_evidence
  FROM helpful_content_findings f
  LEFT JOIN helpful_content_finding_pages p
    ON p.run_id = f.run_id AND p.finding_id = f.finding_id
  LEFT JOIN helpful_content_evidence_links l
    ON l.run_id = f.run_id
   AND l.subject_type = 'finding'
   AND l.subject_key = f.finding_id
  WHERE f.run_id = '<run_id>'
  GROUP BY
    f.finding_id,
    f.affected_pages_count,
    f.eligible_pages_count,
    f.affected_pages_pct
)
SELECT *
FROM finding_counts
WHERE linked_pages = 0
   OR linked_evidence = 0
   OR affected_pages_count <> linked_pages
   OR eligible_pages_count <= 0
   OR affected_pages_count > eligible_pages_count
   OR abs(
        affected_pages_pct
        - (
            100.0 * affected_pages_count
            / NULLIF(eligible_pages_count, 0)
          )
      ) > 0.000001;
```

### Freshness calculation integrity

12. Every required freshness enum is non-null and uses only its declared values.
13. `age_since_publish_days` and `age_since_update_days` reproduce from the
    normalized dates and the run's crawl date; future dates are not represented
    as non-negative ages.
14. The update-recency bucket reproduces from `effective_update_date` and the
    crawl date using the content recency framework's calendar boundaries.
15. `fresh_from_old` is derived only from usable modification and publication
    claims using the study definition; it is null when either is unavailable.
16. `verified_stale` and `artificial_freshness_concern` use
    `status = 'verified_concern'`; no concern is derived from age alone.
17. Publication and modification claims are reconciled separately, and
    `date_relationship_status` reproduces from their normalized values.
18. `effective_update_basis` agrees with its source date. A
    `published_fallback` is allowed only when modification status is
    `unavailable` and is never described as an observed page update.
19. `none` freshness demand maps to `not_applicable`; `not_applicable`,
    `not_verifiable` and `mixed_evidence` outcomes use their matching evidence
    status.

Representative checks:

```sql
SELECT f.url
FROM helpful_content_freshness_assessments f
WHERE f.run_id = '<run_id>'
  AND (
    f.seer_content_type IS NULL OR f.seer_content_type NOT IN (
      'marketplace_aggregator', 'comparison_review', 'reference',
      'brand_corporate', 'blog_guide', 'news_editorial', 'other',
      'not_verifiable'
    )
    OR f.freshness_demand IS NULL OR f.freshness_demand NOT IN (
      'high', 'medium', 'low', 'none', 'not_verifiable'
    )
    OR f.publication_date_status IS NULL
      OR f.publication_date_status NOT IN (
        'consistent_multiple', 'single_claim', 'conflicting',
        'invalid_future', 'unavailable'
      )
    OR f.modification_date_status IS NULL
      OR f.modification_date_status NOT IN (
        'consistent_multiple', 'single_claim', 'conflicting',
        'invalid_future', 'unavailable'
      )
    OR f.date_relationship_status IS NULL
      OR f.date_relationship_status NOT IN (
        'consistent', 'modified_before_published', 'not_verifiable'
      )
    OR f.effective_update_basis IS NULL
      OR f.effective_update_basis NOT IN (
        'modified_claim', 'published_fallback', 'not_verifiable'
      )
    OR f.update_recency_bucket IS NULL
      OR f.update_recency_bucket NOT IN (
        'le_3_months', 'gt_3_months_le_1_year', 'gt_1_le_2_years',
        'gt_2_le_3_years', 'gt_3_le_5_years', 'gt_5_years',
        'future_date', 'not_verifiable'
      )
    OR f.freshness_outcome IS NULL OR f.freshness_outcome NOT IN (
      'current_supported', 'verified_stale',
      'artificial_freshness_concern', 'maintenance_review_candidate',
      'evergreen_no_refresh_need_observed', 'mixed_evidence',
      'not_verifiable', 'not_applicable'
    )
    OR f.status IS NULL OR f.status NOT IN (
      'verified_positive', 'verified_concern', 'supported_inference',
      'mixed_evidence', 'not_verifiable', 'not_applicable'
    )
    OR f.confidence IS NULL OR f.confidence NOT IN ('high', 'medium', 'low')
  );

SELECT f.url
FROM helpful_content_freshness_assessments f
JOIN helpful_content_runs r ON r.run_id = f.run_id
WHERE f.run_id = '<run_id>'
  AND (
    f.age_since_publish_days IS DISTINCT FROM
      CASE
        WHEN f.published_date IS NULL THEN NULL
        ELSE date_diff('day', f.published_date, r.crawl_date)
      END
    OR f.age_since_update_days IS DISTINCT FROM
      CASE
        WHEN f.effective_update_date IS NULL THEN NULL
        ELSE date_diff('day', f.effective_update_date, r.crawl_date)
      END
  );

SELECT f.url, f.update_recency_bucket
FROM helpful_content_freshness_assessments f
JOIN helpful_content_runs r ON r.run_id = f.run_id
WHERE f.run_id = '<run_id>'
  AND f.update_recency_bucket IS DISTINCT FROM
    CASE
      WHEN f.effective_update_date IS NULL THEN 'not_verifiable'
      WHEN f.effective_update_date > r.crawl_date THEN 'future_date'
      WHEN f.effective_update_date >= r.crawl_date - INTERVAL '3 months'
        THEN 'le_3_months'
      WHEN f.effective_update_date >= r.crawl_date - INTERVAL '1 year'
        THEN 'gt_3_months_le_1_year'
      WHEN f.effective_update_date >= r.crawl_date - INTERVAL '2 years'
        THEN 'gt_1_le_2_years'
      WHEN f.effective_update_date >= r.crawl_date - INTERVAL '3 years'
        THEN 'gt_2_le_3_years'
      WHEN f.effective_update_date >= r.crawl_date - INTERVAL '5 years'
        THEN 'gt_3_le_5_years'
      ELSE 'gt_5_years'
    END;

SELECT f.url
FROM helpful_content_freshness_assessments f
JOIN helpful_content_runs r ON r.run_id = f.run_id
WHERE f.run_id = '<run_id>'
  AND f.fresh_from_old IS DISTINCT FROM
    CASE
      WHEN f.effective_update_basis = 'modified_claim'
        AND f.modification_date_status IN (
          'consistent_multiple', 'single_claim'
        )
        AND f.publication_date_status IN (
          'consistent_multiple', 'single_claim'
        )
        AND f.date_relationship_status = 'consistent'
        AND f.modified_date IS NOT NULL
        AND f.published_date IS NOT NULL
      THEN f.modified_date >= r.crawl_date - INTERVAL '1 year'
        AND f.published_date <= r.crawl_date - INTERVAL '2 years'
      ELSE NULL
    END;

SELECT url
FROM helpful_content_freshness_assessments
WHERE run_id = '<run_id>'
  AND freshness_outcome IN (
    'verified_stale', 'artificial_freshness_concern'
  )
  AND status IS DISTINCT FROM 'verified_concern';

SELECT url
FROM helpful_content_freshness_assessments
WHERE run_id = '<run_id>'
  AND (
    (freshness_demand = 'none'
      AND freshness_outcome IS DISTINCT FROM 'not_applicable')
    OR (freshness_outcome = 'not_applicable'
      AND (
        freshness_demand IS DISTINCT FROM 'none'
        OR status IS DISTINCT FROM 'not_applicable'
      ))
    OR (freshness_outcome = 'not_verifiable'
      AND status IS DISTINCT FROM 'not_verifiable')
    OR (freshness_outcome = 'mixed_evidence'
      AND status IS DISTINCT FROM 'mixed_evidence')
    OR (freshness_outcome = 'evergreen_no_refresh_need_observed'
      AND freshness_demand IS DISTINCT FROM 'low')
  );

SELECT f.url
FROM helpful_content_freshness_assessments f
JOIN helpful_content_runs r ON r.run_id = f.run_id
WHERE f.run_id = '<run_id>'
  AND (
    (f.publication_date_status IN ('consistent_multiple', 'single_claim')
      AND (f.published_date IS NULL OR f.published_date > r.crawl_date))
    OR (f.publication_date_status = 'invalid_future'
      AND (f.published_date IS NULL OR f.published_date <= r.crawl_date))
    OR (f.publication_date_status IN ('conflicting', 'unavailable')
      AND f.published_date IS NOT NULL)
    OR (f.modification_date_status IN ('consistent_multiple', 'single_claim')
      AND (f.modified_date IS NULL OR f.modified_date > r.crawl_date))
    OR (f.modification_date_status = 'invalid_future'
      AND (f.modified_date IS NULL OR f.modified_date <= r.crawl_date))
    OR (f.modification_date_status IN ('conflicting', 'unavailable')
      AND f.modified_date IS NOT NULL)
  );

SELECT f.url
FROM helpful_content_freshness_assessments f
WHERE f.run_id = '<run_id>'
  AND f.date_relationship_status IS DISTINCT FROM
    CASE
      WHEN f.publication_date_status NOT IN (
          'consistent_multiple', 'single_claim'
        )
        OR f.modification_date_status NOT IN (
          'consistent_multiple', 'single_claim'
        )
        OR f.published_date IS NULL
        OR f.modified_date IS NULL
        THEN 'not_verifiable'
      WHEN f.modified_date < f.published_date
        THEN 'modified_before_published'
      ELSE 'consistent'
    END;

SELECT f.url
FROM helpful_content_freshness_assessments f
WHERE f.run_id = '<run_id>'
  AND (
    (f.effective_update_basis = 'modified_claim'
      AND (
        f.modification_date_status NOT IN (
          'consistent_multiple', 'single_claim', 'invalid_future'
        )
        OR f.modified_date IS NULL
        OR f.effective_update_date IS DISTINCT FROM f.modified_date
      ))
    OR
    (f.effective_update_basis = 'published_fallback'
      AND (
        f.modification_date_status IS DISTINCT FROM 'unavailable'
        OR f.modified_date IS NOT NULL
        OR f.publication_date_status NOT IN (
          'consistent_multiple', 'single_claim'
        )
        OR f.published_date IS NULL
        OR f.effective_update_date IS DISTINCT FROM f.published_date
      ))
    OR
    (f.effective_update_basis = 'not_verifiable'
      AND (
        f.effective_update_date IS NOT NULL
        OR (
          f.modification_date_status IN (
            'consistent_multiple', 'single_claim', 'invalid_future'
          )
          AND f.modified_date IS NOT NULL
        )
        OR (
          f.modification_date_status = 'unavailable'
          AND f.publication_date_status IN (
            'consistent_multiple', 'single_claim'
          )
          AND f.published_date IS NOT NULL
        )
      ))
  );
```

### Source coverage and prohibited claims

20. Every included target has stored rendered HTML. If a known failure is
    retained in a partial run, it is counted explicitly and every DOM-dependent
    criterion for that URL is `not_verifiable`.
21. Contrast evidence names the completed Screaming Frog Accessibility/axe rule
    and affected locator. Font-size evidence names Mobile/Lighthouse
    `Illegible Font Size`. Readability evidence names the Flesch field.
22. Date evidence preserves the visible, structured-data, sitemap or HTTP source
    locator and does not present a source claim as verified substantive change.
23. No evidence, assessment, finding or methodological source contains
    Photowant.
24. No evidence, assessment or finding claims an official Google rating,
    guaranteed ranking impact, AI-citation impact or an unobserved fact. No Seer
    percentage is used as a page/domain pass threshold.

### Finalization

After the gate passes:

25. Derive and store final row counts and `target_completed` for the current
    `run_id`.
26. Set `completed_at` and `run_status = 'validated'`.
27. Return the operational handoff defined above. Do not generate a report or
    invoke another skill.

### Optional export reconciliation

Only when the user requested an export:

28. Export the selected CSV or NDJSON snapshot from exactly one validated
    `run_id`.
29. Re-read each created export with DuckDB and confirm:
    - URL-matrix rows equal the included target baseline;
    - evidence NDJSON rows equal `helpful_content_evidence` rows;
    - page-assessment NDJSON top-level rows equal page-assessment rows.
30. Keep `run_status = 'validated'`; an optional export is not another analysis
    state.

Warnings such as evidence rows that are not yet linked require review and an
explicit decision. They are not silently treated as success.
