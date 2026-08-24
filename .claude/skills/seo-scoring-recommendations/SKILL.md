---
name: seo-scoring-recommendations
description: >
  Creates area scores, overall SEO health score, audit coverage score, confidence
  labels and prioritized recommendations from file-based SEO audit findings. Separates
  health from data coverage and avoids penalizing missing files.
user-invokable: true
argument-hint: "[issue-register-and-metric-coverage]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# SEO Scoring and Recommendations

## Purpose

Convert evidence-led findings into:
- area health scores
- area data coverage scores
- area confidence labels
- overall score according to the applicable score case (`SEO Health Score`, `Scope-adjusted Health Score` or `Observed Health Score`)
- overall Audit Coverage Score
- prioritized recommendations
- validation plan

This skill must separate website health from audit completeness.

## Stufe 0 — Qdrant SEO-Wissen abrufen

Rufe vor der Scoring- und Empfehlungs-Erstellung relevantes SEO-Wissen aus Qdrant ab.

```
qdrant-find: "SEO recommendations prioritization quick wins high impact issues"
qdrant-find: "SEO health score audit coverage scoring methodology"
```

Verwende die abgerufenen Ergebnisse als Hintergrundwissen für die Einordnung und Begründung von Empfehlungen.

Die Abfragen werden immer ausgeführt — unabhängig davon, ob der Nutzer explizit danach fragt.

## Core Principle

Missing data affects coverage and confidence, not health.

Observed defects affect health.

Do not output a precise score when the data basis is insufficient.

## Required Inputs

### Global Hard Prerequisites

If any of the following is missing, stop immediately. Do not produce area scores, overall scores, recommendations or a validation plan. Output only:

```text
Scoring blocked: [artifact] was not produced.
Required to unblock: ensure [artifact] is produced by seo-data-foundation or the Orchestrator and re-run this skill.
```

- `issue_register` — without validated findings, score derivation is not possible
- `evidence_ledger` — without referenced evidence, scoring logic cannot be verified
- `analysis_readiness_report` — without effective readiness labels, no area can be reliably included or excluded from scoring
- `metric_coverage_report` — without metric computability records, the scoring logic cannot distinguish `not computable` from `zero findings`

### Conditional Prerequisites

Required only when computing specific outputs. If absent, skip the dependent output and document:

- `file_inventory` — required for Data Coverage Score and source-level completeness claims; if absent, set `data_coverage` to `not_computable` for all areas and document:

```text
file_inventory not available. Data Coverage Score cannot be computed.
```

- `schema_registry` — required for field-completeness inputs and field-level auditability claims; if absent, field-completeness claims are suppressed

### Quality-Control Prerequisites

If missing, scoring continues with the following restrictions:

- `data_quality_report` — if absent: empty-cell rules and quality-driven confidence caps cannot be applied; document:

```text
data_quality_report not available. Scoring proceeds without data-quality-driven confidence adjustments.
Do not apply quality-derived confidence caps. Determine confidence only from source scope,
evidence type, join coverage and metric coverage.
```

- `join_key_report` — if absent: no join-confidence-based score adjustments; cross-source claims treated as lower confidence; document:

```text
join_key_report not available. Cross-source confidence reductions cannot be applied.
```

Note: `metric_coverage_report` is a Global Hard Prerequisite (see above), not a Quality-Control input. Its absence blocks scoring entirely because the skill cannot distinguish `not computable` from `zero findings`.

### Contextual Inputs

Present to enrich scoring; scoring can proceed without them but with reduced context:

- `area_diagnosis_outputs` — the complete markdown output of each completed diagnosis skill; specifically the findings, score inputs, and recommendation candidates sections; if absent for a given area, scoring relies exclusively on `issue_register` and `evidence_ledger` for that area

### analysis_readiness_report Pre-Check

Before scoring, read the `effective_readiness_label` field for each area from `analysis_readiness_report`. If `effective_readiness_label` is absent (e.g., pre-existing reports generated before this field was introduced), fall back to `readiness_label`.

