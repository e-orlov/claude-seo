#!/usr/bin/env python3
"""Dependency-light validator for all GEO Stage 1 contracts and fixtures."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
GEO_DIR = REPO_ROOT / ".claude" / "geo-audit"
CONTRACT_DIR = GEO_DIR / "contracts"
FIXTURE_DIR = GEO_DIR / "fixtures"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

SOURCE_ORDER = [
    "SF", "RAW", "REN", "PSI", "GSC-SA", "GSC-UI", "GSC-GAI",
    "AH-BL", "AH-RD", "AH-BB", "SX-M", "SX-O", "SX-C", "SX-P",
    "SX-PC", "SX-S", "SX-SENT", "DJ",
]
BLOCK_DISTRIBUTION = {"T": 24, "B": 26, "C": 27, "S": 20, "O": 15, "M": 17}
POLICY_VERSION = "1.0.0"
POLICY_FINGERPRINT = "77da1451409845f6ba53d97f90071c92a4b26cc248f8d6b2bbc5634aaebe89ed"
EXPECTED_TABLES = {
    "geo_schema_version", "geo_audit_runs", "geo_analysis_events", "geo_source_manifest",
    "geo_source_checks", "geo_schema_registry", "geo_join_quality", "geo_sf_urls",
    "geo_html_raw", "geo_html_rendered", "geo_html_parity", "geo_psi_lab",
    "geo_gsc_search_analytics", "geo_gsc_url_inspection", "geo_gsc_gai",
    "geo_ahrefs_backlinks", "geo_ahrefs_refdomains", "geo_ahrefs_broken",
    "geo_sistrix_models", "geo_sistrix_overview", "geo_sistrix_competitors",
    "geo_sistrix_prompts", "geo_sistrix_prompt_counts", "geo_sistrix_sources",
    "geo_sistrix_sentiment", "geo_dejan_agents", "geo_cluster_runs",
    "geo_url_clusters_vertical", "geo_url_clusters_horizontal", "geo_url_prefix_clusters",
    "geo_url_cluster_memberships", "geo_cluster_semantic_map", "geo_cluster_label_mappings",
    "geo_factor_results", "geo_factor_metrics", "geo_factor_cluster_metrics",
    "geo_evidence_drafts", "geo_evidence", "geo_findings",
    "geo_recommendation_candidates", "geo_analysis_limitations",
}
SCHEMA_KEYWORDS = {
    "$schema", "$id", "$ref", "$defs", "title", "type", "additionalProperties",
    "required", "properties", "const", "enum", "pattern", "format", "minLength",
    "minProperties", "maxProperties", "items", "minItems", "maxItems", "uniqueItems",
    "minimum", "maximum", "exclusiveMinimum", "oneOf",
}


class ContractFailure(AssertionError):
    """A fail-closed contract violation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractFailure(message)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: expected a mapping")
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: expected an object")
    return value


def json_equal(left: Any, right: Any) -> bool:
    return type(left) is type(right) and left == right


def canonical_hash(value: dict[str, Any], blank_field: str) -> str:
    normalized = copy.deepcopy(value)
    normalized[blank_field] = ""
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def policy_hash(policy: dict[str, Any]) -> str:
    normalized = copy.deepcopy(policy)
    normalized["policy_fingerprint"]["digest"] = ""
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    require(reference.startswith("#/"), f"Only local schema references are permitted: {reference}")
    node: Any = root
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        require(isinstance(node, dict) and part in node, f"Unresolved schema reference: {reference}")
        node = node[part]
    require(isinstance(node, dict), f"Schema reference does not resolve to an object: {reference}")
    return node


