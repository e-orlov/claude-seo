#!/usr/bin/env python3
"""Validate the standalone helpful-content audit artifact set."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


EVIDENCE_ID_RE = re.compile(r"^HC-E\d{4,}$")
EVIDENCE_REF_RE = re.compile(r"\bHC-E\d{4,}\b")
ALLOWED_CRITERION_STATUSES = {
    "verified_positive",
    "verified_concern",
    "supported_inference",
    "mixed_evidence",
    "not_verifiable",
    "not_applicable",
}
ALLOWED_CRITERION_IDS = {f"HC{number:02d}" for number in range(1, 19)}
ALLOWED_OUTCOMES = {
    "no_material_verified_concerns",
    "verified_improvement_opportunities",
    "material_verified_concerns",
    "serious_verified_trust_or_harm_concerns",
    "insufficient_evidence",
}
ALLOWED_SOURCE_TYPES = {
    "sf_field",
    "rendered_html",
    "visible_text",
    "structured_data",
    "accessibility",
    "mobile_lighthouse",
    "link_data",
    "derived_aggregate",
    "external_page_in_selected_crawl",
}
ALLOWED_SOURCE_AVAILABILITY = {"available", "partial", "unavailable", "failed"}
REQUIRED_MATRIX_COLUMNS = [
    "URL",
    "Page Type",
    "Inferred Purpose",
    "Inferred Primary Focus",
    "Focus Confidence",
    "Likely User Task",
    "YMYL",
    "Overall Outcome",
    "Verified Strengths",
    "Verified Concerns",
    "Supported Inferences",
    "Not Verifiable",
    "Highest Priority",
    "Evidence IDs",
]


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: cannot read valid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path}: top-level value must be an object")
        return {}
    return value


def load_ndjson(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        errors.append(f"{path}: cannot read file: {exc}")
        return records
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path}:{line_number}: record must be an object")
            continue
        value["_validation_line"] = line_number
        records.append(value)
    return records


def load_csv(path: Path, errors: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            return fieldnames, list(reader)
    except (OSError, csv.Error) as exc:
        errors.append(f"{path}: cannot read valid CSV: {exc}")
        return [], []


def duplicate_values(values: Iterable[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def collect_evidence_references(value: Any) -> set[str]:
    references: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_ids" and isinstance(item, list):
                references.update(str(entry) for entry in item)
            else:
                references.update(collect_evidence_references(item))
    elif isinstance(value, list):
        for item in value:
            references.update(collect_evidence_references(item))
    return references


def validate(audit_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    paths = {
        "scope": audit_dir / "work" / "helpful-content-scope.json",
        "assessments": audit_dir / "work" / "helpful-content-page-assessments.ndjson",
        "matrix": audit_dir / "output" / "helpful-content-url-matrix.csv",
        "evidence": audit_dir / "output" / "helpful-content-evidence.ndjson",
        "report": audit_dir / "output" / "helpful-content-audit.md",
    }
    for label, path in paths.items():
        if not path.is_file():
            errors.append(f"missing required {label} artifact: {path}")
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "counts": {}}

    scope = load_json(paths["scope"], errors)
    assessments = load_ndjson(paths["assessments"], errors)
    evidence = load_ndjson(paths["evidence"], errors)
    matrix_columns, matrix_rows = load_csv(paths["matrix"], errors)
    try:
        report_text = paths["report"].read_text(encoding="utf-8-sig")
    except OSError as exc:
        errors.append(f"{paths['report']}: cannot read file: {exc}")
        report_text = ""

    if scope.get("skill") != "seo-helpful-content-audit":
        errors.append("scope.skill must equal seo-helpful-content-audit")
    baseline = scope.get("target_baseline")
    completed = scope.get("target_completed")
    if not isinstance(baseline, int) or baseline < 0:
        errors.append("scope.target_baseline must be a non-negative integer")
    if not isinstance(completed, int) or completed < 0:
        errors.append("scope.target_completed must be a non-negative integer")
    if isinstance(completed, int) and completed != len(assessments):
        errors.append(
            "scope.target_completed does not equal page-assessment record count "
            f"({completed} != {len(assessments)})"
        )
    if isinstance(baseline, int) and isinstance(completed, int) and completed > baseline:
        errors.append("scope.target_completed cannot exceed scope.target_baseline")

    source_availability = scope.get("source_availability", {})
    if not isinstance(source_availability, dict):
        errors.append("scope.source_availability must be an object")
    else:
        for source_name, status in source_availability.items():
            if status not in ALLOWED_SOURCE_AVAILABILITY:
                errors.append(
                    f"scope.source_availability.{source_name} has invalid value: {status}"
                )

    assessment_urls = [str(record.get("url", "")) for record in assessments]
    for duplicate in duplicate_values(assessment_urls):
        errors.append(f"duplicate page-assessment URL: {duplicate}")
    for record in assessments:
        line = record.get("_validation_line", "?")
        url = record.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            errors.append(f"assessment line {line}: missing valid HTTP(S) URL")
        if record.get("scope_role") != "target":
            errors.append(f"assessment line {line}: scope_role must be target")
        focus = record.get("primary_focus")
        if not isinstance(focus, dict) or focus.get("status") not in {
            "resolved",
            "focus_ambiguous",
            "not_verifiable",
        }:
            errors.append(f"assessment line {line}: invalid primary_focus.status")
        elif focus.get("status") != "not_verifiable" and not focus.get("evidence_ids"):
            errors.append(f"assessment line {line}: resolved/ambiguous focus has no evidence_ids")
        if record.get("overall_outcome") not in ALLOWED_OUTCOMES:
            errors.append(f"assessment line {line}: invalid overall_outcome")
        criteria = record.get("criteria")
        if not isinstance(criteria, list):
            errors.append(f"assessment line {line}: criteria must be a list")
            continue
        criterion_ids: list[str] = []
        for criterion in criteria:
            if not isinstance(criterion, dict):
                errors.append(f"assessment line {line}: criterion must be an object")
                continue
            criterion_id = str(criterion.get("criterion_id", ""))
            criterion_ids.append(criterion_id)
            if criterion_id not in ALLOWED_CRITERION_IDS:
                errors.append(
                    f"assessment line {line}: invalid criterion_id: {criterion_id}"
                )
            status = criterion.get("status")
            if status not in ALLOWED_CRITERION_STATUSES:
                errors.append(f"assessment line {line}: invalid criterion status: {status}")
            if status in {
                "verified_positive",
                "verified_concern",
                "supported_inference",
                "mixed_evidence",
            }:
                ids = criterion.get("evidence_ids")
                if not isinstance(ids, list) or not ids:
                    errors.append(
                        f"assessment line {line}: {status} criterion has no evidence_ids"
                    )
        for duplicate in duplicate_values(criterion_ids):
            errors.append(
                f"assessment line {line}: duplicate criterion_id: {duplicate}"
            )

    evidence_ids = [str(record.get("evidence_id", "")) for record in evidence]
    for duplicate in duplicate_values(evidence_ids):
        errors.append(f"duplicate evidence ID: {duplicate}")
    for record in evidence:
        line = record.get("_validation_line", "?")
        evidence_id = str(record.get("evidence_id", ""))
        if not EVIDENCE_ID_RE.fullmatch(evidence_id):
            errors.append(f"evidence line {line}: invalid evidence_id: {evidence_id}")
        if not str(record.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"evidence line {line}: missing valid HTTP(S) URL")
        if record.get("source_type") not in ALLOWED_SOURCE_TYPES:
            errors.append(
                f"evidence line {line}: invalid source_type: {record.get('source_type')}"
            )
        if not str(record.get("source_locator", "")).strip():
            errors.append(f"evidence line {line}: source_locator is empty")
        if not str(record.get("observation", "")).strip():
            errors.append(f"evidence line {line}: observation is empty")

    evidence_id_set = set(evidence_ids)
    assessment_refs: set[str] = set()
    for record in assessments:
        assessment_refs.update(collect_evidence_references(record))
    matrix_refs = set(EVIDENCE_REF_RE.findall("\n".join(
        str(row.get("Evidence IDs", "")) for row in matrix_rows
    )))
    report_refs = set(EVIDENCE_REF_RE.findall(report_text))
    all_refs = assessment_refs | matrix_refs | report_refs
    for reference in sorted(all_refs - evidence_id_set):
        errors.append(f"cited evidence ID does not exist: {reference}")
    unused_evidence = sorted(evidence_id_set - all_refs)
    if unused_evidence:
        warnings.append(f"{len(unused_evidence)} evidence records are not cited")

    if matrix_columns != REQUIRED_MATRIX_COLUMNS:
        errors.append(
            "URL matrix columns do not match the required order; got: "
            + ", ".join(matrix_columns)
        )
    matrix_urls = [str(row.get("URL", "")) for row in matrix_rows]
    for duplicate in duplicate_values(matrix_urls):
        errors.append(f"duplicate URL matrix row: {duplicate}")
    if set(matrix_urls) != set(assessment_urls) or len(matrix_urls) != len(assessment_urls):
        errors.append("URL matrix rows do not match page-assessment URLs one-to-one")

    combined_output_text = report_text + "\n" + json.dumps(
        assessments + evidence + matrix_rows, ensure_ascii=False
    )
    if "photowant" in combined_output_text.lower():
        errors.append("excluded Photowant source appears in audit outputs")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "target_baseline": baseline,
            "page_assessments": len(assessments),
            "matrix_rows": len(matrix_rows),
            "evidence_records": len(evidence),
            "cited_evidence_ids": len(all_refs),
        },
    }


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="helpful-content-validator-") as tmp:
        audit_dir = Path(tmp)
        work_dir = audit_dir / "work"
        output_dir = audit_dir / "output"
        work_dir.mkdir()
        output_dir.mkdir()
        scope = {
            "skill": "seo-helpful-content-audit",
            "target_baseline": 1,
            "target_completed": 1,
            "source_availability": {"raw_html": "available"},
        }
        assessment = {
            "url": "https://example.com/page",
            "scope_role": "target",
            "primary_focus": {
                "value": "example",
                "status": "resolved",
                "evidence_ids": ["HC-E0001"],
            },
            "criteria": [
                {
                    "criterion_id": "HC01",
                    "status": "verified_positive",
                    "evidence_ids": ["HC-E0001"],
                }
            ],
            "overall_outcome": "no_material_verified_concerns",
        }
        evidence = {
            "evidence_id": "HC-E0001",
            "url": "https://example.com/page",
            "source_type": "rendered_html",
            "source_locator": "main > h1",
            "observation": "The heading states the page purpose.",
        }
        (work_dir / "helpful-content-scope.json").write_text(
            json.dumps(scope), encoding="utf-8"
        )
        (work_dir / "helpful-content-page-assessments.ndjson").write_text(
            json.dumps(assessment) + "\n", encoding="utf-8"
        )
        (output_dir / "helpful-content-evidence.ndjson").write_text(
            json.dumps(evidence) + "\n", encoding="utf-8"
        )
        with (output_dir / "helpful-content-url-matrix.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_MATRIX_COLUMNS)
            writer.writeheader()
            row = {column: "" for column in REQUIRED_MATRIX_COLUMNS}
            row.update({"URL": assessment["url"], "Evidence IDs": "HC-E0001"})
            writer.writerow(row)
        (output_dir / "helpful-content-audit.md").write_text(
            "# Audit\n\nEvidence: HC-E0001.\n", encoding="utf-8"
        )
        result = validate(audit_dir)
        assert result["valid"], result
        assert result["counts"]["page_assessments"] == 1
        print("self-test: ok", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "audit_dir",
        nargs="?",
        type=Path,
        help="Audit directory containing work/ and output/",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run the built-in deterministic test"
    )
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.audit_dir is None:
        parser.error("audit_dir is required unless --self-test is used")
    result = validate(args.audit_dir.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