- `ready`: include area in scoring at full confidence.
- `partially_ready`: include area in scoring; document coverage gaps. Cap confidence at `medium` only for findings that derived exclusively from blocked sub-areas or low-scope sources — not as a uniform area-wide cap. Findings from fully available sub-areas retain their own source-based confidence. If a diagnosis skill reported that specific sub-areas are blocked, apply the following sub-area rule:
  - Only deduct points for findings that were computable. Do not penalize uncomputable sub-areas.
  - Reduce the area's data coverage score proportionally to the blocked sub-area's share of total area coverage.
  - Document sub-area blocks in `score_rationale` under `Non-computable metrics` and `Coverage`.
- `blocked_missing_data` or `blocked_low_quality_data`: exclude area from the full-audit health score calculation. This area contributes to Case 3 (`observed_health_score`) scoring — the reported overall score will be `Observed Health Score`, not `SEO Health Score`. Output:

```text
[Area] excluded from full-audit health score: blocked — insufficient data.
Reason: [reason from readiness report].
Coverage: [n]% — not scored.
Excluded due to: missing_data
Overall score case: Case 3 (Observed Health Score)
```

- `blocked_late_discovery`: exclude area from the full-audit health score calculation (blocked after Phase 2 late discovery). Case 3 applies. Output:

```text
[Area] excluded from full-audit health score: blocked by late discovery during diagnosis.
Reason: [reason from late_discoveries entry in analysis_readiness_report].
Coverage: [n]% — not scored.
Excluded due to: late_discovery
Overall score case: Case 3 (Observed Health Score)
```

- `not_relevant`: exclude area from scoring without coverage penalty. Do not reduce Audit Coverage Score for out-of-scope areas. This area contributes to Case 2 (`scope_adjusted_health_score`) if no other areas are blocked for data reasons. Output:

```text
[Area] excluded from full-audit health score: marked not_relevant — out of audit scope.
Excluded due to: scope
Overall score case: Case 2 (Scope-adjusted Health Score) if no data-blocked areas; Case 3 if any area is also data-blocked
```

If `analysis_readiness_report` was not produced, scoring is blocked (see Global Hard Prerequisites above). Do not apply any fallback behavior.

### Special Handling for Selected Family-B Metric Status Values

The following `metric_status` values from the standard Family-B taxonomy require specific scoring treatment:

- `field_data_only` (most relevant to Performance): the metric requires field data (CrUX/RUM) which was not uploaded; a lab proxy may be available. Do not treat lab proxies as field data. Reduce coverage for the field-data component. Do not apply health penalties for unavailable field metrics.
- `experimental_only` (most relevant to GEO): the metric relates to emerging conventions (e.g., `llms.txt`) and must not be included in the main area health score. Report it in `## Score Caveats` only.

## Scoring Outputs

For each area:

```json
{
  "area": "technical",
  "health_score": 0,
  "health_status": "scored | insufficient_data",
  "data_coverage": 0,
  "data_coverage_status": "computed | not_computable",
  "confidence": "high | medium | low",
  "non_computable_metrics": [],
  "major_data_gaps": [],
  "score_rationale": ""
}
```

`data_coverage` is a number (0–100). If `file_inventory` is absent, set `data_coverage_status` = `not_computable` and `data_coverage` = `null`.

Overall:

```json
{
  "seo_health_score": null,
  "seo_health_score_note": "Case 1 only: use when all relevant areas are scored and none is excluded. Null in all other cases.",
  "scope_adjusted_health_score": null,
  "scope_adjusted_health_score_note": "Case 2 only: use when areas are excluded by scope (not_relevant) but all in-scope areas are scored. Null in all other cases.",
  "observed_health_score": null,
  "observed_health_score_note": "Case 3 only: use when one or more in-scope areas are excluded due to missing data or late discovery. Null in all other cases.",
  "full_audit_health_score_status": "computable | not_computable",
  "audit_coverage_score": 0,
  "overall_confidence": "high | medium | low",
  "scored_areas": [],
  "unscored_areas": [],
  "areas_excluded_due_to_scope": [],
  "areas_excluded_due_to_missing_data": [],
  "areas_excluded_due_to_late_discovery": [],
  "important_caveats": []
}
```

