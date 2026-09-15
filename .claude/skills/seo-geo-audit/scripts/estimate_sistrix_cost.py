#!/usr/bin/env python3
"""Build an auditable SISTRIX request and credit range without false precision."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from preflight_common import atomic_write_json, utc_now


ENDPOINTS = ["ai.models", "ai.check.overview", "ai.check.competitors", "ai.check.prompts", "ai.check.prompts.count", "ai.check.sources"]
PER_ENTRY = {"ai.check.competitors", "ai.check.prompts", "ai.check.prompts.count", "ai.check.sources"}
DOCS = {
    "mcp": "https://www.sistrix.com/api/connection-to-chatbot-ai/technical-information-mcp/",
    "limits": "https://www.sistrix.com/api/limitations/",
    "overview": "https://www.sistrix.com/api/ai-check/ai-check-overview/",
    "competitors": "https://www.sistrix.com/api/ai-check/ai-check-competitors/",
    "prompts": "https://www.sistrix.com/api/ai-check/ai-check-prompts/",
    "prompt_counts": "https://www.sistrix.com/api/ai-check/ai-check-prompts-count/",
    "sources": "https://www.sistrix.com/api/ai-check/ai-check-sources/",
}


def load_counts(path: Path | None) -> dict[str, dict[str, int | None]]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Endpoint count estimates must be an object")
    result = {}
    for endpoint, bounds in value.items():
        if endpoint not in ENDPOINTS or not isinstance(bounds, dict):
            raise ValueError(f"Unsupported endpoint/count object: {endpoint}")
        normalized = {}
        for key in ("lower", "expected", "upper"):
            item = bounds.get(key)
            if item is not None and (not isinstance(item, int) or isinstance(item, bool) or item < 0):
                raise ValueError(f"{endpoint}.{key} must be a non-negative integer or null")
            normalized[key] = item
        result[endpoint] = normalized
    return result


def pages(rows: int | None, page_size: int | None) -> int | None:
    if rows is None or page_size is None:
        return None
    return max(1, math.ceil(rows / page_size))


def add_bound(values: list[int | None]) -> int | None:
    return None if any(value is None for value in values) else sum(value for value in values if value is not None)


def build_plan(transport: str, model_count: int, page_size: int | None, counts: dict[str, dict[str, int | None]]) -> dict[str, Any]:
    endpoint_plan = []
    request_bounds: dict[str, list[int | None]] = {key: [] for key in ("lower", "expected", "upper")}
    credit_bounds: dict[str, list[int | None]] = {key: [] for key in ("lower", "expected", "upper")}
    for endpoint in ENDPOINTS:
        loops = 1 if endpoint in {"ai.models", "ai.check.overview"} else model_count
        row_bounds = counts.get(endpoint, {})
        endpoint_requests = {}
        endpoint_credits = {}
        for bound in ("lower", "expected", "upper"):
            if endpoint in {"ai.models", "ai.check.overview"}:
                requests = 1
            elif endpoint == "ai.check.prompts.count":
                requests = loops
            else:
                estimate = row_bounds.get(bound)
                requests = loops if bound == "lower" and estimate is None else (
                    None if estimate is None or page_size is None else loops * pages(estimate, page_size)
                )
            if transport == "mcp":
                credits = 0
            elif endpoint == "ai.models":
                credits = 0
            elif endpoint == "ai.check.overview":
                credits = 10
            elif endpoint in PER_ENTRY:
                estimate = row_bounds.get(bound)
                credits = None if estimate is None else loops * estimate
            else:
                credits = None
            endpoint_requests[bound] = requests
            endpoint_credits[bound] = credits
            request_bounds[bound].append(requests)
            credit_bounds[bound].append(credits)
        endpoint_plan.append({
            "endpoint": endpoint,
            "model_scopes": loops,
            "row_bounds_per_model": {key: row_bounds.get(key) for key in ("lower", "expected", "upper")},
            "request_bounds": endpoint_requests,
            "credit_bounds": endpoint_credits,
        })
    totals_requests = {key: add_bound(value) for key, value in request_bounds.items()}
    totals_credits = {key: add_bound(value) for key, value in credit_bounds.items()}
    return {
        "plan_type": "sistrix_request_credit_plan",
        "schema_version": 1,
        "created_at": utc_now(),
        "transport": transport,
        "model_count": model_count,
        "page_size": page_size,
        "endpoints": endpoint_plan,
        "total_request_bounds": totals_requests,
        "total_credit_bounds": totals_credits,
        "credit_precision": "exact_zero_for_mcp" if transport == "mcp" else (
            "bounded" if totals_credits["upper"] is not None else "upper_bound_not_proven"
        ),
        "rate_plan": {
            "documented_max_requests_per_minute": 300,
            "documented_minimum_interval_ms": 300,
            "retry_429": "respect server retry/reset signal; do not tighten the interval",
        },
        "assumptions": [
            "MCP requests consume zero API credits according to the official SISTRIX MCP documentation checked on 2026-09-15."
            if transport == "mcp" else
            "Direct API overview costs 10 credits; listed result endpoints cost 1 credit per returned entry.",
            "A null expected or upper value is intentional: pagination/returned-entry volume was not proven.",
            "Request bounds count planned calls, not latency, fair-use capacity, or guaranteed successful responses.",
        ],
        "sources": DOCS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=["mcp", "direct_api"], required=True)
    parser.add_argument("--model-count", type=int, required=True)
    parser.add_argument("--page-size", type=int)
    parser.add_argument("--endpoint-counts", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.model_count < 1:
            raise ValueError("model-count must be >= 1")
        if args.page_size is not None and args.page_size < 1:
            raise ValueError("page-size must be >= 1")
        plan = build_plan(args.transport, args.model_count, args.page_size, load_counts(args.endpoint_counts))
        atomic_write_json(args.output.resolve(), plan)
        print(json.dumps({
            "status": "PASS",
            "transport": plan["transport"],
            "requests": plan["total_request_bounds"],
            "credits": plan["total_credit_bounds"],
            "precision": plan["credit_precision"],
            "output": str(args.output.resolve()),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
