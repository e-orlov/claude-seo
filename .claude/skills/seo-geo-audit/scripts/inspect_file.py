#!/usr/bin/env python3
"""Inspect one mandatory uploaded GEO source and emit its deterministic profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from preflight_common import atomic_write_json, normalize_domain, source_catalog_by_code
from source_adapters import inspect_sentiment_mhtml, inspect_tabular


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-code", required=True, choices=["GSC-GAI", "AH-BL", "AH-RD", "AH-BB", "SX-SENT", "DJ"])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--brand")
    parser.add_argument("--valid-empty-attested", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        catalog = source_catalog_by_code()
        domain = normalize_domain(args.domain)
        if args.source_code == "SX-SENT":
            if not args.brand:
                raise ValueError("--brand is required for SX-SENT")
            result = inspect_sentiment_mhtml(args.input, args.brand, domain, catalog[args.source_code]["freshness_class"])
        else:
            result = inspect_tabular(
                args.input, args.source_code, domain, catalog[args.source_code]["freshness_class"],
                explicit_binding=True, valid_empty_attested=args.valid_empty_attested,
            )
        atomic_write_json(args.output.resolve(), result)
        status = "PASS" if not result["check"]["blocking"] else "BLOCKED"
        print(json.dumps({
            "status": status,
            "source_code": args.source_code,
            "data_status": result["check"]["data_status"],
            "scope_status": result["check"]["scope_status"],
            "record_count": result["artifact"]["record_count"],
            "artifact_sha256": result["artifact"]["sha256"],
            "output": str(args.output.resolve()),
        }, sort_keys=True))
        return 0 if status == "PASS" else 2
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
