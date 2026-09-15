# GEO Audit Scoring Policy

Policy version: `1.0.0`  
Policy status: `frozen`  
Effective date: `2026-09-15`  
Policy fingerprint: `sha256:77da1451409845f6ba53d97f90071c92a4b26cc248f8d6b2bbc5634aaebe89ed`  
Rules: `129`  
Canonical sources: `18`

This is the human-readable view of `scoring-matrix.yaml`. The YAML is the runtime source of truth; version, fingerprint and all 129 IDs must match before release.

## Interpretation boundary

Status, Priority and Confidence are independent. Betroffenheit is affected/analyzed scope, not causal or business impact. Official sources support mechanisms or a small number of hard thresholds; every internally selected cutoff is labelled `internal_audit_policy`. A descriptive metric without a defensible baseline remains ND instead of being forced into a favourable or unfavourable colour.

## Status and no-data order

1. Evaluate applicability: documented false becomes NA.
2. A missing canonical source blocks the complete audit before scoring.
3. Missing required record-level metrics or unresolved denominators become ND.
4. Calculate preliminary red/yellow/green from the exact factor condition.
5. Below the factor coverage gate, only a confirmed preliminary red explicitly allowed by `confirmed_issue_override` remains red, with low confidence; all other results become ND.
6. Green never means unmeasured.

## Evidence and confidence

| Grade | Meaning |
|---|---|
| `G1_DIRECT` | A value copied from a canonical source field with artifact hash, scope, and exact grain. |
| `G2_CALCULATED` | A deterministic calculation over G1 fields with reproducible SQL/filter and exact denominator. |
| `G3_SOURCE_LIMITED` | A complete observation inside a platform-defined corpus or snapshot that is not a universal demand denominator. |
| `G4_SUPPORTED_INFERENCE` | A rule- or rubric-based inference anchored in inspectable excerpts/fields and carrying an explicit limitation. |

Confidence begins at the factor's base and can only be capped downward by coverage, sample type, freshness, corpus size and join quality. Multiple observations from one dependent source do not increase confidence.

If canonical input values conflict and no documented authoritative precedence resolves them, the affected factor is ND with low confidence. If the contradiction is itself the factor being measured, the issue remains scoreable and every conflicting value and artifact ID is retained.

A schema-valid, scope-valid, dated zero-row export is a present source, not a missing source. Its factors resolve only through their explicit `zero_denominator` rules.

## Betroffenheit

| Band | Exact condition |
|---|---|
| `broad` | `affected_rate >= 0.20 OR affected_count >= 100` |
| `material` | `not broad AND (affected_rate >= 0.05 OR affected_count >= 20)` |
| `limited` | `not broad/material AND (affected_rate >= 0.01 OR affected_count >= 5)` |
| `isolated` | `affected_count > 0 AND affected_rate < 0.01 AND affected_count < 5` |
| `none` | `affected_count == 0` |

Sitewide aggregation uses `COUNT(DISTINCT normalized_page_url)`. Parent and child URL-prefix counts are never added.
Structural URL-prefix membership is recalculated from every current crawl. A saved semantic label or business-criticality value is reusable only while its normalized prefix pattern is unchanged.

## Priority algorithm

1. Return null for green, ND, NA, informational_only, or a rule whose base_priority is null.
2. For red start at factor base_priority; for yellow start one step less urgent, capped at P3.
3. Apply Betroffenheit: broad upgrades one step, material makes no change, limited downgrades one step, isolated downgrades two steps.
4. For non-URL direct outcomes, complete configured model/country scope is material; a subset is limited unless explicitly critical.
5. A confirmed critical cluster/model/country may upgrade one step only when the rule permits it; unconfirmed mappings never modify priority.
6. A high-confidence red block veto has a P1 urgency floor; a high-confidence red overall veto has a P0 urgency floor.
7. Apply the factor priority_ceiling, then evidence/scope/confidence ceilings; the least urgent ceiling wins.
8. Yellow can never exceed P1. Medium confidence can never exceed P1; low confidence can never exceed P2.
9. G3 source-limited evidence is capped P1 for direct outcomes and P2 for supporting drivers. G4 is capped P1; diagnostic samples are capped P2 and representative samples P1.
10. Effort and implementation reversibility do not raise priority. Effort is separate; a low-effort P1/P2 item may receive Quick Win.

Deterministic tie-break: `priority` → `veto_role` → `dependency_role` → `betroffenheit_band` → `affected_count` → `factor_id`.

## Block roll-ups

A colour is not averaged numerically. Evaluation order is red veto/material combinations, ND coverage gate, yellow material condition, then green.

| Block | Minimum coverage | Red condition | Yellow condition |
|---|---:|---|---|
| `T` | 90% | `(high_confidence_red_veto_count >= 1 OR material_red_gate_or_outcome_count >= 2 OR material_red_supporting_count >= 3)` | `(red_low_confidence_count >= 1 OR material_yellow_count >= 1 OR red_count >= 1 OR yellow_count >= 2)` |
| `B` | 85% | `(high_confidence_red_veto_count >= 1 OR material_red_gate_or_outcome_count >= 2 OR material_red_supporting_count >= 4)` | `(red_low_confidence_count >= 1 OR material_yellow_count >= 1 OR red_count >= 1 OR yellow_count >= 2)` |
| `C` | 80% | `(high_confidence_red_veto_count >= 1 OR material_red_gate_or_outcome_count >= 2 OR material_red_supporting_count >= 4)` | `(red_low_confidence_count >= 1 OR material_yellow_count >= 1 OR red_count >= 1 OR yellow_count >= 2)` |
| `S` | 85% | `(high_confidence_red_veto_count >= 1 OR material_red_gate_or_outcome_count >= 2 OR material_red_supporting_count >= 4)` | `(red_low_confidence_count >= 1 OR material_yellow_count >= 1 OR red_count >= 1 OR yellow_count >= 2)` |
| `O` | 75% | `(high_confidence_red_veto_count >= 1 OR material_red_gate_or_outcome_count >= 3 OR material_red_supporting_count >= 3)` | `(red_low_confidence_count >= 1 OR material_yellow_count >= 1 OR red_count >= 1 OR yellow_count >= 2)` |
| `M` | 90% | `(high_confidence_red_veto_count >= 1 OR material_red_gate_or_outcome_count >= 2 OR material_red_supporting_count >= 3)` | `(red_low_confidence_count >= 1 OR material_yellow_count >= 1 OR red_count >= 1 OR yellow_count >= 2)` |

