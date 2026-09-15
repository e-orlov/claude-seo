# GEO Audit Contracts

Contract version: `1.0.0`  
Scoring policy version: `1.0.0`  
Scoring policy fingerprint: `sha256:77da1451409845f6ba53d97f90071c92a4b26cc248f8d6b2bbc5634aaebe89ed`

These files are the standalone interface between `seo-geo-audit` and
`seo-geo-report-generator`. Runtime code must not depend on
`methodology/geo-audit-workbench/`.

## Authoritative files

| File | Role |
|---|---|
| `source-catalog.yaml` | Closed registry of 18 mandatory sources and preflight boundaries |
| `factor-catalog.yaml` | Closed registry of 129 factors and their analysis/evidence contracts |
| `scoring-matrix.yaml` | Frozen executable status, confidence, priority and roll-up policy |
| `scoring-rule.schema.json` | Schema for the scoring policy |
| `audit-config.schema.json` | User/project configuration contract |
| `analysis-package.schema.json` | Only permitted analytical handoff to the report skill |
| `report-package.schema.json` | Deterministically scored report/output contract |
| `report-contract.yaml` | Required report sections, wording and blocking invariants |
| `duckdb-schema.sql` | Versioned analytical database DDL |
| `run-manifest.schema.json` | Resumable run state, source checklist and immutable checkpoints |
| `mcp-probe.schema.json` | Response-anchored Screaming Frog/SISTRIX live-probe package |

## Versioning and compatibility

- Patch: clarification that changes neither accepted values nor interpretation.
- Minor: backward-compatible optional field or table addition.
- Major: changed required field, status semantics, grain, key, denominator,
  source set, factor set or incompatible table change.
- A package is accepted only when its declared catalog and policy versions and
  fingerprints match the locally installed contracts exactly.
- Readers may support older major versions only through an explicit, tested
  migration. There is no implicit best-effort parsing.
- Database migrations are additive and transactional. Never edit a completed
  audit database in place: copy it, record the source hash, migrate the copy,
  increment the run revision and append a migration event.
- Policy changes follow their own immutable semantic version and regression
  suite; a catalog version bump cannot silently alter scoring.

## Source-level gate

All 18 source codes are required. Missing access, authentication, artifact,
schema, scope, or successful extraction blocks a complete audit. A zero-row
artifact is present only after those gates and a snapshot/date range are proven;
the factor-specific zero-denominator rule then decides ND, NA, or green.

## Runtime boundary

The analytical skill may read primary sources and write the analysis package.
The report skill reads that validated package and frozen contracts only. It must
not call MCPs, open uploaded source files, query DuckDB for new analysis, or
invent a missing metric, evidence item, recommendation, status, or priority.