Field definitions for overall schema:
- `seo_health_score`: **Case 1 only** — all relevant areas scored, no exclusions. Set to `null` in Case 2 and Case 3.
- `scope_adjusted_health_score`: **Case 2 only** — some areas excluded as `not_relevant` (intentional audit scope), but all in-scope areas are scored. Not equivalent to `seo_health_score`. Set to `null` in Case 1 and Case 3.
- `observed_health_score`: **Case 3 only** — one or more in-scope areas excluded due to missing data or late discovery. Set to `null` in Case 1 and Case 2.
- `full_audit_health_score_status`: `computable` only in Case 1 (all relevant areas scored). `not_computable` in Case 2 (scope exclusions mean a full-audit score was never computed) and Case 3 (in-scope areas missing).
- `areas_excluded_due_to_scope`: areas with `effective_readiness_label` = `not_relevant` — intentional scope decision, not a data gap.
- `areas_excluded_due_to_missing_data`: areas with `effective_readiness_label` = `blocked_missing_data` or `blocked_low_quality_data`.
- `areas_excluded_due_to_late_discovery`: areas with `effective_readiness_label` = `blocked_late_discovery`.

## Area Weights

Default area weights for a full audit:

| Area | Weight |
|---|---:|
| Technical SEO | 30% |
| Content | 25% |
| Performance | 20% |
| Backlinks | 15% |
| GEO / LLM Citation Readiness | 10% |

Area exclusion rules:
- `not_relevant` area (scope exclusion): exclude from the full-audit health score denominator → Case 2 (`scope_adjusted_health_score`)
- `blocked_missing_data`, `blocked_low_quality_data`, or `blocked_late_discovery` area (data-blocked in-scope area): exclude from the health score denominator → Case 3 (`observed_health_score`)
- If any in-scope area is data-blocked, the overall score is Case 3 regardless of how many areas are `not_relevant`.

Report every exclusion explicitly with its type (scope vs. data-blocked) and the applicable score case.

### GEO Area Score Mapping

The GEO diagnosis skill produces three sub-scores: GEO Readiness Score, Retrieval Context Score, and AI Citation Visibility Score.

For the purpose of this skill's area output schema:
- `health_score` for the GEO area = **GEO Readiness Score only**
- Retrieval Context Score and AI Citation Visibility Score are reported as additional notes in `score_rationale` under a `Score Notes` section but do not contribute to `health_score` or the weighted `seo_health_score`
- If only Retrieval Context or AI Citation Visibility sub-scores are available (GEO Readiness not computable), set `health_status` to `insufficient_data` and report the available sub-scores in `score_rationale` as context only

Example:
- Backlinks missing → do not score backlink health.
- Reweight remaining computable areas; report as `Observed Health Score` (Case 3 — in-scope area excluded due to missing data).
- Lower `Audit Coverage Score` and confidence.

## Audit Coverage Score

Calculate separately.

Suggested coverage weights:

| Area | Weight |
|---|---:|
| Technical data coverage | 30% |
| Content data coverage | 25% |
| Performance data coverage | 20% |
| Backlink data coverage | 15% |
| GEO evidence coverage | 10% |

GSC/GA4 impact coverage is factored into the Technical and Content area coverage assessments
(as connector-enriched fields), not as a separate coverage dimension.

Adjust if audit scope is narrower.

Coverage is based on:
- available files
- available fields
- metric computability
- join coverage
- data quality
- source recency if known

## Confidence

Confidence is based on:
- source completeness
- field availability
- data quality
- join coverage
- consistency across sources
- sample size
- whether finding is directly observed or inferred