def validate_schema_definition(schema: dict[str, Any], root: dict[str, Any], path: str = "$schema") -> None:
    unknown = set(schema) - SCHEMA_KEYWORDS
    require(not unknown, f"Unsupported schema keywords at {path}: {sorted(unknown)}")
    if "$ref" in schema:
        resolve_ref(root, schema["$ref"])
    for key in ("properties", "$defs"):
        for name, child in schema.get(key, {}).items():
            require(isinstance(child, dict), f"Malformed schema at {path}.{key}.{name}")
            validate_schema_definition(child, root, f"{path}.{key}.{name}")
    if isinstance(schema.get("additionalProperties"), dict):
        validate_schema_definition(schema["additionalProperties"], root, f"{path}.additionalProperties")
    if isinstance(schema.get("items"), dict):
        validate_schema_definition(schema["items"], root, f"{path}.items")
    for index, child in enumerate(schema.get("oneOf", [])):
        require(isinstance(child, dict), f"Malformed oneOf at {path}[{index}]")
        validate_schema_definition(child, root, f"{path}.oneOf[{index}]")


def type_matches(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    require(expected in checks, f"Unsupported schema type: {expected}")
    return checks[expected](value)


def validate_instance(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str = "$") -> None:
    if "$ref" in schema:
        require(set(schema) == {"$ref"}, f"Sibling keywords next to $ref are unsupported at {path}")
        validate_instance(value, resolve_ref(root, schema["$ref"]), root, path)
        return
    if "oneOf" in schema:
        matches = 0
        for candidate in schema["oneOf"]:
            try:
                validate_instance(value, candidate, root, path)
            except ContractFailure:
                continue
            matches += 1
        require(matches == 1, f"Expected exactly one oneOf match at {path}; found {matches}")
        return
    if "type" in schema:
        expected = schema["type"]
        candidates = expected if isinstance(expected, list) else [expected]
        require(any(type_matches(value, item) for item in candidates), f"Type mismatch at {path}: expected {expected}")
    if "const" in schema:
        require(json_equal(value, schema["const"]), f"Const mismatch at {path}")
    if "enum" in schema:
        require(any(json_equal(value, choice) for choice in schema["enum"]), f"Enum mismatch at {path}: {value!r}")
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        require(required <= set(value), f"Missing keys at {path}: {sorted(required - set(value))}")
        if "minProperties" in schema:
            require(len(value) >= schema["minProperties"], f"Too few properties at {path}")
        if "maxProperties" in schema:
            require(len(value) <= schema["maxProperties"], f"Too many properties at {path}")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                validate_instance(child, properties[key], root, f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise ContractFailure(f"Unexpected property at {path}.{key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate_instance(child, schema["additionalProperties"], root, f"{path}.{key}")
    if isinstance(value, list):
        if "minItems" in schema:
            require(len(value) >= schema["minItems"], f"Too few items at {path}")
        if "maxItems" in schema:
            require(len(value) <= schema["maxItems"], f"Too many items at {path}")
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in value]
            require(len(normalized) == len(set(normalized)), f"Duplicate item at {path}")
        if "items" in schema:
            for index, child in enumerate(value):
                validate_instance(child, schema["items"], root, f"{path}[{index}]")
    if isinstance(value, str):
        if "minLength" in schema:
            require(len(value) >= schema["minLength"], f"String too short at {path}")
        if "pattern" in schema:
            require(re.search(schema["pattern"], value) is not None, f"Pattern mismatch at {path}: {value!r}")
        if schema.get("format") == "date":
            try:
                require(dt.date.fromisoformat(value).isoformat() == value, f"Non-canonical date at {path}")
            except ValueError as exc:
                raise ContractFailure(f"Invalid date at {path}: {value!r}") from exc
        if schema.get("format") == "date-time":
            try:
                dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ContractFailure(f"Invalid date-time at {path}: {value!r}") from exc
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            require(value >= schema["minimum"], f"Value below minimum at {path}")
        if "maximum" in schema:
            require(value <= schema["maximum"], f"Value above maximum at {path}")
        if "exclusiveMinimum" in schema:
            require(value > schema["exclusiveMinimum"], f"Value not above exclusive minimum at {path}")


def validate_with_schema(value: dict[str, Any], schema_name: str) -> None:
    schema = load_json(CONTRACT_DIR / schema_name)
    validate_schema_definition(schema, schema)
    validate_instance(value, schema, schema)


def factor_ids(items: list[dict[str, Any]]) -> list[str]:
    return [item["factor_id"] for item in items]


def validate_dependencies(factors: list[dict[str, Any]]) -> None:
    graph = {factor["factor_id"]: factor["dependency_parents"] for factor in factors}
    known = set(graph)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        require(node not in visiting, f"Factor dependency cycle at {node}")
        if node in visited:
            return
        visiting.add(node)
        for parent in graph[node]:
            require(parent in known, f"{node}: unknown dependency parent {parent}")
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for factor_id in graph:
        visit(factor_id)


def validate_catalog_alignment(
    sources: dict[str, Any], factors: dict[str, Any], policy: dict[str, Any]
) -> None:
    require(canonical_hash(sources, "catalog_fingerprint") == sources["catalog_fingerprint"], "Source catalog fingerprint mismatch")
    require(canonical_hash(factors, "catalog_fingerprint") == factors["catalog_fingerprint"], "Factor catalog fingerprint mismatch")
    require(policy_hash(policy) == POLICY_FINGERPRINT == policy["policy_fingerprint"]["digest"], "Scoring policy fingerprint mismatch")
    require(policy["policy_version"] == POLICY_VERSION, "Scoring policy version mismatch")

    source_codes = [item["source_code"] for item in sources["sources"]]
    require(sources["source_order"] == SOURCE_ORDER, "Source order mismatch")
    require(source_codes == SOURCE_ORDER, "Source inventory/order mismatch")
    require(len(source_codes) == len(set(source_codes)) == 18, "Source IDs are not exactly 18 unique codes")
    require(all(item["required"] is True for item in sources["sources"]), "Every source must be required")

    factor_list = factors["factors"]
    ids = factor_ids(factor_list)
    policy_rules = {rule["factor_id"]: rule for rule in policy["rules"]}
    require(len(ids) == len(set(ids)) == 129, "Factor IDs are not exactly 129 unique codes")
    require(set(ids) == set(policy_rules), "Factor catalog and scoring policy ID sets differ")
    distribution = {block: sum(item["block_id"] == block for item in factor_list) for block in BLOCK_DISTRIBUTION}
    require(distribution == BLOCK_DISTRIBUTION == factors["block_distribution"], "Block distribution mismatch")

    for factor in factor_list:
        factor_id = factor["factor_id"]
        rule = policy_rules[factor_id]
        require(factor["block_id"] == factor_id[0], f"{factor_id}: block mismatch")
        require(factor["ordinal"] == int(factor_id[1:]), f"{factor_id}: ordinal mismatch")
        require(factor["label"] == rule["factor_name"], f"{factor_id}: label mismatch")
        require(factor["primary_sources"] == rule["source_requirements"], f"{factor_id}: source mismatch")
        require(factor["applicability_rule"] == rule["applicability_rule"], f"{factor_id}: applicability mismatch")
        require(factor["canonical_metrics"] == rule["canonical_metrics"], f"{factor_id}: metric mismatch")
        require(factor["measurement_definition"] == rule["measurement_definition"], f"{factor_id}: measurement mismatch")
        require(factor["coverage_gate"] == rule["coverage_gate"], f"{factor_id}: coverage mismatch")
        require(factor["scoring_rule_ref"] == {"factor_id": factor_id, "policy_version": POLICY_VERSION, "policy_fingerprint": POLICY_FINGERPRINT}, f"{factor_id}: scoring reference mismatch")
        require(factor["analysis_method_id"] == f"geo_factor_{factor_id.lower()}_v1", f"{factor_id}: method ID mismatch")
    validate_dependencies(factor_list)

    required_for_expected = {
        code: [factor["factor_id"] for factor in factor_list if code in factor["primary_sources"]]
        for code in SOURCE_ORDER
    }
    for source in sources["sources"]:
        require(source["required_for"] == required_for_expected[source["source_code"]], f"{source['source_code']}: required_for drift")
        require(source["required_for"], f"{source['source_code']}: unused canonical source")


def validate_skill_entrypoints(policy: dict[str, Any]) -> None:
    expected = {"seo-geo-audit", "seo-geo-report-generator"}
    for skill_name in expected:
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        require(skill_file.is_file(), f"Missing {skill_file}")
        text = skill_file.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        require(match is not None, f"{skill_name}: invalid frontmatter")
        frontmatter = yaml.safe_load(match.group(1))
        require(frontmatter["name"] == skill_name, f"{skill_name}: frontmatter name mismatch")
        require(frontmatter.get("user-invocable") is True, f"{skill_name}: must be user-invocable")
        require(frontmatter.get("disable-model-invocation") is True, f"{skill_name}: model invocation must be disabled")
    report_readme = (SKILLS_DIR / "seo-geo-report-generator" / "README.md").read_text(encoding="utf-8")
    require(f"Policy version: `{POLICY_VERSION}`" in report_readme, "Report README policy version mismatch")
    require(f"Policy fingerprint: `sha256:{POLICY_FINGERPRINT}`" in report_readme, "Report README policy fingerprint mismatch")
    readme_ids = set(re.findall(r"^\| `((?:T|B|C|S|O|M)\d{2})` \|", report_readme, re.MULTILINE))
    require(readme_ids == {rule["factor_id"] for rule in policy["rules"]}, "Report README factor IDs differ from policy")
    root_rules = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    require("dedicated GEO workflow additionally permits SISTRIX MCP" in root_rules, "Root operating policy lacks narrow SISTRIX exception")
    require("do not use `seo-data-foundation`" in root_rules, "Root operating policy lacks standalone GEO dependency boundary")


def validate_report_contract() -> None:
    contract = load_yaml(CONTRACT_DIR / "report-contract.yaml")
    require(contract["input"]["require_source_count"] == 18, "Report contract source count mismatch")
    require(contract["input"]["require_factor_count"] == 129, "Report contract factor count mismatch")
    require(contract["input"]["read_primary_sources"] is False, "Report skill may not read primary sources")
    require(contract["scoring"]["runtime_discretion"] == "forbidden", "Report scoring must be deterministic")
    require(contract["summary"]["inclusion_rule"] == "factor_status_equals_red", "Summary must be red-only")
    require(contract["full_report"]["inclusion_rule"] == "all_129_factors_exactly_once", "Full report contract mismatch")
    require(contract["input"]["require_policy"] == {"version": POLICY_VERSION, "fingerprint": POLICY_FINGERPRINT}, "Report policy mismatch")


def validate_ddl() -> None:
    ddl = (CONTRACT_DIR / "duckdb-schema.sql").read_text(encoding="utf-8")
    discovered = set(re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-z0-9_]+)", ddl, re.IGNORECASE))
    require(discovered == EXPECTED_TABLES, f"DDL table mismatch: missing={sorted(EXPECTED_TABLES-discovered)}, extra={sorted(discovered-EXPECTED_TABLES)}")
    database = sqlite3.connect(":memory:")
    try:
        database.executescript(ddl)
    except sqlite3.Error as exc:
        raise ContractFailure(f"Portable DDL syntax check failed: {exc}") from exc
    finally:
        database.close()


def validate_analysis_invariants(package: dict[str, Any], source_ids: set[str], expected_factor_ids: set[str]) -> None:
    require(canonical_hash(package, "package_sha256") == package["package_sha256"], "Analysis package hash mismatch")
    manifest_ids = [item["source_code"] for item in package["source_manifest"]]
    require(len(manifest_ids) == len(set(manifest_ids)) == 18 and set(manifest_ids) == source_ids, "Analysis source inventory mismatch")
    ids = factor_ids(package["factor_results"])
    require(len(ids) == len(set(ids)) == 129 and set(ids) == expected_factor_ids, "Analysis factor inventory mismatch")
    evidence_ids = [item["evidence_id"] for item in package["evidence"]]
    require(len(evidence_ids) == len(set(evidence_ids)), "Duplicate analysis evidence ID")
    known_evidence = set(evidence_ids)
    for finding in package["findings"]:
        require(set(finding["evidence_ids"]) <= known_evidence, f"{finding['finding_id']}: unresolved evidence")
    for recommendation in package["recommendations"]:
        require(set(recommendation["evidence_ids"]) <= known_evidence, f"{recommendation['recommendation_id']}: unresolved evidence")
    for evidence in package["evidence"]:
        numerator, denominator = evidence["numerator"], evidence["denominator"]
        require(numerator is None or denominator is None or numerator <= denominator, f"{evidence['evidence_id']}: numerator exceeds denominator")


def validate_report_invariants(package: dict[str, Any], expected_factor_ids: set[str]) -> None:
    require(canonical_hash(package, "package_sha256") == package["package_sha256"], "Report package hash mismatch")
    scored_ids = factor_ids(package["scored_factors"])
    full_ids = factor_ids(package["full_report"])
    require(len(scored_ids) == len(set(scored_ids)) == 129 and set(scored_ids) == expected_factor_ids, "Scored factor inventory mismatch")
    require(len(full_ids) == len(set(full_ids)) == 129 and set(full_ids) == expected_factor_ids, "Full report factor inventory mismatch")
    require(all(item["status"] == "red" for item in package["summary"]), "Summary contains a non-red factor")
    block_ids = [item["block_id"] for item in package["block_statuses"]]
    require(len(block_ids) == len(set(block_ids)) == 6 and set(block_ids) == set(BLOCK_DISTRIBUTION), "Report block inventory mismatch")


def apply_mutation(
    case: dict[str, Any], sources: dict[str, Any], factors: dict[str, Any], analysis: dict[str, Any], report: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    target_name = case["target"]
    target = {"source_catalog": sources, "factor_catalog": factors, "analysis_package": analysis, "report_package": report}[target_name]
    operation = case["operation"]
    selector = case.get("selector")
    if target_name == "source_catalog":
        items = target["sources"]
        index = next((i for i, item in enumerate(items) if item["source_code"] == selector), None)
        require(index is not None, f"Mutation selector missing: {selector}")
        if operation == "remove":
            items.pop(index)
        elif operation == "duplicate":
            items.append(copy.deepcopy(items[index]))
        elif operation == "replace_id":
            items[index]["source_code"] = case["value"]
    elif target_name == "factor_catalog":
        items = target["factors"]
        if operation == "replace_policy_fingerprint":
            target["scoring_policy_fingerprint"] = case["value"]
        else:
            index = next((i for i, item in enumerate(items) if item["factor_id"] == selector), None)
            require(index is not None, f"Mutation selector missing: {selector}")
            if operation == "remove":
                items.pop(index)
            elif operation == "duplicate":
                items.append(copy.deepcopy(items[index]))
            elif operation == "replace_id":
                items[index]["factor_id"] = case["value"]
            elif operation == "append_source":
                items[index]["primary_sources"].append(case["value"])
    elif target_name == "analysis_package":
        key = "source_manifest" if selector in SOURCE_ORDER else "factor_results"
        id_key = "source_code" if key == "source_manifest" else "factor_id"
        target[key] = [item for item in target[key] if item[id_key] != selector]
    elif target_name == "report_package" and operation == "add_yellow_summary":
        target["summary"].append({
            "block_id": selector[0], "factor_id": selector, "status": "yellow", "priority": "P2",
            "formulation": "synthetic", "why_important": "synthetic", "why_red": "synthetic",
            "recommendation": "synthetic", "evidence_ids": ["E-0001"],
        })
    else:
        raise ContractFailure(f"Unsupported mutation {case['case_id']}")
    return target_name, target


def validate_negative_fixtures(
    source_catalog: dict[str, Any], factor_catalog: dict[str, Any], policy: dict[str, Any],
    analysis: dict[str, Any], report: dict[str, Any]
) -> int:
    fixture = load_yaml(FIXTURE_DIR / "negative" / "contract-mutations.yaml")
    rejected = 0
    for case in fixture["mutations"]:
        sources = copy.deepcopy(source_catalog)
        factors = copy.deepcopy(factor_catalog)
        analysis_copy = copy.deepcopy(analysis)
        report_copy = copy.deepcopy(report)
        target_name, target = apply_mutation(case, sources, factors, analysis_copy, report_copy)
        if target_name == "source_catalog":
            target["catalog_fingerprint"] = canonical_hash(target, "catalog_fingerprint")
        elif target_name == "factor_catalog":
            target["catalog_fingerprint"] = canonical_hash(target, "catalog_fingerprint")
        elif target_name in {"analysis_package", "report_package"}:
            target["package_sha256"] = canonical_hash(target, "package_sha256")
        try:
            if target_name == "source_catalog":
                validate_with_schema(target, "source-catalog.schema.json")
                validate_catalog_alignment(sources, factors, policy)
            elif target_name == "factor_catalog":
                validate_with_schema(target, "factor-catalog.schema.json")
                validate_catalog_alignment(sources, factors, policy)
            elif target_name == "analysis_package":
                validate_with_schema(target, "analysis-package.schema.json")
                validate_analysis_invariants(target, set(SOURCE_ORDER), set(factor_ids(factor_catalog["factors"])))
            else:
                validate_with_schema(target, "report-package.schema.json")
                validate_report_invariants(target, set(factor_ids(factor_catalog["factors"])))
        except ContractFailure:
            rejected += 1
            continue
        raise ContractFailure(f"Negative fixture was accepted: {case['case_id']}")
    return rejected


def main() -> int:
    try:
        source_catalog = load_yaml(CONTRACT_DIR / "source-catalog.yaml")
        factor_catalog = load_yaml(CONTRACT_DIR / "factor-catalog.yaml")
        policy = load_yaml(CONTRACT_DIR / "scoring-matrix.yaml")
        analysis = load_json(FIXTURE_DIR / "minimal-complete" / "analysis-package.json")
        config = load_json(FIXTURE_DIR / "minimal-complete" / "audit-config.json")
        report = load_json(FIXTURE_DIR / "minimal-complete" / "report-package.json")

        validate_with_schema(source_catalog, "source-catalog.schema.json")
        validate_with_schema(factor_catalog, "factor-catalog.schema.json")
        validate_with_schema(policy, "scoring-rule.schema.json")
        validate_with_schema(config, "audit-config.schema.json")
        validate_with_schema(analysis, "analysis-package.schema.json")
        validate_with_schema(report, "report-package.schema.json")
        validate_catalog_alignment(source_catalog, factor_catalog, policy)
        validate_skill_entrypoints(policy)
        validate_report_contract()
        validate_ddl()
        expected_factor_ids = set(factor_ids(factor_catalog["factors"]))
        validate_analysis_invariants(analysis, set(SOURCE_ORDER), expected_factor_ids)
        validate_report_invariants(report, expected_factor_ids)
        negative_rejections = validate_negative_fixtures(source_catalog, factor_catalog, policy, analysis, report)
    except (ContractFailure, KeyError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "PASS",
        "contract_version": source_catalog["catalog_version"],
        "sources": len(source_catalog["sources"]),
        "factors": len(factor_catalog["factors"]),
        "blocks": factor_catalog["block_distribution"],
        "policy_fingerprint": policy["policy_fingerprint"]["digest"],
        "ddl_tables": len(EXPECTED_TABLES),
        "negative_fixtures_rejected": negative_rejections,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
