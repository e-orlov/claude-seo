#!/usr/bin/env python3
"""Validate the frozen GEO scoring policy and every committed fixture."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


POLICY_DIR = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = POLICY_DIR.parent
POLICY_PATH = POLICY_DIR / "scoring-matrix.yaml"
SCHEMA_PATH = POLICY_DIR / "scoring-rule.schema.json"
README_PATH = POLICY_DIR / "README.md"
FIXTURES_PATH = POLICY_DIR / "fixtures" / "boundary-cases.yaml"
FACTOR_MATRIX_PATH = WORKBENCH_DIR / "GEO_audit_sources_and_factor_matrix_FINAL.md"

EXPECTED_SOURCES = {
    "SF", "RAW", "REN", "PSI", "GSC-SA", "GSC-UI", "GSC-GAI",
    "AH-BL", "AH-RD", "AH-BB", "SX-M", "SX-O", "SX-C", "SX-P",
    "SX-PC", "SX-S", "SX-SENT", "DJ",
}
PRIORITY_ORDER = ["P0", "P1", "P2", "P3"]
CONFIDENCE_ORDER = ["high", "medium", "low"]


class ValidationFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain a mapping")
    return value


def canonical_fingerprint(policy: dict[str, Any]) -> str:
    normalized = copy.deepcopy(policy)
    normalized["policy_fingerprint"]["digest"] = ""
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without treating booleans as integers."""
    return type(left) is type(right) and left == right


def resolve_schema_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    require(reference.startswith("#/"), f"Only local schema references are supported: {reference}")
    node: Any = root_schema
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        require(isinstance(node, dict) and part in node, f"Unresolved schema reference: {reference}")
        node = node[part]
    require(isinstance(node, dict), f"Schema reference is not an object: {reference}")
    return node


def json_type_matches(instance: Any, expected: str) -> bool:
    checks = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
        "null": lambda value: value is None,
    }
    require(expected in checks, f"Unsupported JSON Schema type in policy schema: {expected}")
    return checks[expected](instance)


