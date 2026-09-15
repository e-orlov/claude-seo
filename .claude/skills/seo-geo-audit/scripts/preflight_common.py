#!/usr/bin/env python3
"""Shared fail-closed helpers for the standalone GEO preflight."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DIR = REPO_ROOT / ".claude" / "geo-audit" / "contracts"
SOURCE_ORDER = [
    "SF", "RAW", "REN", "PSI", "GSC-SA", "GSC-UI", "GSC-GAI",
    "AH-BL", "AH-RD", "AH-BB", "SX-M", "SX-O", "SX-C", "SX-P",
    "SX-PC", "SX-S", "SX-SENT", "DJ",
]
SF_SOURCES = SOURCE_ORDER[:6]
SISTRIX_SOURCES = SOURCE_ORDER[10:16]
FILE_SOURCES = ["GSC-GAI", "AH-BL", "AH-RD", "AH-BB", "SX-SENT", "DJ"]
POLICY_FINGERPRINT = "77da1451409845f6ba53d97f90071c92a4b26cc248f8d6b2bbc5634aaebe89ed"

STATE_TRANSITIONS = {
    "CREATED": {"CREATED", "PREFLIGHT", "WAITING_FOR_CONFIG", "BLOCKED", "FAILED"},
    "WAITING_FOR_CONFIG": {"WAITING_FOR_CONFIG", "PREFLIGHT", "BLOCKED", "FAILED"},
    "PREFLIGHT": {"PREFLIGHT", "WAITING_FOR_INPUTS", "READY", "READY_WITH_GAPS", "BLOCKED", "FAILED"},
    "WAITING_FOR_INPUTS": {"WAITING_FOR_INPUTS", "PREFLIGHT", "BLOCKED", "FAILED"},
    "READY": {"READY", "PREFLIGHT", "COLLECTING", "BLOCKED", "FAILED"},
    "READY_WITH_GAPS": {"READY_WITH_GAPS", "PREFLIGHT", "COLLECTING", "BLOCKED", "FAILED"},
    "COLLECTING": {"COLLECTING", "STAGED", "BLOCKED", "FAILED"},
    "STAGED": {"STAGED", "CLUSTERING", "BLOCKED", "FAILED"},
    "CLUSTERING": {"CLUSTERING", "WAITING_FOR_CLUSTER_CONFIRMATION", "ANALYZING", "BLOCKED", "FAILED"},
    "WAITING_FOR_CLUSTER_CONFIRMATION": {"WAITING_FOR_CLUSTER_CONFIRMATION", "CLUSTERING", "ANALYZING", "BLOCKED", "FAILED"},
    "ANALYZING": {"ANALYZING", "VALIDATING", "BLOCKED", "FAILED"},
    "VALIDATING": {"VALIDATING", "ANALYSIS_COMPLETE", "ANALYSIS_COMPLETE_WITH_GAPS", "BLOCKED", "FAILED"},
    "ANALYSIS_COMPLETE": {"ANALYSIS_COMPLETE"},
    "ANALYSIS_COMPLETE_WITH_GAPS": {"ANALYSIS_COMPLETE_WITH_GAPS"},
    "BLOCKED": {"BLOCKED", "PREFLIGHT", "FAILED"},
    "FAILED": {"FAILED", "PREFLIGHT"},
}

SECRET_KEY = re.compile(r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|authorization|client[_-]?secret)", re.I)


class PreflightError(RuntimeError):
    """Raised when a runtime invariant cannot be proven."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value: Any, blank_field: str | None = None) -> str:
    normalized = copy.deepcopy(value)
    if blank_field is not None:
        normalized[blank_field] = ""
    return hashlib.sha256(canonical_bytes(normalized)).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    value = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(value, dict):
        raise PreflightError(f"{path}: expected a mapping/object")
    return value


def ensure_no_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(str(key)):
                raise PreflightError(f"Secret-bearing field is forbidden at {path}.{key}")
            ensure_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            ensure_no_secrets(child, f"{path}[{index}]")


def normalize_domain(value: str) -> str:
    raw = value.strip()
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host):
        raise PreflightError(f"Invalid canonical domain: {value!r}")
    return host


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not value:
        raise PreflightError("Cannot derive a non-empty client slug")
    return value[:63].rstrip("-")


