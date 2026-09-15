---
name: seo-geo-report-generator
description: >
  Validate a completed GEO analysis package, apply the frozen deterministic
  129-factor scoring and priority policy, and generate the dedicated German GEO
  audit report in DOCX and PDF with a red-only summary and complete factor table.
user-invocable: true
disable-model-invocation: true
argument-hint: "[clients/<domain>/<date>/geo/output/analysis-package.json]"
license: MIT
metadata:
  version: "0.1.0"
  category: geo-audit
  release-stage: contracts
---

# SEO GEO Report Generator

## Purpose

Turn one completed, contract-valid GEO analysis package into deterministic
scored outputs and a dedicated GEO report. This skill evaluates and renders; it
does not collect data or perform new analysis.

## Invocation boundary

- Run only after the user explicitly invokes `/seo-geo-report-generator`.
- Never invoke it automatically from `seo-geo-audit`.
- Read only the supplied analysis package and `.claude/geo-audit/contracts/`.
- Do not call Screaming Frog, SISTRIX or another MCP/API; do not open Ahrefs,
  Dejan, GSC, MHTML, crawl HTML, DuckDB or arbitrary notes to fill a gap.
- Do not use the generic SEO scoring skill or generic report orchestration.

## Load first

Read and validate:

1. `.claude/geo-audit/contracts/README.md`
2. `.claude/geo-audit/contracts/analysis-package.schema.json`
3. `.claude/geo-audit/contracts/factor-catalog.yaml`
4. `.claude/geo-audit/contracts/scoring-matrix.yaml`
5. `.claude/geo-audit/contracts/report-contract.yaml`
6. `.claude/geo-audit/contracts/report-package.schema.json`
7. this skill's `README.md`, the human-readable policy rendering

Run `.claude/geo-audit/scripts/validate_contracts.py`. If it is absent or does
not return PASS, stop. Then run the skill-local analysis-package validator. If
version, fingerprint, hashes, source count, factor inventory, evidence or
completion gate fails, stop with repair actions; never infer a replacement.

## Deterministic scoring order

1. Evaluate factor applicability and no-data state.
2. Apply the exact status conditions from policy `1.0.0`.
3. Apply coverage and confidence conditions.
4. Calculate Betroffenheit from the declared numerator/denominator.
5. Apply base priority, Betroffenheit, confirmed criticality, veto floors and
   factor/evidence/scope/confidence ceilings in the frozen order.
6. Deduplicate recommendations by root cause without deleting individual factor
   rows or evidence traces.
7. Apply each block roll-up and the overall roll-up without numeric averaging.
8. Emit a byte-stable normalized scored-factor model before rendering.

No model judgment may modify a threshold, status, priority, ceiling, veto,
dependency, roll-up or order. Effort never raises issue importance.

## Report contract

Default language is German. Generate both landscape-A4 DOCX and PDF.

The first part, `Zusammenfassung`, contains only red factors, sorted by the
frozen priority policy. Each row contains block, factor ID, formulation, why it
matters, what is wrong and why red, Handlungsempfehlung and evidence IDs.

The second part, `Gesamtbericht`, contains all 129 factors exactly once. Each row
contains block, factor ID, status, priority, confidence, formulation,
Betroffenheit/coverage, importance and rating rationale, recommendation when
required, and evidence IDs.

ND and NA are explicit states, not negative findings. Green never means
unmeasured. Report Lighthouse results as `Lighthouse lab`. Do not claim a full
prompt denominator, citation correctness/absorption, bot visits, external Brand
Truth verification, causality or business impact.

## Completion

Write a report package conforming to `report-package.schema.json`, run content
checks, render DOCX/PDF, render pages for visual inspection and pass visual QA.
Only then report both output paths, policy fingerprint and validation result.
