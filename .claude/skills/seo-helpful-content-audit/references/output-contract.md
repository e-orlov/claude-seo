# Standalone Output Contract

## Output location

Unless the user supplies an existing audit directory, create:

```text
clients/<domain>/<YYYY-MM-helpful-content-audit>/
  work/
  output/
```

Keep raw Screaming Frog exports in its allowed MCP directory and record their
paths in the scope artifact. Keep derived local working files under `work/`.

This skill produces Markdown, CSV and NDJSON only. It does not create DOCX or use
the shared report renderer.

## Required artifacts

| File | Purpose |
|---|---|
| `work/helpful-content-scope.json` | Run identity, target/context scope, crawl details, source-field availability and working-table/file paths |
| `work/helpful-content-page-assessments.ndjson` | Complete resumable assessment, one record per target URL |
| `output/helpful-content-url-matrix.csv` | Human-readable one-row-per-target summary |
| `output/helpful-content-evidence.ndjson` | Standalone evidence ledger |
| `output/helpful-content-audit.md` | Client-facing audit report |

The scope JSON is a working artifact; the other four are handoff artifacts.

Do not write to `clients/evidence_registry.md`. This standalone audit uses local
IDs and is not part of the shared evidence/scoring pipeline.

## Scope artifact

Minimum fields:

```json
{
  "skill": "seo-helpful-content-audit",
  "skill_version": "1.0.0",
  "run_id": "example.com-2026-09-02T103000Z",
  "mode": "domain",
  "requested_scope": ["https://example.com/"],
  "crawl_id": "...",
  "crawl_date": "...",
  "crawl_complete": true,
  "html_render_state": "confirmed_rendered",
  "target_baseline": 120,
  "target_completed": 120,
  "context_urls": [],
  "excluded_counts": {"non_200": 2, "non_indexable": 8, "no_rendered_html": 1},
  "source_availability": {
    "raw_html": "available",
    "visible_text": "available",
    "flesch": "available",
    "accessibility": "available",
    "illegible_font_size": "unavailable"
  },
  "files": {},
  "tables": {}
}
```

Use `available`, `partial`, `unavailable` or `failed` only inside this skill-local
artifact. These values do not extend or modify repository-wide status taxonomies.

## Page-assessment record

Write one JSON object per target URL after completing it. Save after every batch.

```json
{
  "url": "https://example.com/page",
  "scope_role": "target",
  "page_type": {"value": "editorial guide", "confidence": "high", "evidence_ids": ["HC-E0001"]},
  "purpose": {"value": "help a reader complete ...", "confidence": "high", "evidence_ids": ["HC-E0001"]},
  "audience": {"value": "...", "confidence": "medium", "evidence_ids": ["HC-E0002"]},
  "primary_focus": {"value": "...", "status": "resolved", "confidence": "high", "evidence_ids": ["HC-E0003"]},
  "secondary_topics": [],
  "likely_user_task": "...",
  "ymyl": {"value": "unlikely", "reason": "...", "confidence": "high"},
  "criteria": [
    {
      "criterion_id": "HC01",
      "status": "verified_positive",
      "observation": "...",
      "interpretation": "...",
      "confidence": "high",
      "evidence_ids": ["HC-E0004"]
    }
  ],
  "verified_strengths": [],
  "verified_concerns": [],
  "supported_inferences": [],
  "not_verifiable": [],
  "overall_outcome": "verified_improvement_opportunities",
  "completed_at": "..."
}
```

Allowed `primary_focus.status` values:

- `resolved`
- `focus_ambiguous`
- `not_verifiable`

Allowed `overall_outcome` values:

- `no_material_verified_concerns`
- `verified_improvement_opportunities`
- `material_verified_concerns`
- `serious_verified_trust_or_harm_concerns`
- `insufficient_evidence`

These are audit outcomes, not Google ratings or ranking predictions.

## Evidence record

