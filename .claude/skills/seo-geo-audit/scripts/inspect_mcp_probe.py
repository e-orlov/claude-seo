#!/usr/bin/env python3
"""Verify a captured MCP probe against immutable response files and assertions."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from preflight_common import (
    SF_SOURCES,
    SISTRIX_SOURCES,
    PreflightError,
    atomic_write_json,
    canonical_sha256,
    ensure_no_secrets,
    normalize_domain,
    sha256_file,
    utc_now,
    validate_contract_instance,
)


MAX_RESPONSE_BYTES = 128 * 1024 * 1024
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|authorization)\s*[:=]\s*[\"']?[A-Za-z0-9._-]{16,}"
)
ENDPOINT_BY_SOURCE = {
    "SX-M": "ai.models",
    "SX-O": "ai.check.overview",
    "SX-C": "ai.check.competitors",
    "SX-P": "ai.check.prompts",
    "SX-PC": "ai.check.prompts.count",
    "SX-S": "ai.check.sources",
}


def parse_response(path: Path) -> tuple[str, Any]:
    payload = path.read_bytes()
    if len(payload) > MAX_RESPONSE_BYTES:
        raise PreflightError(f"MCP response exceeds {MAX_RESPONSE_BYTES} bytes: {path}")
    text = payload.decode("utf-8-sig")
    if SECRET_VALUE_PATTERN.search(text):
        raise PreflightError(f"Possible credential material in MCP response capture: {path}")
    try:
        return "json", json.loads(text)
    except json.JSONDecodeError:
        pass
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise PreflightError(f"DTD/entities are forbidden in MCP XML capture: {path}")
    try:
        return "xml", ET.fromstring(text)
    except ET.ParseError:
        return "text", text


def shape(value: Any) -> Any:
    if isinstance(value, ET.Element):
        child_variants = {
            json.dumps(shape(child), sort_keys=True, separators=(",", ":"))
            for child in list(value)[:100]
        }
        return {
            "tag": value.tag,
            "attributes": sorted(value.attrib),
            "children": [json.loads(item) for item in sorted(child_variants)],
        }
    if isinstance(value, dict):
        return {key: shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        variants = {json.dumps(shape(item), sort_keys=True, separators=(",", ":")) for item in value[:100]}
        return [json.loads(item) for item in sorted(variants)]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


def json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise PreflightError(f"Invalid JSON pointer: {pointer}")
    node = value
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            node = node[int(token)]
        elif isinstance(node, dict):
            node = node[token]
        else:
            raise KeyError(token)
    return node


def xml_path(root: ET.Element, locator: str) -> Any:
    attribute = None
    if "/@" in locator:
        locator, attribute = locator.rsplit("/@", 1)
    nodes = root.findall(locator)
    if not nodes:
        raise KeyError(locator)
    values = [node.attrib.get(attribute) if attribute else (node.text or "").strip() for node in nodes]
    return values[0] if len(values) == 1 else values


def resolve(kind: str, parsed: Any, request_parameters: dict[str, Any], assertion: dict[str, Any]) -> Any:
    locator_type = assertion["locator_type"]
    locator = assertion["locator"]
    if locator_type == "json_pointer":
        if kind != "json":
            raise PreflightError("json_pointer assertion targets a non-JSON response")
        return json_pointer(parsed, locator)
    if locator_type == "request_parameter":
        return json_pointer(request_parameters, locator)
    if locator_type == "xml_path":
        if kind != "xml":
            raise PreflightError("xml_path assertion targets a non-XML response")
        return xml_path(parsed, locator)
    if locator_type == "text_contains":
        if kind == "text":
            text = parsed
        elif kind == "json":
            text = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
        else:
            text = ET.tostring(parsed, encoding="unicode")
        return locator in text
    raise PreflightError(f"Unsupported locator type: {locator_type}")


def check_operator(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "exists":
        return actual is not None
    if operator == "nonempty":
        return actual not in (None, "", [], {})
    if operator == "equals":
        return type(actual) is type(expected) and actual == expected
    if operator == "contains":
        return expected in actual
    if operator == "gte":
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual >= expected
    if operator == "length_equals":
        if isinstance(actual, (list, dict, str)):
            return len(actual) == expected
        return (1 if actual is not None else 0) == expected
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-domain", required=True)
    parser.add_argument("--expected-country")
    parser.add_argument("--required-models", help="Comma-separated model codes; omit for all returned models")
    parser.add_argument("--cost-plan", type=Path, help="Output of estimate_sistrix_cost.py")
    args = parser.parse_args()
    try:
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        if not isinstance(draft, dict):
            raise PreflightError("Probe draft must be a JSON object")
        ensure_no_secrets(draft)
        server = draft.get("server")
        expected_sources = SF_SOURCES if server == "screaming_frog" else SISTRIX_SOURCES if server == "sistrix" else None
        if expected_sources is None:
            raise PreflightError("Probe server must be screaming_frog or sistrix")
        if normalize_domain(draft["scope"]["domain"]) != normalize_domain(args.expected_domain):
            raise PreflightError("Probe domain does not match audit domain")
        if server == "sistrix" and draft["scope"].get("country") != args.expected_country:
            raise PreflightError("SISTRIX probe country does not match audit country")
        if server == "sistrix" and not draft["scope"].get("models"):
            raise PreflightError("SISTRIX ai.models probe returned no usable models")
        required_models = {item for item in (args.required_models or "").split(",") if item}
        if required_models and not required_models <= set(draft["scope"].get("models", [])):
            raise PreflightError(f"Missing required SISTRIX models: {sorted(required_models - set(draft['scope'].get('models', [])))}")

        calls = {call["call_id"]: call for call in draft.get("calls", [])}
        if len(calls) != len(draft.get("calls", [])) or not calls:
            raise PreflightError("Probe call IDs must be non-empty and unique")
        parsed_calls = {}
        for call_id, call in calls.items():
            ensure_no_secrets(call.get("request_parameters", {}), f"$.calls.{call_id}.request_parameters")
            response_path = Path(call["response_path"])
            if not response_path.is_absolute():
                response_path = (args.draft.parent / response_path).resolve()
            kind, parsed = parse_response(response_path)
            call["response_path"] = str(response_path)
            call["response_sha256"] = sha256_file(response_path)
            call["response_schema_fingerprint"] = canonical_sha256({"format": kind, "shape": shape(parsed)})
            parsed_calls[call_id] = (kind, parsed)

        results = draft.get("source_results", [])
        result_codes = [item.get("source_code") for item in results]
        if result_codes != expected_sources:
            raise PreflightError(f"Expected source order {expected_sources}; got {result_codes}")
        checks_run = 0
        for result in results:
            if server == "sistrix" and result.get("details", {}).get("endpoint") != ENDPOINT_BY_SOURCE[result["source_code"]]:
                raise PreflightError(f"{result['source_code']}: documented endpoint mapping is missing or wrong")
            if not set(result["call_ids"]) <= set(calls):
                raise PreflightError(f"{result['source_code']}: unresolved call ID")
            assertions = result.get("assertions", [])
            if not assertions:
                raise PreflightError(f"{result['source_code']}: no response-anchored assertions")
            descriptions = []
            roles = {item.get("proof_role") for item in assertions}
            required_roles = {"schema", "snapshot", "record_count"}
            if server == "screaming_frog":
                required_roles.add("scope_domain")
            elif result["source_code"] == "SX-M":
                required_roles.add("scope_model")
            else:
                required_roles.update({"scope_domain", "scope_country"})
            if not required_roles <= roles:
                raise PreflightError(f"{result['source_code']}: missing proof roles {sorted(required_roles - roles)}")
            for assertion in assertions:
                if assertion["call_id"] not in result["call_ids"]:
                    raise PreflightError(f"{result['source_code']}: assertion uses an unrelated call")
                kind, parsed = parsed_calls[assertion["call_id"]]
                try:
                    actual = resolve(kind, parsed, calls[assertion["call_id"]]["request_parameters"], assertion)
                except (KeyError, IndexError, ValueError) as exc:
                    raise PreflightError(f"{result['source_code']}: unresolved locator {assertion['locator']}") from exc
                if not check_operator(actual, assertion["operator"], assertion.get("expected")):
                    raise PreflightError(f"{result['source_code']}: failed assertion {assertion['description']}")
                descriptions.append(assertion["description"])
                checks_run += 1
                if assertion["proof_role"] == "scope_domain" and assertion.get("expected") != normalize_domain(args.expected_domain):
                    raise PreflightError(f"{result['source_code']}: domain proof does not target the configured domain")
                if assertion["proof_role"] == "scope_country" and assertion.get("expected") != args.expected_country:
                    raise PreflightError(f"{result['source_code']}: country proof does not target the configured country")
                if assertion["proof_role"] == "snapshot" and assertion.get("expected") != result["snapshot_at"]:
                    raise PreflightError(f"{result['source_code']}: snapshot proof differs from source result")
                if assertion["proof_role"] == "record_count" and assertion.get("expected") != result["record_count"]:
                    raise PreflightError(f"{result['source_code']}: record-count proof differs from source result")
            result["semantic_checks"] = descriptions
            if result["source_code"] == "SX-M" and required_models:
                proven_models = {item.get("expected") for item in assertions if item.get("proof_role") == "scope_model"}
                if not required_models <= proven_models:
                    raise PreflightError(f"SX-M: response assertions do not prove models {sorted(required_models - proven_models)}")
            if result["record_count"] == 0:
                has_zero_proof = any(
                    item["proof_role"] == "record_count" and item["operator"] in {"equals", "length_equals"} and item.get("expected") == 0
                    for item in assertions
                )
                if not (result["valid_empty"] and has_zero_proof):
                    raise PreflightError(f"{result['source_code']}: zero rows lack explicit valid-empty proof")
            elif result["valid_empty"]:
                raise PreflightError(f"{result['source_code']}: non-zero source cannot be valid_empty")
            if result["data_status"] == "partial" and not result["limitations"]:
                raise PreflightError(f"{result['source_code']}: partial data requires a record-level limitation")

        finalized = copy.deepcopy(draft)
        if args.cost_plan is not None:
            finalized["cost_plan"] = json.loads(args.cost_plan.read_text(encoding="utf-8"))
        if server == "sistrix":
            plan = finalized.get("cost_plan")
            if not isinstance(plan, dict) or plan.get("plan_type") != "sistrix_request_credit_plan":
                raise PreflightError("SISTRIX probe requires the estimator's request/credit plan")
            if plan.get("transport") == "mcp" and plan.get("total_credit_bounds") != {"lower": 0, "expected": 0, "upper": 0}:
                raise PreflightError("MCP credit plan contradicts the documented zero-credit policy")
        finalized["package_type"] = "geo_mcp_probe"
        finalized["schema_version"] = 1
        finalized["adapter_version"] = 1
        finalized["verification"] = {
            "passed": True,
            "verified_at": finalized["captured_at"],
            "checks_run": checks_run,
            "failures": [],
        }
        finalized["package_sha256"] = "0" * 64
        finalized["package_sha256"] = canonical_sha256(finalized, "package_sha256")
        validate_contract_instance(finalized, "mcp-probe.schema.json")
        atomic_write_json(args.output.resolve(), finalized)
        print(json.dumps({
            "status": "PASS",
            "server": server,
            "calls": len(calls),
            "source_results": len(results),
            "checks_run": checks_run,
            "package_sha256": finalized["package_sha256"],
            "output": str(args.output.resolve()),
        }, sort_keys=True))
        return 0
    except (OSError, UnicodeDecodeError, ET.ParseError, KeyError, TypeError, ValueError, json.JSONDecodeError, PreflightError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
