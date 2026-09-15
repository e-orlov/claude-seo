#!/usr/bin/env python3
"""Build the frozen GEO scoring policy, its readable view, and boundary fixtures.

The authoring definitions in this file are intentionally explicit and versioned.
The generated ``scoring-matrix.yaml`` is the runtime source of truth.  Generation
fails when the canonical factor matrix and the rule inventory diverge.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


POLICY_VERSION = "1.0.0"
EFFECTIVE_DATE = "2026-09-15"
POLICY_DIR = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = POLICY_DIR.parent
FACTOR_MATRIX = WORKBENCH_DIR / "GEO_audit_sources_and_factor_matrix_FINAL.md"
POLICY_OUTPUT = POLICY_DIR / "scoring-matrix.yaml"
README_OUTPUT = POLICY_DIR / "README.md"
FIXTURES_OUTPUT = POLICY_DIR / "fixtures" / "boundary-cases.yaml"

SOURCE_IDS = {
    "SF", "RAW", "REN", "PSI", "GSC-SA", "GSC-UI", "GSC-GAI",
    "AH-BL", "AH-RD", "AH-BB", "SX-M", "SX-O", "SX-C", "SX-P",
    "SX-PC", "SX-S", "SX-SENT", "DJ",
}


def comparison(metric: str, operator: str, value: Any) -> dict[str, Any]:
    return {"metric": metric, "operator": operator, "value": value}


def all_of(*conditions: dict[str, Any]) -> dict[str, Any]:
    return {"all": list(conditions)}


def any_of(*conditions: dict[str, Any]) -> dict[str, Any]:
    return {"any": list(conditions)}


def negate(condition: dict[str, Any]) -> dict[str, Any]:
    return {"not": condition}


def metric(name: str, kind: str, unit: str, description: str, required: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "type": kind,
        "unit": unit,
        "required": required,
        "description": description,
    }


COMMON_COUNT_METRICS = [
    metric("affected_count", "integer", "units", "Distinct applicable units meeting the factor's failure predicate."),
    metric("analyzed_count", "integer", "units", "Distinct applicable units successfully analysed."),
    metric("issue_rate", "number", "ratio_0_1", "affected_count divided by analyzed_count."),
    metric("critical_affected_count", "integer", "units", "Affected units in confirmed critical clusters."),
    metric("critical_issue_rate", "number", "ratio_0_1", "Issue rate within confirmed critical clusters."),
]


def bands(red: dict[str, Any], yellow: dict[str, Any], green: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluation_order": ["red", "yellow", "green"],
        "red": red,
        "yellow": yellow,
        "green": green,
    }


PROFILE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "inventory_completeness": {
        "rule_type": "rubric",
        "metrics": [
            metric("scope_error", "boolean", "boolean", "True when crawl scope conflicts with the approved domain/subdomain/resource scope."),
            metric("inventory_gap_rate", "number", "ratio_0_1", "Share of expected inventory URLs absent from the crawl union."),
        ],
        "bands": bands(
            any_of(comparison("scope_error", "eq", True), comparison("inventory_gap_rate", "gt", 0.10)),
            comparison("inventory_gap_rate", "gt", 0.02),
            all_of(comparison("scope_error", "eq", False), comparison("inventory_gap_rate", "lte", 0.02)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "An incomplete or wrongly scoped inventory invalidates downstream denominators and can omit affected templates.",
        "action": "Correct crawl scope or inventory joins, then rebuild every downstream denominator.",
        "fixtures": [
            ("green_at_2pct", {"scope_error": False, "inventory_gap_rate": 0.02}, "green"),
            ("yellow_above_2pct", {"scope_error": False, "inventory_gap_rate": 0.020001}, "yellow"),
            ("yellow_at_10pct", {"scope_error": False, "inventory_gap_rate": 0.10}, "yellow"),
            ("red_above_10pct", {"scope_error": False, "inventory_gap_rate": 0.100001}, "red"),
            ("red_scope_error", {"scope_error": True, "inventory_gap_rate": 0.0}, "red"),
        ],
    },
    "scope_integrity": {
        "rule_type": "consistency",
        "metrics": [
            metric("scope_mismatch_count", "integer", "mismatches", "Material conflicts between approved and observed scope."),
            metric("scope_warning_count", "integer", "warnings", "Non-material omissions or ambiguous scope fields."),
        ],
        "bands": bands(
            comparison("scope_mismatch_count", "gt", 0),
            all_of(comparison("scope_mismatch_count", "eq", 0), comparison("scope_warning_count", "gt", 0)),
            all_of(comparison("scope_mismatch_count", "eq", 0), comparison("scope_warning_count", "eq", 0)),
        ),
        "cutoffs": "deterministic_derivation",
        "mechanism": "Scope mismatches make values from models, countries, brands, domains, or dates non-comparable.",
        "action": "Align the source request and saved artifact with the approved audit configuration.",
        "fixtures": [
            ("green_zero", {"scope_mismatch_count": 0, "scope_warning_count": 0}, "green"),
            ("yellow_warning", {"scope_mismatch_count": 0, "scope_warning_count": 1}, "yellow"),
            ("red_mismatch", {"scope_mismatch_count": 1, "scope_warning_count": 0}, "red"),
        ],
    },
    "hard_issue_prevalence": {
        "rule_type": "boolean_gate",
        "metrics": COMMON_COUNT_METRICS,
        "bands": bands(
            any_of(comparison("critical_affected_count", "gt", 0), comparison("issue_rate", "gte", 0.01)),
            all_of(comparison("affected_count", "gt", 0), comparison("issue_rate", "lt", 0.01), comparison("critical_affected_count", "eq", 0)),
            comparison("affected_count", "eq", 0),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A confirmed eligibility or accuracy failure can remove or materially misrepresent an otherwise strategic URL.",
        "action": "Remove the blocking or contradictory condition and retest the same affected universe.",
        "fixtures": [
            ("green_zero", {"affected_count": 0, "analyzed_count": 1000, "issue_rate": 0.0, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "green"),
            ("yellow_below_1pct", {"affected_count": 9, "analyzed_count": 1000, "issue_rate": 0.009, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "yellow"),
            ("red_at_1pct", {"affected_count": 10, "analyzed_count": 1000, "issue_rate": 0.01, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "red"),
            ("red_one_critical", {"affected_count": 1, "analyzed_count": 1000, "issue_rate": 0.001, "critical_affected_count": 1, "critical_issue_rate": 0.01}, "red"),
        ],
    },
    "strict_issue_prevalence": {
        "rule_type": "prevalence",
        "metrics": COMMON_COUNT_METRICS,
        "bands": bands(
            any_of(comparison("issue_rate", "gt", 0.10), comparison("critical_issue_rate", "gt", 0.02)),
            any_of(comparison("issue_rate", "gt", 0.02), comparison("critical_affected_count", "gt", 0)),
            all_of(comparison("issue_rate", "lte", 0.02), comparison("critical_affected_count", "eq", 0)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "The issue reduces reliable discovery, interpretation, or user access on a measurable share of applicable URLs.",
        "action": "Fix the shared root cause, prioritising confirmed critical clusters, then recrawl the same universe.",
        "fixtures": [
            ("green_at_2pct", {"affected_count": 20, "analyzed_count": 1000, "issue_rate": 0.02, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "green"),
            ("yellow_above_2pct", {"affected_count": 21, "analyzed_count": 1000, "issue_rate": 0.021, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "yellow"),
            ("yellow_at_10pct", {"affected_count": 100, "analyzed_count": 1000, "issue_rate": 0.10, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "yellow"),
            ("red_above_10pct", {"affected_count": 101, "analyzed_count": 1000, "issue_rate": 0.101, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "red"),
            ("yellow_one_critical", {"affected_count": 1, "analyzed_count": 1000, "issue_rate": 0.001, "critical_affected_count": 1, "critical_issue_rate": 0.01}, "yellow"),
            ("red_critical_above_2pct", {"affected_count": 3, "analyzed_count": 1000, "issue_rate": 0.003, "critical_affected_count": 3, "critical_issue_rate": 0.021}, "red"),
        ],
    },
    "standard_issue_prevalence": {
        "rule_type": "prevalence",
        "metrics": COMMON_COUNT_METRICS,
        "bands": bands(
            any_of(comparison("issue_rate", "gt", 0.25), comparison("critical_issue_rate", "gt", 0.10)),
            any_of(comparison("issue_rate", "gt", 0.10), comparison("critical_affected_count", "gt", 0)),
            all_of(comparison("issue_rate", "lte", 0.10), comparison("critical_affected_count", "eq", 0)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A broad recurring implementation weakness reduces the quality or extractability of an affected template.",
        "action": "Apply a template-level correction and validate representative URLs in every affected cluster.",
        "fixtures": [
            ("green_at_10pct", {"affected_count": 100, "analyzed_count": 1000, "issue_rate": 0.10, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "green"),
            ("yellow_above_10pct", {"affected_count": 101, "analyzed_count": 1000, "issue_rate": 0.101, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "yellow"),
            ("yellow_at_25pct", {"affected_count": 250, "analyzed_count": 1000, "issue_rate": 0.25, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "yellow"),
            ("red_above_25pct", {"affected_count": 251, "analyzed_count": 1000, "issue_rate": 0.251, "critical_affected_count": 0, "critical_issue_rate": 0.0}, "red"),
        ],
    },
    "rubric_strict": {
        "rule_type": "rubric",
        "metrics": [
            metric("median_rubric_score", "number", "score_0_100", "Median deterministic rubric score across applicable units."),
            metric("fail_rate", "number", "ratio_0_1", "Share of units with a rubric score below 50."),
            metric("warning_rate", "number", "ratio_0_1", "Share of units with a rubric score from 50 through 79."),
            metric("critical_fail_count", "integer", "units", "Failing units in confirmed critical clusters."),
        ],
        "bands": bands(
            any_of(comparison("critical_fail_count", "gt", 0), comparison("median_rubric_score", "lt", 50), comparison("fail_rate", "gt", 0.20)),
            any_of(comparison("median_rubric_score", "lt", 80), comparison("fail_rate", "gt", 0.05), comparison("warning_rate", "gt", 0.20)),
            all_of(comparison("median_rubric_score", "gte", 80), comparison("fail_rate", "lte", 0.05), comparison("warning_rate", "lte", 0.20), comparison("critical_fail_count", "eq", 0)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A fixed evidence-backed rubric converts qualitative content or entity observations into repeatable, inspectable checks.",
        "action": "Address failed rubric dimensions and retain evidence for every changed dimension.",
        "fixtures": [
            ("green_exact", {"median_rubric_score": 80, "fail_rate": 0.05, "warning_rate": 0.20, "critical_fail_count": 0}, "green"),
            ("yellow_median_below_80", {"median_rubric_score": 79.999, "fail_rate": 0.05, "warning_rate": 0.20, "critical_fail_count": 0}, "yellow"),
            ("yellow_at_fail_20pct", {"median_rubric_score": 80, "fail_rate": 0.20, "warning_rate": 0.0, "critical_fail_count": 0}, "yellow"),
            ("red_above_fail_20pct", {"median_rubric_score": 80, "fail_rate": 0.200001, "warning_rate": 0.0, "critical_fail_count": 0}, "red"),
            ("red_critical", {"median_rubric_score": 100, "fail_rate": 0.0, "warning_rate": 0.0, "critical_fail_count": 1}, "red"),
        ],
    },
    "rubric_standard": {
        "rule_type": "rubric",
        "metrics": [
            metric("median_rubric_score", "number", "score_0_100", "Median deterministic rubric score across applicable units."),
            metric("fail_rate", "number", "ratio_0_1", "Share of units with a rubric score below 40."),
            metric("warning_rate", "number", "ratio_0_1", "Share of units with a rubric score from 40 through 74."),
            metric("critical_fail_count", "integer", "units", "Failing units in confirmed critical clusters."),
        ],
        "bands": bands(
            any_of(comparison("median_rubric_score", "lt", 40), comparison("fail_rate", "gt", 0.30)),
            any_of(comparison("median_rubric_score", "lt", 75), comparison("fail_rate", "gt", 0.10), comparison("warning_rate", "gt", 0.30), comparison("critical_fail_count", "gt", 0)),
            all_of(comparison("median_rubric_score", "gte", 75), comparison("fail_rate", "lte", 0.10), comparison("warning_rate", "lte", 0.30), comparison("critical_fail_count", "eq", 0)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A fixed evidence-backed rubric measures supporting quality without treating a single weak signal as an eligibility failure.",
        "action": "Improve failed rubric dimensions, starting with dimensions repeated across templates.",
        "fixtures": [
            ("green_exact", {"median_rubric_score": 75, "fail_rate": 0.10, "warning_rate": 0.30, "critical_fail_count": 0}, "green"),
            ("yellow_below_75", {"median_rubric_score": 74.999, "fail_rate": 0.10, "warning_rate": 0.30, "critical_fail_count": 0}, "yellow"),
            ("yellow_at_fail_30pct", {"median_rubric_score": 75, "fail_rate": 0.30, "warning_rate": 0.0, "critical_fail_count": 0}, "yellow"),
            ("red_above_fail_30pct", {"median_rubric_score": 75, "fail_rate": 0.300001, "warning_rate": 0.0, "critical_fail_count": 0}, "red"),
        ],
    },
    "coverage_strict": {
        "rule_type": "threshold",
        "metrics": [metric("target_coverage_rate", "number", "ratio_0_1", "Covered configured targets divided by applicable configured targets.")],
        "bands": bands(
            comparison("target_coverage_rate", "lt", 0.25),
            all_of(comparison("target_coverage_rate", "gte", 0.25), comparison("target_coverage_rate", "lt", 0.80)),
            comparison("target_coverage_rate", "gte", 0.80),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Breadth across the configured models, countries, pages, or source records determines whether the observed outcome is strategically representative.",
        "action": "Close the uncovered configured scope and repeat the same measurement.",
        "fixtures": [
            ("red_below_25pct", {"target_coverage_rate": 0.249999}, "red"),
            ("yellow_at_25pct", {"target_coverage_rate": 0.25}, "yellow"),
            ("yellow_below_80pct", {"target_coverage_rate": 0.799999}, "yellow"),
            ("green_at_80pct", {"target_coverage_rate": 0.80}, "green"),
        ],
    },
    "coverage_complete": {
        "rule_type": "threshold",
        "metrics": [metric("record_coverage_rate", "number", "ratio_0_1", "Successfully returned complete records divided by expected records in the platform-defined corpus.")],
        "bands": bands(
            comparison("record_coverage_rate", "lt", 0.50),
            all_of(comparison("record_coverage_rate", "gte", 0.50), comparison("record_coverage_rate", "lt", 0.95)),
            comparison("record_coverage_rate", "gte", 0.95),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Incomplete records constrain which conclusions can be supported within the declared source corpus.",
        "action": "Complete pagination or repair parsing until the platform-defined corpus is represented.",
        "fixtures": [
            ("red_below_50pct", {"record_coverage_rate": 0.499999}, "red"),
            ("yellow_at_50pct", {"record_coverage_rate": 0.50}, "yellow"),
            ("yellow_below_95pct", {"record_coverage_rate": 0.949999}, "yellow"),
            ("green_at_95pct", {"record_coverage_rate": 0.95}, "green"),
        ],
    },
    "text_completeness": {
        "rule_type": "prevalence",
        "metrics": [metric("nonempty_text_rate", "number", "ratio_0_1", "Share of returned prompt records containing a non-empty answer text.")],
        "bands": bands(
            comparison("nonempty_text_rate", "lt", 0.80),
            all_of(comparison("nonempty_text_rate", "gte", 0.80), comparison("nonempty_text_rate", "lt", 0.98)),
            comparison("nonempty_text_rate", "gte", 0.98),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Answer-level representation analysis requires the actual generated message for nearly all returned prompt records.",
        "action": "Repair pagination or parsing and retain the full returned answer text.",
        "fixtures": [
            ("red_below_80pct", {"nonempty_text_rate": 0.799999}, "red"),
            ("yellow_at_80pct", {"nonempty_text_rate": 0.80}, "yellow"),
            ("yellow_below_98pct", {"nonempty_text_rate": 0.979999}, "yellow"),
            ("green_at_98pct", {"nonempty_text_rate": 0.98}, "green"),
        ],
    },
    "presence_with_baseline": {
        "rule_type": "comparative_gap",
        "metrics": [
            metric("observed_count", "integer", "records", "Platform-defined observed count in the frozen model/country scope."),
            metric("comparable_baseline_available", "boolean", "boolean", "True only when a prior value uses the identical frozen scope."),
            metric("change_rate", "number", "ratio", "Change versus the comparable baseline; required when comparable_baseline_available is true.", False),
        ],
        "bands": bands(
            any_of(comparison("observed_count", "eq", 0), all_of(comparison("comparable_baseline_available", "eq", True), comparison("change_rate", "lte", -0.20))),
            all_of(comparison("observed_count", "gt", 0), any_of(comparison("comparable_baseline_available", "eq", False), comparison("change_rate", "lt", -0.05))),
            all_of(comparison("observed_count", "gt", 0), comparison("comparable_baseline_available", "eq", True), comparison("change_rate", "gte", -0.05)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Zero observed visibility or a material decline in an identical platform scope is a direct outcome signal; the absolute count is not a universal market share.",
        "action": "Investigate the affected model/country/topic scope and improve supported source and content gaps without promising causal uplift.",
        "fixtures": [
            ("red_zero", {"observed_count": 0, "comparable_baseline_available": False}, "red"),
            ("yellow_no_baseline", {"observed_count": 1, "comparable_baseline_available": False}, "yellow"),
            ("red_at_minus_20pct", {"observed_count": 10, "comparable_baseline_available": True, "change_rate": -0.20}, "red"),
            ("yellow_above_minus_20pct", {"observed_count": 10, "comparable_baseline_available": True, "change_rate": -0.199999}, "yellow"),
            ("yellow_below_minus_5pct", {"observed_count": 10, "comparable_baseline_available": True, "change_rate": -0.050001}, "yellow"),
            ("green_at_minus_5pct", {"observed_count": 10, "comparable_baseline_available": True, "change_rate": -0.05}, "green"),
        ],
    },
    "trend_only": {
        "rule_type": "comparative_gap",
        "metrics": [
            metric("comparable_baseline_available", "boolean", "boolean", "True only when both values use an identical frozen scope."),
            metric("change_rate", "number", "ratio", "Change versus the comparable baseline.", False),
        ],
        "bands": bands(
            all_of(comparison("comparable_baseline_available", "eq", True), comparison("change_rate", "lte", -0.20)),
            all_of(comparison("comparable_baseline_available", "eq", True), comparison("change_rate", "gt", -0.20), comparison("change_rate", "lt", -0.05)),
            all_of(comparison("comparable_baseline_available", "eq", True), comparison("change_rate", "gte", -0.05)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A stable-scope time comparison supports direction; a single absolute snapshot does not establish healthy or unhealthy quantity.",
        "action": "Investigate material loss in the identical scope; if no baseline exists, establish one rather than inventing a judgement.",
        "fixtures": [
            ("nd_no_baseline", {"comparable_baseline_available": False}, "ND"),
            ("red_at_minus_20pct", {"comparable_baseline_available": True, "change_rate": -0.20}, "red"),
            ("yellow_above_minus_20pct", {"comparable_baseline_available": True, "change_rate": -0.199999}, "yellow"),
            ("yellow_below_minus_5pct", {"comparable_baseline_available": True, "change_rate": -0.050001}, "yellow"),
            ("green_at_minus_5pct", {"comparable_baseline_available": True, "change_rate": -0.05}, "green"),
        ],
    },
    "prominence": {
        "rule_type": "prevalence",
        "metrics": [metric("prominent_answer_rate", "number", "ratio_0_1", "Share of brand-containing answers where the brand is in the title/lead/top-three list positions or is the primary recommendation.")],
        "bands": bands(
            comparison("prominent_answer_rate", "lt", 0.30),
            all_of(comparison("prominent_answer_rate", "gte", 0.30), comparison("prominent_answer_rate", "lt", 0.60)),
            comparison("prominent_answer_rate", "gte", 0.60),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A mention placed prominently is more visible than a marginal mention, but remains measured only within returned SISTRIX answers.",
        "action": "Strengthen clear, supportable differentiation for the topics where the brand is present but marginal.",
        "fixtures": [
            ("red_below_30pct", {"prominent_answer_rate": 0.299999}, "red"),
            ("yellow_at_30pct", {"prominent_answer_rate": 0.30}, "yellow"),
            ("yellow_below_60pct", {"prominent_answer_rate": 0.599999}, "yellow"),
            ("green_at_60pct", {"prominent_answer_rate": 0.60}, "green"),
        ],
    },
    "sentiment_wilson": {
        "rule_type": "threshold",
        "metrics": [
            metric("positive_count", "integer", "mentions", "Lob count in the applicable SISTRIX sentiment scope."),
            metric("negative_count", "integer", "mentions", "Kritik count in the applicable SISTRIX sentiment scope."),
            metric("wilson_lower_95", "number", "ratio_0_1", "Lower 95% Wilson bound for positive share among Lob plus Kritik."),
            metric("wilson_upper_95", "number", "ratio_0_1", "Upper 95% Wilson bound for positive share among Lob plus Kritik."),
        ],
        "bands": bands(
            comparison("wilson_upper_95", "lt", 0.50),
            all_of(comparison("wilson_lower_95", "lte", 0.50), comparison("wilson_upper_95", "gte", 0.50)),
            comparison("wilson_lower_95", "gt", 0.50),
        ),
        "cutoffs": "statistical_inference",
        "mechanism": "The 95% Wilson interval distinguishes evidence of net-positive or net-negative evaluative mentions while accounting for sample size.",
        "action": "Address evidence-backed recurring criticism; do not treat a small inconclusive sample as proven negative sentiment.",
        "fixtures": [
            ("red_upper_below_half", {"positive_count": 10, "negative_count": 30, "wilson_lower_95": 0.14, "wilson_upper_95": 0.40}, "red"),
            ("yellow_upper_at_half", {"positive_count": 10, "negative_count": 20, "wilson_lower_95": 0.19, "wilson_upper_95": 0.50}, "yellow"),
            ("yellow_lower_at_half", {"positive_count": 20, "negative_count": 10, "wilson_lower_95": 0.50, "wilson_upper_95": 0.81}, "yellow"),
            ("green_lower_above_half", {"positive_count": 30, "negative_count": 10, "wilson_lower_95": 0.60, "wilson_upper_95": 0.86}, "green"),
        ],
    },
    "group_sentiment": {
        "rule_type": "prevalence",
        "metrics": [
            metric("material_group_count", "integer", "groups", "Groups with Lob plus Kritik greater than zero."),
            metric("reliably_negative_group_rate", "number", "ratio_0_1", "Share of material groups whose Wilson upper bound is below 0.50."),
            metric("reliably_positive_group_rate", "number", "ratio_0_1", "Share of material groups whose Wilson lower bound is above 0.50."),
            metric("critical_negative_group_count", "integer", "groups", "Reliably negative groups configured as strategically critical."),
        ],
        "bands": bands(
            any_of(comparison("critical_negative_group_count", "gt", 0), comparison("reliably_negative_group_rate", "gt", 0.50)),
            any_of(comparison("reliably_negative_group_rate", "gt", 0), comparison("reliably_positive_group_rate", "lt", 0.80)),
            all_of(comparison("reliably_negative_group_rate", "eq", 0), comparison("reliably_positive_group_rate", "gte", 0.80)),
        ),
        "cutoffs": "statistical_inference",
        "mechanism": "Platform/topic groups are first classified with Wilson intervals; the aggregate then measures breadth of reliable sentiment direction.",
        "action": "Prioritise reliably negative strategic groups and preserve platform/topic scope in validation.",
        "fixtures": [
            ("green_exact", {"material_group_count": 5, "reliably_negative_group_rate": 0.0, "reliably_positive_group_rate": 0.80, "critical_negative_group_count": 0}, "green"),
            ("yellow_below_80pct_positive", {"material_group_count": 5, "reliably_negative_group_rate": 0.0, "reliably_positive_group_rate": 0.799999, "critical_negative_group_count": 0}, "yellow"),
            ("yellow_at_50pct_negative", {"material_group_count": 4, "reliably_negative_group_rate": 0.50, "reliably_positive_group_rate": 0.0, "critical_negative_group_count": 0}, "yellow"),
            ("red_above_50pct_negative", {"material_group_count": 4, "reliably_negative_group_rate": 0.500001, "reliably_positive_group_rate": 0.0, "critical_negative_group_count": 0}, "red"),
            ("red_critical_group", {"material_group_count": 5, "reliably_negative_group_rate": 0.20, "reliably_positive_group_rate": 0.80, "critical_negative_group_count": 1}, "red"),
        ],
    },
    "weak_theme_balance": {
        "rule_type": "rubric",
        "metrics": [
            metric("weak_theme_count", "integer", "themes", "Distinct negative themes supported by SISTRIX examples."),
            metric("weak_theme_share", "number", "ratio_0_1", "Weak themes divided by all supported strong and weak themes."),
            metric("critical_weak_theme_count", "integer", "themes", "Weak themes concerning critical product, price, eligibility, legal, safety, or service facts."),
        ],
        "bands": bands(
            any_of(comparison("critical_weak_theme_count", "gt", 0), comparison("weak_theme_share", "gt", 0.50)),
            comparison("weak_theme_count", "gt", 0),
            comparison("weak_theme_count", "eq", 0),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Recurring supported weaknesses show which brand attributes dominate critical AI representation within the snapshot.",
        "action": "Resolve factual causes where possible and publish supportable evidence for misunderstood attributes.",
        "fixtures": [
            ("green_zero", {"weak_theme_count": 0, "weak_theme_share": 0.0, "critical_weak_theme_count": 0}, "green"),
            ("yellow_at_half", {"weak_theme_count": 1, "weak_theme_share": 0.50, "critical_weak_theme_count": 0}, "yellow"),
            ("red_above_half", {"weak_theme_count": 2, "weak_theme_share": 0.500001, "critical_weak_theme_count": 0}, "red"),
            ("red_critical", {"weak_theme_count": 1, "weak_theme_share": 0.10, "critical_weak_theme_count": 1}, "red"),
        ],
    },
    "percentile_quartile": {
        "rule_type": "comparative_gap",
        "metrics": [metric("benchmark_percentile", "number", "percentile_0_100", "SISTRIX-displayed percentile in the documented comparison group.")],
        "bands": bands(
            comparison("benchmark_percentile", "lt", 25),
            all_of(comparison("benchmark_percentile", "gte", 25), comparison("benchmark_percentile", "lt", 75)),
            comparison("benchmark_percentile", "gte", 75),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Quartiles provide a transparent relative classification inside the displayed SISTRIX benchmark, not a universal market ranking.",
        "action": "Compare the attributes behind the benchmark gap and address evidence-backed weaknesses.",
        "fixtures": [
            ("red_below_25", {"benchmark_percentile": 24.999}, "red"),
            ("yellow_at_25", {"benchmark_percentile": 25}, "yellow"),
            ("yellow_below_75", {"benchmark_percentile": 74.999}, "yellow"),
            ("green_at_75", {"benchmark_percentile": 75}, "green"),
        ],
    },
    "lighthouse_distribution": {
        "rule_type": "threshold",
        "metrics": [
            metric("red_url_rate", "number", "ratio_0_1", "Share of tested URLs with Lighthouse category score 0 through 49."),
            metric("yellow_url_rate", "number", "ratio_0_1", "Share of tested URLs with Lighthouse category score 50 through 89."),
            metric("critical_red_count", "integer", "urls", "Red Lighthouse URLs in confirmed critical clusters."),
        ],
        "bands": bands(
            any_of(comparison("critical_red_count", "gt", 0), comparison("red_url_rate", "gt", 0.10)),
            any_of(comparison("red_url_rate", "gt", 0), comparison("yellow_url_rate", "gt", 0.20)),
            all_of(comparison("red_url_rate", "eq", 0), comparison("yellow_url_rate", "lte", 0.20), comparison("critical_red_count", "eq", 0)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Individual Lighthouse lab scores use Google's 0–49, 50–89, and 90–100 bands; site roll-up uses explicit internal prevalence rules.",
        "action": "Fix the URL-level Lighthouse diagnostics, preserving mobile/desktop strategy and lab terminology.",
        "fixtures": [
            ("green_at_20pct_yellow", {"red_url_rate": 0.0, "yellow_url_rate": 0.20, "critical_red_count": 0}, "green"),
            ("yellow_above_20pct_yellow", {"red_url_rate": 0.0, "yellow_url_rate": 0.200001, "critical_red_count": 0}, "yellow"),
            ("yellow_at_10pct_red", {"red_url_rate": 0.10, "yellow_url_rate": 0.0, "critical_red_count": 0}, "yellow"),
            ("red_above_10pct_red", {"red_url_rate": 0.100001, "yellow_url_rate": 0.0, "critical_red_count": 0}, "red"),
            ("red_critical", {"red_url_rate": 0.001, "yellow_url_rate": 0.0, "critical_red_count": 1}, "red"),
        ],
    },
    "freshness_sla": {
        "rule_type": "prevalence",
        "metrics": [
            metric("overdue_rate", "number", "ratio_0_1", "Share of applicable URLs older than the deterministic content-class freshness SLA."),
            metric("critical_overdue_count", "integer", "urls", "Overdue URLs in confirmed critical clusters with current demand."),
        ],
        "bands": bands(
            any_of(comparison("critical_overdue_count", "gt", 0), comparison("overdue_rate", "gt", 0.25)),
            comparison("overdue_rate", "gt", 0.10),
            all_of(comparison("overdue_rate", "lte", 0.10), comparison("critical_overdue_count", "eq", 0)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Time-sensitive facts can become inconsistent with current demand; dates alone do not prove freshness, so class-specific evidence is required.",
        "action": "Review overdue high-demand facts and update content only when substantive facts or user needs changed.",
        "fixtures": [
            ("green_at_10pct", {"overdue_rate": 0.10, "critical_overdue_count": 0}, "green"),
            ("yellow_above_10pct", {"overdue_rate": 0.100001, "critical_overdue_count": 0}, "yellow"),
            ("yellow_at_25pct", {"overdue_rate": 0.25, "critical_overdue_count": 0}, "yellow"),
            ("red_above_25pct", {"overdue_rate": 0.250001, "critical_overdue_count": 0}, "red"),
            ("red_critical", {"overdue_rate": 0.01, "critical_overdue_count": 1}, "red"),
        ],
    },
    "source_concentration": {
        "rule_type": "threshold",
        "metrics": [metric("top_source_share", "number", "ratio_0_1", "Share of links or source amount attributable to the largest single source group.")],
        "bands": bands(
            comparison("top_source_share", "gt", 0.50),
            all_of(comparison("top_source_share", "gt", 0.25), comparison("top_source_share", "lte", 0.50)),
            comparison("top_source_share", "lte", 0.25),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Extreme concentration makes observed authority or citations dependent on one source and exposes a resilience gap.",
        "action": "Diversify relevant, legitimate source coverage instead of manufacturing link volume.",
        "fixtures": [
            ("green_at_25pct", {"top_source_share": 0.25}, "green"),
            ("yellow_above_25pct", {"top_source_share": 0.250001}, "yellow"),
            ("yellow_at_50pct", {"top_source_share": 0.50}, "yellow"),
            ("red_above_50pct", {"top_source_share": 0.500001}, "red"),
        ],
    },
    "geo_relevance": {
        "rule_type": "threshold",
        "metrics": [metric("relevant_source_share", "number", "ratio_0_1", "Share of classifiable referring sources matching the configured market language, country, or topic.")],
        "bands": bands(
            comparison("relevant_source_share", "lt", 0.25),
            all_of(comparison("relevant_source_share", "gte", 0.25), comparison("relevant_source_share", "lt", 0.60)),
            comparison("relevant_source_share", "gte", 0.60),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "Topical and market relevance is more diagnostic than raw source quantity, but inferred URL/TLD signals have limited confidence.",
        "action": "Prioritise legitimate sources that match the configured market and subject area.",
        "fixtures": [
            ("red_below_25pct", {"relevant_source_share": 0.249999}, "red"),
            ("yellow_at_25pct", {"relevant_source_share": 0.25}, "yellow"),
            ("yellow_below_60pct", {"relevant_source_share": 0.599999}, "yellow"),
            ("green_at_60pct", {"relevant_source_share": 0.60}, "green"),
        ],
    },
    "opportunity_gap": {
        "rule_type": "comparative_gap",
        "metrics": [metric("competitor_gap_rate", "number", "ratio_0_1", "Share of comparable external source opportunities where competitors are observed and the brand is not observed in available records.")],
        "bands": bands(
            comparison("competitor_gap_rate", "gt", 0.50),
            all_of(comparison("competitor_gap_rate", "gt", 0.20), comparison("competitor_gap_rate", "lte", 0.50)),
            comparison("competitor_gap_rate", "lte", 0.20),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A source gap identifies an observed competitive opportunity inside the available corpus, not proof of absence from the whole web page.",
        "action": "Validate each source manually before pursuing legitimate editorial, profile, review, or partnership coverage.",
        "fixtures": [
            ("green_at_20pct", {"competitor_gap_rate": 0.20}, "green"),
            ("yellow_above_20pct", {"competitor_gap_rate": 0.200001}, "yellow"),
            ("yellow_at_50pct", {"competitor_gap_rate": 0.50}, "yellow"),
            ("red_above_50pct", {"competitor_gap_rate": 0.500001}, "red"),
        ],
    },
    "source_mix": {
        "rule_type": "rubric",
        "metrics": [
            metric("independent_source_share", "number", "ratio_0_1", "Share of classifiable sources that are neither owned nor competitor-owned."),
            metric("competitor_source_share", "number", "ratio_0_1", "Share of classifiable sources controlled by configured competitors."),
        ],
        "bands": bands(
            any_of(comparison("independent_source_share", "lt", 0.20), comparison("competitor_source_share", "gt", 0.60)),
            any_of(comparison("independent_source_share", "lt", 0.50), comparison("competitor_source_share", "gt", 0.40)),
            all_of(comparison("independent_source_share", "gte", 0.50), comparison("competitor_source_share", "lte", 0.40)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A diverse independent source layer provides a more resilient observed information ecosystem than owned or competitor-dominated records alone.",
        "action": "Close evidence-backed gaps in relevant independent source types without treating source quantity as causality.",
        "fixtures": [
            ("green_exact", {"independent_source_share": 0.50, "competitor_source_share": 0.40}, "green"),
            ("yellow_independent_below_50pct", {"independent_source_share": 0.499999, "competitor_source_share": 0.40}, "yellow"),
            ("yellow_independent_at_20pct", {"independent_source_share": 0.20, "competitor_source_share": 0.40}, "yellow"),
            ("red_independent_below_20pct", {"independent_source_share": 0.199999, "competitor_source_share": 0.40}, "red"),
            ("red_competitor_above_60pct", {"independent_source_share": 0.30, "competitor_source_share": 0.600001}, "red"),
        ],
    },
    "measurement_integrity": {
        "rule_type": "consistency",
        "metrics": [
            metric("validation_error_count", "integer", "errors", "Schema, arithmetic, scope, or invariant violations in the calculated metric."),
            metric("partial_record_rate", "number", "ratio_0_1", "Share of expected records that are incomplete but still parseable."),
        ],
        "bands": bands(
            comparison("validation_error_count", "gt", 0),
            all_of(comparison("validation_error_count", "eq", 0), comparison("partial_record_rate", "gt", 0)),
            all_of(comparison("validation_error_count", "eq", 0), comparison("partial_record_rate", "eq", 0)),
        ),
        "cutoffs": "deterministic_derivation",
        "mechanism": "A metric is reportable only when its schema, denominator, arithmetic, and frozen scope reconcile exactly.",
        "action": "Repair the source parsing or calculation; do not reinterpret invalid data as a performance problem.",
        "fixtures": [
            ("green_valid", {"validation_error_count": 0, "partial_record_rate": 0.0}, "green"),
            ("yellow_partial", {"validation_error_count": 0, "partial_record_rate": 0.000001}, "yellow"),
            ("red_error", {"validation_error_count": 1, "partial_record_rate": 0.0}, "red"),
        ],
    },
    "history_coverage": {
        "rule_type": "threshold",
        "metrics": [
            metric("valid_daily_points", "integer", "days", "Valid daily values in one unchanged model/country/brand/domain scope."),
            metric("scope_break_count", "integer", "breaks", "Changes in the tracked scope within the analysed window."),
            metric("missing_day_rate", "number", "ratio_0_1", "Missing expected calendar days within the analysed window."),
        ],
        "bands": bands(
            any_of(comparison("valid_daily_points", "lt", 7), comparison("scope_break_count", "gt", 0)),
            any_of(comparison("valid_daily_points", "lt", 28), comparison("missing_day_rate", "gt", 0.10)),
            all_of(comparison("valid_daily_points", "gte", 28), comparison("scope_break_count", "eq", 0), comparison("missing_day_rate", "lte", 0.10)),
        ),
        "cutoffs": "internal_audit_policy",
        "mechanism": "A stable daily series needs enough observations to distinguish direction from isolated snapshots; it does not create answer-level history.",
        "action": "Preserve an unchanged scope and collect sufficient daily points before interpreting movement.",
        "fixtures": [
            ("red_below_7", {"valid_daily_points": 6, "scope_break_count": 0, "missing_day_rate": 0.0}, "red"),
            ("yellow_at_7", {"valid_daily_points": 7, "scope_break_count": 0, "missing_day_rate": 0.0}, "yellow"),
            ("yellow_at_27", {"valid_daily_points": 27, "scope_break_count": 0, "missing_day_rate": 0.0}, "yellow"),
            ("green_at_28", {"valid_daily_points": 28, "scope_break_count": 0, "missing_day_rate": 0.10}, "green"),
            ("yellow_missing_above_10pct", {"valid_daily_points": 28, "scope_break_count": 0, "missing_day_rate": 0.100001}, "yellow"),
            ("red_scope_break", {"valid_daily_points": 100, "scope_break_count": 1, "missing_day_rate": 0.0}, "red"),
        ],
    },
    "descriptive_no_norm": {
        "rule_type": "rubric",
        "metrics": [
            metric("normative_baseline_available", "boolean", "boolean", "True only when an approved comparable baseline or directional target exists."),
            metric("normative_grade", "string", "enum", "Approved grade derived from that comparable baseline.", False),
        ],
        "bands": bands(
            all_of(comparison("normative_baseline_available", "eq", True), comparison("normative_grade", "eq", "red")),
            all_of(comparison("normative_baseline_available", "eq", True), comparison("normative_grade", "eq", "yellow")),
            all_of(comparison("normative_baseline_available", "eq", True), comparison("normative_grade", "eq", "green")),
        ),
        "cutoffs": "no_normative_cutoff",
        "mechanism": "The available absolute inventory is descriptive; without a comparable baseline, no defensible good/bad direction exists.",
        "action": "Report the value and limitation; establish a comparable baseline before assigning a remediation priority.",
        "fixtures": [
            ("nd_no_baseline", {"normative_baseline_available": False}, "ND"),
            ("red_approved_grade", {"normative_baseline_available": True, "normative_grade": "red"}, "red"),
            ("yellow_approved_grade", {"normative_baseline_available": True, "normative_grade": "yellow"}, "yellow"),
            ("green_approved_grade", {"normative_baseline_available": True, "normative_grade": "green"}, "green"),
        ],
    },
}


CITATIONS: dict[str, dict[str, str]] = {
    "CLAUDE_SKILLS": {
        "title": "Claude Code skills",
        "url": "https://code.claude.com/docs/en/skills",
        "authority": "official",
        "supports": "Project skill layout and progressive supporting resources.",
    },
    "GOOGLE_AI_GUIDE": {
        "title": "Optimizing for generative AI features on Google Search",
        "url": "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide",
        "authority": "official",
        "supports": "Search eligibility, crawlability, JavaScript, page experience, helpful content, and duplicate-content mechanisms.",
    },
    "GOOGLE_HELPFUL_CONTENT": {
        "title": "Creating helpful, reliable, people-first content",
        "url": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
        "authority": "official",
        "supports": "Originality, completeness, authorship, sourcing, trust, and Who/How/Why evaluation.",
    },
    "GOOGLE_ROBOTS_META": {
        "title": "Robots meta tag and X-Robots-Tag specifications",
        "url": "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
        "authority": "official",
        "supports": "Indexing and snippet controls, including direct-input limits for AI Overviews and AI Mode.",
    },
    "GOOGLE_CANONICAL": {
        "title": "Canonical URL methods",
        "url": "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
        "authority": "official",
        "supports": "Canonical signals, redirects, rel=canonical, and sitemap interaction.",
    },
    "GOOGLE_JAVASCRIPT": {
        "title": "JavaScript SEO basics",
        "url": "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics",
        "authority": "official",
        "supports": "Crawl-render-index sequence, raw/rendered risks, canonical parity, and the fact that not all bots run JavaScript.",
    },
    "GOOGLE_CRAWL_BUDGET": {
        "title": "Optimize your crawl budget",
        "url": "https://developers.google.com/crawling/docs/crawl-budget",
        "authority": "official",
        "supports": "Applicability to very large or rapidly changing sites and crawl-efficiency mechanisms.",
    },
    "GOOGLE_SITEMAPS": {
        "title": "What is a sitemap",
        "url": "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
        "authority": "official",
        "supports": "Sitemap discovery and inventory guidance.",
    },
    "GOOGLE_HREFLANG": {
        "title": "Localized versions of pages",
        "url": "https://developers.google.com/search/docs/specialty/international/localized-versions",
        "authority": "official",
        "supports": "Hreflang implementation and return-link requirements.",
    },
    "GOOGLE_STRUCTURED_DATA": {
        "title": "General structured data guidelines",
        "url": "https://developers.google.com/search/docs/appearance/structured-data/sd-policies",
        "authority": "official",
        "supports": "Visible-content consistency, relevance, correctness, completeness, and misleading-markup restrictions.",
    },
    "LIGHTHOUSE_SCORING": {
        "title": "Lighthouse performance scoring",
        "url": "https://developer.chrome.com/docs/lighthouse/performance/performance-scoring",
        "authority": "official",
        "supports": "Lab score calculation and 0–49, 50–89, 90–100 colour bands.",
    },
    "GSC_LIMITS": {
        "title": "Search Console API usage limits",
        "url": "https://developers.google.com/webmaster-tools/limits",
        "authority": "official",
        "supports": "URL Inspection quota of 2,000 requests per site per day.",
    },
    "SISTRIX_MODELS": {
        "title": "SISTRIX ai.models API",
        "url": "https://www.sistrix.com/api/ai/ai-models/",
        "authority": "official",
        "supports": "Available model identifiers.",
    },
    "SISTRIX_OVERVIEW": {
        "title": "SISTRIX ai.check.overview API",
        "url": "https://www.sistrix.com/api/ai-check/ai-check-overview/",
        "authority": "official",
        "supports": "Observed prompt_count and model/country breakdowns for mention, citation, or combined scope.",
    },
    "SISTRIX_PROMPTS": {
        "title": "SISTRIX ai.check.prompts API",
        "url": "https://www.sistrix.com/api/ai-check/ai-check-prompts/",
        "authority": "official",
        "supports": "Returned prompt, model, generated message, and country; records already contain a mention or citation.",
    },
    "SISTRIX_PROMPT_HISTORY": {
        "title": "SISTRIX ai.check.prompts.count API",
        "url": "https://www.sistrix.com/api/ai-check/ai-check-prompts-count/",
        "authority": "official",
        "supports": "Daily aggregate prompt_count history in a model/country scope.",
    },
    "SISTRIX_SOURCES": {
        "title": "SISTRIX ai.check.sources API",
        "url": "https://www.sistrix.com/api/ai-check/ai-check-sources/",
        "authority": "official",
        "supports": "Aggregated source URL/domain/host amount and prompt_count without an answer-level source join.",
    },
    "SISTRIX_COMPETITORS": {
        "title": "SISTRIX ai.check.competitors API",
        "url": "https://www.sistrix.com/api/ai-check/ai-check-competitors/",
        "authority": "official",
        "supports": "Competitor brands in the selected AI environment.",
    },
    "AHREFS_BACKLINKS": {
        "title": "Backlinks and referring domains",
        "url": "https://help.ahrefs.com/en/articles/2791107-what-s-the-difference-between-referring-domains-and-backlinks",
        "authority": "official",
        "supports": "Difference in backlink-level and domain-level grains.",
    },
    "AHREFS_BROKEN": {
        "title": "Broken backlinks",
        "url": "https://help.ahrefs.com/en/articles/72842-what-are-broken-backlinks",
        "authority": "official",
        "supports": "Definition of backlinks pointing to broken target pages.",
    },
    "DEJAN_AGENTS": {
        "title": "AI Agent Access",
        "url": "https://dejan.ai/tools/agents/",
        "authority": "official",
        "supports": "Configuration-level AI agent access test rather than observed crawling.",
    },
    "NIST_WILSON": {
        "title": "NIST binomial confidence intervals",
        "url": "https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/binomial.htm",
        "authority": "statistical_reference",
        "supports": "Wilson confidence interval for a binomial proportion.",
    },
    "RFC3986_PATHS": {
        "title": "RFC 3986 path hierarchy",
        "url": "https://www.rfc-editor.org/rfc/rfc3986#section-3.3",
        "authority": "standards_body",
        "supports": "URI path segments and hierarchical path structure.",
    },
}


APPLICABILITY: dict[str, dict[str, Any]] = {
    "default": all_of(comparison("source_preflight_pass", "eq", True), comparison("applicable_universe_count", "gt", 0)),
    "sitewide": comparison("source_preflight_pass", "eq", True),
    "multilingual": all_of(comparison("source_preflight_pass", "eq", True), comparison("multilingual_url_count", "gt", 0)),
    "dual_psi": all_of(comparison("source_preflight_pass", "eq", True), comparison("mobile_psi_count", "gt", 0), comparison("desktop_psi_count", "gt", 0)),
    "crawl_budget": all_of(
        comparison("source_preflight_pass", "eq", True),
        any_of(
            comparison("unique_url_count", "gte", 1000000),
            all_of(comparison("unique_url_count", "gte", 10000), comparison("changes_daily", "eq", True)),
            comparison("discovered_not_indexed_rate", "gt", 0.10),
        ),
    ),
    "question_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("question_intent_url_count", "gt", 0)),
    "authored_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("authorship_expected_url_count", "gt", 0)),
    "dated_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("date_relevant_url_count", "gt", 0)),
    "claim_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("factual_claim_url_count", "gt", 0)),
    "localized_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("localized_url_count", "gt", 0)),
    "media_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("media_url_count", "gt", 0)),
    "product_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("product_url_count", "gt", 0)),
    "service_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("service_url_count", "gt", 0)),
    "local_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("local_business_url_count", "gt", 0)),
    "article_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("article_url_count", "gt", 0)),
    "faq_howto_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("faq_howto_url_count", "gt", 0)),
    "review_pages": all_of(comparison("source_preflight_pass", "eq", True), comparison("review_url_count", "gt", 0)),
    "link_time_fields": all_of(comparison("source_preflight_pass", "eq", True), comparison("link_time_field_count", "gt", 0)),
    "comparable_baseline": all_of(comparison("source_preflight_pass", "eq", True), comparison("comparable_baseline_available", "eq", True)),
}


COVERAGE_PROFILES = {
    "full": {"minimum_rate": 0.90, "allowed_scope_types": ["full", "representative_sample", "snapshot", "source_corpus"], "below_minimum_status": "ND"},
    "partial": {"minimum_rate": 0.70, "allowed_scope_types": ["full", "representative_sample", "diagnostic_sample", "snapshot", "source_corpus"], "below_minimum_status": "ND"},
    "inspection": {"minimum_rate": 0.80, "allowed_scope_types": ["full", "representative_sample"], "below_minimum_status": "ND"},
    "source": {"minimum_rate": 0.80, "allowed_scope_types": ["source_corpus", "snapshot"], "below_minimum_status": "ND"},
    "history": {"minimum_rate": 0.80, "allowed_scope_types": ["source_corpus"], "below_minimum_status": "ND"},
}


CONFIDENCE_PROFILES = {
    "direct_crawl": {
        "base": "high", "freshness_class": "crawl_14d",
        "caps": [
            {"when": any_of(comparison("coverage_rate", "lt", 0.90), comparison("scope_type", "eq", "representative_sample")), "maximum": "medium", "reason": "Incomplete full-scope coverage or a representative sample limits sitewide certainty."},
            {"when": any_of(comparison("scope_type", "eq", "diagnostic_sample"), comparison("join_quality", "in", ["fuzzy", "unresolved"]), comparison("artifact_age_days", "gt", 45)), "maximum": "low", "reason": "Diagnostic scope, non-exact joins, or stale crawl evidence permits issue confirmation but weak prevalence inference."},
        ],
    },
    "direct_visibility": {
        "base": "medium", "freshness_class": "visibility_30d",
        "caps": [
            {"when": any_of(comparison("coverage_rate", "lt", 0.80), comparison("material_record_count", "lt", 10)), "maximum": "low", "reason": "Sparse or incomplete platform corpus cannot support a stable visibility interpretation."},
            {"when": any_of(comparison("artifact_age_days", "gt", 90), comparison("scope_mismatch_count", "gt", 0)), "maximum": "low", "reason": "Stale or mismatched model/country evidence does not represent the approved audit scope reliably."},
        ],
    },
    "exact_cross_source": {
        "base": "high", "freshness_class": "visibility_30d",
        "caps": [
            {"when": any_of(comparison("coverage_rate", "lt", 0.90), comparison("exact_normalized_field_rate", "lt", 1.0)), "maximum": "medium", "reason": "The comparison is not complete across exact normalized fields."},
            {"when": any_of(comparison("join_quality", "in", ["fuzzy", "unresolved"]), comparison("claim_scope_match", "eq", False), comparison("artifact_age_days", "gt", 90)), "maximum": "low", "reason": "Fuzzy identity, a claim-scope mismatch, or stale evidence weakens the cross-source conclusion."},
        ],
    },
    "rubric": {
        "base": "medium", "freshness_class": "crawl_14d",
        "caps": [
            {"when": any_of(comparison("coverage_rate", "lt", 0.80), comparison("missing_rubric_evidence_count", "gt", 0)), "maximum": "low", "reason": "A rubric without sufficient inspected units or evidence for every required dimension is weak inference."},
            {"when": comparison("join_quality", "not_in", ["exact", "normalized_exact"]), "maximum": "low", "reason": "Rubric evidence joined by fuzzy or unresolved identity cannot support medium confidence."},
        ],
    },
    "history": {
        "base": "high", "freshness_class": "historical_window",
        "caps": [
            {"when": any_of(comparison("valid_daily_point_count", "lt", 28), comparison("missing_day_rate", "gt", 0.10)), "maximum": "medium", "reason": "A short or incomplete history weakens trend stability."},
            {"when": any_of(comparison("scope_break_count", "gt", 0), comparison("valid_daily_point_count", "lt", 7)), "maximum": "low", "reason": "Scope breaks or fewer than seven observations prevent a reliable trend comparison."},
        ],
    },
    "measurement": {
        "base": "high", "freshness_class": "static_reference",
        "caps": [
            {"when": any_of(comparison("partial_record_rate", "gt", 0), comparison("coverage_rate", "lt", 0.95)), "maximum": "medium", "reason": "Partial records or incomplete reconciliation limit measurement certainty."},
            {"when": comparison("validation_error_count", "gt", 0), "maximum": "low", "reason": "A demonstrated validation error invalidates high- or medium-confidence use of the metric."},
        ],
    },
}


BLOCK_DEFAULTS = {
    "T": {"citations": ["GOOGLE_AI_GUIDE"], "mechanism_basis": "official_guidance", "consequence": "Technical discovery, rendering, indexing, or access can be weakened for the affected URLs."},
    "B": {"citations": ["SISTRIX_OVERVIEW", "SISTRIX_PROMPTS"], "mechanism_basis": "platform_definition", "consequence": "Observed AI visibility or brand representation is weaker in the declared platform corpus."},
    "C": {"citations": ["GOOGLE_AI_GUIDE", "GOOGLE_HELPFUL_CONTENT"], "mechanism_basis": "official_guidance", "consequence": "The affected content is less clear, complete, attributable, or extractable for users and retrieval systems."},
    "S": {"citations": ["GOOGLE_STRUCTURED_DATA"], "mechanism_basis": "official_guidance", "consequence": "Machine-readable entity information is incomplete, inconsistent, or misleading on the affected pages."},
    "O": {"citations": ["AHREFS_BACKLINKS", "SISTRIX_SOURCES"], "mechanism_basis": "internal_audit_policy", "consequence": "The observed external authority or AI source ecosystem is weaker or less resilient in the available corpus."},
    "M": {"citations": ["SISTRIX_OVERVIEW"], "mechanism_basis": "deterministic_derivation", "consequence": "The affected KPI cannot be interpreted or reproduced with the required measurement integrity."},
}


FACTOR_SPECS: dict[str, dict[str, Any]] = {}


def add_spec(
    factor_id: str,
    profile: str,
    universe: str,
    *,
    applicability: str = "default",
    evidence: str = "G2_CALCULATED",
    confidence: str = "direct_crawl",
    role: str = "supporting_driver",
    base_priority: str | None = "P2",
    priority_ceiling: str | None = "P1",
    criticality: str = "url_cluster",
    veto: str = "none",
    coverage: str = "full",
    zero_denominator: str = "NA",
    citations: tuple[str, ...] = (),
    mechanism_basis: str | None = None,
    dependency_parents: tuple[str, ...] = (),
    root_cause_group: str | None = None,
    informational_only: bool = False,
) -> None:
    if factor_id in FACTOR_SPECS:
        raise ValueError(f"Duplicate factor policy authoring definition: {factor_id}")
    FACTOR_SPECS[factor_id] = {
        "profile": profile,
        "universe": universe,
        "applicability": applicability,
        "evidence": evidence,
        "confidence": confidence,
        "role": role,
        "base_priority": base_priority,
        "priority_ceiling": priority_ceiling,
        "criticality": criticality,
        "veto": veto,
        "coverage": coverage,
        "zero_denominator": zero_denominator,
        "citations": list(citations),
        "mechanism_basis": mechanism_basis,
        "dependency_parents": list(dependency_parents),
        "root_cause_group": root_cause_group,
        "informational_only": informational_only,
    }


# T — Technical AI Eligibility (24 factors)
add_spec("T01", "inventory_completeness", "approved crawl inventory union", applicability="sitewide", role="eligibility_gate", base_priority="P1", priority_ceiling="P1", criticality="sitewide", veto="block", citations=("RFC3986_PATHS",))
add_spec("T02", "hard_issue_prevalence", "expected-indexable internal HTML URLs", role="eligibility_gate", base_priority="P1", priority_ceiling="P0", veto="block")
add_spec("T03", "hard_issue_prevalence", "expected-indexable URLs evaluated against search-crawler robots rules", role="eligibility_gate", base_priority="P0", priority_ceiling="P0", veto="overall", citations=("GOOGLE_ROBOTS_META",))
add_spec("T04", "hard_issue_prevalence", "configured search/retrieval and user-fetch AI agents; training-only agents excluded", role="eligibility_gate", base_priority="P1", priority_ceiling="P0", criticality="sitewide", veto="block", citations=("DEJAN_AGENTS",))
add_spec("T05", "hard_issue_prevalence", "expected-indexable URLs and their effective meta/X-Robots directives", role="eligibility_gate", base_priority="P0", priority_ceiling="P0", veto="overall", citations=("GOOGLE_ROBOTS_META",))
add_spec("T06", "hard_issue_prevalence", "expected-indexable internal HTML URLs", role="eligibility_gate", base_priority="P0", priority_ceiling="P0", veto="overall")
add_spec("T08", "strict_issue_prevalence", "canonical expected-indexable URLs eligible for XML sitemap inclusion", role="eligibility_gate", base_priority="P2", priority_ceiling="P1", citations=("GOOGLE_SITEMAPS",))
add_spec("T09", "hard_issue_prevalence", "canonical expected-indexable internal HTML URLs", role="eligibility_gate", base_priority="P0", priority_ceiling="P0", veto="overall", citations=("GOOGLE_CANONICAL", "GOOGLE_JAVASCRIPT"))
add_spec("T10", "hard_issue_prevalence", "GSC-inspected priority URL sample capped at 2,000 URLs", role="eligibility_gate", base_priority="P0", priority_ceiling="P0", veto="overall", coverage="inspection", citations=("GSC_LIMITS",))
add_spec("T11", "strict_issue_prevalence", "internal redirecting URLs and links pointing to redirects", role="eligibility_gate", base_priority="P2", priority_ceiling="P1", citations=("GOOGLE_CANONICAL",))
add_spec("T12", "strict_issue_prevalence", "expected-indexable URLs with measured crawl depth", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("T13", "strict_issue_prevalence", "expected-indexable URLs and crawlable internal link edges", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("T14", "strict_issue_prevalence", "distinct URLs in the sitemap/GSC/crawl union", evidence="G2_CALCULATED", role="supporting_driver", base_priority="P2", priority_ceiling="P1", coverage="partial")
add_spec("T15", "hard_issue_prevalence", "rendered expected-indexable HTML URLs", role="eligibility_gate", base_priority="P1", priority_ceiling="P0", veto="overall", citations=("GOOGLE_JAVASCRIPT",))
add_spec("T16", "standard_issue_prevalence", "URLs with paired original and rendered HTML", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("GOOGLE_JAVASCRIPT",))
add_spec("T17", "hard_issue_prevalence", "URLs with paired original and rendered directives, metadata, links and schema", role="eligibility_gate", base_priority="P1", priority_ceiling="P0", veto="overall", citations=("GOOGLE_JAVASCRIPT",))
add_spec("T18", "strict_issue_prevalence", "rendered URLs and required page resources", role="eligibility_gate", base_priority="P1", priority_ceiling="P0", veto="block", citations=("GOOGLE_JAVASCRIPT",))
add_spec("T19", "strict_issue_prevalence", "localized URL alternates", applicability="multilingual", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("GOOGLE_HREFLANG",))
add_spec("T20", "strict_issue_prevalence", "URLs with both mobile and desktop PSI lab results", applicability="dual_psi", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("LIGHTHOUSE_SCORING",))
add_spec("T21", "lighthouse_distribution", "successfully tested PSI URLs by mobile and desktop strategy", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("LIGHTHOUSE_SCORING",))
add_spec("T22", "standard_issue_prevalence", "crawlable URL inventory of an applicable large/rapidly changing site", applicability="crawl_budget", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("GOOGLE_CRAWL_BUDGET",))
add_spec("T23", "standard_issue_prevalence", "indexable content URLs with exact/near-duplicate signals", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("GOOGLE_CANONICAL",))
add_spec("T24", "rubric_standard", "crawlable internal URLs and their response/resource diagnostics", evidence="G2_CALCULATED", role="supporting_driver", base_priority="P3", priority_ceiling="P2")
add_spec("T25", "lighthouse_distribution", "URLs with successful automated SF and PSI accessibility audits", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("LIGHTHOUSE_SCORING",))


# B — AI Visibility, Brand Representation & Sentiment (26 factors)
add_spec("B01", "scope_integrity", "all SISTRIX API artifacts and sentiment snapshots for the run", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="eligibility_gate", base_priority="P0", priority_ceiling="P0", criticality="sitewide", veto="block", coverage="source")
add_spec("B02", "presence_with_baseline", "SISTRIX brand-mention prompt_count in the frozen model/country scope", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", zero_denominator="ND", citations=("SISTRIX_PROMPT_HISTORY",))
add_spec("B03", "presence_with_baseline", "SISTRIX domain-citation prompt_count in the frozen model/country scope", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", zero_denominator="ND", citations=("SISTRIX_SOURCES", "SISTRIX_PROMPT_HISTORY"))
add_spec("B04", "presence_with_baseline", "SISTRIX combined prompt_count in the frozen model/country scope", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", zero_denominator="ND", citations=("SISTRIX_PROMPT_HISTORY",))
add_spec("B06", "coverage_strict", "configured SISTRIX AI models", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P2", priority_ceiling="P1", criticality="model_country", coverage="source", citations=("SISTRIX_MODELS",))
add_spec("B07", "coverage_strict", "configured target countries", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P2", priority_ceiling="P1", criticality="model_country", coverage="source")
add_spec("B08", "coverage_complete", "platform-defined detected prompt corpus versus fully paginated prompt records", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="model_country", coverage="source")
add_spec("B09", "text_completeness", "returned SISTRIX prompt records", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="eligibility_gate", base_priority="P1", priority_ceiling="P1", criticality="model_country", veto="block", coverage="source")
add_spec("B10", "rubric_strict", "brand-containing returned answer texts and sentiment examples", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source")
add_spec("B11", "coverage_complete", "fully paginated SISTRIX source records in the frozen scope", applicability="sitewide", evidence="G3_SOURCE_LIMITED", confidence="direct_visibility", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="model_country", coverage="source", citations=("SISTRIX_SOURCES",))
add_spec("B12", "descriptive_no_norm", "SISTRIX competitor-brand set in the frozen scope", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="supporting_driver", base_priority=None, priority_ceiling=None, criticality="none", coverage="source", zero_denominator="ND", citations=("SISTRIX_COMPETITORS",), informational_only=True)
add_spec("B13", "rubric_strict", "returned answers containing the brand and at least one observed competitor", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", citations=("SISTRIX_COMPETITORS",))
add_spec("B14", "prominence", "brand-containing returned SISTRIX answers", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source")
add_spec("B15", "rubric_strict", "distinct supported brand-attribute statements in returned answers and sentiment snapshot", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source")
add_spec("B16", "rubric_strict", "returned answers where the brand appears with alternatives or comparison criteria", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", citations=("SISTRIX_COMPETITORS",))
add_spec("B17", "hard_issue_prevalence", "AI brand claims that can be exactly matched to site-declared truth fields", applicability="sitewide", evidence="G2_CALCULATED", confidence="exact_cross_source", role="direct_observed_outcome", base_priority="P0", priority_ceiling="P0", criticality="model_country", veto="overall", coverage="partial", zero_denominator="ND")
add_spec("B18", "sentiment_wilson", "all Lob and Kritik mentions in the SISTRIX sentiment snapshot", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", veto="block", coverage="source", zero_denominator="ND", citations=("NIST_WILSON",))
add_spec("B19", "group_sentiment", "platform groups displayed in the SISTRIX sentiment snapshot", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", veto="block", coverage="source", zero_denominator="ND", citations=("NIST_WILSON",))
add_spec("B20", "sentiment_wilson", "all Lob and Kritik mentions in the SISTRIX sentiment snapshot", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", zero_denominator="ND", citations=("NIST_WILSON",), dependency_parents=("B18",), root_cause_group="brand-sentiment")
add_spec("B21", "group_sentiment", "topic groups displayed in the SISTRIX sentiment snapshot", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", zero_denominator="ND", citations=("NIST_WILSON",), dependency_parents=("B18",), root_cause_group="brand-sentiment")
add_spec("B22", "weak_theme_balance", "supported strong and weak themes in the SISTRIX sentiment snapshot", applicability="sitewide", evidence="G3_SOURCE_LIMITED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", dependency_parents=("B18",), root_cause_group="brand-sentiment")
add_spec("B23", "percentile_quartile", "SISTRIX-displayed sentiment benchmark group", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P2", priority_ceiling="P1", criticality="model_country", coverage="source")
add_spec("B24", "coverage_complete", "sentiment claims/examples with displayed platform and source fields", applicability="sitewide", evidence="G3_SOURCE_LIMITED", confidence="direct_visibility", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="model_country", coverage="source")
add_spec("B25", "trend_only", "daily SISTRIX prompt_count values in one unchanged scope", applicability="comparable_baseline", evidence="G2_CALCULATED", confidence="history", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="history", zero_denominator="ND", citations=("SISTRIX_PROMPT_HISTORY",))
add_spec("B26", "presence_with_baseline", "Google Generative AI impressions in the provided export scope", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="model_country", coverage="source", zero_denominator="ND")
add_spec("B27", "coverage_strict", "confirmed critical landing pages eligible for first-party GAI impressions", applicability="sitewide", evidence="G2_CALCULATED", confidence="direct_visibility", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="url_cluster", coverage="source", zero_denominator="ND")


# C — Content, Evidence & Trust (27 factors)
add_spec("C01", "rubric_strict", "indexable URLs mapped to observed GSC queries and SISTRIX prompts", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("C02", "rubric_strict", "question- or task-intent content sections", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("C03", "rubric_standard", "indexable content URLs", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("C04", "strict_issue_prevalence", "indexable content URLs and paired raw/rendered metadata", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("C05", "rubric_strict", "indexable URLs mapped to material observed intents", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("C06", "rubric_standard", "content URLs introducing entities, services, processes, or specialist terms", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric")
add_spec("C07", "rubric_strict", "content URLs containing material factual claims", applicability="claim_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("C08", "rubric_standard", "URLs with comparison intent or multiple alternatives", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric")
add_spec("C09", "rubric_standard", "URLs describing a process, application, claim, purchase, or other ordered task", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric")
add_spec("C10", "rubric_standard", "URLs with observed question intent or FAQ sections", applicability="question_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric")
add_spec("C11", "rubric_strict", "indexable brand, organization, product, and service URLs", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("C12", "rubric_strict", "commercial product/service URLs", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("C13", "rubric_strict", "commercial URLs mapped to observed competitor comparisons", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("C14", "rubric_strict", "URLs making claims about price, eligibility, availability, exclusions, risk, geography, or terms", applicability="claim_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P0", veto="block")
add_spec("C17", "strict_issue_prevalence", "editorial/YMYL URLs where readers reasonably expect authorship", applicability="authored_pages", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("C18", "rubric_standard", "identified author/editor profiles and their linked content", applicability="authored_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", coverage="partial")
add_spec("C19", "freshness_sla", "date-relevant content URLs classified by volatility", applicability="dated_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("C20", "rubric_strict", "content URLs making material factual or comparative claims", applicability="claim_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", coverage="partial")
add_spec("C21", "rubric_standard", "editorial, advisory, research, review, and comparison URLs", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", coverage="partial")
add_spec("C22", "rubric_strict", "site-level organization, legal, editorial, contact, support, and policy surfaces", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="sitewide", veto="block")
add_spec("C23", "hard_issue_prevalence", "normalized site-declared facts repeated across URLs", evidence="G2_CALCULATED", confidence="exact_cross_source", role="direct_observed_outcome", base_priority="P0", priority_ceiling="P0", veto="overall")
add_spec("C24", "rubric_strict", "site-level brand truth categories: identity, offers, audiences, prices, geography, and limitations", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", criticality="sitewide")
add_spec("C25", "rubric_strict", "localized URLs in the configured market", applicability="localized_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("C26", "rubric_standard", "indexable content URLs with readable main text", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric")
add_spec("C27", "standard_issue_prevalence", "indexable URLs containing meaningful images or video", applicability="media_pages", role="supporting_driver", base_priority="P2", priority_ceiling="P1")
add_spec("C28", "strict_issue_prevalence", "indexable content URLs grouped by duplicate/near-duplicate/template patterns", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1", veto="block")
add_spec("C29", "freshness_sla", "date-relevant URLs with current GSC demand or matched SISTRIX prompts", applicability="dated_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")


# S — Structured Data & Entity Consistency (20 factors)
add_spec("S01", "coverage_strict", "URLs whose confirmed page type has an applicable main entity schema type", role="supporting_driver", base_priority="P2", priority_ceiling="P2")
add_spec("S02", "strict_issue_prevalence", "URLs containing structured data items", role="supporting_driver", base_priority="P2", priority_ceiling="P1", veto="block")
add_spec("S03", "hard_issue_prevalence", "URLs containing structured data items with a page-type mapping", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P0", veto="block")
add_spec("S04", "rubric_strict", "site-level Organization nodes and pages declaring organization identity", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", base_priority="P2", priority_ceiling="P1", criticality="sitewide")
add_spec("S05", "rubric_strict", "site-level WebSite nodes", applicability="sitewide", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", base_priority="P2", priority_ceiling="P1", criticality="sitewide")
add_spec("S06", "rubric_strict", "WebPage and Article nodes on article/editorial URLs", applicability="article_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", base_priority="P2", priority_ceiling="P1")
add_spec("S07", "rubric_strict", "Product and Offer nodes on confirmed product URLs", applicability="product_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P0", veto="block")
add_spec("S08", "rubric_strict", "Service nodes on confirmed service URLs", applicability="service_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", base_priority="P2", priority_ceiling="P1")
add_spec("S09", "rubric_strict", "LocalBusiness nodes on confirmed location/business URLs", applicability="local_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P1")
add_spec("S10", "rubric_standard", "Person/author nodes on authored content and profile URLs", applicability="authored_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric")
add_spec("S11", "strict_issue_prevalence", "indexable URLs with visible or marked-up breadcrumb trails", base_priority="P2", priority_ceiling="P1")
add_spec("S12", "hard_issue_prevalence", "URLs with visible FAQ/HowTo content or corresponding schema", applicability="faq_howto_pages", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P0", veto="block")
add_spec("S13", "hard_issue_prevalence", "URLs with Review or AggregateRating markup", applicability="review_pages", evidence="G2_CALCULATED", confidence="exact_cross_source", role="direct_observed_outcome", base_priority="P0", priority_ceiling="P0", veto="overall")
add_spec("S14", "rubric_standard", "entity nodes exposing sameAs or stable identifiers", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric")
add_spec("S15", "hard_issue_prevalence", "authored/date-relevant URLs with both visible and structured author/publisher/date values", applicability="authored_pages", evidence="G2_CALCULATED", confidence="exact_cross_source", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P0", veto="block")
add_spec("S16", "hard_issue_prevalence", "product/service URLs with both visible and structured offer fields", applicability="product_pages", evidence="G2_CALCULATED", confidence="exact_cross_source", role="direct_observed_outcome", base_priority="P0", priority_ceiling="P0", veto="overall")
add_spec("S17", "standard_issue_prevalence", "URLs containing meaningful images or video with applicable media schema", applicability="media_pages", base_priority="P2", priority_ceiling="P1")
add_spec("S18", "strict_issue_prevalence", "URLs with paired original and rendered structured-data graphs", role="supporting_driver", base_priority="P2", priority_ceiling="P1", citations=("GOOGLE_JAVASCRIPT",))
add_spec("S19", "hard_issue_prevalence", "structured properties that make material claims about visible page content", evidence="G2_CALCULATED", confidence="exact_cross_source", role="direct_observed_outcome", base_priority="P0", priority_ceiling="P0", veto="overall")
add_spec("S20", "hard_issue_prevalence", "normalized structured-data entity graph IDs and properties", evidence="G2_CALCULATED", confidence="exact_cross_source", role="direct_observed_outcome", base_priority="P1", priority_ceiling="P0", veto="block")


# O — Offsite Authority & Source Ecosystem (15 factors)
add_spec("O01", "trend_only", "backlink records in two comparable Ahrefs snapshots", applicability="comparable_baseline", evidence="G2_CALCULATED", confidence="history", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="url_cluster", coverage="source", zero_denominator="ND")
add_spec("O02", "trend_only", "unique referring domains in two comparable Ahrefs snapshots", applicability="comparable_baseline", evidence="G2_CALCULATED", confidence="history", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="url_cluster", coverage="source", zero_denominator="ND")
add_spec("O03", "descriptive_no_norm", "exported Ahrefs authority/rating distribution", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="supporting_driver", base_priority=None, priority_ceiling=None, criticality="none", coverage="source", zero_denominator="ND", informational_only=True)
add_spec("O04", "descriptive_no_norm", "follow/nofollow/link-attribute records returned by Screaming Frog", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_crawl", role="supporting_driver", base_priority=None, priority_ceiling=None, criticality="none", zero_denominator="ND", informational_only=True)
add_spec("O05", "strict_issue_prevalence", "classifiable Ahrefs backlink anchors", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="supporting_driver", base_priority="P2", priority_ceiling="P1", coverage="source")
add_spec("O06", "hard_issue_prevalence", "Ahrefs broken-backlink records joined exactly to current target status", role="supporting_driver", base_priority="P1", priority_ceiling="P0", veto="block", coverage="source", zero_denominator="green", citations=("AHREFS_BROKEN",))
add_spec("O07", "coverage_strict", "confirmed critical target pages versus pages receiving at least one referring domain", evidence="G2_CALCULATED", confidence="direct_visibility", role="supporting_driver", base_priority="P2", priority_ceiling="P1", coverage="source")
add_spec("O08", "source_concentration", "referring domains or referring pages grouped by source and sitewide pattern", evidence="G2_CALCULATED", confidence="direct_visibility", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="sitewide", coverage="source")
add_spec("O09", "descriptive_no_norm", "classifiable exported link types, platforms and attributes", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="supporting_driver", base_priority=None, priority_ceiling=None, criticality="none", coverage="source", zero_denominator="ND", informational_only=True)
add_spec("O10", "trend_only", "links with exported first-seen/last-seen/lost/new fields", applicability="link_time_fields", evidence="G2_CALCULATED", confidence="history", role="supporting_driver", base_priority="P2", priority_ceiling="P2", coverage="source", zero_denominator="ND")
add_spec("O11", "geo_relevance", "referring sources with classifiable country/language/topic signals", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="supporting_driver", base_priority="P2", priority_ceiling="P2", coverage="partial")
add_spec("O12", "opportunity_gap", "comparable competitor and external-source records in the SISTRIX corpus", evidence="G3_SOURCE_LIMITED", confidence="direct_visibility", role="supporting_driver", base_priority="P2", priority_ceiling="P1", criticality="model_country", coverage="source", citations=("SISTRIX_COMPETITORS",))
add_spec("O13", "descriptive_no_norm", "SISTRIX AI-cited hosts, domains and URLs", applicability="sitewide", evidence="G1_DIRECT", confidence="direct_visibility", role="supporting_driver", base_priority=None, priority_ceiling=None, criticality="none", coverage="source", zero_denominator="ND", citations=("SISTRIX_SOURCES",), informational_only=True)
add_spec("O14", "source_mix", "classifiable owned, competitor and independent SISTRIX source records", evidence="G3_SOURCE_LIMITED", confidence="direct_visibility", role="supporting_driver", base_priority="P2", priority_ceiling="P1", criticality="model_country", coverage="source", citations=("SISTRIX_SOURCES",))
add_spec("O17", "opportunity_gap", "validated external source opportunities observed for competitors in available SISTRIX/Ahrefs records", evidence="G4_SUPPORTED_INFERENCE", confidence="rubric", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="model_country", coverage="partial", citations=("SISTRIX_COMPETITORS",))


# M — Measurement & Reporting (17 factors)
add_spec("M01", "measurement_integrity", "calculation of Observed Brand Prompt Count", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", dependency_parents=("B02",), root_cause_group="sistrix-observed-counts")
add_spec("M02", "measurement_integrity", "calculation of Observed Domain Citation Prompt Count", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", dependency_parents=("B03",), root_cause_group="sistrix-observed-counts")
add_spec("M03", "measurement_integrity", "calculation of Observed Combined Visibility Prompt Count", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", dependency_parents=("B04",), root_cause_group="sistrix-observed-counts")
add_spec("M04", "measurement_integrity", "model distribution calculation and reconciliation", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", citations=("SISTRIX_MODELS",))
add_spec("M05", "measurement_integrity", "country distribution calculation and reconciliation", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source")
add_spec("M06", "measurement_integrity", "competitor set/count parsing and deduplication", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P3", priority_ceiling="P2", criticality="none", coverage="source", zero_denominator="green", citations=("SISTRIX_COMPETITORS",))
add_spec("M07", "measurement_integrity", "returned prompt record count after full pagination", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", citations=("SISTRIX_PROMPTS",))
add_spec("M08", "measurement_integrity", "unique cited host/domain/URL counts", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", coverage="source", citations=("SISTRIX_SOURCES",))
add_spec("M09", "measurement_integrity", "source amount aggregation in the documented grain", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", citations=("SISTRIX_SOURCES",))
add_spec("M10", "measurement_integrity", "source prompt_count aggregation in the documented grain", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", citations=("SISTRIX_SOURCES",))
add_spec("M11", "measurement_integrity", "owned cited-source share with an explicit nonzero denominator", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", zero_denominator="ND", citations=("SISTRIX_SOURCES",))
add_spec("M12", "measurement_integrity", "top-source concentration calculation with an explicit amount or prompt_count denominator", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", coverage="source", zero_denominator="ND", citations=("SISTRIX_SOURCES",))
add_spec("M13", "history_coverage", "daily SISTRIX prompt_count series in one unchanged scope", applicability="sitewide", evidence="G2_CALCULATED", confidence="history", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", coverage="history", zero_denominator="ND", citations=("SISTRIX_PROMPT_HISTORY",))
add_spec("M14", "measurement_integrity", "Google Generative AI impression totals and date aggregation", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", veto="block", coverage="source", zero_denominator="green")
add_spec("M15", "measurement_integrity", "GAI page/country/device distribution reconciliation", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P2", priority_ceiling="P2", criticality="none", coverage="source", zero_denominator="green")
add_spec("M16", "measurement_integrity", "SISTRIX sentiment score arithmetic against displayed Lob/Kritik counts", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P1", priority_ceiling="P1", criticality="none", veto="block", coverage="source", zero_denominator="ND", citations=("NIST_WILSON",), dependency_parents=("B18",), root_cause_group="brand-sentiment")
add_spec("M17", "measurement_integrity", "topic sentiment balance arithmetic against displayed counts", applicability="sitewide", evidence="G2_CALCULATED", confidence="measurement", role="supporting_driver", base_priority="P1", priority_ceiling="P1", criticality="none", veto="block", coverage="source", zero_denominator="ND", citations=("NIST_WILSON",), dependency_parents=("B21",), root_cause_group="brand-sentiment")


RUBRIC_CRITERIA: dict[str, list[str]] = {
    "T24": [
        "Normalized URL is at most 115 characters and has no unapproved crawlable parameter; 116–200 characters or one approved parameter is partial; otherwise fail.",
        "Median server response time is at most 800 ms; 801–1500 ms is partial; above 1500 ms or no response fails.",
        "Transferred HTML is at most 500 KiB; above 500 KiB through 1 MiB is partial; above 1 MiB fails.",
        "Total transferred page weight is at most 2 MiB; above 2 MiB through 5 MiB is partial; above 5 MiB or a required failed resource fails.",
    ],
    "B10": [
        "The answer explicitly identifies the brand's role, offer, or category instead of an unexplained name-only mention.",
        "The mentioned attribute is supported by the answer context or a site-declared fact and is not internally contradictory.",
        "The answer identifies the relevant audience, use case, or comparison context when one is material to the prompt.",
        "Material eligibility limits, exclusions, price qualifications, or uncertainty are stated next to the claim when relevant.",
    ],
    "B13": [
        "The brand and competitor are compared in the same prompt intent and product/service category.",
        "At least one explicit common comparison criterion is stated for both sides.",
        "The wording distinguishes observation from recommendation and avoids unsupported winner language.",
        "Material advantages and limitations are represented symmetrically enough to support the stated conclusion.",
    ],
    "B15": [
        "Each recurring brand attribute has an exact answer excerpt and normalized attribute label.",
        "The attribute is consistent with site-declared truth or is explicitly marked externally unverified.",
        "The attribute's audience, product, geography, or time scope is retained.",
        "Repeated attributes are quantified across distinct prompts/models rather than inferred from one quotation.",
    ],
    "B16": [
        "The answer names the comparison or alternative-selection criterion.",
        "Brand and alternatives are evaluated within the same product, audience, country, and time scope.",
        "Recommendation or shortlist position is recorded separately from a simple mention.",
        "The stated reason and material limitations are retained in the evidence excerpt.",
    ],
    "C01": [
        "The page's primary topic matches the dominant mapped query/prompt intent.",
        "The main content resolves the primary user task rather than only repeating query vocabulary.",
        "Material mapped sub-intents are covered or linked to an appropriate dedicated page.",
        "Unrelated template or marketing text does not obscure the primary topic.",
    ],
    "C02": [
        "A direct answer, definition, or decision statement appears in the first relevant section.",
        "The answer precedes supporting detail instead of requiring the reader to infer the conclusion.",
        "The subject, audience, and jurisdiction/product scope of the answer are explicit.",
        "Material exceptions or conditions appear adjacent to the direct answer.",
    ],
    "C03": [
        "The URL has one descriptive H1 aligned with the main topic.",
        "H2–H6 headings form coherent sections and describe their content rather than using generic labels.",
        "Lists and tables are used for genuinely repeated fields, steps, or comparisons.",
        "Navigation, breadcrumbs, and in-page links expose the page's place in the topic hierarchy.",
    ],
    "C05": [
        "The page explains prerequisites or eligibility for the mapped intent.",
        "It covers material options, variants, or alternatives.",
        "It states material exceptions, exclusions, risks, or failure cases.",
        "It answers or links to the principal next questions evidenced by GSC queries or SISTRIX prompts.",
    ],
    "C06": [
        "A definition appears at or immediately after the first material use of the term.",
        "The definition states the broader category and distinguishing characteristics.",
        "It uses plain language and expands unavoidable specialist abbreviations.",
        "The same term is used consistently across the page and linked related pages.",
    ],
    "C07": [
        "Each material fact identifies a subject and unambiguous value or categorical assertion.",
        "Numbers retain unit, currency, period, geography, and calculation basis where applicable.",
        "Time-sensitive facts include an effective or checked date.",
        "Material externally derived facts have an adjacent source or documented first-party method.",
    ],
    "C08": [
        "Alternatives are compared with an explicit, common set of criteria.",
        "Rows and columns have semantic headers and remain understandable outside visual styling.",
        "Values retain units, effective dates, and material qualifications.",
        "Advantages and disadvantages are represented without unsupported absolute-superiority claims.",
    ],
    "C09": [
        "Steps are ordered and each step contains one identifiable action.",
        "Prerequisites, required inputs, or responsible party are stated before the relevant step.",
        "Expected outcome or completion condition is stated.",
        "Material exceptions, alternative paths, time limits, or failure handling are included.",
    ],
    "C10": [
        "Questions correspond to evidenced user language or a necessary next question for the page intent.",
        "Each answer is direct, self-contained, and materially distinct from the other answers.",
        "The full answer is visible in HTML and does not depend on inaccessible interaction.",
        "The FAQ does not duplicate a stronger dedicated section or create near-identical scaled pages.",
    ],
    "C11": [
        "The legal/common brand name and organization or service category are explicit.",
        "The relationship between organization, brands, products, and services is unambiguous.",
        "Primary geography, service area, or market is explicit where relevant.",
        "Identity statements agree with contact, legal, and structured-data surfaces.",
    ],
    "C12": [
        "The product or service is named and described in concrete terms.",
        "Intended and excluded audiences or eligibility conditions are explicit.",
        "Availability geography and delivery/service channel are explicit.",
        "Variants, principal use cases, and material limits are discoverable on the page.",
    ],
    "C13": [
        "Each differentiator names a concrete attribute rather than an unqualified superlative.",
        "A first-party method, specification, example, or cited source supports the differentiator.",
        "The comparison baseline and relevant competitor/product category are explicit.",
        "Material limits and cases where the alternative may be preferable are not hidden.",
    ],
    "C14": [
        "Price, availability, eligibility, term, or benefit claims include effective scope and date where needed.",
        "Material exclusions, deductibles, conditions, or risks are stated next to the benefit claim.",
        "Jurisdiction and regional/product variation are explicit.",
        "The page provides a clear route to authoritative current terms or contractual detail.",
    ],
    "C18": [
        "The author/editor has a visible biography connected to the audited content.",
        "Role, employer/affiliation, and subject responsibility are explicit.",
        "Relevant qualifications or first-hand experience are described without unverifiable inflation.",
        "A stable profile, contact route, publication history, or external identifier permits verification.",
    ],
    "C20": [
        "Material externally derived claims have an adjacent, identifiable source.",
        "The cited source actually addresses the neighbouring claim and is not merely a generic homepage.",
        "Primary data or calculations include method, denominator, period, and limitations.",
        "Sources are reachable, current enough for the claim, and distinguished from marketing evidence.",
    ],
    "C21": [
        "The page contains identifiable first-party data, testing, experience, cases, or calculations.",
        "The method or conditions under which the original material was produced are stated.",
        "Examples contain enough concrete detail to be independently understood.",
        "The original material adds an insight not obtained by merely paraphrasing cited sources.",
    ],
    "C22": [
        "Impressum/legal identity and a functioning contact route are present and consistent.",
        "Editorial responsibility, correction route, or content governance is discoverable where expected.",
        "Privacy, terms, complaints, and other material policies are accessible for the site's activity.",
        "Support and escalation routes are explicit for material customer or YMYL decisions.",
    ],
    "C24": [
        "Organization and brand identity, including relationships and identifiers, are normalized without contradiction.",
        "Products/services, variants, and intended audiences are explicitly represented.",
        "Prices/benefits, geography, availability, and effective dates are represented where applicable.",
        "Eligibility, exclusions, risks, and other material limitations are represented and traceable to URLs.",
    ],
    "C25": [
        "Language, spelling, currency, units, and market terminology match the configured locale.",
        "Products, service availability, contacts, and prices correspond to that market.",
        "Applicable laws, institutions, and cited sources are local rather than mechanically translated substitutes.",
        "Examples and user problems reflect the local audience and are not translation-only boilerplate.",
    ],
    "C26": [
        "Sentence and paragraph length avoid repeated extremes according to the language-specific SF readability output.",
        "Headings, lists, and spacing make major answers and transitions scannable.",
        "Specialist terms and abbreviations are defined at first material use.",
        "The visible hierarchy distinguishes main content, navigation, disclaimers, and supporting detail.",
    ],
    "S04": [
        "Organization has stable @id plus name/legalName and canonical URL.",
        "Logo, contactPoint, address, and identifiers are present when visibly applicable.",
        "sameAs values point to official profiles for the same organization.",
        "All material values agree with visible identity, legal, and contact content.",
    ],
    "S05": [
        "WebSite has stable @id, canonical URL, and site name.",
        "publisher points to the canonical Organization entity.",
        "The WebSite node is unique or consistently merged across templates.",
        "Name, URL, and publisher agree with visible site identity.",
    ],
    "S06": [
        "WebPage/Article headline, mainEntity, and canonical URL identify the visible page.",
        "author and publisher resolve to stable Person/Organization entities.",
        "datePublished and dateModified agree with visible dates and chronology.",
        "Image and other material properties are crawlable and represented in visible content.",
    ],
    "S07": [
        "Product identity, brand, model/SKU, and stable @id match the visible product.",
        "Offer price, currency, availability, seller, and validity fields are complete when shown.",
        "Variants and aggregate offers are not merged into a misleading single value.",
        "All material Product/Offer values agree with visible current content.",
    ],
    "S08": [
        "Service type, name, stable @id, and provider identify the visible service.",
        "audience and areaServed match visible eligibility and geography.",
        "Offers or terms are represented only when visible and current.",
        "The Service node is linked coherently to WebPage and Organization entities.",
    ],
    "S09": [
        "The most specific applicable LocalBusiness subtype, name, URL, and stable @id are used.",
        "Address/NAP and geo coordinates agree with visible contact/location content.",
        "Opening hours and service area are complete and current where applicable.",
        "The location entity is not conflated with the parent Organization or another branch.",
    ],
    "S10": [
        "Person name, stable @id, and profile URL identify the visible author.",
        "affiliation/jobTitle match visible biography and Organization relationships.",
        "Credentials or expertise fields are used only when visibly supported.",
        "sameAs values resolve to profiles belonging to the same person.",
    ],
    "S14": [
        "Each principal entity has one stable, canonical @id reused consistently.",
        "sameAs links resolve and represent the identical entity rather than a topic or search result.",
        "Organization, brand, product, location, and person identifiers are not conflated.",
        "External identifiers are authoritative enough to disambiguate the entity and agree with visible content.",
    ],
}


RUBRIC_VALUE_POLICY = {
    "full": {"value": 1.0, "definition": "Criterion is completely satisfied and supported by inspectable evidence."},
    "partial": {"value": 0.5, "definition": "Criterion is only partly satisfied; the missing component is named and evidenced."},
    "fail": {"value": 0.0, "definition": "Criterion is absent, contradicted, materially wrong, or unsupported."},
    "not_applicable": {"value": None, "definition": "Criterion is inapplicable under the factor's documented universe and is excluded from the denominator."},
}


ROOT_CAUSE_GROUPS = {
    "T02": "http-routing", "T11": "http-routing", "O06": "http-routing",
    "T03": "crawler-access", "T04": "crawler-access",
    "T05": "indexability-control", "T06": "indexability-control", "T10": "indexability-control",
    "T09": "canonical-duplicate-control", "T23": "canonical-duplicate-control", "C28": "canonical-duplicate-control",
    "T12": "internal-discovery", "T13": "internal-discovery", "T14": "internal-discovery",
    "T15": "javascript-rendering", "T16": "javascript-rendering", "T17": "javascript-rendering", "T18": "javascript-rendering", "S18": "javascript-rendering",
    "T19": "international-targeting", "C25": "international-targeting",
    "T20": "cross-device-delivery", "T21": "page-performance", "T24": "page-performance",
    "T25": "accessible-content", "C26": "accessible-content",
    "B02": "brand-mention-visibility", "B03": "owned-citation-visibility", "B04": "combined-ai-visibility",
    "B06": "ai-scope-breadth", "B07": "ai-scope-breadth", "B08": "sistrix-prompt-corpus", "B09": "sistrix-prompt-corpus",
    "B10": "brand-context", "B13": "brand-comparison-context", "B14": "brand-prominence", "B16": "brand-comparison-context",
    "B15": "brand-attributes", "B17": "brand-fact-consistency", "C11": "brand-fact-consistency", "C12": "brand-fact-consistency",
    "C13": "brand-differentiation", "C14": "brand-fact-consistency", "C23": "brand-fact-consistency", "C24": "brand-fact-consistency",
    "S07": "brand-fact-consistency", "S16": "brand-fact-consistency", "S19": "brand-fact-consistency",
    "B18": "brand-sentiment", "B19": "brand-sentiment", "B20": "brand-sentiment", "B21": "brand-sentiment", "B22": "brand-sentiment", "B23": "brand-sentiment", "B24": "brand-sentiment",
    "B25": "ai-visibility-trend", "B26": "google-gai-visibility", "B27": "google-gai-visibility",
    "C01": "demand-content-match", "C05": "demand-content-match", "C10": "demand-content-match", "C29": "demand-content-match",
    "C02": "answer-extractability", "C03": "answer-extractability", "C06": "answer-extractability", "C07": "answer-extractability", "C08": "answer-extractability", "C09": "answer-extractability",
    "C17": "authorship-trust", "C18": "authorship-trust", "S10": "authorship-trust", "S15": "authorship-trust",
    "C19": "content-freshness", "C20": "content-evidence", "C21": "content-evidence", "C22": "site-accountability",
    "C27": "media-context", "S17": "media-context",
    "S01": "structured-data-coverage", "S02": "structured-data-validity", "S03": "structured-data-applicability",
    "S04": "organization-entity", "S05": "website-entity", "S06": "article-entity", "S08": "service-entity", "S09": "local-entity",
    "S11": "breadcrumb-entity", "S12": "faq-howto-entity", "S13": "review-entity", "S14": "entity-identifiers", "S20": "entity-identifiers",
    "O01": "backlink-profile", "O02": "backlink-profile", "O03": "backlink-profile", "O04": "backlink-profile", "O05": "backlink-profile",
    "O07": "backlink-target-distribution", "O08": "backlink-concentration", "O09": "backlink-profile", "O10": "backlink-profile", "O11": "backlink-relevance",
    "O12": "external-source-gap", "O13": "ai-source-inventory", "O14": "ai-source-mix", "O17": "external-source-gap",
    "M04": "sistrix-scope-measurement", "M05": "sistrix-scope-measurement", "M06": "sistrix-competitor-measurement", "M07": "sistrix-prompt-corpus",
    "M08": "sistrix-source-measurement", "M09": "sistrix-source-measurement", "M10": "sistrix-source-measurement", "M11": "sistrix-source-measurement", "M12": "sistrix-source-measurement",
    "M13": "sistrix-history-measurement", "M14": "gsc-gai-measurement", "M15": "gsc-gai-measurement",
}


DEPENDENCY_PARENT_OVERRIDES = {
    "T10": ["T03", "T05", "T06", "T09"],
    "T14": ["T13"],
    "T17": ["T16"],
    "B04": ["B02", "B03"],
    "B13": ["B10"],
    "B16": ["B13"],
    "C05": ["C01"],
    "C10": ["C01"],
    "C13": ["C12"],
    "C24": ["C11", "C12", "C14", "C23"],
    "C29": ["C19", "C01"],
    "S03": ["S01"],
    "S07": ["C12", "C14"],
    "S10": ["C17", "C18"],
    "S15": ["C17", "C19"],
    "S16": ["C14", "S07"],
    "S18": ["T17"],
    "S19": ["C23"],
    "O06": ["T02"],
    "O07": ["T13"],
    "O12": ["B12", "B11"],
    "O14": ["B11"],
    "O17": ["O12"],
}


EVIDENCE_POLICY = {
    "grades": {
        "G1_DIRECT": "A value copied from a canonical source field with artifact hash, scope, and exact grain.",
        "G2_CALCULATED": "A deterministic calculation over G1 fields with reproducible SQL/filter and exact denominator.",
        "G3_SOURCE_LIMITED": "A complete observation inside a platform-defined corpus or snapshot that is not a universal demand denominator.",
        "G4_SUPPORTED_INFERENCE": "A rule- or rubric-based inference anchored in inspectable excerpts/fields and carrying an explicit limitation.",
    },
    "independence_rule": "Repeated fields, pages, or snapshots from the same dependent source do not raise evidence grade or confidence.",
    "finding_gate": [
        "Every finding resolves to at least one evidence ID and source artifact SHA-256.",
        "Numerator cannot exceed denominator and representative examples must belong to the calculated affected set.",
        "Grain, scope, source limitation, and join quality must agree with the wording of the finding.",
    ],
    "confidence_order": ["high", "medium", "low"],
    "confidence_resolution": "Start with the factor confidence base and apply every applicable cap; the lowest resulting confidence wins.",
    "confidence_control_metrics": {
        "coverage_rate": "Analysed required units divided by the declared applicable denominator.",
        "scope_type": "One of full, representative_sample, diagnostic_sample, source_corpus, or snapshot.",
        "join_quality": "One of exact, normalized_exact, fuzzy, or unresolved.",
        "artifact_age_days": "Whole UTC days from source snapshot/crawl time to audit evaluation time.",
        "material_record_count": "Records in the declared source corpus that enter the factor calculation.",
        "scope_mismatch_count": "Detected model, country, domain, language, or date-scope mismatches.",
        "exact_normalized_field_rate": "Comparable claims having exact normalized fields on both sides divided by comparable claims.",
        "claim_scope_match": "True only when entity, product, geography, time and qualifier scope agree.",
        "missing_rubric_evidence_count": "Required rubric dimensions lacking an inspectable locator.",
        "valid_daily_point_count": "Distinct valid daily observations inside one unchanged historical scope.",
        "missing_day_rate": "Missing expected days divided by expected days in the history window.",
        "scope_break_count": "Changes to brand/domain/model/country/method inside the comparison window.",
        "partial_record_rate": "Present but incomplete required records divided by expected records.",
        "validation_error_count": "Failed deterministic integrity assertions for the factor metric.",
    },
    "conflict_resolution": {
        "unresolved_input_conflict": "When canonical inputs conflict and no documented authoritative precedence resolves them, the affected factor is ND and confidence is capped low.",
        "measured_conflict_exception": "When the contradiction itself is the factor's measured outcome, retain the observed issue and score that factor; do not replace it with ND.",
        "required_evidence": "Persist every conflicting value, source artifact ID, comparison key, and the applied precedence rule or explicit unresolved result.",
    },
    "freshness_thresholds_days": {
        "crawl_14d": {"high_max": 14, "medium_max": 45, "older": "low"},
        "visibility_30d": {"high_max": 30, "medium_max": 90, "older": "low"},
        "static_reference": {"high_max": None, "medium_max": None, "older": "unchanged"},
    },
    "join_caps": {"exact": "unchanged", "normalized_exact": "medium", "fuzzy": "low", "unresolved": "ND"},
    "source_corpus_size_caps": {"0": "ND", "1_to_9": "low", "10_to_29": "medium", "30_plus": "unchanged"},
}


COVERAGE_POLICY = {
    "source_level_gate": "All 18 canonical sources must pass authentication, scope and schema preflight; otherwise the run is BLOCKED before scoring.",
    "record_level_rule": "Missing records inside a present source lower factor coverage; they never become zero-valued observations.",
    "valid_empty_source_rule": "A zero-row artifact is source-ready only when authentication/file access, expected schema, approved scope, snapshot date, and successful extraction are all proven. Factor handling then follows its explicit zero_denominator rule.",
    "factor_resolution_order": ["NA", "BLOCK_RUN", "preliminary_status", "coverage_gate", "confidence"],
    "confirmed_issue_override": "Below minimum coverage, only a preliminary red with confirmed_issue_override=true remains red; confidence is capped low. Every other preliminary result becomes ND.",
    "scope_types": {
        "full": "Every unit in the declared universe was analysed.",
        "representative_sample": "A documented deterministic or stratified sample supports only the sampled/represented universe.",
        "diagnostic_sample": "A non-representative sample supports examples and issue existence, not sitewide prevalence.",
        "source_corpus": "Every returned record in the platform-defined corpus was analysed; no universal demand inference is allowed.",
        "snapshot": "Every displayed record in a dated captured interface snapshot was analysed.",
    },
    "betroffenheit_bands": {
        "none": "affected_count == 0",
        "isolated": "affected_count > 0 AND affected_rate < 0.01 AND affected_count < 5",
        "limited": "not broad/material AND (affected_rate >= 0.01 OR affected_count >= 5)",
        "material": "not broad AND (affected_rate >= 0.05 OR affected_count >= 20)",
        "broad": "affected_rate >= 0.20 OR affected_count >= 100",
    },
    "betroffenheit_conditions": {
        "broad": any_of(comparison("affected_rate", "gte", 0.20), comparison("affected_count", "gte", 100)),
        "material": any_of(comparison("affected_rate", "gte", 0.05), comparison("affected_count", "gte", 20)),
        "limited": any_of(comparison("affected_rate", "gte", 0.01), comparison("affected_count", "gte", 5)),
        "isolated": comparison("affected_count", "gt", 0),
        "none": comparison("affected_count", "eq", 0),
    },
    "betroffenheit_precedence": ["broad", "material", "limited", "isolated", "none"],
    "betroffenheit_input_invariants": [
        "analyzed_count must be a positive integer before a band is assigned; otherwise Betroffenheit is ND.",
        "affected_count must be an integer from zero through analyzed_count.",
        "affected_rate is calculated, never supplied: affected_count / analyzed_count.",
    ],
    "sitewide_counting_rule": "COUNT(DISTINCT normalized_page_url); never add parent and child path-prefix counts.",
    "cluster_mapping_reuse": "Structural URL-prefix membership is always recalculated from the current crawl. Confirmed semantic labels and business criticality may be reused only while their normalized prefix pattern is unchanged; stale mappings cannot modify status or priority.",
    "gsc_url_inspection": "Full inventory when eligible URL count <= 2000; deterministic priority sample capped at 2000 otherwise.",
    "lighthouse_basis": "Lighthouse lab is the primary URL-level basis. CrUX is optional context; TBT is never renamed INP.",
}


PRIORITY_POLICY = {
    "algorithm_version": "priority-v1",
    "priority_order": ["P0", "P1", "P2", "P3"],
    "priority_index": {"P0": 0, "P1": 1, "P2": 2, "P3": 3},
    "evaluation_order": [
        "eligibility", "status_base", "betroffenheit", "criticality", "veto_floor",
        "factor_ceiling", "evidence_ceiling", "scope_ceiling", "confidence_ceiling", "clamp", "tie_break",
    ],
    "status_steps": {"red": 0, "yellow": 1, "green": None, "ND": None, "NA": None},
    "ceiling_resolution": "Convert every applicable ceiling to its priority index and take max(current_index, ceiling_indices); a ceiling can only make priority less urgent.",
    "floor_resolution": "For a proven red veto at high confidence, take min(current_index, floor_index) before ceilings; a floor can only make priority more urgent.",
    "meaning": {
        "P0": "Confirmed critical eligibility block or severe accuracy/reputation risk on a critical or broad scope.",
        "P1": "Material direct problem or strategic gap requiring planned remediation.",
        "P2": "Meaningful limited-scope problem or supporting driver.",
        "P3": "Low-materiality hygiene or opportunity item.",
    },
    "algorithm": [
        "Return null for green, ND, NA, informational_only, or a rule whose base_priority is null.",
        "For red start at factor base_priority; for yellow start one step less urgent, capped at P3.",
        "Apply Betroffenheit: broad upgrades one step, material makes no change, limited downgrades one step, isolated downgrades two steps.",
        "For non-URL direct outcomes, complete configured model/country scope is material; a subset is limited unless explicitly critical.",
        "A confirmed critical cluster/model/country may upgrade one step only when the rule permits it; unconfirmed mappings never modify priority.",
        "A high-confidence red block veto has a P1 urgency floor; a high-confidence red overall veto has a P0 urgency floor.",
        "Apply the factor priority_ceiling, then evidence/scope/confidence ceilings; the least urgent ceiling wins.",
        "Yellow can never exceed P1. Medium confidence can never exceed P1; low confidence can never exceed P2.",
        "G3 source-limited evidence is capped P1 for direct outcomes and P2 for supporting drivers. G4 is capped P1; diagnostic samples are capped P2 and representative samples P1.",
        "Effort and implementation reversibility do not raise priority. Effort is separate; a low-effort P1/P2 item may receive Quick Win.",
    ],
    "betroffenheit_steps": {"broad": -1, "material": 0, "limited": 1, "isolated": 2, "none": None},
    "criticality_uplift_steps": {"critical": -1, "high": -1, "medium": 0, "low": 0, "unconfirmed": 0},
    "criticality_conditions": {"critical": "any affected unit", "high": "material or broad Betroffenheit only"},
    "criticality_application": {
        "requires_confirmed_mapping": True,
        "critical_allowed_betroffenheit": ["isolated", "limited", "material", "broad"],
        "high_allowed_betroffenheit": ["material", "broad"],
        "maximum_uplift_steps": 1,
    },
    "veto_floors": {"overall_red_high": "P0", "block_red_high": "P1"},
    "confidence_ceilings": {"high": "factor_ceiling", "medium": "P1", "low": "P2"},
    "evidence_ceilings": {"G1_DIRECT": "factor_ceiling", "G2_CALCULATED": "factor_ceiling", "G3_SOURCE_LIMITED_direct": "P1", "G3_SOURCE_LIMITED_supporting": "P2", "G4_SUPPORTED_INFERENCE": "P1"},
    "scope_ceilings": {"full": "factor_ceiling", "snapshot": "factor_ceiling", "representative_sample": "P1", "diagnostic_sample": "P2", "source_corpus_direct": "P1", "source_corpus_supporting": "P2"},
    "harm_risk_rule": "Only an evidence-backed eligibility/accuracy/reputation veto affects the urgency floor; speculative harm does not.",
    "implementation_risk_rule": "Implementation risk changes validation and rollback requirements, not issue importance.",
    "effort_effect_on_priority": "none",
    "tie_break_order": ["priority", "veto_role", "dependency_role", "betroffenheit_band", "affected_count", "factor_id"],
    "summary_order": "P0, P1, P2, P3, then overall veto before block veto, eligibility/direct before supporting, broad before isolated, larger affected_count, factor_id ascending.",
}


def rollup_rule(minimum_coverage: float, red_direct: int, red_supporting: int) -> dict[str, Any]:
    red_condition = any_of(
        comparison("high_confidence_red_veto_count", "gte", 1),
        comparison("material_red_gate_or_outcome_count", "gte", red_direct),
        comparison("material_red_supporting_count", "gte", red_supporting),
    )
    return {
        "minimum_coverage_rate": minimum_coverage,
        "evaluation_order": ["red", "ND", "yellow", "green"],
        "red": red_condition,
        "yellow": any_of(
            comparison("red_low_confidence_count", "gte", 1),
            comparison("material_yellow_count", "gte", 1),
            comparison("red_count", "gte", 1),
            comparison("yellow_count", "gte", 2),
        ),
        "green": all_of(
            comparison("coverage_rate", "gte", minimum_coverage),
            comparison("red_count", "eq", 0),
            comparison("material_yellow_count", "eq", 0),
            comparison("yellow_count", "lte", 1),
        ),
        "nd": comparison("coverage_rate", "lt", minimum_coverage),
    }


BLOCK_ROLLUP_SPECS = {
    "T": {"minimum_coverage": 0.90, "red_direct": 2, "red_supporting": 3},
    "B": {"minimum_coverage": 0.85, "red_direct": 2, "red_supporting": 4},
    "C": {"minimum_coverage": 0.80, "red_direct": 2, "red_supporting": 4},
    "S": {"minimum_coverage": 0.85, "red_direct": 2, "red_supporting": 4},
    "O": {"minimum_coverage": 0.75, "red_direct": 3, "red_supporting": 3},
    "M": {"minimum_coverage": 0.90, "red_direct": 2, "red_supporting": 3},
}


BLOCK_ROLLUPS = {
    block: rollup_rule(spec["minimum_coverage"], spec["red_direct"], spec["red_supporting"])
    for block, spec in BLOCK_ROLLUP_SPECS.items()
}


OVERALL_ROLLUP = {
    "minimum_coverage_rate": 0.85,
    "evaluation_order": ["red", "ND", "yellow", "green"],
    "red": any_of(
        comparison("high_confidence_overall_veto_red_count", "gte", 1),
        comparison("red_block_count", "gte", 2),
    ),
    "yellow": any_of(
        comparison("red_block_count", "gte", 1),
        comparison("yellow_block_count", "gte", 1),
    ),
    "green": all_of(
        comparison("coverage_rate", "gte", 0.85),
        comparison("red_block_count", "eq", 0),
        comparison("yellow_block_count", "eq", 0),
        comparison("green_block_count", "eq", 6),
    ),
    "nd": comparison("coverage_rate", "lt", 0.85),
}


def parse_factor_matrix() -> dict[str, dict[str, Any]]:
    row_pattern = re.compile(
        r"^\| `(?P<id>(?:T|B|C|S|O|M)\d{2})` \| (?P<name>.*?) \| "
        r"(?P<description>.*?) \| (?P<sources>.*?) \| (?P<coverage>.*?) \|$"
    )
    factors: dict[str, dict[str, Any]] = {}
    for line in FACTOR_MATRIX.read_text(encoding="utf-8").splitlines():
        match = row_pattern.match(line)
        if not match:
            continue
        factor_id = match.group("id")
        if factor_id in factors:
            raise ValueError(f"Duplicate factor in canonical matrix: {factor_id}")
        sources = re.findall(r"`([^`]+)`", match.group("sources"))
        factors[factor_id] = {
            "factor_id": factor_id,
            "factor_name": match.group("name"),
            "description": match.group("description"),
            "sources": sources,
            "coverage_label": match.group("coverage"),
        }
    return factors


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def root_cause_for(factor_id: str, spec: dict[str, Any]) -> str:
    if spec["root_cause_group"]:
        return spec["root_cause_group"]
    return ROOT_CAUSE_GROUPS.get(factor_id, f"factor-{factor_id.lower()}")


def dependencies_for(factor_id: str, spec: dict[str, Any]) -> list[str]:
    return dedupe(spec["dependency_parents"] + DEPENDENCY_PARENT_OVERRIDES.get(factor_id, []))


def rubric_dimensions_for(factor_id: str, profile_name: str) -> list[dict[str, Any]]:
    if profile_name not in {"rubric_strict", "rubric_standard"}:
        return []
    criteria = RUBRIC_CRITERIA.get(factor_id)
    if not criteria:
        raise ValueError(f"Missing exact rubric criteria for {factor_id}")
    weight = 100.0 / len(criteria)
    return [
        {"dimension_id": f"{factor_id}-R{index}", "weight": weight, "criterion": criterion}
        for index, criterion in enumerate(criteria, start=1)
    ]


def affected_definition(profile_name: str, factor: dict[str, Any]) -> str:
    if profile_name == "hard_issue_prevalence":
        return "The factor analyzer marks a unit affected only for a material contradiction/block described by the source observation; configured intentional exclusions are removed before counting."
    if profile_name in {"strict_issue_prevalence", "standard_issue_prevalence"}:
        return "The factor analyzer marks each distinct applicable unit affected when at least one material check in the source observation fails after documented intentional exclusions."
    if profile_name in {"rubric_strict", "rubric_standard"}:
        return "Score each applicable rubric dimension 1, 0.5, 0, or NA under rubric_value_policy; compute the weighted 0–100 unit score, then classify unit fail/warning bands exactly as the selected profile defines."
    if profile_name == "sentiment_wilson":
        return "Compute positive share as Lob/(Lob+Kritik) and its two-sided 95% Wilson interval; neutral/unclassified mentions are reported but excluded from this binomial denominator."
    if profile_name == "group_sentiment":
        return "Compute a 95% Wilson interval per material platform/topic group, classify each group relative to 0.50, then calculate the group rates."
    if profile_name == "trend_only":
        return "Calculate change only when baseline and current values have identical brand/domain/model/country/grain definitions; otherwise no status band matches and result is ND."
    if profile_name == "presence_with_baseline":
        return "Use the platform-defined observed count; compare over time only when the frozen scope is identical and never divide by an invented relevant-prompt denominator."
    if profile_name == "descriptive_no_norm":
        return "Record the inventory value; assign no traffic-light direction unless an approved comparable baseline supplies an explicit normative grade."
    return f"Calculate the canonical profile metrics directly from this source observation: {factor['description']}"


def aggregation_definition(profile_name: str) -> str:
    if profile_name in {"hard_issue_prevalence", "strict_issue_prevalence", "standard_issue_prevalence"}:
        return "Use distinct units; issue_rate = affected_count / analyzed_count and calculate critical-cluster values separately."
    if profile_name in {"rubric_strict", "rubric_standard"}:
        return "Use weighted per-unit rubric scores, median score, distinct fail/warning unit rates, and critical fail count."
    if profile_name in {"sentiment_wilson", "group_sentiment"}:
        return "Use integer Lob/Kritik counts and deterministic Wilson calculations; never average displayed percentages across unequal groups."
    if profile_name in {"trend_only", "presence_with_baseline"}:
        return "Use exact current and baseline values in an identical scope; change_rate = (current - baseline) / baseline when baseline is nonzero."
    return "Use the canonical metrics and declared grain exactly; no fuzzy join or undocumented denominator is allowed."


def denominator_definition(profile_name: str, spec: dict[str, Any]) -> str:
    if profile_name in {"sentiment_wilson", "group_sentiment"}:
        return "Lob + Kritik inside the displayed snapshot group; zero produces the configured zero_denominator status."
    if profile_name in {"presence_with_baseline", "trend_only", "descriptive_no_norm", "measurement_integrity", "history_coverage"}:
        return "Use only the platform/source-defined scope; never invent a universal relevant-demand denominator."
    return f"Distinct applicable units in '{spec['universe']}'; missing records lower coverage and never enter the denominator as passing units."


def make_rule(factor: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    factor_id = factor["factor_id"]
    block = factor_id[0]
    profile_name = spec["profile"]
    profile = PROFILE_DEFINITIONS[profile_name]
    block_defaults = BLOCK_DEFAULTS[block]
    citation_ids = dedupe(block_defaults["citations"] + spec["citations"])
    coverage_gate = copy.deepcopy(COVERAGE_PROFILES[spec["coverage"]])
    coverage_gate["confirmed_issue_override"] = spec["veto"] != "none" or profile["rule_type"] in {"boolean_gate", "consistency"}
    criticality_profile = spec["criticality"]
    criticality_modifiers = {
        "profile": criticality_profile,
        "maximum_uplift_steps": 0 if criticality_profile == "none" else 1,
        "requires_confirmed_mapping": criticality_profile in {"url_cluster", "model_country"},
    }
    informational = spec["informational_only"]
    recommendation_trigger = {
        "statuses": [] if informational else ["red", "yellow"],
        "minimum_confidence": "medium" if spec["veto"] != "none" else "low",
        "informational_only": informational,
    }
    mechanism_basis = spec["mechanism_basis"] or block_defaults["mechanism_basis"]
    rationale = (
        f"{factor['factor_name']} evaluates {factor['description']}. "
        f"The mechanism is supported as {mechanism_basis}; the traffic-light cutoffs are classified as "
        f"{profile['cutoffs']} and are an audit decision unless explicitly official. "
        "The result is bounded to the declared universe and does not assert universal ranking causality."
    )
    return {
        "factor_id": factor_id,
        "factor_name": factor["factor_name"],
        "policy_version": POLICY_VERSION,
        "rule_type": profile["rule_type"],
        "applicability_rule": copy.deepcopy(APPLICABILITY[spec["applicability"]]),
        "canonical_metrics": copy.deepcopy(profile["metrics"]),
        "measurement_definition": {
            "source_observation": factor["description"],
            "unit_of_analysis": spec["universe"],
            "affected_definition": affected_definition(profile_name, factor),
            "aggregation": aggregation_definition(profile_name),
            "denominator_policy": denominator_definition(profile_name, spec),
        },
        "rubric_dimensions": rubric_dimensions_for(factor_id, profile_name),
        "measurement_universe": spec["universe"],
        "source_requirements": factor["sources"],
        "coverage_gate": coverage_gate,
        "evidence_grade": spec["evidence"],
        "confidence_rule": copy.deepcopy(CONFIDENCE_PROFILES[spec["confidence"]]),
        "status_bands": copy.deepcopy(profile["bands"]),
        "no_data_rule": {
            "source_level_failure": "BLOCK_RUN",
            "missing_required_metric": "ND",
            "zero_denominator": spec["zero_denominator"],
            "not_applicable": "NA",
        },
        "dependency_role": spec["role"],
        "dependency_parents": dependencies_for(factor_id, spec),
        "root_cause_group": root_cause_for(factor_id, spec),
        "base_priority": spec["base_priority"],
        "priority_ceiling": spec["priority_ceiling"],
        "criticality_modifiers": criticality_modifiers,
        "veto_role": spec["veto"],
        "recommendation_trigger": recommendation_trigger,
        "threshold_basis": {"mechanism": mechanism_basis, "cutoffs": profile["cutoffs"]},
        "causal_chain": {
            "observation": f"Measure {factor['description']} in the canonical source set.",
            "mechanism": profile["mechanism"],
            "affected_scope": spec["universe"],
            "consequence": block_defaults["consequence"],
            "action": profile["action"],
            "consequence_basis": {
                "official_hard_rule": "official",
                "official_guidance": "official",
                "platform_definition": "platform_observation",
                "empirical_association": "internal_policy_inference",
                "deterministic_derivation": "internal_policy_inference",
                "internal_audit_policy": "internal_policy_inference",
            }[mechanism_basis],
        },
        "rationale": rationale,
        "citations": citation_ids,
    }


def policy_fingerprint(policy: dict[str, Any]) -> str:
    normalized = copy.deepcopy(policy)
    normalized["policy_fingerprint"]["digest"] = ""
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_policy() -> dict[str, Any]:
    factors = parse_factor_matrix()
    if set(factors) != set(FACTOR_SPECS):
        missing = sorted(set(factors) - set(FACTOR_SPECS))
        extra = sorted(set(FACTOR_SPECS) - set(factors))
        raise ValueError(f"Factor policy mismatch; missing={missing}, extra={extra}")
    if len(factors) != 129:
        raise ValueError(f"Expected 129 factors, found {len(factors)}")
    observed_sources = {source for factor in factors.values() for source in factor["sources"]}
    if observed_sources != SOURCE_IDS:
        raise ValueError(f"Source catalog mismatch: expected={sorted(SOURCE_IDS)}, observed={sorted(observed_sources)}")
    rules = [make_rule(factors[factor_id], FACTOR_SPECS[factor_id]) for factor_id in sorted(factors)]
    policy: dict[str, Any] = {
        "policy_version": POLICY_VERSION,
        "policy_status": "frozen",
        "effective_date": EFFECTIVE_DATE,
        "factor_count": 129,
        "source_count": 18,
        "policy_fingerprint": {
            "algorithm": "sha256",
            "canonicalization": "canonical-json-v1-excluding-digest",
            "digest": "",
        },
        "rubric_value_policy": RUBRIC_VALUE_POLICY,
        "evidence_policy": EVIDENCE_POLICY,
        "coverage_policy": COVERAGE_POLICY,
        "priority_policy": PRIORITY_POLICY,
        "block_rollups": BLOCK_ROLLUPS,
        "overall_rollup": OVERALL_ROLLUP,
        "citations": CITATIONS,
        "rules": rules,
    }
    policy["policy_fingerprint"]["digest"] = policy_fingerprint(policy)
    return policy


def render_condition(condition: dict[str, Any]) -> str:
    if "all" in condition:
        return "(" + " AND ".join(render_condition(item) for item in condition["all"]) + ")"
    if "any" in condition:
        return "(" + " OR ".join(render_condition(item) for item in condition["any"]) + ")"
    if "not" in condition:
        return f"NOT {render_condition(condition['not'])}"
    operator = {"eq": "=", "ne": "!=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">=", "in": "IN", "not_in": "NOT IN", "between": "BETWEEN", "exists": "EXISTS"}[condition["operator"]]
    value = json.dumps(condition["value"], ensure_ascii=False)
    return f"{condition['metric']} {operator} {value}"


def render_policy_readme(policy: dict[str, Any]) -> str:
    digest = policy["policy_fingerprint"]["digest"]
    lines = [
        "# GEO Audit Scoring Policy",
        "",
        f"Policy version: `{policy['policy_version']}`  ",
        f"Policy status: `{policy['policy_status']}`  ",
        f"Effective date: `{policy['effective_date']}`  ",
        f"Policy fingerprint: `sha256:{digest}`  ",
        f"Rules: `{policy['factor_count']}`  ",
        f"Canonical sources: `{policy['source_count']}`",
        "",
        "This is the human-readable view of `scoring-matrix.yaml`. The YAML is the runtime source of truth; version, fingerprint and all 129 IDs must match before release.",
        "",
        "## Interpretation boundary",
        "",
        "Status, Priority and Confidence are independent. Betroffenheit is affected/analyzed scope, not causal or business impact. Official sources support mechanisms or a small number of hard thresholds; every internally selected cutoff is labelled `internal_audit_policy`. A descriptive metric without a defensible baseline remains ND instead of being forced into a favourable or unfavourable colour.",
        "",
        "## Status and no-data order",
        "",
        "1. Evaluate applicability: documented false becomes NA.",
        "2. A missing canonical source blocks the complete audit before scoring.",
        "3. Missing required record-level metrics or unresolved denominators become ND.",
        "4. Calculate preliminary red/yellow/green from the exact factor condition.",
        "5. Below the factor coverage gate, only a confirmed preliminary red explicitly allowed by `confirmed_issue_override` remains red, with low confidence; all other results become ND.",
        "6. Green never means unmeasured.",
        "",
        "## Evidence and confidence",
        "",
        "| Grade | Meaning |",
        "|---|---|",
    ]
    for grade, meaning in policy["evidence_policy"]["grades"].items():
        lines.append(f"| `{grade}` | {meaning} |")
    lines.extend([
        "",
        "Confidence begins at the factor's base and can only be capped downward by coverage, sample type, freshness, corpus size and join quality. Multiple observations from one dependent source do not increase confidence.",
        "",
        "If canonical input values conflict and no documented authoritative precedence resolves them, the affected factor is ND with low confidence. If the contradiction is itself the factor being measured, the issue remains scoreable and every conflicting value and artifact ID is retained.",
        "",
        "A schema-valid, scope-valid, dated zero-row export is a present source, not a missing source. Its factors resolve only through their explicit `zero_denominator` rules.",
        "",
        "## Betroffenheit",
        "",
        "| Band | Exact condition |",
        "|---|---|",
    ])
    for band_name in policy["coverage_policy"]["betroffenheit_precedence"]:
        lines.append(f"| `{band_name}` | `{policy['coverage_policy']['betroffenheit_bands'][band_name]}` |")
    lines.extend([
        "",
        "Sitewide aggregation uses `COUNT(DISTINCT normalized_page_url)`. Parent and child URL-prefix counts are never added.",
        "Structural URL-prefix membership is recalculated from every current crawl. A saved semantic label or business-criticality value is reusable only while its normalized prefix pattern is unchanged.",
        "",
        "## Priority algorithm",
        "",
    ])
    for index, step in enumerate(policy["priority_policy"]["algorithm"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend([
        "",
        "Deterministic tie-break: " + " → ".join(f"`{value}`" for value in policy["priority_policy"]["tie_break_order"]) + ".",
        "",
        "## Block roll-ups",
        "",
        "A colour is not averaged numerically. Evaluation order is red veto/material combinations, ND coverage gate, yellow material condition, then green.",
        "",
        "| Block | Minimum coverage | Red condition | Yellow condition |",
        "|---|---:|---|---|",
    ])
    for block, rollup in policy["block_rollups"].items():
        lines.append(f"| `{block}` | {rollup['minimum_coverage_rate']:.0%} | `{render_condition(rollup['red'])}` | `{render_condition(rollup['yellow'])}` |")
    lines.extend([
        "",
        "Overall red requires a high-confidence overall veto or at least two red blocks. One red block makes overall yellow unless an overall veto applies. Overall green requires all six blocks green and at least 85% applicable-factor coverage.",
        "",
        "## All factor rules",
        "",
        "| ID | Factor | Rule | Status bands | Base / ceiling | Evidence | Basis |",
        "|---|---|---|---|---|---|---|",
    ])
    for rule in policy["rules"]:
        status_summary = "; ".join(
            f"{status}: {render_condition(rule['status_bands'][status])}" for status in ("red", "yellow", "green")
        )
        lines.append(
            f"| `{rule['factor_id']}` | {rule['factor_name']} | `{rule['rule_type']}` | "
            f"{status_summary} | `{rule['base_priority']}` / `{rule['priority_ceiling']}` | "
            f"`{rule['evidence_grade']}` | `{rule['threshold_basis']['mechanism']}` + `{rule['threshold_basis']['cutoffs']}` |"
        )
    lines.extend(["", "## Exact qualitative rubrics", ""])
    for rule in policy["rules"]:
        if not rule["rubric_dimensions"]:
            continue
        lines.extend([f"### {rule['factor_id']} — {rule['factor_name']}", ""])
        for dimension in rule["rubric_dimensions"]:
            lines.append(f"- `{dimension['dimension_id']}` ({dimension['weight']:g}%): {dimension['criterion']}")
        lines.append("")
    lines.extend(["## Source basis", ""])
    for citation_id, citation in policy["citations"].items():
        lines.append(f"- `{citation_id}` — [{citation['title']}]({citation['url']}): {citation['supports']}")
    lines.extend([
        "",
        "## Change control",
        "",
        "Any rule, threshold, priority ceiling, veto, roll-up, rubric dimension, or interpretation change requires a semantic policy version bump, a written rationale, regenerated fingerprint, and passing boundary/adversarial regression tests.",
        "",
    ])
    return "\n".join(lines)


def build_betroffenheit_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "zero-denominator-is-nd", "affected_count": 0, "analyzed_count": 0, "expected": "ND"},
        {"case_id": "none-at-zero", "affected_count": 0, "analyzed_count": 1000, "expected": "none"},
        {"case_id": "isolated-below-one-percent", "affected_count": 4, "analyzed_count": 1000, "expected": "isolated"},
        {"case_id": "limited-at-one-percent", "affected_count": 1, "analyzed_count": 100, "expected": "limited"},
        {"case_id": "limited-at-five-count", "affected_count": 5, "analyzed_count": 1000, "expected": "limited"},
        {"case_id": "material-at-five-percent", "affected_count": 5, "analyzed_count": 100, "expected": "material"},
        {"case_id": "material-at-twenty-count", "affected_count": 20, "analyzed_count": 1000, "expected": "material"},
        {"case_id": "broad-at-twenty-percent", "affected_count": 20, "analyzed_count": 100, "expected": "broad"},
        {"case_id": "broad-at-one-hundred-count", "affected_count": 100, "analyzed_count": 1000, "expected": "broad"},
        {"case_id": "affected-over-analyzed-invalid", "affected_count": 11, "analyzed_count": 10, "expected": "ND"},
        {"case_id": "negative-affected-invalid", "affected_count": -1, "analyzed_count": 10, "expected": "ND"},
    ]


def build_confidence_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "direct-crawl-high", "factor_id": "T01", "metrics": {"coverage_rate": 1.0, "scope_type": "full", "join_quality": "exact", "artifact_age_days": 1}, "expected": "high"},
        {"case_id": "direct-crawl-representative-medium", "factor_id": "T01", "metrics": {"coverage_rate": 1.0, "scope_type": "representative_sample", "join_quality": "exact", "artifact_age_days": 1}, "expected": "medium"},
        {"case_id": "direct-crawl-stale-low", "factor_id": "T01", "metrics": {"coverage_rate": 1.0, "scope_type": "full", "join_quality": "exact", "artifact_age_days": 46}, "expected": "low"},
        {"case_id": "visibility-base-medium", "factor_id": "B02", "metrics": {"coverage_rate": 1.0, "material_record_count": 30, "artifact_age_days": 1, "scope_mismatch_count": 0}, "expected": "medium"},
        {"case_id": "visibility-sparse-low", "factor_id": "B02", "metrics": {"coverage_rate": 1.0, "material_record_count": 9, "artifact_age_days": 1, "scope_mismatch_count": 0}, "expected": "low"},
        {"case_id": "cross-source-high", "factor_id": "B17", "metrics": {"coverage_rate": 1.0, "exact_normalized_field_rate": 1.0, "join_quality": "exact", "claim_scope_match": True, "artifact_age_days": 1}, "expected": "high"},
        {"case_id": "cross-source-incomplete-medium", "factor_id": "B17", "metrics": {"coverage_rate": 0.89, "exact_normalized_field_rate": 1.0, "join_quality": "exact", "claim_scope_match": True, "artifact_age_days": 1}, "expected": "medium"},
        {"case_id": "cross-source-fuzzy-low", "factor_id": "B17", "metrics": {"coverage_rate": 1.0, "exact_normalized_field_rate": 1.0, "join_quality": "fuzzy", "claim_scope_match": True, "artifact_age_days": 1}, "expected": "low"},
        {"case_id": "rubric-base-medium", "factor_id": "B10", "metrics": {"coverage_rate": 1.0, "missing_rubric_evidence_count": 0, "join_quality": "exact"}, "expected": "medium"},
        {"case_id": "rubric-missing-evidence-low", "factor_id": "B10", "metrics": {"coverage_rate": 1.0, "missing_rubric_evidence_count": 1, "join_quality": "exact"}, "expected": "low"},
        {"case_id": "history-high", "factor_id": "B25", "metrics": {"valid_daily_point_count": 28, "missing_day_rate": 0.0, "scope_break_count": 0}, "expected": "high"},
        {"case_id": "history-short-medium", "factor_id": "B25", "metrics": {"valid_daily_point_count": 27, "missing_day_rate": 0.0, "scope_break_count": 0}, "expected": "medium"},
        {"case_id": "history-scope-break-low", "factor_id": "B25", "metrics": {"valid_daily_point_count": 28, "missing_day_rate": 0.0, "scope_break_count": 1}, "expected": "low"},
        {"case_id": "measurement-high", "factor_id": "M01", "metrics": {"partial_record_rate": 0.0, "coverage_rate": 1.0, "validation_error_count": 0}, "expected": "high"},
        {"case_id": "measurement-partial-medium", "factor_id": "M01", "metrics": {"partial_record_rate": 0.01, "coverage_rate": 1.0, "validation_error_count": 0}, "expected": "medium"},
        {"case_id": "measurement-error-low", "factor_id": "M01", "metrics": {"partial_record_rate": 0.0, "coverage_rate": 1.0, "validation_error_count": 1}, "expected": "low"},
        {"case_id": "missing-confidence-control-is-nd", "factor_id": "T01", "metrics": {"coverage_rate": 1.0}, "expected": "ND"},
    ]


def build_priority_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "green-null", "status": "green", "base": "P0", "expected": None},
        {"case_id": "red-material-p1", "status": "red", "base": "P1", "betroffenheit": "material", "confidence": "high", "factor_ceiling": "P1", "expected": "P1"},
        {"case_id": "red-broad-upgrade", "status": "red", "base": "P2", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P1", "expected": "P1"},
        {"case_id": "red-isolated-downgrade", "status": "red", "base": "P1", "betroffenheit": "isolated", "confidence": "high", "factor_ceiling": "P0", "expected": "P3"},
        {"case_id": "low-confidence-ceiling", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "low", "factor_ceiling": "P0", "expected": "P2"},
        {"case_id": "yellow-never-p0", "status": "yellow", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P0", "expected": "P1"},
        {"case_id": "critical-uplift-one-step", "status": "red", "base": "P2", "betroffenheit": "material", "criticality": "critical", "confirmed_mapping": True, "confidence": "high", "factor_ceiling": "P1", "expected": "P1"},
        {"case_id": "unconfirmed-criticality-no-uplift", "status": "red", "base": "P2", "betroffenheit": "material", "criticality": "critical", "confirmed_mapping": False, "confidence": "high", "factor_ceiling": "P0", "expected": "P2"},
        {"case_id": "high-criticality-isolated-no-uplift", "status": "red", "base": "P2", "betroffenheit": "isolated", "criticality": "high", "confirmed_mapping": True, "confidence": "high", "factor_ceiling": "P0", "expected": "P3"},
        {"case_id": "overall-veto-high-floor", "status": "red", "base": "P2", "betroffenheit": "material", "confidence": "high", "factor_ceiling": "P0", "veto_role": "overall", "confirmed_issue": True, "expected": "P0"},
        {"case_id": "block-veto-high-floor", "status": "red", "base": "P2", "betroffenheit": "material", "confidence": "high", "factor_ceiling": "P0", "veto_role": "block", "confirmed_issue": True, "expected": "P1"},
        {"case_id": "veto-low-confidence-no-floor", "status": "red", "base": "P2", "betroffenheit": "broad", "confidence": "low", "factor_ceiling": "P0", "veto_role": "overall", "confirmed_issue": True, "expected": "P2"},
        {"case_id": "g3-direct-ceiling", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P0", "evidence_grade": "G3_SOURCE_LIMITED", "dependency_role": "direct_observed_outcome", "expected": "P1"},
        {"case_id": "g3-supporting-ceiling", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P0", "evidence_grade": "G3_SOURCE_LIMITED", "dependency_role": "supporting_driver", "expected": "P2"},
        {"case_id": "g4-ceiling", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P0", "evidence_grade": "G4_SUPPORTED_INFERENCE", "expected": "P1"},
        {"case_id": "representative-scope-ceiling", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P0", "scope_type": "representative_sample", "expected": "P1"},
        {"case_id": "diagnostic-scope-ceiling", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P0", "scope_type": "diagnostic_sample", "expected": "P2"},
        {"case_id": "source-corpus-supporting-ceiling", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P0", "scope_type": "source_corpus", "dependency_role": "supporting_driver", "expected": "P2"},
        {"case_id": "factor-ceiling-wins", "status": "red", "base": "P0", "betroffenheit": "broad", "confidence": "high", "factor_ceiling": "P2", "expected": "P2"},
        {"case_id": "effort-does-not-upgrade", "status": "red", "base": "P2", "betroffenheit": "material", "confidence": "high", "factor_ceiling": "P0", "effort": "low", "expected": "P2"},
    ]


def build_rollup_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for block, spec in BLOCK_ROLLUP_SPECS.items():
        minimum = spec["minimum_coverage"]
        direct = spec["red_direct"]
        supporting = spec["red_supporting"]
        cases.extend([
            {"case_id": f"{block}-veto-red", "scope": "block", "block": block, "coverage_rate": 1.0, "high_confidence_red_veto_count": 1, "expected": "red"},
            {"case_id": f"{block}-veto-survives-low-coverage", "scope": "block", "block": block, "coverage_rate": minimum - 0.01, "high_confidence_red_veto_count": 1, "expected": "red"},
            {"case_id": f"{block}-direct-red-at-threshold", "scope": "block", "block": block, "coverage_rate": 1.0, "material_red_gate_or_outcome_count": direct, "red_count": direct, "expected": "red"},
            {"case_id": f"{block}-direct-below-threshold-yellow", "scope": "block", "block": block, "coverage_rate": 1.0, "material_red_gate_or_outcome_count": direct - 1, "red_count": direct - 1, "expected": "yellow"},
            {"case_id": f"{block}-supporting-red-at-threshold", "scope": "block", "block": block, "coverage_rate": 1.0, "material_red_supporting_count": supporting, "red_count": supporting, "expected": "red"},
            {"case_id": f"{block}-low-coverage-nd", "scope": "block", "block": block, "coverage_rate": minimum - 0.01, "expected": "ND"},
            {"case_id": f"{block}-green-at-coverage-boundary", "scope": "block", "block": block, "coverage_rate": minimum, "green_count": 1, "expected": "green"},
            {"case_id": f"{block}-one-nonmaterial-yellow-stays-green", "scope": "block", "block": block, "coverage_rate": 1.0, "yellow_count": 1, "material_yellow_count": 0, "expected": "green"},
            {"case_id": f"{block}-two-yellow-is-yellow", "scope": "block", "block": block, "coverage_rate": 1.0, "yellow_count": 2, "material_yellow_count": 0, "expected": "yellow"},
            {"case_id": f"{block}-one-material-yellow-is-yellow", "scope": "block", "block": block, "coverage_rate": 1.0, "yellow_count": 1, "material_yellow_count": 1, "expected": "yellow"},
        ])
    cases.extend([
        {"case_id": "overall-veto-red", "scope": "overall", "coverage_rate": 0.50, "high_confidence_overall_veto_red_count": 1, "expected": "red"},
        {"case_id": "overall-two-red-blocks-red", "scope": "overall", "coverage_rate": 1.0, "red_block_count": 2, "expected": "red"},
        {"case_id": "overall-one-red-block-yellow", "scope": "overall", "coverage_rate": 1.0, "red_block_count": 1, "expected": "yellow"},
        {"case_id": "overall-one-yellow-block-yellow", "scope": "overall", "coverage_rate": 1.0, "yellow_block_count": 1, "expected": "yellow"},
        {"case_id": "overall-all-green", "scope": "overall", "coverage_rate": 0.85, "red_block_count": 0, "yellow_block_count": 0, "green_block_count": 6, "expected": "green"},
        {"case_id": "overall-low-coverage-nd", "scope": "overall", "coverage_rate": 0.849999, "red_block_count": 0, "yellow_block_count": 0, "green_block_count": 6, "expected": "ND"},
    ])
    return cases


def build_boundary_fixtures(policy: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for rule in policy["rules"]:
        profile_name = FACTOR_SPECS[rule["factor_id"]]["profile"]
        for fixture_name, fixture_metrics, expected in PROFILE_DEFINITIONS[profile_name]["fixtures"]:
            cases.append({
                "case_id": f"{rule['factor_id']}-{fixture_name}",
                "factor_id": rule["factor_id"],
                "coverage_rate": 1.0,
                "applicable": True,
                "source_preflight_pass": True,
                "metrics": fixture_metrics,
                "expected_status": expected,
            })
    return {
        "policy_version": policy["policy_version"],
        "policy_fingerprint": policy["policy_fingerprint"]["digest"],
        "factor_boundary_cases": cases,
        "betroffenheit_cases": build_betroffenheit_cases(),
        "confidence_cases": build_confidence_cases(),
        "adversarial_cases": [
            {"case_id": "missing-source-blocks-run", "source_preflight_pass": False, "expected": "BLOCK_RUN"},
            {"case_id": "green-below-coverage-becomes-nd", "preliminary_status": "green", "coverage_rate": 0.69, "minimum_rate": 0.70, "confirmed_issue_override": True, "expected": "ND"},
            {"case_id": "yellow-below-coverage-becomes-nd", "preliminary_status": "yellow", "coverage_rate": 0.69, "minimum_rate": 0.70, "confirmed_issue_override": True, "expected": "ND"},
            {"case_id": "confirmed-red-survives-low-coverage", "preliminary_status": "red", "coverage_rate": 0.69, "minimum_rate": 0.70, "confirmed_issue_override": True, "expected": "red", "expected_confidence_cap": "low"},
            {"case_id": "unconfirmed-red-below-coverage-becomes-nd", "preliminary_status": "red", "coverage_rate": 0.69, "minimum_rate": 0.70, "confirmed_issue_override": False, "expected": "ND"},
            {"case_id": "zero-denominator-nd", "factor_id": "B18", "expected": "ND"},
            {"case_id": "zero-denominator-na", "factor_id": "C01", "expected": "NA"},
            {"case_id": "zero-denominator-green", "factor_id": "O06", "expected": "green"},
            {"case_id": "valid-empty-export-is-present", "access_ok": True, "schema_ok": True, "scope_ok": True, "extraction_ok": True, "snapshot_date_present": True, "row_count": 0, "expected": "SOURCE_READY"},
            {"case_id": "empty-export-without-schema-blocks", "access_ok": True, "schema_ok": False, "scope_ok": True, "extraction_ok": True, "snapshot_date_present": True, "row_count": 0, "expected": "BLOCK_RUN"},
            {"case_id": "unresolved-input-conflict-becomes-nd", "conflict_is_measured_outcome": False, "authoritative_precedence_resolved": False, "expected": "ND", "expected_confidence_cap": "low"},
            {"case_id": "measured-conflict-remains-scoreable", "conflict_is_measured_outcome": True, "authoritative_precedence_resolved": False, "expected": "SCORE_OBSERVED_CONFLICT"},
            {"case_id": "nested-clusters-distinct-sitewide", "parent_urls": ["/a/x", "/a/y"], "child_urls": ["/a/x"], "expected_sitewide_distinct": 2, "forbidden_sum": 3},
            {"case_id": "stale-prefix-mapping-not-reused", "mapping_kind": "semantic_label", "pattern_unchanged": False, "previously_confirmed": True, "expected_reuse": False},
            {"case_id": "unchanged-confirmed-semantic-mapping-reused", "mapping_kind": "semantic_label", "pattern_unchanged": True, "previously_confirmed": True, "expected_reuse": True},
            {"case_id": "structural-membership-never-reused", "mapping_kind": "structural_membership", "pattern_unchanged": True, "previously_confirmed": True, "expected_reuse": False},
            {"case_id": "same-source-repetition-no-confidence-uplift", "independent_source_count": 1, "repeated_observation_count": 100, "expected_confidence_uplift": 0},
        ],
        "priority_cases": build_priority_cases(),
        "rollup_cases": build_rollup_cases(),
    }


def write_outputs(policy: dict[str, Any]) -> None:
    POLICY_OUTPUT.write_text(yaml.safe_dump(policy, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    README_OUTPUT.write_text(render_policy_readme(policy), encoding="utf-8")
    fixtures = build_boundary_fixtures(policy)
    FIXTURES_OUTPUT.write_text(yaml.safe_dump(fixtures, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")


def main() -> int:
    policy = build_policy()
    write_outputs(policy)
    print(
        json.dumps(
            {
                "policy_version": policy["policy_version"],
                "policy_fingerprint": policy["policy_fingerprint"]["digest"],
                "rules": len(policy["rules"]),
                "boundary_cases": len(build_boundary_fixtures(policy)["factor_boundary_cases"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
