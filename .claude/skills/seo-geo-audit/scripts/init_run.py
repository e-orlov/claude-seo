#!/usr/bin/env python3
"""Create or safely resume a standalone GEO audit run."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator

import yaml

from preflight_common import (
    PreflightError,
    atomic_write_json,
    canonical_sha256,
    contract_identity,
    load_document,
    load_manifest,
    normalize_domain,
    save_manifest,
    slugify,
    utc_now,
    validate_contract_instance,
)


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def template() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "client_id": None,
        "brand": None,
        "domain": None,
        "country": None,
        "language": None,
        "report_language": "de",
        "crawl": {"expected_scope": None, "include_subdomains": False},
        "sistrix": {
            "connection_mode": "mcp",
            "models": "all_available",
            "country": None,
            "direct_api_fallback": False,
            "max_credit_cost": None,
        },
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
            "ahrefs_backlinks": None,
            "ahrefs_refdomains": None,
            "ahrefs_broken_backlinks": None,
            "dejan": None,
            "sistrix_sentiment_mhtml": [],
            "gsc_generative_ai_export": None,
        },
        "report": {"output_docx": True, "output_pdf": True},
    }


def apply_args(config: dict[str, Any], args: argparse.Namespace) -> None:
    for name in ("client_id", "brand", "domain", "country", "language", "report_language"):
        value = getattr(args, name, None)
        if value is not None:
            config[name] = value
    if args.models:
        config["sistrix"]["models"] = [item.strip() for item in args.models.split(",") if item.strip()]
    if args.crawl_scope:
        config["crawl"]["expected_scope"] = args.crawl_scope


def normalize_config(config: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    normalized = dict(config)
    original_domain = normalized.get("domain")
    if original_domain:
        normalized["domain"] = normalize_domain(str(original_domain))
        normalized["client_id"] = normalized.get("client_id") or slugify(normalized["domain"])
        crawl = dict(normalized.get("crawl") or {})
        crawl["expected_scope"] = normalize_domain(str(crawl.get("expected_scope") or normalized["domain"]))
        normalized["crawl"] = crawl
    if normalized.get("country"):
        normalized["country"] = str(normalized["country"]).lower()
    sistrix = dict(normalized.get("sistrix") or {})
    sistrix["country"] = str(sistrix.get("country") or normalized.get("country") or "").lower() or None
    normalized["sistrix"] = sistrix
    if normalized.get("language") and not normalized.get("report_language"):
        normalized["report_language"] = normalized["language"].split("-")[0]
    return normalized, str(original_domain) if original_domain else None


def missing_fields(config: dict[str, Any]) -> list[str]:
    checks = {
        "client_id": config.get("client_id"),
        "brand": config.get("brand"),
        "domain": config.get("domain"),
        "country": config.get("country"),
        "language": config.get("language"),
        "crawl.expected_scope": (config.get("crawl") or {}).get("expected_scope"),
        "sistrix.country": (config.get("sistrix") or {}).get("country"),
        "sistrix.models": (config.get("sistrix") or {}).get("models"),
    }
    return [key for key, value in checks.items() if value in (None, "", [])]


def write_yaml_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(temporary, path)


@contextlib.contextmanager
def run_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".geo-run.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def iter_manifests(root: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    for path in sorted(root.glob("geo-*-r*/run-manifest.json")):
        try:
            yield path, load_manifest(path)
        except PreflightError:
            continue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--client-id")
    parser.add_argument("--brand")
    parser.add_argument("--domain")
    parser.add_argument("--country")
    parser.add_argument("--language")
    parser.add_argument("--report-language", choices=["de", "en"])
    parser.add_argument("--models", help="Comma-separated SISTRIX model codes")
    parser.add_argument("--crawl-scope")
    parser.add_argument("--new-revision", action="store_true")
    args = parser.parse_args()

    try:
        supplied = load_document(args.config) if args.config.exists() else {}
        config = deep_merge(template(), supplied)
        apply_args(config, args)
        config, original_domain = normalize_config(config)
        missing = missing_fields(config)
        if missing:
            write_yaml_atomic(args.config.resolve(), config)
            print(json.dumps({
                "status": "WAITING_FOR_CONFIG",
                "config_path": str(args.config.resolve()),
                "missing_fields": missing,
                "action": "Provide only the listed values, then rerun init_run.py.",
            }, ensure_ascii=False, sort_keys=True))
            return 2

        validate_contract_instance(config, "audit-config.schema.json")
        config_sha = canonical_sha256(config)
        run_root = args.run_root.resolve()
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        client_id = config["client_id"]

        with run_lock(run_root):
            existing = list(iter_manifests(run_root))
            same_config = [(path, manifest) for path, manifest in existing if manifest["config"]["sha256"] == config_sha]
            if same_config and not args.new_revision:
                path, manifest = max(same_config, key=lambda pair: pair[1]["revision"])
                print(json.dumps({
                    "status": "RESUMED",
                    "run_id": manifest["run_id"],
                    "run_state": manifest["state"],
                    "manifest_path": str(path),
                    "manifest_sha256": manifest["manifest_sha256"],
                }, sort_keys=True))
                return 0

            run_pattern = re.compile(rf"^geo-{re.escape(client_id)}-\d{{4}}-\d{{2}}-\d{{2}}-r([1-9][0-9]*)$")
            directory_revisions = [
                int(match.group(1)) for directory in run_root.iterdir() if directory.is_dir()
                if (match := run_pattern.fullmatch(directory.name))
            ]
            revision = max(directory_revisions, default=0) + 1
            run_id = f"geo-{client_id}-{today}-r{revision}"
            run_dir = run_root / run_id
            for directory in ("raw", "probes", "staging", "output", "logs"):
                (run_dir / directory).mkdir(parents=True, exist_ok=True)
            created_at = utc_now()
            manifest = {
                "package_type": "geo_run_manifest",
                "schema_version": 1,
                "run_id": run_id,
                "revision": revision,
                "state": "CREATED",
                "created_at": created_at,
                "updated_at": created_at,
                "config": {
                    "path": str(args.config.resolve()),
                    "sha256": config_sha,
                    "original_domain": original_domain or config["domain"],
                    "normalized_domain": config["domain"],
                },
                "contract": contract_identity(),
                "source_set_sha256": None,
                "source_checks": [],
                "artifacts": [],
                "mcp_probes": [],
                "sistrix_cost_plan": None,
                "record_gaps": [],
                "blocking_actions": [],
                "events": [{
                    "sequence": 1,
                    "from_state": None,
                    "to_state": "CREATED",
                    "event_type": "RUN_CREATED",
                    "created_at": created_at,
                    "payload": {"config_sha256": config_sha},
                }],
                "manifest_sha256": "0" * 64,
            }
            manifest_path = run_dir / "run-manifest.json"
            save_manifest(manifest_path, manifest)
            atomic_write_json(run_dir / "config.normalized.json", config)

        print(json.dumps({
            "status": "CREATED",
            "run_id": run_id,
            "manifest_path": str(manifest_path),
            "config_sha256": config_sha,
            "manifest_sha256": manifest["manifest_sha256"],
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, yaml.YAMLError, PreflightError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