### Source-Specific Confidence Caps

Confidence caps derived from `seo-data-foundation` Step 6 (based on `scope_unknown` / `date_unknown` status) apply **per source**, not per area.

Rules:
- If a finding is supported by multiple sources, use the confidence cap of the source that is authoritative for that finding (e.g., crawl data for indexability findings; GSC data for search-demand findings).
- Do not apply the lowest available source cap uniformly across all findings in an area.
- If a finding requires a cross-source join and one source is `scope_unknown`, apply the cap only to claims that depend on the join result, not to claims from the non-capped source alone.
- Document in `score_rationale` which sources drove the confidence cap for which findings.

Example: Technical area has a Screaming Frog crawl (`scope_known`, cap = high) and a GSC connector export (`scope_partial`, cap = medium). Indexability findings from Screaming Frog alone can be rated high confidence. CTR-prioritized findings that join GSC to crawl are capped at medium.

### High Confidence
- direct source evidence
- required fields available
- sufficient affected rows
- strong join coverage if joined sources used
- low ambiguity

### Medium Confidence
- direct evidence but incomplete scope
- partial field coverage
- moderate join coverage
- some inference

### Low Confidence
- proxy evidence only
- important fields missing
- low join coverage
- ambiguous source semantics
- very small sample

## Severity Classification Basis

Before applying penalty bands, classify each finding using the Cross-Area Priority Matrix defined in CLAUDE.md. The matrix maps Impact × Scope to severity levels:
- **Impact axis**: blocks indexing/ranking/conversion | significantly harms performance/visibility/authority | likely improvement opportunity | best-practice deviation
- **Scope axis**: widespread (>20% of indexable pages or high-traffic URLs) | moderate (5–20%) | limited (<5%)

The resulting severity (Critical / High / Medium / Low) determines which penalty band applies. Within the band, calibrate by affected share, business impact, confidence and source quality.

Do not assign Critical severity to a finding that the matrix classifies as High or below without documenting the override reason in `score_rationale`.

## Finding Severity

Use severity based on actual impact, not just issue type.

### Kritisch
- blocks indexing/crawling of important pages
- widespread 5xx/4xx on important URLs
- canonical/noindex conflicts on high-value pages
- severe performance blockers on key tested pages
- major data-backed traffic/conversion risk
- severe toxic backlink/manual action evidence

### Hoch
- affects many indexable pages
- affects pages with high impressions/clicks/sessions/conversions
- significantly harms crawl efficiency, content clarity, LCP/TBT/CLS or authority flow
- creates duplicate/cannibalization risk with evidence

### Mittel
- affects moderate volume or less important pages
- likely improvement opportunity
- issue is real but limited in scope
- confidence medium

### Niedrig
- small scope
- best-practice improvement
- low impact
- low confidence or limited evidence

## Health Score Calculation

Start each computable area from 100 and subtract penalties only for validated findings.

Default penalty ranges:
- Critical: -20 to -40 points
- High: -8 to -20 points
- Medium: -3 to -8 points
- Low: -0 to -3 points

Calibrate the exact penalty inside the band by:
- affected share
- affected absolute count
- business/search impact
- confidence
- source coverage
- whether the issue is systemic/template-level
- whether the issue affects indexable/important pages
- whether the issue is directly observed or inferred

### Within-Band Calibration Guide

Use the following sub-band positions as starting priors. Adjust in either direction based on the calibration factors above.

| Band | Upper third (lean toward high end) | Middle third | Lower third (lean toward low end) |
|---|---|---|---|
| Critical (-20 to -40) | Widespread + high confidence + direct evidence + blocks indexing/conversion | Widespread or high-traffic + medium confidence | Moderate scope or inferred; strong but incomplete evidence |
| High (-8 to -20) | Widespread + high confidence + significant harm + important pages | Moderate scope + high confidence or widespread + medium confidence | Limited scope + high confidence or moderate scope + low confidence |
| Medium (-3 to -8) | Moderate scope + high confidence + clear improvement opportunity | Moderate scope + medium confidence | Limited scope or low confidence |
| Low (-0 to -3) | Multiple low-impact issues in same sub-area | Single best-practice deviation | Inferred or low-confidence; low scope |

