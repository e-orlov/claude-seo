#!/usr/bin/env python3
"""Parse a SISTRIX Sentiment MHTML locally without fetching remote resources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from preflight_common import atomic_write_json
from source_adapters import inspect_sentiment_mhtml


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = inspect_sentiment_mhtml(args.input, args.brand, args.domain, "visibility_30d")
        atomic_write_json(args.output.resolve(), result)
        status = "PASS" if not result["check"]["blocking"] else "BLOCKED"
        print(json.dumps({
            "status": status,
            "source_code": "SX-SENT",
            "artifact_sha256": result["artifact"]["sha256"],
            "data_status": result["check"]["data_status"],
            "scope_status": result["check"]["scope_status"],
            "remote_resources_loaded": False,
            "output": str(args.output.resolve()),
        }, sort_keys=True))
        return 0 if status == "PASS" else 2
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