Overall red requires a high-confidence overall veto or at least two red blocks. One red block makes overall yellow unless an overall veto applies. Overall green requires all six blocks green and at least 85% applicable-factor coverage.

## All factor rules

| ID | Factor | Rule | Status bands | Base / ceiling | Evidence | Basis |
|---|---|---|---|---|---|---|
| `B01` | Целостность scope SISTRIX | `consistency` | red: scope_mismatch_count > 0; yellow: (scope_mismatch_count = 0 AND scope_warning_count > 0); green: (scope_mismatch_count = 0 AND scope_warning_count = 0) | `P0` / `P0` | `G2_CALCULATED` | `platform_definition` + `deterministic_derivation` |
| `B02` | Observed Brand Prompt Count | `comparative_gap` | red: (observed_count = 0 OR (comparable_baseline_available = true AND change_rate <= -0.2)); yellow: (observed_count > 0 AND (comparable_baseline_available = false OR change_rate < -0.05)); green: (observed_count > 0 AND comparable_baseline_available = true AND change_rate >= -0.05) | `P1` / `P1` | `G1_DIRECT` | `platform_definition` + `internal_audit_policy` |
| `B03` | Observed Domain Citation Prompt Count | `comparative_gap` | red: (observed_count = 0 OR (comparable_baseline_available = true AND change_rate <= -0.2)); yellow: (observed_count > 0 AND (comparable_baseline_available = false OR change_rate < -0.05)); green: (observed_count > 0 AND comparable_baseline_available = true AND change_rate >= -0.05) | `P1` / `P1` | `G1_DIRECT` | `platform_definition` + `internal_audit_policy` |
| `B04` | Observed Combined Visibility Prompt Count | `comparative_gap` | red: (observed_count = 0 OR (comparable_baseline_available = true AND change_rate <= -0.2)); yellow: (observed_count > 0 AND (comparable_baseline_available = false OR change_rate < -0.05)); green: (observed_count > 0 AND comparable_baseline_available = true AND change_rate >= -0.05) | `P1` / `P1` | `G1_DIRECT` | `platform_definition` + `internal_audit_policy` |
| `B06` | Покрытие AI-моделей | `threshold` | red: target_coverage_rate < 0.25; yellow: (target_coverage_rate >= 0.25 AND target_coverage_rate < 0.8); green: target_coverage_rate >= 0.8 | `P2` / `P1` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `B07` | Географическое покрытие | `threshold` | red: target_coverage_rate < 0.25; yellow: (target_coverage_rate >= 0.25 AND target_coverage_rate < 0.8); green: target_coverage_rate >= 0.8 | `P2` / `P1` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `B08` | Инвентарь обнаруженных промптов | `threshold` | red: record_coverage_rate < 0.5; yellow: (record_coverage_rate >= 0.5 AND record_coverage_rate < 0.95); green: record_coverage_rate >= 0.95 | `P2` / `P2` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `B09` | Текст AI-ответов | `prevalence` | red: nonempty_text_rate < 0.8; yellow: (nonempty_text_rate >= 0.8 AND nonempty_text_rate < 0.98); green: nonempty_text_rate >= 0.98 | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `B10` | Контекст упоминания бренда | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `platform_definition` + `internal_audit_policy` |
| `B11` | Ландшафт цитируемых источников | `threshold` | red: record_coverage_rate < 0.5; yellow: (record_coverage_rate >= 0.5 AND record_coverage_rate < 0.95); green: record_coverage_rate >= 0.95 | `P2` / `P2` | `G3_SOURCE_LIMITED` | `platform_definition` + `internal_audit_policy` |
| `B12` | Набор AI-конкурентов | `rubric` | red: (normative_baseline_available = true AND normative_grade = "red"); yellow: (normative_baseline_available = true AND normative_grade = "yellow"); green: (normative_baseline_available = true AND normative_grade = "green") | `None` / `None` | `G1_DIRECT` | `platform_definition` + `no_normative_cutoff` |
| `B13` | Конкурентный контекст | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `platform_definition` + `internal_audit_policy` |
| `B14` | Prominence в доступных ответах | `prevalence` | red: prominent_answer_rate < 0.3; yellow: (prominent_answer_rate >= 0.3 AND prominent_answer_rate < 0.6); green: prominent_answer_rate >= 0.6 | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `B15` | Атрибуты и narrative бренда | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `platform_definition` + `internal_audit_policy` |
| `B16` | Сравнения и альтернативы | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `platform_definition` + `internal_audit_policy` |
| `B17` | Фактическая согласованность AI-представления | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `B18` | Brand sentiment в AI-ответах | `threshold` | red: wilson_upper_95 < 0.5; yellow: (wilson_lower_95 <= 0.5 AND wilson_upper_95 >= 0.5); green: wilson_lower_95 > 0.5 | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `statistical_inference` |
| `B19` | Sentiment по AI-платформам | `prevalence` | red: (critical_negative_group_count > 0 OR reliably_negative_group_rate > 0.5); yellow: (reliably_negative_group_rate > 0 OR reliably_positive_group_rate < 0.8); green: (reliably_negative_group_rate = 0 AND reliably_positive_group_rate >= 0.8) | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `statistical_inference` |
| `B20` | Lob/Kritik distribution | `threshold` | red: wilson_upper_95 < 0.5; yellow: (wilson_lower_95 <= 0.5 AND wilson_upper_95 >= 0.5); green: wilson_lower_95 > 0.5 | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `statistical_inference` |
| `B21` | Тематический sentiment | `prevalence` | red: (critical_negative_group_count > 0 OR reliably_negative_group_rate > 0.5); yellow: (reliably_negative_group_rate > 0 OR reliably_positive_group_rate < 0.8); green: (reliably_negative_group_rate = 0 AND reliably_positive_group_rate >= 0.8) | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `statistical_inference` |
| `B22` | Сильные и слабые стороны | `rubric` | red: (critical_weak_theme_count > 0 OR weak_theme_share > 0.5); yellow: weak_theme_count > 0; green: weak_theme_count = 0 | `P1` / `P1` | `G3_SOURCE_LIMITED` | `platform_definition` + `internal_audit_policy` |
| `B23` | Sentiment benchmark | `comparative_gap` | red: benchmark_percentile < 25; yellow: (benchmark_percentile >= 25 AND benchmark_percentile < 75); green: benchmark_percentile >= 75 | `P2` / `P1` | `G1_DIRECT` | `platform_definition` + `internal_audit_policy` |
| `B24` | Примеры и источники sentiment | `threshold` | red: record_coverage_rate < 0.5; yellow: (record_coverage_rate >= 0.5 AND record_coverage_rate < 0.95); green: record_coverage_rate >= 0.95 | `P2` / `P2` | `G3_SOURCE_LIMITED` | `platform_definition` + `internal_audit_policy` |
| `B25` | Историческая динамика prompt count | `comparative_gap` | red: (comparable_baseline_available = true AND change_rate <= -0.2); yellow: (comparable_baseline_available = true AND change_rate > -0.2 AND change_rate < -0.05); green: (comparable_baseline_available = true AND change_rate >= -0.05) | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `B26` | First-party Generative AI visibility | `comparative_gap` | red: (observed_count = 0 OR (comparable_baseline_available = true AND change_rate <= -0.2)); yellow: (observed_count > 0 AND (comparable_baseline_available = false OR change_rate < -0.05)); green: (observed_count > 0 AND comparable_baseline_available = true AND change_rate >= -0.05) | `P1` / `P1` | `G1_DIRECT` | `platform_definition` + `internal_audit_policy` |
| `B27` | First-party GAI landing-page coverage | `threshold` | red: target_coverage_rate < 0.25; yellow: (target_coverage_rate >= 0.25 AND target_coverage_rate < 0.8); green: target_coverage_rate >= 0.8 | `P1` / `P1` | `G2_CALCULATED` | `platform_definition` + `internal_audit_policy` |
| `C01` | Семантическая релевантность | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C02` | Прямота ответа | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C03` | Информационная архитектура | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C04` | Title и description | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `C05` | Тематическая полнота | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C06` | Извлекаемые определения | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C07` | Извлекаемые факты | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C08` | Сравнения и таблицы | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C09` | Процессы и шаги | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C10` | FAQ-контент | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C11` | Явность сущности и бренда | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C12` | Продукты, услуги и аудитории | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C13` | Дифференциация | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C14` | Условия и ограничения | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P0` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C17` | Идентификация автора | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `C18` | Наблюдаемые сигналы экспертизы | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C19` | Даты и актуальность | `prevalence` | red: (critical_overdue_count > 0 OR overdue_rate > 0.25); yellow: overdue_rate > 0.1; green: (overdue_rate <= 0.1 AND critical_overdue_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C20` | Доказательность и источники | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C21` | Оригинальный информационный вклад | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C22` | Trust и ответственность | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C23` | Межстраничная согласованность | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `C24` | Site-declared Brand Truth Set | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C25` | Локализованная субстанция | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C26` | Читаемость и сканируемость | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `C27` | Контекст и доступность медиа | `prevalence` | red: (issue_rate > 0.25 OR critical_issue_rate > 0.1); yellow: (issue_rate > 0.1 OR critical_affected_count > 0); green: (issue_rate <= 0.1 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `C28` | Thin, duplicate и scaled content | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P1` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `C29` | Freshness относительно спроса | `prevalence` | red: (critical_overdue_count > 0 OR overdue_rate > 0.25); yellow: overdue_rate > 0.1; green: (overdue_rate <= 0.1 AND critical_overdue_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `M01` | Observed Brand Prompt Count | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M02` | Observed Domain Citation Prompt Count | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M03` | Observed Combined Visibility Prompt Count | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M04` | Model distribution | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M05` | Country distribution | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M06` | Competitor set/count | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P3` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M07` | Returned prompt record count | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M08` | Unique cited sources | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M09` | Source amount | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M10` | Source prompt count | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M11` | Owned cited-source share | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M12` | Source concentration | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M13` | Historical prompt-count trend | `threshold` | red: (valid_daily_points < 7 OR scope_break_count > 0); yellow: (valid_daily_points < 28 OR missing_day_rate > 0.1); green: (valid_daily_points >= 28 AND scope_break_count = 0 AND missing_day_rate <= 0.1) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `internal_audit_policy` |
| `M14` | Google Generative AI impressions | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M15` | GAI distribution | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P2` / `P2` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M16` | SISTRIX Sentiment Score | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P1` / `P1` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `M17` | Topic Sentiment Balance | `consistency` | red: validation_error_count > 0; yellow: (validation_error_count = 0 AND partial_record_rate > 0); green: (validation_error_count = 0 AND partial_record_rate = 0) | `P1` / `P1` | `G2_CALCULATED` | `deterministic_derivation` + `deterministic_derivation` |
| `O01` | Backlink volume | `comparative_gap` | red: (comparable_baseline_available = true AND change_rate <= -0.2); yellow: (comparable_baseline_available = true AND change_rate > -0.2 AND change_rate < -0.05); green: (comparable_baseline_available = true AND change_rate >= -0.05) | `P2` / `P2` | `G2_CALCULATED` | `internal_audit_policy` + `internal_audit_policy` |
| `O02` | Referring domains | `comparative_gap` | red: (comparable_baseline_available = true AND change_rate <= -0.2); yellow: (comparable_baseline_available = true AND change_rate > -0.2 AND change_rate < -0.05); green: (comparable_baseline_available = true AND change_rate >= -0.05) | `P2` / `P2` | `G2_CALCULATED` | `internal_audit_policy` + `internal_audit_policy` |
| `O03` | Authority distribution | `rubric` | red: (normative_baseline_available = true AND normative_grade = "red"); yellow: (normative_baseline_available = true AND normative_grade = "yellow"); green: (normative_baseline_available = true AND normative_grade = "green") | `None` / `None` | `G1_DIRECT` | `internal_audit_policy` + `no_normative_cutoff` |
| `O04` | Follow/nofollow distribution | `rubric` | red: (normative_baseline_available = true AND normative_grade = "red"); yellow: (normative_baseline_available = true AND normative_grade = "yellow"); green: (normative_baseline_available = true AND normative_grade = "green") | `None` / `None` | `G1_DIRECT` | `internal_audit_policy` + `no_normative_cutoff` |
| `O05` | Anchor text profile | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `internal_audit_policy` + `internal_audit_policy` |
| `O06` | Broken backlinks | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G2_CALCULATED` | `internal_audit_policy` + `internal_audit_policy` |
| `O07` | Распределение target pages | `threshold` | red: target_coverage_rate < 0.25; yellow: (target_coverage_rate >= 0.25 AND target_coverage_rate < 0.8); green: target_coverage_rate >= 0.8 | `P2` / `P1` | `G2_CALCULATED` | `internal_audit_policy` + `internal_audit_policy` |
| `O08` | Link concentration и sitewide patterns | `threshold` | red: top_source_share > 0.5; yellow: (top_source_share > 0.25 AND top_source_share <= 0.5); green: top_source_share <= 0.25 | `P2` / `P2` | `G2_CALCULATED` | `internal_audit_policy` + `internal_audit_policy` |
| `O09` | Типы ссылок и платформ | `rubric` | red: (normative_baseline_available = true AND normative_grade = "red"); yellow: (normative_baseline_available = true AND normative_grade = "yellow"); green: (normative_baseline_available = true AND normative_grade = "green") | `None` / `None` | `G1_DIRECT` | `internal_audit_policy` + `no_normative_cutoff` |
| `O10` | Давность и свежесть ссылок | `comparative_gap` | red: (comparable_baseline_available = true AND change_rate <= -0.2); yellow: (comparable_baseline_available = true AND change_rate > -0.2 AND change_rate < -0.05); green: (comparable_baseline_available = true AND change_rate >= -0.05) | `P2` / `P2` | `G2_CALCULATED` | `internal_audit_policy` + `internal_audit_policy` |
| `O11` | Географическая и языковая релевантность | `threshold` | red: relevant_source_share < 0.25; yellow: (relevant_source_share >= 0.25 AND relevant_source_share < 0.6); green: relevant_source_share >= 0.6 | `P2` / `P2` | `G4_SUPPORTED_INFERENCE` | `internal_audit_policy` + `internal_audit_policy` |
| `O12` | Пересечение с AI-конкурентами | `comparative_gap` | red: competitor_gap_rate > 0.5; yellow: (competitor_gap_rate > 0.2 AND competitor_gap_rate <= 0.5); green: competitor_gap_rate <= 0.2 | `P2` / `P1` | `G3_SOURCE_LIMITED` | `internal_audit_policy` + `internal_audit_policy` |
| `O13` | AI-cited hosts/domains/URLs | `rubric` | red: (normative_baseline_available = true AND normative_grade = "red"); yellow: (normative_baseline_available = true AND normative_grade = "yellow"); green: (normative_baseline_available = true AND normative_grade = "green") | `None` / `None` | `G1_DIRECT` | `internal_audit_policy` + `no_normative_cutoff` |
| `O14` | Source mix | `rubric` | red: (independent_source_share < 0.2 OR competitor_source_share > 0.6); yellow: (independent_source_share < 0.5 OR competitor_source_share > 0.4); green: (independent_source_share >= 0.5 AND competitor_source_share <= 0.4) | `P2` / `P1` | `G3_SOURCE_LIMITED` | `internal_audit_policy` + `internal_audit_policy` |
| `O17` | Source и citation opportunities | `comparative_gap` | red: competitor_gap_rate > 0.5; yellow: (competitor_gap_rate > 0.2 AND competitor_gap_rate <= 0.5); green: competitor_gap_rate <= 0.2 | `P2` / `P2` | `G4_SUPPORTED_INFERENCE` | `internal_audit_policy` + `internal_audit_policy` |
| `S01` | Наличие и форматы schema | `threshold` | red: target_coverage_rate < 0.25; yellow: (target_coverage_rate >= 0.25 AND target_coverage_rate < 0.8); green: target_coverage_rate >= 0.8 | `P2` / `P2` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S02` | Ошибки валидации | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S03` | Соответствие type странице | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S04` | Organization | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S05` | WebSite | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S06` | WebPage и Article | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S07` | Product и Offer | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P0` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S08` | Service | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S09` | LocalBusiness | `rubric` | red: (critical_fail_count > 0 OR median_rubric_score < 50 OR fail_rate > 0.2); yellow: (median_rubric_score < 80 OR fail_rate > 0.05 OR warning_rate > 0.2); green: (median_rubric_score >= 80 AND fail_rate <= 0.05 AND warning_rate <= 0.2 AND critical_fail_count = 0) | `P1` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S10` | Person и author entity | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S11` | BreadcrumbList | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S12` | FAQPage и HowTo | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S13` | Review и AggregateRating | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S14` | SameAs и entity identifiers | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P2` / `P1` | `G4_SUPPORTED_INFERENCE` | `official_guidance` + `internal_audit_policy` |
| `S15` | Author/publisher/date consistency | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S16` | Offer consistency | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S17` | ImageObject и VideoObject | `prevalence` | red: (issue_rate > 0.25 OR critical_issue_rate > 0.1); yellow: (issue_rate > 0.1 OR critical_affected_count > 0); green: (issue_rate <= 0.1 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S18` | Raw/rendered schema parity | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S19` | Schema-visible content consistency | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `S20` | Дубли и конфликты сущностей | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T01` | Crawl-инвентарь | `rubric` | red: (scope_error = true OR inventory_gap_rate > 0.1); yellow: inventory_gap_rate > 0.02; green: (scope_error = false AND inventory_gap_rate <= 0.02) | `P1` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T02` | HTTP-доступность | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T03` | Robots.txt для поисковых краулеров | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T04` | Доступ AI-агентов | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T05` | Meta Robots и X-Robots-Tag | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T06` | Indexability | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T08` | XML Sitemap | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T09` | Canonicalization | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T10` | Google index status | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P0` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T11` | Redirect integrity | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T12` | Crawl depth | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T13` | Internal link graph | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T14` | Orphan-page candidates | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T15` | Rendered-content availability | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T16` | Зависимость от JavaScript | `prevalence` | red: (issue_rate > 0.25 OR critical_issue_rate > 0.1); yellow: (issue_rate > 0.1 OR critical_affected_count > 0); green: (issue_rate <= 0.1 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T17` | Raw/rendered parity | `boolean_gate` | red: (critical_affected_count > 0 OR issue_rate >= 0.01); yellow: (affected_count > 0 AND issue_rate < 0.01 AND critical_affected_count = 0); green: affected_count = 0 | `P1` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T18` | JS и resource errors | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P1` / `P0` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T19` | Hreflang integrity | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T20` | Mobile/desktop rendering | `prevalence` | red: (issue_rate > 0.1 OR critical_issue_rate > 0.02); yellow: (issue_rate > 0.02 OR critical_affected_count > 0); green: (issue_rate <= 0.02 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T21` | Page performance — Lighthouse lab | `threshold` | red: (critical_red_count > 0 OR red_url_rate > 0.1); yellow: (red_url_rate > 0 OR yellow_url_rate > 0.2); green: (red_url_rate = 0 AND yellow_url_rate <= 0.2 AND critical_red_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T22` | Crawl-budget risk | `prevalence` | red: (issue_rate > 0.25 OR critical_issue_rate > 0.1); yellow: (issue_rate > 0.1 OR critical_affected_count > 0); green: (issue_rate <= 0.1 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T23` | Duplicate-content mechanics | `prevalence` | red: (issue_rate > 0.25 OR critical_issue_rate > 0.1); yellow: (issue_rate > 0.1 OR critical_affected_count > 0); green: (issue_rate <= 0.1 AND critical_affected_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T24` | URL и response efficiency | `rubric` | red: (median_rubric_score < 40 OR fail_rate > 0.3); yellow: (median_rubric_score < 75 OR fail_rate > 0.1 OR warning_rate > 0.3 OR critical_fail_count > 0); green: (median_rubric_score >= 75 AND fail_rate <= 0.1 AND warning_rate <= 0.3 AND critical_fail_count = 0) | `P3` / `P2` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |
| `T25` | Agent-friendly accessibility | `threshold` | red: (critical_red_count > 0 OR red_url_rate > 0.1); yellow: (red_url_rate > 0 OR yellow_url_rate > 0.2); green: (red_url_rate = 0 AND yellow_url_rate <= 0.2 AND critical_red_count = 0) | `P2` / `P1` | `G2_CALCULATED` | `official_guidance` + `internal_audit_policy` |

## Exact qualitative rubrics

### B10 — Контекст упоминания бренда

- `B10-R1` (25%): The answer explicitly identifies the brand's role, offer, or category instead of an unexplained name-only mention.
- `B10-R2` (25%): The mentioned attribute is supported by the answer context or a site-declared fact and is not internally contradictory.
- `B10-R3` (25%): The answer identifies the relevant audience, use case, or comparison context when one is material to the prompt.
- `B10-R4` (25%): Material eligibility limits, exclusions, price qualifications, or uncertainty are stated next to the claim when relevant.

### B13 — Конкурентный контекст

- `B13-R1` (25%): The brand and competitor are compared in the same prompt intent and product/service category.
- `B13-R2` (25%): At least one explicit common comparison criterion is stated for both sides.
- `B13-R3` (25%): The wording distinguishes observation from recommendation and avoids unsupported winner language.
- `B13-R4` (25%): Material advantages and limitations are represented symmetrically enough to support the stated conclusion.

### B15 — Атрибуты и narrative бренда

- `B15-R1` (25%): Each recurring brand attribute has an exact answer excerpt and normalized attribute label.
- `B15-R2` (25%): The attribute is consistent with site-declared truth or is explicitly marked externally unverified.
- `B15-R3` (25%): The attribute's audience, product, geography, or time scope is retained.
- `B15-R4` (25%): Repeated attributes are quantified across distinct prompts/models rather than inferred from one quotation.

### B16 — Сравнения и альтернативы

- `B16-R1` (25%): The answer names the comparison or alternative-selection criterion.
- `B16-R2` (25%): Brand and alternatives are evaluated within the same product, audience, country, and time scope.
- `B16-R3` (25%): Recommendation or shortlist position is recorded separately from a simple mention.
- `B16-R4` (25%): The stated reason and material limitations are retained in the evidence excerpt.

### C01 — Семантическая релевантность

- `C01-R1` (25%): The page's primary topic matches the dominant mapped query/prompt intent.
- `C01-R2` (25%): The main content resolves the primary user task rather than only repeating query vocabulary.
- `C01-R3` (25%): Material mapped sub-intents are covered or linked to an appropriate dedicated page.
- `C01-R4` (25%): Unrelated template or marketing text does not obscure the primary topic.

### C02 — Прямота ответа

- `C02-R1` (25%): A direct answer, definition, or decision statement appears in the first relevant section.
- `C02-R2` (25%): The answer precedes supporting detail instead of requiring the reader to infer the conclusion.
- `C02-R3` (25%): The subject, audience, and jurisdiction/product scope of the answer are explicit.
- `C02-R4` (25%): Material exceptions or conditions appear adjacent to the direct answer.

### C03 — Информационная архитектура

- `C03-R1` (25%): The URL has one descriptive H1 aligned with the main topic.
- `C03-R2` (25%): H2–H6 headings form coherent sections and describe their content rather than using generic labels.
- `C03-R3` (25%): Lists and tables are used for genuinely repeated fields, steps, or comparisons.
- `C03-R4` (25%): Navigation, breadcrumbs, and in-page links expose the page's place in the topic hierarchy.

### C05 — Тематическая полнота

- `C05-R1` (25%): The page explains prerequisites or eligibility for the mapped intent.
- `C05-R2` (25%): It covers material options, variants, or alternatives.
- `C05-R3` (25%): It states material exceptions, exclusions, risks, or failure cases.
- `C05-R4` (25%): It answers or links to the principal next questions evidenced by GSC queries or SISTRIX prompts.

### C06 — Извлекаемые определения

- `C06-R1` (25%): A definition appears at or immediately after the first material use of the term.
- `C06-R2` (25%): The definition states the broader category and distinguishing characteristics.
- `C06-R3` (25%): It uses plain language and expands unavoidable specialist abbreviations.
- `C06-R4` (25%): The same term is used consistently across the page and linked related pages.

### C07 — Извлекаемые факты

- `C07-R1` (25%): Each material fact identifies a subject and unambiguous value or categorical assertion.
- `C07-R2` (25%): Numbers retain unit, currency, period, geography, and calculation basis where applicable.
- `C07-R3` (25%): Time-sensitive facts include an effective or checked date.
- `C07-R4` (25%): Material externally derived facts have an adjacent source or documented first-party method.

### C08 — Сравнения и таблицы

- `C08-R1` (25%): Alternatives are compared with an explicit, common set of criteria.
- `C08-R2` (25%): Rows and columns have semantic headers and remain understandable outside visual styling.
- `C08-R3` (25%): Values retain units, effective dates, and material qualifications.
- `C08-R4` (25%): Advantages and disadvantages are represented without unsupported absolute-superiority claims.

### C09 — Процессы и шаги

- `C09-R1` (25%): Steps are ordered and each step contains one identifiable action.
- `C09-R2` (25%): Prerequisites, required inputs, or responsible party are stated before the relevant step.
- `C09-R3` (25%): Expected outcome or completion condition is stated.
- `C09-R4` (25%): Material exceptions, alternative paths, time limits, or failure handling are included.

### C10 — FAQ-контент

- `C10-R1` (25%): Questions correspond to evidenced user language or a necessary next question for the page intent.
- `C10-R2` (25%): Each answer is direct, self-contained, and materially distinct from the other answers.
- `C10-R3` (25%): The full answer is visible in HTML and does not depend on inaccessible interaction.
- `C10-R4` (25%): The FAQ does not duplicate a stronger dedicated section or create near-identical scaled pages.

### C11 — Явность сущности и бренда

- `C11-R1` (25%): The legal/common brand name and organization or service category are explicit.
- `C11-R2` (25%): The relationship between organization, brands, products, and services is unambiguous.
- `C11-R3` (25%): Primary geography, service area, or market is explicit where relevant.
- `C11-R4` (25%): Identity statements agree with contact, legal, and structured-data surfaces.

### C12 — Продукты, услуги и аудитории

- `C12-R1` (25%): The product or service is named and described in concrete terms.
- `C12-R2` (25%): Intended and excluded audiences or eligibility conditions are explicit.
- `C12-R3` (25%): Availability geography and delivery/service channel are explicit.
- `C12-R4` (25%): Variants, principal use cases, and material limits are discoverable on the page.

### C13 — Дифференциация

- `C13-R1` (25%): Each differentiator names a concrete attribute rather than an unqualified superlative.
- `C13-R2` (25%): A first-party method, specification, example, or cited source supports the differentiator.
- `C13-R3` (25%): The comparison baseline and relevant competitor/product category are explicit.
- `C13-R4` (25%): Material limits and cases where the alternative may be preferable are not hidden.

### C14 — Условия и ограничения

- `C14-R1` (25%): Price, availability, eligibility, term, or benefit claims include effective scope and date where needed.
- `C14-R2` (25%): Material exclusions, deductibles, conditions, or risks are stated next to the benefit claim.
- `C14-R3` (25%): Jurisdiction and regional/product variation are explicit.
- `C14-R4` (25%): The page provides a clear route to authoritative current terms or contractual detail.

### C18 — Наблюдаемые сигналы экспертизы

- `C18-R1` (25%): The author/editor has a visible biography connected to the audited content.
- `C18-R2` (25%): Role, employer/affiliation, and subject responsibility are explicit.
- `C18-R3` (25%): Relevant qualifications or first-hand experience are described without unverifiable inflation.
- `C18-R4` (25%): A stable profile, contact route, publication history, or external identifier permits verification.

### C20 — Доказательность и источники

- `C20-R1` (25%): Material externally derived claims have an adjacent, identifiable source.
- `C20-R2` (25%): The cited source actually addresses the neighbouring claim and is not merely a generic homepage.
- `C20-R3` (25%): Primary data or calculations include method, denominator, period, and limitations.
- `C20-R4` (25%): Sources are reachable, current enough for the claim, and distinguished from marketing evidence.

### C21 — Оригинальный информационный вклад

- `C21-R1` (25%): The page contains identifiable first-party data, testing, experience, cases, or calculations.
- `C21-R2` (25%): The method or conditions under which the original material was produced are stated.
- `C21-R3` (25%): Examples contain enough concrete detail to be independently understood.
- `C21-R4` (25%): The original material adds an insight not obtained by merely paraphrasing cited sources.

### C22 — Trust и ответственность

- `C22-R1` (25%): Impressum/legal identity and a functioning contact route are present and consistent.
- `C22-R2` (25%): Editorial responsibility, correction route, or content governance is discoverable where expected.
- `C22-R3` (25%): Privacy, terms, complaints, and other material policies are accessible for the site's activity.
- `C22-R4` (25%): Support and escalation routes are explicit for material customer or YMYL decisions.

### C24 — Site-declared Brand Truth Set

- `C24-R1` (25%): Organization and brand identity, including relationships and identifiers, are normalized without contradiction.
- `C24-R2` (25%): Products/services, variants, and intended audiences are explicitly represented.
- `C24-R3` (25%): Prices/benefits, geography, availability, and effective dates are represented where applicable.
- `C24-R4` (25%): Eligibility, exclusions, risks, and other material limitations are represented and traceable to URLs.

### C25 — Локализованная субстанция

- `C25-R1` (25%): Language, spelling, currency, units, and market terminology match the configured locale.
- `C25-R2` (25%): Products, service availability, contacts, and prices correspond to that market.
- `C25-R3` (25%): Applicable laws, institutions, and cited sources are local rather than mechanically translated substitutes.
- `C25-R4` (25%): Examples and user problems reflect the local audience and are not translation-only boilerplate.

### C26 — Читаемость и сканируемость

- `C26-R1` (25%): Sentence and paragraph length avoid repeated extremes according to the language-specific SF readability output.
- `C26-R2` (25%): Headings, lists, and spacing make major answers and transitions scannable.
- `C26-R3` (25%): Specialist terms and abbreviations are defined at first material use.
- `C26-R4` (25%): The visible hierarchy distinguishes main content, navigation, disclaimers, and supporting detail.

### S04 — Organization

- `S04-R1` (25%): Organization has stable @id plus name/legalName and canonical URL.
- `S04-R2` (25%): Logo, contactPoint, address, and identifiers are present when visibly applicable.
- `S04-R3` (25%): sameAs values point to official profiles for the same organization.
- `S04-R4` (25%): All material values agree with visible identity, legal, and contact content.

### S05 — WebSite

- `S05-R1` (25%): WebSite has stable @id, canonical URL, and site name.
- `S05-R2` (25%): publisher points to the canonical Organization entity.
- `S05-R3` (25%): The WebSite node is unique or consistently merged across templates.
- `S05-R4` (25%): Name, URL, and publisher agree with visible site identity.

### S06 — WebPage и Article

- `S06-R1` (25%): WebPage/Article headline, mainEntity, and canonical URL identify the visible page.
- `S06-R2` (25%): author and publisher resolve to stable Person/Organization entities.
- `S06-R3` (25%): datePublished and dateModified agree with visible dates and chronology.
- `S06-R4` (25%): Image and other material properties are crawlable and represented in visible content.

### S07 — Product и Offer

- `S07-R1` (25%): Product identity, brand, model/SKU, and stable @id match the visible product.
- `S07-R2` (25%): Offer price, currency, availability, seller, and validity fields are complete when shown.
- `S07-R3` (25%): Variants and aggregate offers are not merged into a misleading single value.
- `S07-R4` (25%): All material Product/Offer values agree with visible current content.

### S08 — Service

- `S08-R1` (25%): Service type, name, stable @id, and provider identify the visible service.
- `S08-R2` (25%): audience and areaServed match visible eligibility and geography.
- `S08-R3` (25%): Offers or terms are represented only when visible and current.
- `S08-R4` (25%): The Service node is linked coherently to WebPage and Organization entities.

### S09 — LocalBusiness

- `S09-R1` (25%): The most specific applicable LocalBusiness subtype, name, URL, and stable @id are used.
- `S09-R2` (25%): Address/NAP and geo coordinates agree with visible contact/location content.
- `S09-R3` (25%): Opening hours and service area are complete and current where applicable.
- `S09-R4` (25%): The location entity is not conflated with the parent Organization or another branch.

### S10 — Person и author entity

- `S10-R1` (25%): Person name, stable @id, and profile URL identify the visible author.
- `S10-R2` (25%): affiliation/jobTitle match visible biography and Organization relationships.
- `S10-R3` (25%): Credentials or expertise fields are used only when visibly supported.
- `S10-R4` (25%): sameAs values resolve to profiles belonging to the same person.

### S14 — SameAs и entity identifiers

- `S14-R1` (25%): Each principal entity has one stable, canonical @id reused consistently.
- `S14-R2` (25%): sameAs links resolve and represent the identical entity rather than a topic or search result.
- `S14-R3` (25%): Organization, brand, product, location, and person identifiers are not conflated.
- `S14-R4` (25%): External identifiers are authoritative enough to disambiguate the entity and agree with visible content.

### T24 — URL и response efficiency

- `T24-R1` (25%): Normalized URL is at most 115 characters and has no unapproved crawlable parameter; 116–200 characters or one approved parameter is partial; otherwise fail.
- `T24-R2` (25%): Median server response time is at most 800 ms; 801–1500 ms is partial; above 1500 ms or no response fails.
- `T24-R3` (25%): Transferred HTML is at most 500 KiB; above 500 KiB through 1 MiB is partial; above 1 MiB fails.
- `T24-R4` (25%): Total transferred page weight is at most 2 MiB; above 2 MiB through 5 MiB is partial; above 5 MiB or a required failed resource fails.

## Source basis

- `CLAUDE_SKILLS` — [Claude Code skills](https://code.claude.com/docs/en/skills): Project skill layout and progressive supporting resources.
- `GOOGLE_AI_GUIDE` — [Optimizing for generative AI features on Google Search](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide): Search eligibility, crawlability, JavaScript, page experience, helpful content, and duplicate-content mechanisms.
- `GOOGLE_HELPFUL_CONTENT` — [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content): Originality, completeness, authorship, sourcing, trust, and Who/How/Why evaluation.
- `GOOGLE_ROBOTS_META` — [Robots meta tag and X-Robots-Tag specifications](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag): Indexing and snippet controls, including direct-input limits for AI Overviews and AI Mode.
- `GOOGLE_CANONICAL` — [Canonical URL methods](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls): Canonical signals, redirects, rel=canonical, and sitemap interaction.
- `GOOGLE_JAVASCRIPT` — [JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics): Crawl-render-index sequence, raw/rendered risks, canonical parity, and the fact that not all bots run JavaScript.
- `GOOGLE_CRAWL_BUDGET` — [Optimize your crawl budget](https://developers.google.com/crawling/docs/crawl-budget): Applicability to very large or rapidly changing sites and crawl-efficiency mechanisms.
- `GOOGLE_SITEMAPS` — [What is a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview): Sitemap discovery and inventory guidance.
- `GOOGLE_HREFLANG` — [Localized versions of pages](https://developers.google.com/search/docs/specialty/international/localized-versions): Hreflang implementation and return-link requirements.
- `GOOGLE_STRUCTURED_DATA` — [General structured data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies): Visible-content consistency, relevance, correctness, completeness, and misleading-markup restrictions.
- `LIGHTHOUSE_SCORING` — [Lighthouse performance scoring](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring): Lab score calculation and 0–49, 50–89, 90–100 colour bands.
- `GSC_LIMITS` — [Search Console API usage limits](https://developers.google.com/webmaster-tools/limits): URL Inspection quota of 2,000 requests per site per day.
- `SISTRIX_MODELS` — [SISTRIX ai.models API](https://www.sistrix.com/api/ai/ai-models/): Available model identifiers.
- `SISTRIX_OVERVIEW` — [SISTRIX ai.check.overview API](https://www.sistrix.com/api/ai-check/ai-check-overview/): Observed prompt_count and model/country breakdowns for mention, citation, or combined scope.
- `SISTRIX_PROMPTS` — [SISTRIX ai.check.prompts API](https://www.sistrix.com/api/ai-check/ai-check-prompts/): Returned prompt, model, generated message, and country; records already contain a mention or citation.
- `SISTRIX_PROMPT_HISTORY` — [SISTRIX ai.check.prompts.count API](https://www.sistrix.com/api/ai-check/ai-check-prompts-count/): Daily aggregate prompt_count history in a model/country scope.
- `SISTRIX_SOURCES` — [SISTRIX ai.check.sources API](https://www.sistrix.com/api/ai-check/ai-check-sources/): Aggregated source URL/domain/host amount and prompt_count without an answer-level source join.
- `SISTRIX_COMPETITORS` — [SISTRIX ai.check.competitors API](https://www.sistrix.com/api/ai-check/ai-check-competitors/): Competitor brands in the selected AI environment.
- `AHREFS_BACKLINKS` — [Backlinks and referring domains](https://help.ahrefs.com/en/articles/2791107-what-s-the-difference-between-referring-domains-and-backlinks): Difference in backlink-level and domain-level grains.
- `AHREFS_BROKEN` — [Broken backlinks](https://help.ahrefs.com/en/articles/72842-what-are-broken-backlinks): Definition of backlinks pointing to broken target pages.
- `DEJAN_AGENTS` — [AI Agent Access](https://dejan.ai/tools/agents/): Configuration-level AI agent access test rather than observed crawling.
- `NIST_WILSON` — [NIST binomial confidence intervals](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/binomial.htm): Wilson confidence interval for a binomial proportion.
- `RFC3986_PATHS` — [RFC 3986 path hierarchy](https://www.rfc-editor.org/rfc/rfc3986#section-3.3): URI path segments and hierarchical path structure.

## Change control

Any rule, threshold, priority ceiling, veto, roll-up, rubric dimension, or interpretation change requires a semantic policy version bump, a written rationale, regenerated fingerprint, and passing boundary/adversarial regression tests.
