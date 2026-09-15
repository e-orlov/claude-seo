#!/usr/bin/env python3
"""Run the closed 18-source GEO readiness gate and checkpoint its result."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from extract_zip import extract as extract_zip
from preflight_common import (
    FILE_SOURCES,
    SF_SOURCES,
    SISTRIX_SOURCES,
    SOURCE_ORDER,
    PreflightError,
    canonical_sha256,
    freshness,
    load_document,
    load_manifest,
    normalize_domain,
    save_manifest,
    sha256_file,
    source_catalog_by_code,
    transition,
    validate_contract_instance,
)
from source_adapters import (
    SUPPORTED_TABLE_EXTENSIONS,
    classify_headers,
    inspect_sentiment_mhtml,
    inspect_tabular,
    profile_for_source,
    profile_table,
)


CONFIG_KEY_BY_SOURCE = {
    "AH-BL": "ahrefs_backlinks",
    "AH-RD": "ahrefs_refdomains",
    "AH-BB": "ahrefs_broken_backlinks",
    "GSC-GAI": "gsc_generative_ai_export",
    "DJ": "dejan",
}


def missing_check(source_code: str, affected: list[str], action: str, auth: bool = False) -> dict[str, Any]:
    return {
        "source_code": source_code,
        "access_status": "auth_required" if auth else "fail",
        "data_status": "missing",
        "scope_status": "unknown",
        "freshness_status": "unknown",
        "blocking": True,
        "affected_factors": affected,
        "action": action,
        "details": {},
    }


def resolve_input(path_value: str, config_path: Path) -> Path:
    path = Path(path_value)
    unresolved = path if path.is_absolute() else config_path.parent / path
    if unresolved.is_symlink():
        raise PreflightError(f"Symlinked mandatory input is forbidden: {unresolved}")
    return unresolved.resolve()


def expand_input_roots(roots: Iterable[Path], run_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for root in roots:
        if root.is_symlink():
            raise PreflightError(f"Symlinked input root is forbidden: {root}")
        root = root.resolve()
        if root.is_file() and root.suffix.casefold() == ".zip":
            digest = sha256_file(root)
            destination = run_dir / "raw" / "extracted" / digest[:16]
            extraction_manifest = destination.parent / f"{digest[:16]}.manifest.json"
            if extraction_manifest.exists():
                prior = load_document(extraction_manifest)
                if prior.get("archive_sha256") != digest:
                    raise PreflightError(f"ZIP extraction manifest hash mismatch: {extraction_manifest}")
                for item in prior.get("files", []):
                    path = Path(item["path"])
                    if not path.is_file() or sha256_file(path) != item["sha256"]:
                        raise PreflightError(f"Previously extracted ZIP member changed: {path}")
                    candidates.append(path)
            else:
                if destination.exists() and any(destination.iterdir()):
                    raise PreflightError(f"Uncheckpointed ZIP extraction directory exists: {destination}")
                result = extract_zip(root, destination)
                from preflight_common import atomic_write_json
                atomic_write_json(extraction_manifest, result)
                candidates.extend(Path(item["path"]) for item in result["files"])
        elif root.is_dir():
            candidates.extend(path for path in root.rglob("*") if path.is_file() and not path.is_symlink())
        elif root.is_file():
            candidates.append(root)
    unique = {str(path.resolve()): path.resolve() for path in candidates}
    return [unique[key] for key in sorted(unique)]


def discover_tables(paths: list[Path]) -> dict[str, list[tuple[float, Path]]]:
    discovered: dict[str, list[tuple[float, Path]]] = {code: [] for code in CONFIG_KEY_BY_SOURCE}
    for path in paths:
        if path.suffix.casefold() not in SUPPORTED_TABLE_EXTENSIONS:
            continue
        try:
            headers, _, _, _ = profile_table(path)
        except Exception:
            if path.suffix.casefold() in {".html", ".htm"}:
                try:
                    headers, _, _, _ = profile_for_source(path, "DJ")
                except Exception:
                    continue
            else:
                continue
        candidates = classify_headers(headers, path.name)
        if candidates and candidates[0]["source_code"] in discovered and candidates[0]["complete_signature"]:
            discovered[candidates[0]["source_code"]].append((candidates[0]["score"], path))
    for source_code in discovered:
        discovered[source_code].sort(key=lambda item: (-item[0], str(item[1])))
    return discovered


def choose_discovered(source_code: str, values: list[tuple[float, Path]]) -> tuple[Path | None, str | None]:
    if not values:
        return None, None
    if len(values) > 1 and values[0][0] == values[1][0]:
        return None, "Ambiguous candidates: " + ", ".join(str(path) for _, path in values[:5])
    return values[0][1], None


def load_probe(path: Path, server: str, expected_domain: str, expected_country: str | None) -> dict[str, Any]:
    package = load_document(path)
    validate_contract_instance(package, "mcp-probe.schema.json")
    if canonical_sha256(package, "package_sha256") != package["package_sha256"]:
        raise PreflightError(f"MCP probe package hash mismatch: {path}")
    if package["server"] != server:
        raise PreflightError(f"Expected {server} probe; got {package['server']}")
    if normalize_domain(package["scope"]["domain"]) != expected_domain:
        raise PreflightError(f"{server} probe domain mismatch")
    if server == "sistrix" and package["scope"]["country"] != expected_country:
        raise PreflightError("SISTRIX probe country mismatch")
    for call in package["calls"]:
        response = Path(call["response_path"])
        if not response.is_file() or sha256_file(response) != call["response_sha256"]:
            raise PreflightError(f"MCP response artifact changed or disappeared: {response}")
    return package


def probe_records(
    package: dict[str, Any], package_path: Path, catalog: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    checks, artifacts, gaps = [], [], []
    for index, result in enumerate(package["source_results"], start=1):
        source_code = result["source_code"]
        computed_freshness = freshness(result["snapshot_at"], catalog[source_code]["freshness_class"])
        partial = result["data_status"] == "partial"
        stale = computed_freshness != "current"
        blocking = stale
        if partial:
            gaps.append({
                "source_code": source_code,
                "gap_type": "record_level_partial",
                "limitations": result["limitations"],
            })
        check = {
            "source_code": source_code,
            "access_status": result["access_status"],
            "data_status": result["data_status"],
            "scope_status": result["scope_status"],
            "freshness_status": computed_freshness,
            "blocking": blocking,
            "affected_factors": catalog[source_code]["required_for"],
            "action": f"Refresh the {source_code} MCP extraction." if stale else None,
            "details": {
                "call_ids": result["call_ids"],
                "semantic_checks": result["semantic_checks"],
                "limitations": result["limitations"],
                "probe_package_sha256": package["package_sha256"],
            },
        }
        checks.append(check)
        artifacts.append({
            "artifact_id": f"{source_code.lower().replace('-', '_')}-{package['package_sha256'][:16]}-{index}",
            "source_code": source_code,
            "path_or_locator": f"{package_path.resolve()}#{source_code}",
            "sha256": package["package_sha256"],
            "byte_size": package_path.stat().st_size,
            "schema_fingerprint": canonical_sha256(result),
            "snapshot_at": result["snapshot_at"],
            "record_count": result["record_count"],
            "valid_empty": result["valid_empty"],
            "adapter_version": package["adapter_version"],
        })
    probe = {
        "server": package["server"],
        "package_path": str(package_path.resolve()),
        "package_sha256": package["package_sha256"],
        "adapter_version": package["adapter_version"],
        "captured_at": package["captured_at"],
        "verified": True,
    }
    return checks, artifacts, [probe], gaps


def aggregate_sentiment(results: list[dict[str, Any]], catalog_entry: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not results:
        return missing_check(
            "SX-SENT", catalog_entry["required_for"],
            "Upload at least one current SISTRIX Sentiment page saved as complete MHTML for the configured brand/domain.",
        ), []
    checks = [item["check"] for item in results]
    artifacts = [item["artifact"] for item in results]
    main_scope_match = any(check["scope_status"] == "match" for check in checks)
    malformed = any(check["data_status"] == "malformed" for check in checks)
    stale = any(check["freshness_status"] == "stale" for check in checks)
    blocking = malformed or not main_scope_match or stale
    return {
        "source_code": "SX-SENT",
        "access_status": "pass",
        "data_status": "malformed" if malformed else "present",
        "scope_status": "match" if main_scope_match else "mismatch",
        "freshness_status": "stale" if stale else ("current" if all(check["freshness_status"] == "current" for check in checks) else "unknown"),
        "blocking": blocking,
        "affected_factors": catalog_entry["required_for"],
        "action": None if not blocking else "Replace malformed/stale MHTML and include the configured brand/domain sentiment page.",
        "details": {
            "file_count": len(results),
            "main_scope_match_count": sum(check["scope_status"] == "match" for check in checks),
            "competitor_or_other_scope_count": sum(check["scope_status"] != "match" for check in checks),
            "remote_resources_loaded": False,
        },
    }, artifacts


def source_set_hash(artifacts: list[dict[str, Any]]) -> str:
    identity = sorted(
        ({key: item[key] for key in ("source_code", "sha256", "schema_fingerprint", "record_count", "valid_empty")}
         for item in artifacts),
        key=lambda item: (item["source_code"], item["sha256"], item["schema_fingerprint"]),
    )
    return canonical_sha256(identity)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--sf-probe", type=Path)
    parser.add_argument("--sistrix-probe", type=Path)
    parser.add_argument("--input-root", action="append", default=[], type=Path)
    parser.add_argument("--valid-empty", action="append", default=[], choices=FILE_SOURCES)
    args = parser.parse_args()
    lock_handle = None
    try:
        manifest_path = args.manifest.resolve()
        lock_path = manifest_path.parent / ".preflight.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = lock_path.open("a+", encoding="utf-8")
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        manifest = load_manifest(manifest_path)
        if manifest["state"] in {"ANALYSIS_COMPLETE", "ANALYSIS_COMPLETE_WITH_GAPS"}:
            raise PreflightError("Completed runs are immutable")
        transition(manifest, "PREFLIGHT", "PREFLIGHT_STARTED")
        run_dir = manifest_path.parent
        config_path = run_dir / "config.normalized.json"
        config = load_document(config_path)
        validate_contract_instance(config, "audit-config.schema.json")
        if canonical_sha256(config) != manifest["config"]["sha256"]:
            action = "Normalized audit config changed after run creation; rerun init_run.py to create/resume the correct revision."
            manifest["blocking_actions"] = [action]
            transition(manifest, "BLOCKED", "CONFIG_HASH_CHANGED")
            save_manifest(manifest_path, manifest)
            print(json.dumps({"status": "BLOCKED", "action": action, "manifest": str(manifest_path)}, sort_keys=True))
            return 2
        expected_domain = normalize_domain(config["domain"])
        catalog = source_catalog_by_code()
        checks: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []
        probes: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []

        for server, path, expected_sources in (
            ("screaming_frog", args.sf_probe, SF_SOURCES),
            ("sistrix", args.sistrix_probe, SISTRIX_SOURCES),
        ):
            if path is None:
                for source_code in expected_sources:
                    checks.append(missing_check(
                        source_code, catalog[source_code]["required_for"],
                        f"Connect {server.replace('_', ' ')} MCP and run the documented harmless live probe for {source_code}.",
                        auth=True,
                    ))
                continue
            package = load_probe(path.resolve(), server, expected_domain, config["sistrix"]["country"] if server == "sistrix" else None)
            new_checks, new_artifacts, new_probes, new_gaps = probe_records(package, path, catalog)
            checks.extend(new_checks)
            artifacts.extend(new_artifacts)
            probes.extend(new_probes)
            gaps.extend(new_gaps)

        explicit_paths: dict[str, Path] = {}
        for source_code, config_key in CONFIG_KEY_BY_SOURCE.items():
            value = config["inputs"].get(config_key)
            if value:
                explicit_paths[source_code] = resolve_input(value, Path(manifest["config"]["path"]))
        sentiment_paths = [resolve_input(value, Path(manifest["config"]["path"])) for value in config["inputs"]["sistrix_sentiment_mhtml"]]

        discovered_files = expand_input_roots(args.input_root, run_dir)
        discovered_tables = discover_tables(discovered_files)
        explicit_path_owners: dict[str, list[str]] = {}
        for source_code, path in explicit_paths.items():
            explicit_path_owners.setdefault(str(path), []).append(source_code)
        duplicate_explicit_sources = {
            source_code for owners in explicit_path_owners.values() if len(owners) > 1 for source_code in owners
        }
        for source_code in CONFIG_KEY_BY_SOURCE:
            if source_code in duplicate_explicit_sources:
                checks.append(missing_check(
                    source_code, catalog[source_code]["required_for"],
                    "One physical file is mapped to multiple mandatory source codes; provide each distinct export explicitly.",
                ))
                continue
            selected = explicit_paths.get(source_code)
            ambiguity = None
            if selected is None:
                selected, ambiguity = choose_discovered(source_code, discovered_tables[source_code])
            if selected is None:
                action = ambiguity or f"Upload and map the required {source_code} export in audit config."
                checks.append(missing_check(source_code, catalog[source_code]["required_for"], action))
                continue
            if not selected.is_file():
                checks.append(missing_check(source_code, catalog[source_code]["required_for"], f"Configured {source_code} file does not exist: {selected}"))
                continue
            result = inspect_tabular(
                selected, source_code, expected_domain, catalog[source_code]["freshness_class"],
                explicit_binding=source_code in explicit_paths,
                valid_empty_attested=source_code in set(args.valid_empty),
            )
            result["check"]["affected_factors"] = catalog[source_code]["required_for"]
            checks.append(result["check"])
            artifacts.append(result["artifact"])

        if not sentiment_paths:
            sentiment_paths = [path for path in discovered_files if path.suffix.casefold() in {".mhtml", ".mht"}]
        sentiment_results = [
            inspect_sentiment_mhtml(path, config["brand"], expected_domain, catalog["SX-SENT"]["freshness_class"])
            for path in sentiment_paths if path.is_file()
        ]
        sentiment_results = list({item["artifact"]["sha256"]: item for item in sentiment_results}.values())
        sentiment_check, sentiment_artifacts = aggregate_sentiment(sentiment_results, catalog["SX-SENT"])
        checks.append(sentiment_check)
        artifacts.extend(sentiment_artifacts)

        by_code = {check["source_code"]: check for check in checks}
        if set(by_code) != set(SOURCE_ORDER) or len(checks) != len(SOURCE_ORDER):
            raise PreflightError(f"Preflight did not produce exactly 18 unique source checks: {sorted(by_code)}")
        checks = [by_code[source_code] for source_code in SOURCE_ORDER]
        new_source_set = source_set_hash(artifacts)
        artifact_source_codes = {item["source_code"] for item in artifacts}
        all_source_artifacts_present = artifact_source_codes == set(SOURCE_ORDER)
        if manifest["source_set_sha256"] and manifest["source_set_sha256"] != new_source_set:
            action = "Source artifacts changed after checkpoint; rerun init_run.py with --new-revision."
            manifest["blocking_actions"] = [action]
            transition(manifest, "BLOCKED", "SOURCE_SET_CHANGED", {"observed_source_set_sha256": new_source_set})
            save_manifest(manifest_path, manifest)
            print(json.dumps({"status": "BLOCKED", "action": action, "manifest": str(manifest_path)}, sort_keys=True))
            return 2

        manifest["source_checks"] = checks
        manifest["artifacts"] = sorted(artifacts, key=lambda item: (SOURCE_ORDER.index(item["source_code"]), item["artifact_id"]))
        manifest["mcp_probes"] = probes
        manifest["sistrix_cost_plan"] = None
        if args.sistrix_probe:
            sistrix_package = load_document(args.sistrix_probe.resolve())
            manifest["sistrix_cost_plan"] = sistrix_package.get("cost_plan")
            plan = manifest["sistrix_cost_plan"]
            check = by_code["SX-O"]
            if plan is None:
                check["blocking"] = True
                check["action"] = "Generate and embed the SISTRIX request/credit plan before collection."
            elif plan.get("transport") != config["sistrix"]["connection_mode"]:
                check["blocking"] = True
                check["action"] = "Regenerate the SISTRIX cost plan for the configured connection mode."
            elif plan.get("transport") == "mcp" and plan.get("total_credit_bounds") != {"lower": 0, "expected": 0, "upper": 0}:
                check["blocking"] = True
                check["action"] = "Correct the MCP cost plan: current official SISTRIX MCP calls use zero API credits."
            elif plan.get("transport") == "direct_api":
                upper = (plan.get("total_credit_bounds") or {}).get("upper")
                maximum = config["sistrix"]["max_credit_cost"]
                if upper is None:
                    check["blocking"] = True
                    check["action"] = "Prove a finite direct-API credit upper bound before collection."
                elif maximum is not None and upper > maximum:
                    check["blocking"] = True
                    check["action"] = f"Direct-API upper bound {upper} exceeds configured max_credit_cost {maximum}; change the limit explicitly or reduce scope."
            check["details"]["sistrix_cost_plan"] = plan
        manifest["record_gaps"] = gaps
        blockers = [check for check in checks if check["blocking"]]
        if manifest["source_set_sha256"] is None and all_source_artifacts_present and not blockers:
            manifest["source_set_sha256"] = new_source_set
        manifest["blocking_actions"] = [check["action"] for check in blockers if check["action"]]
        if blockers:
            missing_files = any(check["source_code"] in FILE_SOURCES for check in blockers)
            target = "WAITING_FOR_INPUTS" if missing_files else "BLOCKED"
            transition(manifest, target, "PREFLIGHT_BLOCKED", {"blocking_source_codes": [check["source_code"] for check in blockers]})
        elif gaps:
            transition(manifest, "READY_WITH_GAPS", "PREFLIGHT_PASSED_WITH_GAPS", {"record_gap_count": len(gaps)})
        else:
            transition(manifest, "READY", "PREFLIGHT_PASSED", {"source_count": 18})
        save_manifest(manifest_path, manifest)
        print(json.dumps({
            "status": manifest["state"],
            "run_id": manifest["run_id"],
            "source_count": len(checks),
            "artifact_count": len(artifacts),
            "blocking_source_codes": [check["source_code"] for check in blockers],
            "record_gap_count": len(gaps),
            "source_set_sha256": manifest["source_set_sha256"],
            "observed_source_set_sha256": new_source_set,
            "manifest_sha256": manifest["manifest_sha256"],
            "manifest": str(manifest_path),
        }, sort_keys=True))
        return 0 if not blockers else 2
    except (OSError, ValueError, json.JSONDecodeError, PreflightError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        if lock_handle is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