Assign monotonically increasing run-local IDs: `HC-E0001`, `HC-E0002`, etc.

```json
{
  "evidence_id": "HC-E0001",
  "url": "https://example.com/page",
  "source_type": "rendered_html",
  "source_locator": "page > main > h1",
  "observation": "The H1 describes ...",
  "raw_value": "short value or count",
  "collected_at": "...",
  "confidence": "high",
  "limitations": ""
}
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

Evidence records contain observations, not recommendations. Keep quotations
short and necessary. Prefer paraphrase plus a selector/property locator.

## URL matrix

CSV columns, in this order:

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

Use semicolon-separated lists within a cell. Preserve one row per target URL.
Do not omit rows that have no concern.

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

### Scope and evidence basis

State:

- crawl ID/date and target mode;
- target denominator and completed count;
- whether rendered HTML was confirmed;
- availability of Flesch, Accessibility/contrast and `Illegible Font Size`;
- exact exclusions that materially affect interpretation.

Do not turn this into a generic shopping list of missing tools or data.

### Executive assessment

Summarize only patterns traceable to page records. State coverage separately
from content outcome. Do not calculate a 0-100 helpful-content score.

### Finding tables

Each verified concern row includes:

```text
Finding ID | Scope | Observation | Why it matters | Affected pages | Priority | Recommendation | Validation | Evidence
```

Assign run-local finding IDs `HC-F001`, `HC-F002`, etc. Every verified finding
must cite one or more `HC-E####` records. `supported_inference` items must be kept
in their own section and cannot be phrased as facts.

### URL matrix in Markdown

For up to 100 target URLs, include the complete compact matrix in the report.
For larger scopes, include an outcome distribution and the highest-priority rows,
then link to `helpful-content-url-matrix.csv`, which remains complete.

### Recommendations

Every recommendation must include:

- the observed problem or opportunity;
- affected scope;
- concrete change;
- reason the change addresses the page purpose;
- validation method;
- priority and evidence IDs.

Store priorities as `critical`, `high`, `medium` or `low`; translate the visible
label into the report language.

Avoid generic advice such as "improve E-E-A-T", "add more content" or "make the
page more helpful". Do not prescribe lists, FAQs, author boxes or longer copy
unless the evidence shows why that form solves the identified task failure.

### Verification boundaries

Briefly distinguish:

- direct instrument/DOM checks completed;
- supported interpretations;
- material questions the selected evidence cannot establish.

Do not describe `not_verifiable` items as passed. Do not claim complete factual,
visual, reputation or accessibility validation.

## Calculation rules

- State one denominator immediately before every distribution table.
- Show numerator, denominator and percentage together.
- Round displayed percentages to one decimal place, but calculate from raw counts.
- Do not average Flesch values across different languages without separate
  language groups.
- Do not aggregate `not_applicable` criteria with passes or concerns.
- Do not convert missing fields to zero.
- A domain-level concern rate includes only URLs for which that criterion was
  actually verifiable; state that criterion-specific denominator.

## Final QA

Before delivery, validate programmatically where possible:

```bash
python .claude/skills/seo-helpful-content-audit/scripts/validate_audit_outputs.py \
  clients/<domain>/<YYYY-MM-helpful-content-audit>
```

The command must return exit code 0. Review warnings; correct them or document
why the retained state is intentional.

1. Scope baseline equals target page-assessment record count, unless the scope
   artifact explicitly records a partial run.
2. URL matrix has exactly one row per target assessment.
3. Every evidence ID is unique.
4. Every cited evidence ID exists.
5. Every `verified_concern` and `verified_positive` criterion has evidence.
6. `not_verifiable` criteria do not appear in verified-strength counts.
7. Finding percentages reproduce from their page lists.
8. No official Google rating, ranking prediction or unsupported ranking-factor
   statement appears.
9. No Photowant source or citation appears.
10. The report names Screaming Frog as the evidence source for contrast,
    `Illegible Font Size` and Flesch claims.