When confidence is `low`, apply the lower third of the applicable band unless additional factors justify a higher penalty.

Rules:
- Do not deduct points for missing data.
- Missing data affects Coverage and Confidence, not Health.
- Do not mechanically add unlimited penalties.
- Cap total deductions at 100.
- Floor area score at 0.
- If too few metrics are computable, output `INSUFFICIENT_DATA` instead of a numeric score.
- Every score must include main deductions, coverage, confidence and non-computable metrics.

### Double-Counting Rule

If one root cause creates multiple symptoms, penalize the primary root cause once. Secondary symptom penalties are allowed only when they add independent impact, and their combined deduction should be capped at 50% of the primary root-cause penalty.

#### Cross-Area Double-Counting

If the same root cause (e.g., noindex on key pages) produces findings in both Technical SEO and GEO / LLM Citation Readiness diagnosis:
- Apply the primary penalty in the higher-weighted area (Technical SEO, weight 30%).
- In the GEO area, apply a secondary penalty only if the GEO-specific impact is independent (e.g., the page is indexable but the content structure is not AI-parseable).
- If the GEO finding is a direct consequence of the Technical finding (e.g., pages are noindexed, therefore AI crawlers cannot access them), treat it as a dependent symptom and cap the GEO penalty at 50% of the Technical penalty.
- Document cross-area overlap in `score_rationale` for both areas.

Example:
- A template noindexes all service pages.
- Do not separately over-penalize missing indexability, missing GSC traffic and canonical side effects.
- Treat as one critical root cause with related symptoms.

### score_rationale Required Format

`score_rationale` in every area score output is NOT a free-text field. It must follow this structure:

```text
Starting score: 100

Deductions:
- [Issue ID / finding description]: -[X] points ([severity band])
  Reason: [why this penalty was applied at this size within the band]
- [Issue ID / finding description]: -[X] points ([severity band])
  ...

Total deductions: -[Y] points
Final score: [100 - Y]

Non-computable metrics: [list or "none"]
Coverage: [n]%
Confidence: high | medium | low
Confidence caveat: [explain any confidence reductions due to scope_unknown, date_unknown, low join rate, etc.]
```

If `health_status` is `insufficient_data`, replace the above with:

```text
INSUFFICIENT_DATA
Reason: [which required metrics were not computable and why]
Minimum data needed to produce a score: [list]
```

## Data Coverage Calculation

Coverage should consider:
- source availability
- required fields
- optional/enhancement fields
- data quality
- row volume
- join success
- source recency

Example area coverage:
- Technical: internal crawl 50%, canonicals/directives 15%, hreflang 10%, schema 10%, images 10%, links/redirects 5%
- Content: metadata/headings 25%, word count/content 20%, duplicates 15%, GSC 25%, GA4 15%
- Backlinks: backlinks 35%, refdomains 25%, anchors 20%, link attributes 10%, link intersect 10%
- Performance: core lab metrics 25%, request waterfall 30%, Lighthouse diagnostics 20%, HAR 15%, field data 10%
- GEO: content/structure 30%, schema/entity 20%, crawl/indexability 15%, authority/backlinks 15%, query demand 10%, llms/bot data 10%

These are guidance, not rigid formulas.

## Recommendation Format

Every recommendation must include:

```json
{
  "recommendation_id": "R001",
  "area": "",
  "title": "",
  "priority": "Kritisch | Hoch | Mittel | Niedrig",
  "time_horizon": "Low Hanging Fruit | Mid Term | Long Term / Strategic",
  "current_state_problem": "",
  "negative_impact": "",
  "evidence_ids": [],
  "affected_scope": "",
  "expected_effect": "",
  "implementation_effort": "low | medium | high",
  "risk": "low | medium | high",
  "confidence": "high | medium | low",
  "validation_method": ""
}
```