def validate_json_schema_instance(
    instance: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str = "$",
) -> None:
    """Validate the JSON Schema vocabulary used by scoring-rule.schema.json.

    The policy validator stays dependency-free at runtime. This deliberately
    implements only the Draft 2020-12 keywords present in the committed schema;
    encountering an unsupported construct must fail closed rather than be
    ignored.
    """
    if "$ref" in schema:
        require(set(schema) == {"$ref"}, f"Sibling keywords next to $ref are unsupported at {path}")
        validate_json_schema_instance(instance, resolve_schema_ref(root_schema, schema["$ref"]), root_schema, path)
        return

    if "oneOf" in schema:
        candidates = schema["oneOf"]
        require(isinstance(candidates, list) and candidates, f"Malformed oneOf at {path}")
        matches = 0
        for candidate in candidates:
            try:
                validate_json_schema_instance(instance, candidate, root_schema, path)
            except ValidationFailure:
                continue
            matches += 1
        require(matches == 1, f"Expected exactly one oneOf match at {path}; found {matches}")
        return

    allowed_keywords = {
        "$schema", "$id", "title", "type", "additionalProperties", "required", "properties",
        "$defs", "const", "enum", "pattern", "format", "minLength", "minProperties", "maxProperties",
        "items", "minItems", "maxItems", "uniqueItems", "minimum", "maximum", "exclusiveMinimum",
    }
    unknown_keywords = set(schema) - allowed_keywords
    require(not unknown_keywords, f"Unsupported schema keywords at {path}: {sorted(unknown_keywords)}")

    if "type" in schema:
        expected_type = schema["type"]
        if isinstance(expected_type, list):
            require(any(json_type_matches(instance, item) for item in expected_type), f"Type mismatch at {path}")
        else:
            require(json_type_matches(instance, expected_type), f"Expected {expected_type} at {path}")

    if "const" in schema:
        require(json_equal(instance, schema["const"]), f"Const mismatch at {path}")
    if "enum" in schema:
        require(any(json_equal(instance, choice) for choice in schema["enum"]), f"Enum mismatch at {path}: {instance!r}")

    if isinstance(instance, dict):
        required_keys = set(schema.get("required", []))
        require(required_keys <= set(instance), f"Missing keys at {path}: {sorted(required_keys - set(instance))}")
        if "minProperties" in schema:
            require(len(instance) >= schema["minProperties"], f"Too few properties at {path}")
        if "maxProperties" in schema:
            require(len(instance) <= schema["maxProperties"], f"Too many properties at {path}")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            child_path = f"{path}.{key}"
            if key in properties:
                validate_json_schema_instance(value, properties[key], root_schema, child_path)
            elif schema.get("additionalProperties") is False:
                raise ValidationFailure(f"Unexpected property at {child_path}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate_json_schema_instance(value, schema["additionalProperties"], root_schema, child_path)

    if isinstance(instance, list):
        if "minItems" in schema:
            require(len(instance) >= schema["minItems"], f"Too few items at {path}")
        if "maxItems" in schema:
            require(len(instance) <= schema["maxItems"], f"Too many items at {path}")
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in instance]
            require(len(normalized) == len(set(normalized)), f"Duplicate array item at {path}")
        if "items" in schema:
            for index, value in enumerate(instance):
                validate_json_schema_instance(value, schema["items"], root_schema, f"{path}[{index}]")

    if isinstance(instance, str):
        if "minLength" in schema:
            require(len(instance) >= schema["minLength"], f"String too short at {path}")
        if "pattern" in schema:
            require(re.search(schema["pattern"], instance) is not None, f"Pattern mismatch at {path}: {instance!r}")
        if schema.get("format") == "date":
            try:
                parsed = dt.date.fromisoformat(instance)
            except ValueError as exc:
                raise ValidationFailure(f"Invalid ISO date at {path}: {instance!r}") from exc
            require(parsed.isoformat() == instance, f"Non-canonical ISO date at {path}: {instance!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema:
            require(instance >= schema["minimum"], f"Value below minimum at {path}")
        if "maximum" in schema:
            require(instance <= schema["maximum"], f"Value above maximum at {path}")
        if "exclusiveMinimum" in schema:
            require(instance > schema["exclusiveMinimum"], f"Value not above exclusive minimum at {path}")


def parse_factor_matrix() -> dict[str, dict[str, Any]]:
    pattern = re.compile(
        r"^\| `(?P<id>(?:T|B|C|S|O|M)\d{2})` \| (?P<name>.*?) \| "
        r"(?P<description>.*?) \| (?P<sources>.*?) \| (?P<coverage>.*?) \|$"
    )
    factors: dict[str, dict[str, Any]] = {}
    for line in FACTOR_MATRIX_PATH.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        factor_id = match.group("id")
        require(factor_id not in factors, f"Duplicate matrix factor {factor_id}")
        factors[factor_id] = {
            "name": match.group("name"),
            "sources": re.findall(r"`([^`]+)`", match.group("sources")),
        }
    return factors


def evaluate_condition(condition: dict[str, Any], values: dict[str, Any]) -> bool:
    if "all" in condition:
        return all(evaluate_condition(item, values) for item in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(item, values) for item in condition["any"])
    if "not" in condition:
        return not evaluate_condition(condition["not"], values)
    metric_name = condition["metric"]
    operator = condition["operator"]
    if operator == "exists":
        return (metric_name in values) is bool(condition["value"])
    if metric_name not in values:
        return False
    actual = values[metric_name]
    expected = condition["value"]
    operations = {
        "eq": lambda: actual == expected,
        "ne": lambda: actual != expected,
        "lt": lambda: actual < expected,
        "lte": lambda: actual <= expected,
        "gt": lambda: actual > expected,
        "gte": lambda: actual >= expected,
        "in": lambda: actual in expected,
        "not_in": lambda: actual not in expected,
        "between": lambda: expected[0] <= actual <= expected[1],
    }
    require(operator in operations, f"Unsupported operator {operator}")
    return bool(operations[operator]())


def preliminary_status(rule: dict[str, Any], metrics: dict[str, Any]) -> str:
    for status in rule["status_bands"]["evaluation_order"]:
        if evaluate_condition(rule["status_bands"][status], metrics):
            return status
    return "ND"


def apply_coverage(preliminary: str, coverage_rate: float, gate: dict[str, Any]) -> tuple[str, str | None]:
    if coverage_rate >= gate["minimum_rate"]:
        return preliminary, None
    if preliminary == "red" and gate["confirmed_issue_override"]:
        return "red", "low"
    return "ND", None


def condition_metrics(condition: dict[str, Any]) -> set[str]:
    if "all" in condition:
        return set().union(*(condition_metrics(item) for item in condition["all"]))
    if "any" in condition:
        return set().union(*(condition_metrics(item) for item in condition["any"]))
    if "not" in condition:
        return condition_metrics(condition["not"])
    return {condition["metric"]}


def resolve_confidence(confidence_rule: dict[str, Any], metrics: dict[str, Any]) -> str:
    required_controls = set().union(*(condition_metrics(cap["when"]) for cap in confidence_rule["caps"]))
    if not required_controls <= set(metrics):
        return "ND"
    index = CONFIDENCE_ORDER.index(confidence_rule["base"])
    for cap in confidence_rule["caps"]:
        if evaluate_condition(cap["when"], metrics):
            index = max(index, CONFIDENCE_ORDER.index(cap["maximum"]))
    return CONFIDENCE_ORDER[index]


def calculate_betroffenheit(coverage_policy: dict[str, Any], affected_count: Any, analyzed_count: Any) -> str:
    if (
        not isinstance(affected_count, int)
        or isinstance(affected_count, bool)
        or not isinstance(analyzed_count, int)
        or isinstance(analyzed_count, bool)
        or analyzed_count <= 0
        or affected_count < 0
        or affected_count > analyzed_count
    ):
        return "ND"
    values = {"affected_count": affected_count, "affected_rate": affected_count / analyzed_count}
    for band in coverage_policy["betroffenheit_precedence"]:
        if evaluate_condition(coverage_policy["betroffenheit_conditions"][band], values):
            return band
    raise ValidationFailure("Betroffenheit conditions did not resolve")


def priority_index(value: str) -> int:
    return PRIORITY_ORDER.index(value)


def clamp_index(index: int) -> int:
    return max(0, min(len(PRIORITY_ORDER) - 1, index))


def apply_priority_case(case: dict[str, Any]) -> str | None:
    if case["status"] not in {"red", "yellow"} or case.get("base") is None:
        return None
    index = priority_index(case["base"])
    if case["status"] == "yellow":
        index += 1
    betroffenheit_steps = {"broad": -1, "material": 0, "limited": 1, "isolated": 2, "none": 0}
    index += betroffenheit_steps.get(case.get("betroffenheit", "material"), 0)
    criticality = case.get("criticality")
    betroffenheit = case.get("betroffenheit", "material")
    confirmed_mapping = case.get("confirmed_mapping", False)
    if confirmed_mapping and (
        criticality == "critical" and betroffenheit != "none"
        or criticality == "high" and betroffenheit in {"broad", "material"}
    ):
        index -= min(int(case.get("criticality_maximum_uplift_steps", 1)), 1)
    index = clamp_index(index)

    if case["status"] == "red" and case.get("confidence", "high") == "high" and case.get("confirmed_issue", True):
        if case.get("veto_role") == "overall":
            index = min(index, priority_index("P0"))
        elif case.get("veto_role") == "block":
            index = min(index, priority_index("P1"))

    ceilings: list[str | None] = [case.get("factor_ceiling")]
    if case["status"] == "yellow":
        ceilings.append("P1")
    evidence_grade = case.get("evidence_grade", "G2_CALCULATED")
    dependency_role = case.get("dependency_role", "direct_observed_outcome")
    if evidence_grade == "G3_SOURCE_LIMITED":
        ceilings.append("P1" if dependency_role == "direct_observed_outcome" else "P2")
    elif evidence_grade == "G4_SUPPORTED_INFERENCE":
        ceilings.append("P1")
    scope_type = case.get("scope_type", "full")
    if scope_type == "representative_sample":
        ceilings.append("P1")
    elif scope_type == "diagnostic_sample":
        ceilings.append("P2")
    elif scope_type == "source_corpus":
        ceilings.append("P1" if dependency_role == "direct_observed_outcome" else "P2")
    if case.get("confidence") == "medium":
        ceilings.append("P1")
    if case.get("confidence") == "low":
        ceilings.append("P2")
    for ceiling in filter(None, ceilings):
        index = max(index, priority_index(ceiling))
    return PRIORITY_ORDER[index]


def evaluate_rollup(rule: dict[str, Any], values: dict[str, Any]) -> str:
    defaults = {
        "coverage_rate": 0.0,
        "high_confidence_red_veto_count": 0,
        "material_red_gate_or_outcome_count": 0,
        "material_red_supporting_count": 0,
        "red_low_confidence_count": 0,
        "material_yellow_count": 0,
        "red_count": 0,
        "yellow_count": 0,
        "high_confidence_overall_veto_red_count": 0,
        "red_block_count": 0,
        "yellow_block_count": 0,
        "green_block_count": 0,
    }
    merged = {**defaults, **values}
    for status in rule["evaluation_order"]:
        key = status.lower() if status == "ND" else status
        if status == "ND":
            key = "nd"
        if evaluate_condition(rule[key], merged):
            return status
    raise ValidationFailure("Roll-up conditions did not resolve to a status")


def validate_condition(condition: dict[str, Any], path: str) -> None:
    branch_keys = [key for key in ("all", "any", "not") if key in condition]
    if branch_keys:
        require(len(branch_keys) == 1 and len(condition) == 1, f"Malformed composite condition at {path}")
        key = branch_keys[0]
        children = condition[key] if key != "not" else [condition[key]]
        require(isinstance(children, list) and children, f"Empty composite condition at {path}")
        for index, child in enumerate(children):
            validate_condition(child, f"{path}.{key}[{index}]")
        return
    require(set(condition) == {"metric", "operator", "value"}, f"Malformed leaf condition at {path}")
    require(re.fullmatch(r"[a-z][a-z0-9_]*", condition["metric"]) is not None, f"Invalid metric name at {path}")
    require(condition["operator"] in {"eq", "ne", "lt", "lte", "gt", "gte", "in", "not_in", "between", "exists"}, f"Invalid operator at {path}")


def validate_policy_structure(policy: dict[str, Any], schema: dict[str, Any]) -> None:
    top_required = set(schema["required"])
    top_allowed = set(schema["properties"])
    require(top_required <= set(policy), f"Missing top-level keys: {sorted(top_required - set(policy))}")
    require(set(policy) <= top_allowed, f"Unknown top-level keys: {sorted(set(policy) - top_allowed)}")
    require(policy["policy_status"] == "frozen", "Policy is not frozen")
    require(policy["factor_count"] == 129 and policy["source_count"] == 18, "Frozen counts differ")
    require(re.fullmatch(r"\d+\.\d+\.\d+", policy["policy_version"]) is not None, "Invalid semantic version")
    factor_schema = schema["$defs"]["factorRule"]
    factor_required = set(factor_schema["required"])
    factor_allowed = set(factor_schema["properties"])
    require(len(policy["rules"]) == 129, f"Expected 129 rules, found {len(policy['rules'])}")
    for rule in policy["rules"]:
        factor_id = rule.get("factor_id", "unknown")
        require(factor_required <= set(rule), f"{factor_id}: missing fields {sorted(factor_required - set(rule))}")
        require(set(rule) <= factor_allowed, f"{factor_id}: unknown fields {sorted(set(rule) - factor_allowed)}")
        require(rule["policy_version"] == policy["policy_version"], f"{factor_id}: version mismatch")
        require(rule["status_bands"]["evaluation_order"] == ["red", "yellow", "green"], f"{factor_id}: status order")
        for status in ("red", "yellow", "green"):
            validate_condition(rule["status_bands"][status], f"{factor_id}.{status}")
        validate_condition(rule["applicability_rule"], f"{factor_id}.applicability")
        confidence_controls = set(policy["evidence_policy"]["confidence_control_metrics"])
        for cap_index, cap in enumerate(rule["confidence_rule"]["caps"]):
            validate_condition(cap["when"], f"{factor_id}.confidence.caps[{cap_index}]")
            require(condition_metrics(cap["when"]) <= confidence_controls, f"{factor_id}: unknown confidence control metric")
        metric_names = [item["name"] for item in rule["canonical_metrics"]]
        require(len(metric_names) == len(set(metric_names)), f"{factor_id}: duplicate canonical metric")
        require(set(rule["source_requirements"]) <= EXPECTED_SOURCES, f"{factor_id}: unknown source")
        require(rule["coverage_gate"]["below_minimum_status"] == "ND", f"{factor_id}: bad coverage fallback")
        require(rule["no_data_rule"]["source_level_failure"] == "BLOCK_RUN", f"{factor_id}: source failure must block")
        require(rule["no_data_rule"]["missing_required_metric"] == "ND", f"{factor_id}: missing metric must be ND")
        require(bool(rule["rationale"].strip()), f"{factor_id}: empty rationale")
        require(rule["citations"], f"{factor_id}: no citations")
        for citation_id in rule["citations"]:
            require(citation_id in policy["citations"], f"{factor_id}: unresolved citation {citation_id}")
        rubric_weights = [float(item["weight"]) for item in rule["rubric_dimensions"]]
        if "median_rubric_score" in metric_names:
            require(rubric_weights, f"{factor_id}: score-based rubric has no dimensions")
            require(abs(sum(rubric_weights) - 100.0) < 1e-9, f"{factor_id}: rubric weights do not sum to 100")
        else:
            require(not rubric_weights, f"{factor_id}: unexpected qualitative rubric dimensions")
        if rule["recommendation_trigger"]["informational_only"]:
            require(rule["base_priority"] is None and rule["priority_ceiling"] is None, f"{factor_id}: informational priority must be null")
            require(rule["recommendation_trigger"]["statuses"] == [], f"{factor_id}: informational recommendation trigger")
        else:
            require(rule["base_priority"] in PRIORITY_ORDER and rule["priority_ceiling"] in PRIORITY_ORDER, f"{factor_id}: missing priority")
        for parent in rule["dependency_parents"]:
            require(parent != factor_id, f"{factor_id}: self dependency")
    for rollup_name, rollup in {**policy["block_rollups"], "overall": policy["overall_rollup"]}.items():
        require(rollup["evaluation_order"] == ["red", "ND", "yellow", "green"], f"{rollup_name}: bad rollup order")
        for status_key in ("red", "yellow", "green", "nd"):
            validate_condition(rollup[status_key], f"rollup.{rollup_name}.{status_key}")
    coverage_policy = policy["coverage_policy"]
    require(coverage_policy["betroffenheit_precedence"] == ["broad", "material", "limited", "isolated", "none"], "Bad Betroffenheit precedence")
    require(set(coverage_policy["betroffenheit_conditions"]) == set(coverage_policy["betroffenheit_precedence"]), "Betroffenheit condition inventory mismatch")
    for band, condition in coverage_policy["betroffenheit_conditions"].items():
        validate_condition(condition, f"coverage_policy.betroffenheit_conditions.{band}")
        require(condition_metrics(condition) <= {"affected_count", "affected_rate"}, f"{band}: unknown Betroffenheit metric")
    priority_policy = policy["priority_policy"]
    require(priority_policy["algorithm_version"] == "priority-v1", "Unknown priority algorithm")
    require(priority_policy["priority_order"] == PRIORITY_ORDER, "Priority order mismatch")
    require(priority_policy["priority_index"] == {value: index for index, value in enumerate(PRIORITY_ORDER)}, "Priority index mismatch")
    require(priority_policy["status_steps"] == {"red": 0, "yellow": 1, "green": None, "ND": None, "NA": None}, "Priority status steps mismatch")


def validate_matrix_alignment(policy: dict[str, Any]) -> None:
    factors = parse_factor_matrix()
    rules = {rule["factor_id"]: rule for rule in policy["rules"]}
    require(len(factors) == 129, f"Canonical matrix has {len(factors)} factors")
    require(set(rules) == set(factors), f"Factor ID mismatch: rules-only={sorted(set(rules)-set(factors))}, matrix-only={sorted(set(factors)-set(rules))}")
    for factor_id, matrix_factor in factors.items():
        rule = rules[factor_id]
        require(rule["factor_name"] == matrix_factor["name"], f"{factor_id}: name drift")
        require(rule["source_requirements"] == matrix_factor["sources"], f"{factor_id}: source drift")
    observed_sources = {source for rule in rules.values() for source in rule["source_requirements"]}
    require(observed_sources == EXPECTED_SOURCES, "Policy does not resolve to exactly 18 canonical sources")


def validate_dependencies(policy: dict[str, Any]) -> None:
    graph = {rule["factor_id"]: rule["dependency_parents"] for rule in policy["rules"]}
    known = set(graph)
    for factor_id, parents in graph.items():
        require(set(parents) <= known, f"{factor_id}: unknown dependency parent")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValidationFailure(f"Dependency cycle at {node}")
        if node in visited:
            return
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for factor_id in graph:
        visit(factor_id)


def validate_fingerprint_and_readme(policy: dict[str, Any]) -> None:
    digest = canonical_fingerprint(policy)
    require(policy["policy_fingerprint"]["digest"] == digest, "Policy fingerprint mismatch")
    readme = README_PATH.read_text(encoding="utf-8")
    require(f"Policy version: `{policy['policy_version']}`" in readme, "README policy version mismatch")
    require(f"Policy fingerprint: `sha256:{digest}`" in readme, "README fingerprint mismatch")
    readme_ids = set(re.findall(r"^\| `((?:T|B|C|S|O|M)\d{2})` \|", readme, flags=re.MULTILINE))
    policy_ids = {rule["factor_id"] for rule in policy["rules"]}
    require(readme_ids == policy_ids, "README factor inventory mismatch")


def validate_citations(policy: dict[str, Any]) -> None:
    for citation_id, citation in policy["citations"].items():
        url = citation["url"]
        require(url.startswith("https://"), f"{citation_id}: citation must use https")
        require("utm_source=" not in url.lower(), f"{citation_id}: tracking parameter forbidden")
        require(bool(citation["supports"].strip()), f"{citation_id}: missing support statement")


def validate_no_placeholders(policy: dict[str, Any]) -> None:
    serialized = json.dumps(policy, ensure_ascii=False).lower()
    forbidden = ["todo", "tbd", "placeholder", "fill later", "runtime discretion"]
    for token in forbidden:
        require(token not in serialized, f"Forbidden placeholder token: {token}")


def validate_factor_fixtures(policy: dict[str, Any], fixtures: dict[str, Any]) -> None:
    rules = {rule["factor_id"]: rule for rule in policy["rules"]}
    require(fixtures["policy_version"] == policy["policy_version"], "Fixture version mismatch")
    require(fixtures["policy_fingerprint"] == policy["policy_fingerprint"]["digest"], "Fixture fingerprint mismatch")
    represented: set[str] = set()
    for case in fixtures["factor_boundary_cases"]:
        rule = rules[case["factor_id"]]
        represented.add(case["factor_id"])
        preliminary = preliminary_status(rule, case["metrics"])
        actual, _ = apply_coverage(preliminary, case["coverage_rate"], rule["coverage_gate"])
        require(actual == case["expected_status"], f"{case['case_id']}: expected {case['expected_status']}, got {actual}")
    require(represented == set(rules), "Not every factor has boundary fixtures")
    require(len(fixtures["factor_boundary_cases"]) >= 3 * len(rules), "Insufficient factor boundary fixtures")


def validate_betroffenheit_fixtures(policy: dict[str, Any], fixtures: dict[str, Any]) -> None:
    for case in fixtures["betroffenheit_cases"]:
        actual = calculate_betroffenheit(policy["coverage_policy"], case["affected_count"], case["analyzed_count"])
        require(actual == case["expected"], f"{case['case_id']}: expected {case['expected']}, got {actual}")


def validate_confidence_fixtures(policy: dict[str, Any], fixtures: dict[str, Any]) -> None:
    rules = {rule["factor_id"]: rule for rule in policy["rules"]}
    represented_profiles: set[str] = set()
    profile_signature_by_rule: dict[str, str] = {}
    for rule in policy["rules"]:
        signature = json.dumps(rule["confidence_rule"], ensure_ascii=False, sort_keys=True)
        profile_signature_by_rule[rule["factor_id"]] = signature
    for case in fixtures["confidence_cases"]:
        rule = rules[case["factor_id"]]
        represented_profiles.add(profile_signature_by_rule[case["factor_id"]])
        actual = resolve_confidence(rule["confidence_rule"], case["metrics"])
        require(actual == case["expected"], f"{case['case_id']}: expected {case['expected']}, got {actual}")
    all_profiles = set(profile_signature_by_rule.values())
    require(represented_profiles == all_profiles, "Not every distinct confidence profile has a fixture")


def resolve_source_readiness(case: dict[str, Any]) -> str:
    gates = ("access_ok", "schema_ok", "scope_ok", "extraction_ok", "snapshot_date_present")
    if not all(case.get(gate) is True for gate in gates):
        return "BLOCK_RUN"
    row_count = case.get("row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
        return "BLOCK_RUN"
    return "SOURCE_READY"


def resolve_input_conflict(case: dict[str, Any]) -> tuple[str, str | None]:
    if case["conflict_is_measured_outcome"]:
        return "SCORE_OBSERVED_CONFLICT", None
    if case["authoritative_precedence_resolved"]:
        return "CONTINUE_WITH_PROVENANCE", None
    return "ND", "low"


def can_reuse_cluster_mapping(case: dict[str, Any]) -> bool:
    if case["mapping_kind"] == "structural_membership":
        return False
    return bool(case["pattern_unchanged"] and case["previously_confirmed"])


def validate_adversarial_fixtures(policy: dict[str, Any], fixtures: dict[str, Any]) -> None:
    adversarial = {case["case_id"]: case for case in fixtures["adversarial_cases"]}
    rules = {rule["factor_id"]: rule for rule in policy["rules"]}
    require(adversarial["missing-source-blocks-run"]["expected"] == "BLOCK_RUN", "Missing source case")
    for case_id in (
        "green-below-coverage-becomes-nd",
        "yellow-below-coverage-becomes-nd",
        "confirmed-red-survives-low-coverage",
        "unconfirmed-red-below-coverage-becomes-nd",
    ):
        case = adversarial[case_id]
        actual, cap = apply_coverage(
            case["preliminary_status"],
            case["coverage_rate"],
            {"minimum_rate": case["minimum_rate"], "confirmed_issue_override": case["confirmed_issue_override"]},
        )
        require(actual == case["expected"], f"{case_id}: coverage result")
        if "expected_confidence_cap" in case:
            require(cap == case["expected_confidence_cap"], f"{case_id}: confidence cap")
    for case_id in ("zero-denominator-nd", "zero-denominator-na", "zero-denominator-green"):
        case = adversarial[case_id]
        actual = rules[case["factor_id"]]["no_data_rule"]["zero_denominator"]
        require(actual == case["expected"], f"{case_id}: expected {case['expected']}, got {actual}")
    for case_id in ("valid-empty-export-is-present", "empty-export-without-schema-blocks"):
        case = adversarial[case_id]
        actual = resolve_source_readiness(case)
        require(actual == case["expected"], f"{case_id}: expected {case['expected']}, got {actual}")
    for case_id in ("unresolved-input-conflict-becomes-nd", "measured-conflict-remains-scoreable"):
        case = adversarial[case_id]
        actual, cap = resolve_input_conflict(case)
        require(actual == case["expected"], f"{case_id}: expected {case['expected']}, got {actual}")
        if "expected_confidence_cap" in case:
            require(cap == case["expected_confidence_cap"], f"{case_id}: confidence cap")
    nested = adversarial["nested-clusters-distinct-sitewide"]
    distinct = len(set(nested["parent_urls"]) | set(nested["child_urls"]))
    require(distinct == nested["expected_sitewide_distinct"], "Distinct URL roll-up mismatch")
    require(len(nested["parent_urls"]) + len(nested["child_urls"]) == nested["forbidden_sum"], "Nested fixture malformed")
    for case_id in (
        "stale-prefix-mapping-not-reused",
        "unchanged-confirmed-semantic-mapping-reused",
        "structural-membership-never-reused",
    ):
        case = adversarial[case_id]
        actual = can_reuse_cluster_mapping(case)
        require(actual is case["expected_reuse"], f"{case_id}: expected reuse={case['expected_reuse']}, got {actual}")
    repeated = adversarial["same-source-repetition-no-confidence-uplift"]
    require(repeated["independent_source_count"] == 1 and repeated["expected_confidence_uplift"] == 0, "Source independence fixture")


def validate_priority_fixtures(fixtures: dict[str, Any]) -> None:
    for case in fixtures["priority_cases"]:
        actual = apply_priority_case(case)
        require(actual == case["expected"], f"{case['case_id']}: expected {case['expected']}, got {actual}")


def validate_rollup_fixtures(policy: dict[str, Any], fixtures: dict[str, Any]) -> None:
    represented_blocks: set[str] = set()
    for case in fixtures["rollup_cases"]:
        if case["scope"] == "overall":
            rule = policy["overall_rollup"]
        else:
            represented_blocks.add(case["block"])
            rule = policy["block_rollups"][case["block"]]
        values = {key: value for key, value in case.items() if key not in {"case_id", "scope", "block", "expected"}}
        actual = evaluate_rollup(rule, values)
        require(actual == case["expected"], f"{case['case_id']}: expected {case['expected']}, got {actual}")
    require(represented_blocks == set(policy["block_rollups"]), "Not every block roll-up has fixtures")


def main() -> int:
    try:
        policy = load_yaml(POLICY_PATH)
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        fixtures = load_yaml(FIXTURES_PATH)
        validate_json_schema_instance(policy, schema, schema)
        validate_policy_structure(policy, schema)
        validate_matrix_alignment(policy)
        validate_dependencies(policy)
        validate_fingerprint_and_readme(policy)
        validate_citations(policy)
        validate_no_placeholders(policy)
        validate_factor_fixtures(policy, fixtures)
        validate_betroffenheit_fixtures(policy, fixtures)
        validate_confidence_fixtures(policy, fixtures)
        validate_adversarial_fixtures(policy, fixtures)
        validate_priority_fixtures(fixtures)
        validate_rollup_fixtures(policy, fixtures)
    except (ValidationFailure, KeyError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "policy_version": policy["policy_version"],
                "policy_fingerprint": policy["policy_fingerprint"]["digest"],
                "rules": len(policy["rules"]),
                "factor_boundary_cases": len(fixtures["factor_boundary_cases"]),
                "betroffenheit_cases": len(fixtures["betroffenheit_cases"]),
                "confidence_cases": len(fixtures["confidence_cases"]),
                "adversarial_cases": len(fixtures["adversarial_cases"]),
                "priority_cases": len(fixtures["priority_cases"]),
                "rollup_cases": len(fixtures["rollup_cases"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
