# Gate A Closeout — GEO Contracts

Status: **PASS**  
Closed: **2026-09-15**  
Contract version: **1.0.0**

## Frozen identifiers

| Artifact | Count/version | Fingerprint |
|---|---:|---|
| Source catalog | 18 required sources | `sha256:401f387b1d525cd6711d9e3578f3bfd491d22e9ec29a9735f0ba39748499e0ca` |
| Factor catalog | 129 factors | `sha256:3ac10563160965636731a9cb46e96c303b3c707a058e8cb0858b1f5fbfaf1e5a` |
| Scoring policy | 1.0.0 | `sha256:77da1451409845f6ba53d97f90071c92a4b26cc248f8d6b2bbc5634aaebe89ed` |
| DuckDB DDL | 41 tables | schema version `1.0.0` |

Factor distribution remains `T24 / B26 / C27 / S20 / O15 / M17`.

## Implemented contracts

- `source-catalog.yaml`: exact source transport, grain, scope, preflight,
  freshness, limitations, required factors and valid-empty behavior.
- `factor-catalog.yaml`: exact factor definition, sources, method ID, metrics,
  applicability, universe, coverage, evidence requirements, dependency chain and
  scoring-policy reference.
- byte-exact runtime copy of the frozen scoring policy and schema.
- `audit-config.schema.json`, `analysis-package.schema.json` and
  `report-package.schema.json`.
- `report-contract.yaml`, including a red-only summary and all-129 full report.
- versioned `duckdb-schema.sql` for run management, all source layers,
  clustering, factor metrics, evidence, findings and recommendations.
- compact, explicit-only entrypoints for exactly `seo-geo-audit` and
  `seo-geo-report-generator`.
- human-readable scoring policy at the report skill README.
- project operating-policy exception scoped only to the dedicated GEO workflow:
  Screaming Frog MCP, SISTRIX MCP and catalogued files; no Semrush in this flow.

## Validation evidence

Run from repository root:

```bash
python3 methodology/geo-audit-workbench/scripts/build_stage1_contracts.py
python3 .claude/geo-audit/scripts/validate_contracts.py
python3 -m unittest discover -s .claude/geo-audit/tests -v
```

Current result:

- all five JSON Schema documents parse and their supported vocabulary and local
  references validate;
- valid config, analysis-package and report-package fixtures pass;
- catalogs and policy cross-resolve without missing, duplicate, unknown or
  cyclic IDs;
- policy and report README match version, fingerprint and all 129 IDs;
- both skills enforce Claude Code's explicit invocation fields;
- all 41 expected DDL tables are present and the portable SQL syntax executes;
- all 11 negative mutations are rejected after their own catalog/package hashes
  are recalculated, so rejection is not merely stale-fingerprint detection;
- three regression tests pass, including two consecutive byte-identical builds.

## Deliberate boundary

The current container has no DuckDB binary or Python module. The DDL therefore
passes a SQLite execution check over the intentionally portable DDL subset, but
this is not represented as native DuckDB execution. A real DuckDB apply and
transaction test remains mandatory in Stage 3 before Gate C.

The bundled `skill-creator` quick validator targets Codex skill frontmatter and
rejects Claude Code-only keys. It is not used to weaken the required Claude
frontmatter: `user-invocable`, `disable-model-invocation` and `argument-hint`
remain present and are checked by the GEO contract validator.

Exact Screaming Frog and SISTRIX callable names and response shapes remain
unknown until harmless reads against the user's connected MCP servers. They are
intentionally Stage 2 integration evidence, not guessed Stage 1 contracts.

## Next step

Proceed with `GEO-200` through `GEO-205`: state machine, real MCP probes, SISTRIX
cost plan, mandatory-file inventory, secure parsers and readiness gate.

## Primary references

- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [DuckDB CREATE TABLE](https://duckdb.org/docs/stable/sql/statements/create_table)
- [DuckDB transactions](https://duckdb.org/docs/stable/sql/statements/transactions)
