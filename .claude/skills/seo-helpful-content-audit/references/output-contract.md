# Standalone DuckDB and Output Contract

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
run_status                collecting | assessing | partial | validated | exported
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
priority                  critical | high | medium | low
recommendation
validation
```

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
`assessment_status != 'completed'`; do not reconstruct state from a report or
NDJSON export.

Derive `target_completed` from completed included target rows before the
completion gate. If work stops early, set `run_status = 'partial'` and report
the exact completed and remaining counts.

## Output location

Unless the user supplies an existing audit directory, create:

```text
clients/<domain>/<YYYY-MM-helpful-content-audit>/output/
```

Required handoff outputs:

| File | Purpose |
|---|---|
| `helpful-content-audit.md` | Client-facing audit report |
| `helpful-content-url-matrix.csv` | One row per included target URL |
| `helpful-content-evidence.ndjson` | Direct export of the run's evidence rows |
| `helpful-content-page-assessments.ndjson` | Direct export of the run's page and criterion assessments |

The CSV and NDJSON files are immutable exports of validated DuckDB rows, not
additional working stores. Generate them only after the SQL completion gate.
If regeneration is needed, overwrite them from the same `run_id`; never patch
them independently.

Do not write to `clients/evidence_registry.md`. This standalone audit uses
`HC-*` IDs and is not part of the shared evidence/scoring pipeline.

## URL matrix

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

## Markdown report

Use the user's requested language. If none is stated, use the language of the
request. Keep stable field/status values in English inside code or artifact
references, but translate prose and table labels.

Required structure:

```markdown
# Helpful, Reliable, People-First Content Audit: <domain>

## 1. Scope and evidence basis
## 2. Executive assessment
## 3. Domain context
## 4. Page-level outcome distribution
## 5. Verified strengths
## 6. Verified concerns
## 7. Supported but unverified interpretations
## 8. Prioritized actions
## 9. URL matrix
## 10. Verification boundaries
## 11. Methodological sources
```

The scope and evidence-basis section must state:

- crawl ID and date, audit mode and requested scope;
- included-target denominator and completed-target count;
- whether stored HTML was confirmed as rendered, unconfirmed or unavailable;
- availability of Flesch, Accessibility/axe and Mobile/Lighthouse
  `Illegible Font Size` data;
- exclusions and material collection limitations.

The executive assessment may summarize only patterns traceable to stored page
assessments and evidence rows. Keep source coverage separate from quality
outcomes: unavailable evidence is not a positive result.

For up to 100 targets, include the complete compact URL matrix. For larger
scopes, include the distribution and highest-priority rows and link to the
complete CSV.

Each verified concern row includes:

```text
Finding ID | Scope | Observation | Why it matters | Affected pages | Priority | Recommendation | Validation | Evidence
```

Every verified finding must join to at least one `HC-E####` row.
`supported_inference` items remain in their own section and cannot be phrased as
facts. Do not calculate a 0-100 helpful-content score.

Every recommendation must name the observed issue, affected scope, proposed
change, reason, validation method, priority and supporting evidence. Avoid
generic actions such as "improve E-E-A-T", "add more content" or "make the
page helpful" unless they are converted into a concrete change tied to a
verified observation.

The verification-boundaries section must distinguish direct observations,
supported interpretations and facts that the available crawl cannot establish.
It must disclose partial coverage and must not describe `not_verifiable` checks
as passes.

## Calculation rules

- State one denominator immediately before every distribution table.
- Show numerator, denominator and percentage together.
- Round displayed percentages to one decimal place, but calculate from raw rows.
- Do not average Flesch across different languages without separate groups.
- Do not aggregate `not_applicable` with passes or concerns.
- Do not convert missing fields to zero.
- For a criterion rate, use only URLs for which that criterion was verifiable
  and state that denominator.

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
   its stored affected-page count equals the joined distinct URL count.
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
  GROUP BY f.finding_id, f.affected_pages_count
)
SELECT *
FROM finding_counts
WHERE linked_pages = 0
   OR linked_evidence = 0
   OR affected_pages_count <> linked_pages;
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
13. No row or report passage claims an official Google rating, guaranteed
    ranking impact or an unobserved fact.

### Export reconciliation

After the gate passes:

14. Export CSV and NDJSON from DuckDB for exactly one `run_id`.
15. Re-read the exports with DuckDB and confirm:
    - CSV rows equal the included target baseline;
    - evidence NDJSON rows equal `helpful_content_evidence` rows;
    - page-assessment NDJSON top-level rows equal page-assessment rows.
16. Generate the Markdown report only from gate-passing aggregates and cited
    rows. Review it for the prohibited claims above.
17. Set `run_status = 'exported'` only after all reconciliation checks pass.

Warnings such as evidence rows that are not yet linked require review and an
explicit decision. They are not silently treated as success.
