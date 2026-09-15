---
name: seo-geo-audit
description: >
  Run a standalone evidence-led GEO audit from Screaming Frog MCP, SISTRIX MCP,
  mandatory Ahrefs/Dejan/GSC/SISTRIX-Sentiment files, and automatic URL
  clustering. Produces a validated analysis package for all 129 canonical GEO
  factors without assigning traffic lights or report priorities.
user-invocable: true
disable-model-invocation: true
argument-hint: "[clients/<domain>/<date>/geo/config/audit.yaml]"
license: MIT
metadata:
  version: "0.1.0"
  category: geo-audit
  release-stage: contracts
---

# SEO GEO Audit

## Purpose

Collect, normalize and analyse the closed GEO data basis, then hand one
contract-valid `analysis-package.json` to `seo-geo-report-generator`.

This skill ends at evidence-backed measurements, findings and recommendation
candidates. It does not assign red/yellow/green, P0–P3, block status, overall
status, or render a client report.

## Invocation boundary

- Run only after the user explicitly invokes `/seo-geo-audit`.
- Do not invoke `seo-data-foundation` or `seo-file-audit-orchestrator`.
- Invoke `seo-url-clustering` automatically through the explicit run/table/field
  contract after Screaming Frog staging succeeds.
- Do not invoke the report skill automatically.

## Load first

Read and validate these runtime contracts before touching client inputs:

1. `.claude/geo-audit/contracts/README.md`
2. `.claude/geo-audit/contracts/audit-config.schema.json`
3. `.claude/geo-audit/contracts/source-catalog.yaml`
4. `.claude/geo-audit/contracts/factor-catalog.yaml`
5. `.claude/geo-audit/contracts/analysis-package.schema.json`
6. `.claude/geo-audit/contracts/duckdb-schema.sql`

Run `.claude/geo-audit/scripts/validate_contracts.py`. If it is absent or does
not return PASS, stop: the installed skill is not contract-complete.

## Closed source gate

Preflight all 18 source codes every run:

`SF`, `RAW`, `REN`, `PSI`, `GSC-SA`, `GSC-UI`, `GSC-GAI`, `AH-BL`,
`AH-RD`, `AH-BB`, `SX-M`, `SX-O`, `SX-C`, `SX-P`, `SX-PC`, `SX-S`,
`SX-SENT`, `DJ`.

A missing source-level access, artifact, schema, scope, date/snapshot, or
successful extraction blocks the complete audit and produces a precise action
for the user. Never convert absence into zero, green, or a website defect. A
valid empty export is present only after all source-level gates pass.

## Required execution order

1. Validate or create the audit config; ask only for missing brand, domain,
   country, language, model scope, or file locations.
2. Perform harmless real reads against Screaming Frog MCP and SISTRIX MCP.
3. Produce the SISTRIX request/credit plan before full collection.
4. Fingerprint and validate all mandatory file inputs, including MHTML as MIME.
5. Create or resume the run by config/source hashes; keep one DuckDB writer.
6. Ingest immutable raw references, staging, canonical and derived layers.
7. Normalize URLs and record every non-exact join and confidence cap.
8. Automatically invoke URL clustering; rebuild all path-prefix memberships
   from the current crawl and reuse only confirmed labels/criticality for an
   unchanged pattern.
9. Calculate raw/rendered HTML parity as a shared method for T16, T17 and S18,
   not as a 130th factor.
10. Calculate all 129 factor metric records and cluster scopes.
11. Create evidence, findings and deduplicated recommendation candidates.
12. Pass every analysis completion invariant and write the immutable analysis
    package. End the skill.

## Non-negotiable interpretation

- `affected / analyzed` is Betroffenheit, not causal or business impact.
- Sitewide URL aggregation uses distinct normalized URLs; never add parent and
  child path-prefix counts.
- Lighthouse lab is the primary PSI basis; optional CrUX does not gate coverage,
  and TBT is not field INP.
- SISTRIX prompt counts describe the observed SISTRIX corpus, not all relevant
  user prompts.
- Do not join prompt/answer rows to source URLs without a documented common key.
- Site-declared Brand Truth supports consistency checks, not independent legal
  or factual verification.
- Dejan shows access configuration, not actual bot visits.
- Never persist credentials in config, DuckDB, manifests, evidence or logs.

## Completion

Success is only `ANALYSIS_COMPLETE` or `ANALYSIS_COMPLETE_WITH_GAPS` under
`analysis-package.schema.json`. Source-level absence cannot produce the latter.
On success, show the package path, run ID, hashes, source coverage, factor count,
evidence range and limitations; do not score or render it.