### Evidence Gate Rule

A recommendation MUST have at least one `evidence_id` pointing to an entry in the `evidence_ledger`.

If no `evidence_id` can be assigned, do not create or classify a recommendation here. The Orchestrator has already applied one of three outcomes in Phase 3:
- `verified_for_recommendation_planning` — has `evidence_id`; this skill scores and prioritizes it.
- `converted_to_unverified_hypothesis` — Orchestrator classified it as `record_type: unverified_hypothesis` in the `issue_register`; this skill lists it in Section 10.4 only, with `confidence: low` and the `verification_requirement` from the `issue_register`.
- `discarded_action_candidate` — Orchestrator discarded it; this skill does not reference it anywhere.

Do not re-classify unverified hypotheses or create new hypotheses in this skill. Only entries already present in the `issue_register` as `record_type: unverified_hypothesis` may appear in Section 10.4. Also ensure these entries are reflected in Section 12 (Data Gaps and Non-Computable Metrics / Evidence Needed) when the hypothesis is blocked by a data gap rather than a logic gap.

This rule applies to all recommendations regardless of priority level, area, or time horizon.

### expected_effect Standard

`expected_effect` must state at minimum:
1. **Which metric improves** (e.g., CTR, LCP, organic sessions, referring domains)
2. **Direction of change** (e.g., increase, decrease, eliminate)
3. **Why this effect is expected** (linked to the root cause)
4. Where data allows, add a **magnitude estimate** (e.g., "approximately 10-20% CTR improvement on pages currently below 2%")

Do not use vague effects like "improve SEO" or "better performance." These are not actionable and cannot be validated.

Examples:
- Weak: "Improve organic visibility"
- Standard: "Increase CTR on the 47 high-impression pages with missing meta descriptions; pages with meta descriptions in the cohort currently show 3.1% CTR vs 1.4% without — expected improvement of 1-2 percentage points"
- Weak: "Fix LCP"
- Standard: "Reduce LCP on the tested page from 4.2s to below 2.5s by eliminating the render-blocking font CSS file (540ms) and deferring the third-party tag manager (320ms)"

### validation_method Standard

`validation_method` must state:
1. **What metric to measure** (the same metric named in `expected_effect`)
2. **How to measure it** (tool, report, export)
3. **When to measure** (timeframe or trigger)
4. **What counts as success** (threshold or comparison)

Examples:
- Weak: "Check in Screaming Frog"
- Standard: "Re-crawl and export metadata; filter indexable HTML pages; compare meta description coverage rate against current baseline of 68%; success = ≥ 95% coverage"
- Weak: "Monitor in GSC"
- Standard: "In GSC Search Results report, filter affected pages (URL filter: /service/*), compare average CTR before and after for a 28-day period post-deployment; success = average CTR ≥ 3.0% (up from current 1.4%)"
- Weak: "Run Lighthouse"
- Standard: "Re-run WebPageTest on the same test URL with identical settings (mobile, throttled 4G); compare LCP to baseline of 4.2s; success = LCP ≤ 2.5s"

## Time Horizon Rules

### Low Hanging Fruit
- low implementation effort
- clear evidence
- low risk
- immediate measurable benefit
- examples: metadata fixes, broken links, cache headers, obvious redirects, missing alt on key images

### Mid Term
- moderate implementation effort
- may require templates, content production, internal linking or script changes
- examples: content expansion, canonical cleanup, JS defer strategy, link reclamation, schema improvements

### Long Term / Strategic
- architecture, process, content strategy or authority building
- examples: site architecture redesign, content hub strategy, performance budget, entity/trust framework, linkable assets, template refactor

## Implementation Effort Criteria

Use these definitions for `implementation_effort` consistently across all recommendations:

