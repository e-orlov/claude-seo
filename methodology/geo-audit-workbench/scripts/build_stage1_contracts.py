#!/usr/bin/env python3
"""Migrate the frozen workbench policy into standalone GEO runtime contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH = REPO_ROOT / "methodology" / "geo-audit-workbench"
POLICY_SOURCE = WORKBENCH / "scoring-policy" / "scoring-matrix.yaml"
POLICY_SCHEMA_SOURCE = WORKBENCH / "scoring-policy" / "scoring-rule.schema.json"
POLICY_README_SOURCE = WORKBENCH / "scoring-policy" / "README.md"
FACTOR_MATRIX_SOURCE = WORKBENCH / "GEO_audit_sources_and_factor_matrix_FINAL.md"
CONTRACT_DIR = REPO_ROOT / ".claude" / "geo-audit" / "contracts"
REPORT_SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "seo-geo-report-generator"
FIXTURE_DIR = REPO_ROOT / ".claude" / "geo-audit" / "fixtures"
CATALOG_VERSION = "1.0.0"


SOURCE_ORDER = [
    "SF", "RAW", "REN", "PSI", "GSC-SA", "GSC-UI", "GSC-GAI",
    "AH-BL", "AH-RD", "AH-BB", "SX-M", "SX-O", "SX-C", "SX-P",
    "SX-PC", "SX-S", "SX-SENT", "DJ",
]


SOURCE_METADATA: dict[str, dict[str, Any]] = {
    "SF": {
        "label": "Screaming Frog crawl and native metrics",
        "transport": "screaming_frog_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one crawled resource or relation record",
        "scope_fields": ["domain", "crawl_timestamp", "crawl_configuration", "content_type"],
        "freshness_class": "crawl_14d",
        "preflight_probe": "harmless crawl overview plus one bounded HTML-row read",
        "limitations": ["crawl_state_not_external_bot_visit", "scope_depends_on_crawl_configuration"],
    },
    "RAW": {
        "label": "Original HTML from Screaming Frog",
        "transport": "screaming_frog_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one original response body per crawled HTML URL",
        "scope_fields": ["domain", "page_url", "crawl_timestamp", "user_agent"],
        "freshness_class": "crawl_14d",
        "preflight_probe": "bounded raw HTML read for a confirmed HTML URL",
        "limitations": ["depends_on_crawl_scope_and_user_agent"],
    },
    "REN": {
        "label": "Rendered HTML from Screaming Frog",
        "transport": "screaming_frog_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one rendered DOM per crawled HTML URL",
        "scope_fields": ["domain", "page_url", "crawl_timestamp", "renderer"],
        "freshness_class": "crawl_14d",
        "preflight_probe": "bounded rendered HTML read for the same URL used by RAW",
        "limitations": ["chromium_render_does_not_prove_rendering_by_each_ai_bot"],
    },
    "PSI": {
        "label": "PageSpeed Insights connector data",
        "transport": "screaming_frog_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one URL and Lighthouse strategy result",
        "scope_fields": ["page_url", "strategy", "test_timestamp"],
        "freshness_class": "crawl_14d",
        "preflight_probe": "bounded PSI-field read for mobile and desktop where configured",
        "limitations": ["lighthouse_lab_is_primary", "crux_optional", "tbt_is_not_field_inp"],
    },
    "GSC-SA": {
        "label": "Google Search Console Search Analytics connector data",
        "transport": "screaming_frog_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one returned Search Analytics dimension row",
        "scope_fields": ["property", "date_range", "search_type", "dimensions"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "bounded Search Analytics field read and date-range check",
        "limitations": ["only_returned_google_search_measurements"],
    },
    "GSC-UI": {
        "label": "Google Search Console URL Inspection connector data",
        "transport": "screaming_frog_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one inspected URL",
        "scope_fields": ["property", "page_url", "inspection_timestamp"],
        "freshness_class": "crawl_14d",
        "preflight_probe": "one bounded inspection-field read without starting a bulk run",
        "limitations": ["full_when_eligible_url_count_lte_2000", "deterministic_sample_max_2000_otherwise"],
    },
    "GSC-GAI": {
        "label": "Google Search Console Generative AI performance export",
        "transport": "uploaded_file",
        "artifact_kind": "tabular_export",
        "grain": "one exported date/page/country/device dimension row",
        "scope_fields": ["property", "date_range", "dimensions"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "file fingerprint, schema signature, scope and date-range validation",
        "limitations": ["file_snapshot_not_api_stream"],
    },
    "AH-BL": {
        "label": "Ahrefs Backlinks export",
        "transport": "uploaded_file",
        "artifact_kind": "tabular_export",
        "grain": "one exported backlink record",
        "scope_fields": ["target_domain", "export_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "header signature, target-domain, row-count and export-date validation",
        "limitations": ["bounded_to_exported_rows_and_fields"],
    },
    "AH-RD": {
        "label": "Ahrefs Referring Domains export",
        "transport": "uploaded_file",
        "artifact_kind": "tabular_export",
        "grain": "one exported referring-domain record",
        "scope_fields": ["target_domain", "export_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "header signature, target-domain, row-count and export-date validation",
        "limitations": ["does_not_measure_unlinked_brand_mentions"],
    },
    "AH-BB": {
        "label": "Ahrefs Broken Backlinks export",
        "transport": "uploaded_file",
        "artifact_kind": "tabular_export",
        "grain": "one exported broken-backlink record",
        "scope_fields": ["target_domain", "export_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "header signature, target-domain, row-count and export-date validation",
        "limitations": ["bounded_to_ahrefs_broken_backlink_export"],
    },
    "SX-M": {
        "label": "SISTRIX AI models",
        "transport": "sistrix_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one returned model record",
        "scope_fields": ["llm_model", "llm_label", "request_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "ai.models read",
        "limitations": ["model_availability_does_not_guarantee_brand_rows"],
    },
    "SX-O": {
        "label": "SISTRIX AI Check overview",
        "transport": "sistrix_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one brand/domain/model/country overview record",
        "scope_fields": ["brand", "domain", "country", "llm_model", "request_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "minimal ai.check.overview read for approved scope",
        "limitations": ["observed_prompt_count_not_universal_relevant_prompt_rate"],
    },
    "SX-C": {
        "label": "SISTRIX AI Check competitors",
        "transport": "sistrix_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one returned competitor record",
        "scope_fields": ["brand", "country", "llm_model", "request_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "bounded ai.check.competitors schema read",
        "limitations": ["competitor_list_not_complete_sov_denominator"],
    },
    "SX-P": {
        "label": "SISTRIX AI Check prompts",
        "transport": "sistrix_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one returned prompt and answer record",
        "scope_fields": ["brand", "domain", "country", "llm_model", "request_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "bounded ai.check.prompts schema read after cost plan",
        "limitations": ["corpus_contains_observed_mentions_or_citations", "no_complete_relevant_prompt_denominator", "no_proven_prompt_to_source_join"],
    },
    "SX-PC": {
        "label": "SISTRIX AI Check prompt counts",
        "transport": "sistrix_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one date/model/country prompt-count record",
        "scope_fields": ["brand", "domain", "country", "llm_model", "date"],
        "freshness_class": "historical_window",
        "preflight_probe": "bounded ai.check.prompts.count schema read",
        "limitations": ["daily_aggregate_not_prompt_answer_history"],
    },
    "SX-S": {
        "label": "SISTRIX AI Check sources",
        "transport": "sistrix_mcp",
        "artifact_kind": "mcp_extraction",
        "grain": "one returned cited host/domain/URL record",
        "scope_fields": ["brand", "domain", "country", "llm_model", "request_timestamp"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "bounded ai.check.sources schema read after cost plan",
        "limitations": ["no_documented_prompt_answer_source_key", "no_citation_correctness_or_absorption"],
    },
    "SX-SENT": {
        "label": "SISTRIX Sentiment GUI MHTML",
        "transport": "uploaded_file",
        "artifact_kind": "mhtml_snapshot",
        "grain": "one brand/platform/topic/snapshot observation",
        "scope_fields": ["brand", "snapshot_date", "displayed_platforms", "comparison_group"],
        "freshness_class": "visibility_30d",
        "preflight_probe": "MIME structure, main HTML, brand, date, platform and sentiment-field validation",
        "limitations": ["snapshot_only", "displayed_platforms_only", "remote_resources_must_not_load"],
    },
    "DJ": {
        "label": "Dejan AI Agent Access result",
        "transport": "uploaded_file",
        "artifact_kind": "tabular_or_html_export",
        "grain": "one agent and access-rule result",
        "scope_fields": ["domain", "test_timestamp", "agent"],
        "freshness_class": "crawl_14d",
        "preflight_probe": "domain, timestamp, agent inventory and result-schema validation",
        "limitations": ["configuration_test_not_observed_bot_crawl"],
    },
}


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping in {path}")
    return value


def fingerprint(value: dict[str, Any], field: str) -> str:
    normalized = copy.deepcopy(value)
    normalized[field] = ""
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_factor_matrix() -> dict[str, dict[str, Any]]:
    pattern = re.compile(
        r"^\| `(?P<id>(?:T|B|C|S|O|M)\d{2})` \| (?P<label>.*?) \| "
        r"(?P<definition>.*?) \| (?P<sources>.*?) \| (?P<coverage>.*?) \|$"
    )
    factors: dict[str, dict[str, Any]] = {}
    for line in FACTOR_MATRIX_SOURCE.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        factor_id = match.group("id")
        if factor_id in factors:
            raise ValueError(f"Duplicate factor {factor_id}")
        factors[factor_id] = {
            "factor_id": factor_id,
            "label": match.group("label"),
            "definition": match.group("definition"),
            "sources": re.findall(r"`([^`]+)`", match.group("sources")),
            "coverage_statement": match.group("coverage"),
        }
    if len(factors) != 129:
        raise ValueError(f"Expected 129 matrix factors, got {len(factors)}")
    return factors


def method_family(factor_id: str, rule: dict[str, Any]) -> str:
    special = {
        "T10": "gsc_url_inspection",
        "T16": "html_parity",
        "T17": "html_parity",
        "S18": "html_parity",
        "B18": "sentiment_wilson",
        "B19": "sentiment_group_wilson",
        "B20": "sentiment_wilson",
        "B21": "sentiment_group_wilson",
    }
    return special.get(factor_id, rule["rule_type"])


def build_source_catalog(policy: dict[str, Any]) -> dict[str, Any]:
    required_for = {
        source: [rule["factor_id"] for rule in policy["rules"] if source in rule["source_requirements"]]
        for source in SOURCE_ORDER
    }
    sources = []
    for source_code in SOURCE_ORDER:
        entry = {
            "source_code": source_code,
            **copy.deepcopy(SOURCE_METADATA[source_code]),
            "required": True,
            "required_for": required_for[source_code],
            "adapter_version": 1,
            "source_level_gate": ["access", "schema", "scope", "snapshot_or_range", "successful_extraction"],
            "valid_empty_policy": "zero rows are valid only after every source-level gate passes",
        }
        sources.append(entry)
    catalog = {
        "catalog_version": CATALOG_VERSION,
        "catalog_fingerprint": "",
        "source_count": 18,
        "all_sources_required": True,
        "source_order": SOURCE_ORDER,
        "sources": sources,
    }
    catalog["catalog_fingerprint"] = fingerprint(catalog, "catalog_fingerprint")
    return catalog


def build_factor_catalog(policy: dict[str, Any], matrix: dict[str, dict[str, Any]]) -> dict[str, Any]:
    factors = []
    for rule in policy["rules"]:
        factor_id = rule["factor_id"]
        source = matrix[factor_id]
        if source["label"] != rule["factor_name"] or source["sources"] != rule["source_requirements"]:
            raise ValueError(f"Canonical drift for {factor_id}")
        factors.append({
            "factor_id": factor_id,
            "block_id": factor_id[0],
            "ordinal": int(factor_id[1:]),
            "label": source["label"],
            "definition": source["definition"],
            "coverage_statement": source["coverage_statement"],
            "primary_sources": source["sources"],
            "analysis_method_id": f"geo_factor_{factor_id.lower()}_v1",
            "method_family": method_family(factor_id, rule),
            "measurement_universe": rule["measurement_universe"],
            "applicability_rule": rule["applicability_rule"],
            "canonical_metrics": rule["canonical_metrics"],
            "measurement_definition": rule["measurement_definition"],
            "coverage_gate": rule["coverage_gate"],
            "evidence_contract": {
                "source_artifact_sha256_required": True,
                "method_and_filter_fingerprint_required": True,
                "grain_required": True,
                "numerator_denominator_required": True,
                "minimum_representative_examples_for_red_or_yellow": 1,
                "examples_must_belong_to_affected_set": True,
            },
            "scoring_rule_ref": {
                "factor_id": factor_id,
                "policy_version": policy["policy_version"],
                "policy_fingerprint": policy["policy_fingerprint"]["digest"],
            },
            "dependency_role": rule["dependency_role"],
            "dependency_parents": rule["dependency_parents"],
            "root_cause_group": rule["root_cause_group"],
            "cluster_applicable": rule["criticality_modifiers"]["profile"] == "url_cluster",
            "limitations": [
                "bounded_to_declared_sources_and_measurement_universe",
                "betroffenheit_is_not_causal_or_business_impact",
            ],
        })
    distribution = {block: sum(item["block_id"] == block for item in factors) for block in "TBCSOM"}
    catalog = {
        "catalog_version": CATALOG_VERSION,
        "catalog_fingerprint": "",
        "factor_count": 129,
        "block_count": 6,
        "block_distribution": distribution,
        "scoring_policy_version": policy["policy_version"],
        "scoring_policy_fingerprint": policy["policy_fingerprint"]["digest"],
        "factors": factors,
    }
    catalog["catalog_fingerprint"] = fingerprint(catalog, "catalog_fingerprint")
    return catalog


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def package_hash(value: dict[str, Any]) -> str:
    normalized = copy.deepcopy(value)
    normalized["package_sha256"] = ""
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_contract_fixtures(
    policy: dict[str, Any],
    source_catalog: dict[str, Any],
    factor_catalog: dict[str, Any],
) -> None:
    complete_dir = FIXTURE_DIR / "minimal-complete"
    over_limit_dir = FIXTURE_DIR / "over-2000-urls"
    negative_dir = FIXTURE_DIR / "negative"
    for directory in (complete_dir, over_limit_dir, negative_dir):
        directory.mkdir(parents=True, exist_ok=True)

    config = {
        "schema_version": 1,
        "client_id": "contract-fixture",
        "brand": "Example",
        "domain": "example.com",
        "country": "de",
        "language": "de",
        "report_language": "de",
        "crawl": {"expected_scope": "example.com", "include_subdomains": False},
        "sistrix": {"connection_mode": "mcp", "models": "all_available", "country": "de", "direct_api_fallback": False, "max_credit_cost": None},
        "gsc_url_inspection": {"max_urls": 2000, "selection": "cluster_stratified"},
        "clustering": {
            "auto_invoke": True,
            "build_path_prefix_hierarchy": True,
            "recompute_memberships_each_run": True,
            "require_url_type_confirmation": True,
            "confirmation_scope": "semantic_labels_and_criticality_only",
            "require_zero_unresolved": True,
        },
        "inputs": {
            "ahrefs_backlinks": "inputs/ahrefs-backlinks.csv",
            "ahrefs_refdomains": "inputs/ahrefs-refdomains.csv",
            "ahrefs_broken_backlinks": "inputs/ahrefs-broken-backlinks.csv",
            "dejan": "inputs/dejan.csv",
            "sistrix_sentiment_mhtml": ["inputs/sistrix-sentiment.mhtml"],
            "gsc_generative_ai_export": "inputs/gsc-gai.csv",
        },
        "report": {"output_docx": True, "output_pdf": True},
    }
    write_json(complete_dir / "audit-config.json", config)

    run_id = "geo-contract-fixture-2026-09-15-r1"
    source_manifest = []
    for source_code in SOURCE_ORDER:
        artifact_sha = hashlib.sha256(f"fixture:{source_code}".encode()).hexdigest()
        source_manifest.append({
            "source_code": source_code,
            "source_level_status": "ready",
            "artifact_id": f"fixture-{source_code.lower()}",
            "artifact_sha256": artifact_sha,
            "scope_status": "match",
            "freshness_status": "current",
            "record_count": 1,
            "valid_empty": False,
            "limitations": ["synthetic_contract_fixture"],
        })
    factor_results = [{
        "factor_id": factor["factor_id"],
        "applicability": "not_applicable",
        "measurement_status": "not_applicable",
        "scope_type": "full",
        "coverage_rate": 1.0,
        "metrics": {},
        "confidence": "ND",
        "evidence_ids": [],
        "recommendation_ids": [],
        "limitations": ["synthetic_contract_fixture"],
    } for factor in factor_catalog["factors"]]
    analysis = {
        "package_type": "geo_analysis_package",
        "schema_version": 1,
        "run_id": run_id,
        "run_state": "ANALYSIS_COMPLETE",
        "created_at": "2026-09-15T00:00:00Z",
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "contract": {
            "source_catalog_version": source_catalog["catalog_version"],
            "source_catalog_fingerprint": source_catalog["catalog_fingerprint"],
            "factor_catalog_version": factor_catalog["catalog_version"],
            "factor_catalog_fingerprint": factor_catalog["catalog_fingerprint"],
        },
        "policy": {"version": policy["policy_version"], "fingerprint": policy["policy_fingerprint"]["digest"]},
        "source_manifest": source_manifest,
        "clustering": {
            "cluster_run_id": "cluster-contract-fixture-r1",
            "crawl_universe_sha256": hashlib.sha256(b"fixture-crawl-universe").hexdigest(),
            "html_url_count": 1,
            "vertical_row_count": 1,
            "horizontal_row_count": 1,
            "prefix_membership_count": 1,
            "unresolved_count": 0,
            "memberships_recomputed": True,
        },
        "factor_results": factor_results,
        "evidence": [],
        "findings": [],
        "recommendations": [],
        "limitations": ["Synthetic package validates structure only; it is not an audit result."],
        "completion_gate": {"passed": True, "check_count": 1, "failed_checks": []},
        "package_sha256": "",
    }
    analysis["package_sha256"] = package_hash(analysis)
    write_json(complete_dir / "analysis-package.json", analysis)

    rules = {rule["factor_id"]: rule for rule in policy["rules"]}
    scored_factors = [{
        "factor_id": factor["factor_id"],
        "status": "NA",
        "priority": None,
        "confidence": "ND",
        "betroffenheit": "NA",
        "coverage_rate": 1.0,
        "rule_fingerprint": hashlib.sha256(json.dumps(rules[factor["factor_id"]], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "evidence_ids": [],
        "recommendation_ids": [],
    } for factor in factor_catalog["factors"]]
    full_report = [{
        "block_id": factor["block_id"],
        "factor_id": factor["factor_id"],
        "status": "NA",
        "priority": None,
        "confidence": "ND",
        "formulation": factor["label"],
        "why_important": rules[factor["factor_id"]]["rationale"],
        "rating_explanation": "Synthetic contract fixture: factor is marked not applicable.",
        "recommendation": None,
        "evidence_ids": [],
    } for factor in factor_catalog["factors"]]
    report = {
        "package_type": "geo_report_package",
        "schema_version": 1,
        "run_id": run_id,
        "analysis_package_sha256": analysis["package_sha256"],
        "policy": {"version": policy["policy_version"], "fingerprint": policy["policy_fingerprint"]["digest"]},
        "scored_factors": scored_factors,
        "block_statuses": [{"block_id": block, "status": "ND", "coverage_rate": 1.0, "rule_trace": "synthetic_contract_fixture"} for block in "TBCSOM"],
        "overall_status": "ND",
        "summary": [],
        "full_report": full_report,
        "outputs": {"docx": "output/geo-report.docx", "pdf": "output/geo-report.pdf"},
        "validation": {"content_passed": True, "visual_passed": True, "failed_checks": []},
        "package_sha256": "",
    }
    report["package_sha256"] = package_hash(report)
    write_json(complete_dir / "report-package.json", report)

    write_yaml(over_limit_dir / "gsc-selection-case.yaml", {
        "case_id": "eligible-url-count-over-2000",
        "eligible_url_count": 2001,
        "maximum_inspection_count": 2000,
        "selection": "cluster_stratified",
        "required_inclusion_reason": True,
        "sitewide_prevalence_without_weighting": False,
    })
    write_yaml(negative_dir / "contract-mutations.yaml", {
        "mutations": [
            {"case_id": "missing-source", "target": "source_catalog", "operation": "remove", "selector": "DJ"},
            {"case_id": "duplicate-source", "target": "source_catalog", "operation": "duplicate", "selector": "SF"},
            {"case_id": "unknown-source", "target": "source_catalog", "operation": "replace_id", "selector": "SF", "value": "UNKNOWN"},
            {"case_id": "missing-factor", "target": "factor_catalog", "operation": "remove", "selector": "M17"},
            {"case_id": "duplicate-factor", "target": "factor_catalog", "operation": "duplicate", "selector": "T01"},
            {"case_id": "unknown-factor", "target": "factor_catalog", "operation": "replace_id", "selector": "T01", "value": "T99"},
            {"case_id": "factor-source-drift", "target": "factor_catalog", "operation": "append_source", "selector": "T01", "value": "SX-P"},
            {"case_id": "policy-fingerprint-drift", "target": "factor_catalog", "operation": "replace_policy_fingerprint", "value": "0" * 64},
            {"case_id": "analysis-source-count-17", "target": "analysis_package", "operation": "remove", "selector": "DJ"},
            {"case_id": "analysis-factor-count-128", "target": "analysis_package", "operation": "remove", "selector": "M17"},
            {"case_id": "report-summary-non-red", "target": "report_package", "operation": "add_yellow_summary", "selector": "T01"},
        ]
    })


def main() -> int:
    policy = load_yaml(POLICY_SOURCE)
    matrix = parse_factor_matrix()
    CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_SKILL_DIR.mkdir(parents=True, exist_ok=True)
    source_catalog = build_source_catalog(policy)
    factor_catalog = build_factor_catalog(policy, matrix)
    write_yaml(CONTRACT_DIR / "source-catalog.yaml", source_catalog)
    write_yaml(CONTRACT_DIR / "factor-catalog.yaml", factor_catalog)
    (CONTRACT_DIR / "scoring-matrix.yaml").write_bytes(POLICY_SOURCE.read_bytes())
    (CONTRACT_DIR / "scoring-rule.schema.json").write_bytes(POLICY_SCHEMA_SOURCE.read_bytes())
    (REPORT_SKILL_DIR / "README.md").write_bytes(POLICY_README_SOURCE.read_bytes())
    build_contract_fixtures(policy, source_catalog, factor_catalog)
    print(json.dumps({
        "status": "PASS",
        "sources": len(source_catalog["sources"]),
        "factors": len(factor_catalog["factors"]),
        "source_catalog_fingerprint": source_catalog["catalog_fingerprint"],
        "factor_catalog_fingerprint": factor_catalog["catalog_fingerprint"],
        "scoring_policy_fingerprint": policy["policy_fingerprint"]["digest"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
