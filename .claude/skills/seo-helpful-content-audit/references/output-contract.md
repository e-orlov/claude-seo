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
subject_type              page_assessment | criterion | finding
subject_key               URL | URL#HC01 | HC-F001
evidence_id
```

Enforce uniqueness on `(run_id, subject_type, subject_key, evidence_id)`.

## Persistence and resume

Insert evidence and assessments directly in DuckDB. Commit each bounded batch
before starting the next. On resume, select included targets whose
`assessment_status != 'completed'`; do not reconstruct state from an export or
other file.

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
- page-assessment, criterion, evidence and finding row counts;
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
| `helpful-content-page-assessments.ndjson` | One object per page assembled from page and criterion rows |

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

## SQL completion gate

Run the checks below for the current `run_id`. Adapt only physical table or
column names recorded in `table_map_json`; do not weaken the invariants.

### Scope and uniqueness

1. The included target count equals `helpful_content_runs.target_baseline`.
2. Every included target has exactly one page-assessment row.
3. No duplicate `(run_id, url, criterion_id)`, evidence ID, finding ID or
   evidence-link tuple exists.
4. `target_completed` equals the count of included targets marked `completed`.

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

SELECT evidence_id, count(*)
FROM helpful_content_evidence
WHERE run_id = '<run_id>'
GROUP BY evidence_id
HAVING count(*) <> 1;
```

### Domain values and evidence integrity

5. Criterion IDs are only `HC01` through `HC18`; statuses and outcomes use only
   the enumerations above.
6. Each `verified_positive`, `verified_concern`, `supported_inference` and
   `mixed_evidence` criterion has at least one evidence link.
7. Every evidence link resolves to an evidence row in the same run.
8. Every finding has at least one affected URL and at least one evidence link;
   its stored affected-page count equals the joined distinct URL count, and its
   denominator and percentage reproduce from stored rows.
9. A resolved or ambiguous primary focus has supporting evidence.

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

### Source coverage and prohibited claims

10. Every included target has stored rendered HTML. If a known failure is
    retained in a partial run, it is counted explicitly and every DOM-dependent
    criterion for that URL is `not_verifiable`.
11. Contrast evidence names the completed Screaming Frog Accessibility/axe rule
    and affected locator. Font-size evidence names Mobile/Lighthouse
    `Illegible Font Size`. Readability evidence names the Flesch field.
12. No evidence, assessment, finding or methodological source contains
    Photowant.
13. No evidence, assessment or finding claims an official Google rating,
    guaranteed ranking impact or an unobserved fact.

### Finalization

After the gate passes:

14. Derive and store final row counts and `target_completed` for the current
    `run_id`.
15. Set `completed_at` and `run_status = 'validated'`.
16. Return the operational handoff defined above. Do not generate a report or
    invoke another skill.

### Optional export reconciliation

Only when the user requested an export:

17. Export the selected CSV or NDJSON snapshot from exactly one validated
    `run_id`.
18. Re-read each created export with DuckDB and confirm:
    - URL-matrix rows equal the included target baseline;
    - evidence NDJSON rows equal `helpful_content_evidence` rows;
    - page-assessment NDJSON top-level rows equal page-assessment rows.
19. Keep `run_status = 'validated'`; an optional export is not another analysis
    state.

Warnings such as evidence rows that are not yet linked require review and an
explicit decision. They are not silently treated as success.