def _contract_validator_module():
    path = REPO_ROOT / ".claude" / "geo-audit" / "scripts" / "validate_contracts.py"
    spec = importlib.util.spec_from_file_location("geo_contract_validator", path)
    if spec is None or spec.loader is None:
        raise PreflightError(f"Cannot load contract validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_contract_instance(value: dict[str, Any], schema_name: str) -> None:
    module = _contract_validator_module()
    try:
        module.validate_with_schema(value, schema_name)
    except Exception as exc:
        raise PreflightError(f"{schema_name} validation failed: {exc}") from exc


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_no_secrets(value)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def manifest_hash(manifest: dict[str, Any]) -> str:
    return canonical_sha256(manifest, "manifest_sha256")


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = load_document(path)
    validate_contract_instance(manifest, "run-manifest.schema.json")
    if manifest_hash(manifest) != manifest["manifest_sha256"]:
        raise PreflightError(f"Run manifest hash mismatch: {path}")
    sequences = [event["sequence"] for event in manifest["events"]]
    if sequences != list(range(1, len(sequences) + 1)):
        raise PreflightError("Run event sequence is not contiguous")
    previous = None
    for index, event in enumerate(manifest["events"]):
        if event["from_state"] != previous:
            raise PreflightError(f"Run event {index + 1} has a broken from_state chain")
        if previous is None:
            if event["to_state"] != "CREATED":
                raise PreflightError("First run event must create the run")
        elif event["to_state"] not in STATE_TRANSITIONS.get(previous, set()):
            raise PreflightError(f"Run history contains forbidden transition: {previous} -> {event['to_state']}")
        previous = event["to_state"]
    if previous != manifest["state"]:
        raise PreflightError("Manifest state differs from the last event")
    check_codes = [item["source_code"] for item in manifest["source_checks"]]
    if len(check_codes) != len(set(check_codes)):
        raise PreflightError("Run manifest contains duplicate source checks")
    artifact_ids = [item["artifact_id"] for item in manifest["artifacts"]]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise PreflightError("Run manifest contains duplicate artifact IDs")
    probe_servers = [item["server"] for item in manifest["mcp_probes"]]
    if len(probe_servers) != len(set(probe_servers)):
        raise PreflightError("Run manifest contains duplicate MCP probe packages")
    if manifest["state"] in {"READY", "READY_WITH_GAPS"}:
        if check_codes != SOURCE_ORDER or any(item["blocking"] for item in manifest["source_checks"]):
            raise PreflightError("Ready manifest does not contain 18 non-blocking checks in canonical order")
        if manifest["source_set_sha256"] is None:
            raise PreflightError("Ready manifest lacks a frozen source-set hash")
        if manifest["state"] == "READY" and manifest["record_gaps"]:
            raise PreflightError("READY manifest contains record-level gaps")
        if manifest["state"] == "READY_WITH_GAPS" and not manifest["record_gaps"]:
            raise PreflightError("READY_WITH_GAPS manifest lacks a documented gap")
    return manifest


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = utc_now()
    manifest["manifest_sha256"] = manifest_hash(manifest)
    validate_contract_instance(manifest, "run-manifest.schema.json")
    atomic_write_json(path, manifest)


def transition(
    manifest: dict[str, Any], new_state: str, event_type: str, payload: dict[str, Any] | None = None
) -> None:
    old_state = manifest["state"]
    if new_state not in STATE_TRANSITIONS.get(old_state, set()):
        raise PreflightError(f"Forbidden state transition: {old_state} -> {new_state}")
    event = {
        "sequence": len(manifest["events"]) + 1,
        "from_state": old_state,
        "to_state": new_state,
        "event_type": event_type,
        "created_at": utc_now(),
        "payload": payload or {},
    }
    manifest["state"] = new_state
    manifest["events"].append(event)


def contract_identity() -> dict[str, str]:
    sources = load_document(CONTRACT_DIR / "source-catalog.yaml")
    factors = load_document(CONTRACT_DIR / "factor-catalog.yaml")
    return {
        "source_catalog_version": sources["catalog_version"],
        "source_catalog_fingerprint": sources["catalog_fingerprint"],
        "factor_catalog_version": factors["catalog_version"],
        "factor_catalog_fingerprint": factors["catalog_fingerprint"],
        "policy_version": "1.0.0",
        "policy_fingerprint": POLICY_FINGERPRINT,
    }


def source_catalog_by_code() -> dict[str, dict[str, Any]]:
    catalog = load_document(CONTRACT_DIR / "source-catalog.yaml")
    return {entry["source_code"]: entry for entry in catalog["sources"]}


def freshness(snapshot_at: str | None, freshness_class: str, now: dt.datetime | None = None) -> str:
    if not snapshot_at:
        return "unknown"
    moment = dt.datetime.fromisoformat(snapshot_at.replace("Z", "+00:00"))
    now = now or dt.datetime.now(dt.timezone.utc)
    age = now - moment.astimezone(dt.timezone.utc)
    if age < -dt.timedelta(minutes=5):
        return "unknown"
    if freshness_class == "crawl_14d":
        return "current" if age <= dt.timedelta(days=14) else "stale"
    if freshness_class == "visibility_30d":
        return "current" if age <= dt.timedelta(days=30) else "stale"
    if freshness_class == "historical_window":
        return "current"
    return "unknown"


def artifact_id(source_code: str, digest: str, ordinal: int = 1) -> str:
    return f"{source_code.lower().replace('-', '_')}-{digest[:16]}-{ordinal}"