| Effort Level | Criteria |
|---|---|
| `low` | ≤ 4 hours of work; no deployment required or CMS-based edit; single person; reversible without system risk; examples: title/meta text edits, redirect fixes, cache header changes, alt text additions |
| `medium` | 1–3 days; requires template or code change or content creation; may require developer involvement or deployment; limited system risk; examples: schema markup, canonical implementation, structured content expansion, JS defer strategy, internal linking changes |
| `high` | > 3 days; requires architectural change, significant content production, CMS reconfiguration, cross-team coordination or infrastructure change; non-trivial rollback; examples: site architecture redesign, international implementation, consent management rework, full template refactor, major performance stack changes |

When effort is genuinely unknown, use `medium` and add a note: `effort_note: "exact effort depends on [CMS / stack / team context]"`.

## Negative Impact Explanation

For every recommendation, explain the current negative impact in plain language.

Examples:
- Crawl waste: search engines spend crawl resources on URLs that should not be indexed.
- Indexability loss: important pages cannot be considered for ranking.
- Duplicate ambiguity: Google may choose the wrong page or split signals.
- CTR loss: high-impression pages may underperform because snippets are weak.
- LCP delay: users see important content late and conversion probability drops.
- TBT/main-thread cost: the page may react slowly to user input.
- Backlink waste: external authority points to pages that redirect, 404 or are non-indexable.
- GEO weakness: content is harder for AI systems to extract and cite.

## Output Structure

```markdown
## Scores

| Area | Health Score | Data Coverage | Confidence | Status |
|---|---:|---:|---|---|

### Overall

**Case 1 — All relevant areas scored (no exclusions):**
- SEO Health Score: [weighted score over all relevant areas]
- Audit Coverage Score:
- Overall Confidence:
- Scored Areas:
- Unscored Areas: none
- Main Caveats:

**Case 2 — Some areas excluded due to deliberate audit scope (`not_relevant`) only:**
- Scope-adjusted Health Score: [weighted score over scored in-scope areas only]
- Full-audit Health Score: not computable — out-of-scope areas excluded by design: [list]
- Audit Coverage Score:
- Overall Confidence:
- Scored Areas:
- Areas Excluded (scope): [list — not a data gap]
- Main Caveats:

**Case 3 — One or more in-scope areas excluded due to missing data or late discovery:**
- Observed Health Score (scored areas only): [weighted score over scored areas only]
- Full-audit Health Score: not computable — excluded areas: [list with exclusion reason per area]
- Audit Coverage Score:
- Overall Confidence:
- Scored Areas:
- Areas Excluded (missing data): [list]
- Areas Excluded (late discovery): [list]
- Areas Excluded (scope): [list, if any]
- Main Caveats:

Use Case 3 whenever any in-scope area is blocked. Use Case 2 only when all exclusions are intentional `not_relevant` scope decisions. Use Case 1 only when every area relevant to the audit is scored.

## Prioritized Recommendations

### Low Hanging Fruit
| Priority | Area | Recommendation | Impact | Evidence | Effort | Confidence |
|---|---|---|---|---|---|---|

### Mid Term
...

### Long Term / Strategic
...

### Unverified Hypotheses / Evidence Needed

Plausible but unverified audit observations that require additional data before they can become findings or recommendations. These are **not** recommendations. For each hypothesis, state:
- what data would confirm or reject it
- the expected impact if confirmed
- confidence: low
- these items are excluded from health score deductions and the prioritized Recommendation Plan

## Validation Plan

| Recommendation | Success Metric | Required Data | How to Validate |
|---|---|---|---|
```

## Score Caveats

Always include caveats:
- data areas not uploaded
- metrics not computable
- joins with low match rate
- lab vs field data distinction
- source date range limitations
- sample/export limitations

## Do Not

- Do not produce a score if all area data is insufficient.
- Do not punish missing files.
- Do not hide missing files.
- Do not use false precision.
- Do not recommend actions without evidence.
- Do not treat every best-practice deviation as high priority.
