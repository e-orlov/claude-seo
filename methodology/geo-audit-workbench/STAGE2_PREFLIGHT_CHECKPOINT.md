# Stage 2 Checkpoint — GEO Preflight and Source Adapters

Status: **IMPLEMENTED; GATE B NOT YET PASSED**  
Recorded: **2026-09-15**  
Reason Gate B remains open: production Screaming Frog and SISTRIX MCP tools are
not connected in the implementation environment, so their real callable names
and response schemas have not yet been captured.

## Implemented scope

| Backlog item | Result |
|---|---|
| `GEO-200` | Resumable/idempotent state machine, normalized config, exact missing-field output, atomic hashed manifest, revision-on-source-change policy |
| `GEO-201` | Response-anchored Screaming Frog probe package and verifier implemented; production live capture pending |
| `GEO-202` | SISTRIX six-endpoint probe verifier and lower/expected/upper request/credit estimator implemented; production live capture pending |
| `GEO-203` | Explicit and signature-based discovery, SHA-256, byte size, schema fingerprint, row count, scope, snapshot and freshness |
| `GEO-204` | ZIP traversal/resource guards, MIME MHTML transfer decoding, multilingual table signatures, no MHTML remote loading |
| `GEO-205` | Closed 18-source checklist, valid-empty proof, blocker actions and `READY_WITH_GAPS` restriction |

## Runtime artifacts

- `.claude/geo-audit/contracts/run-manifest.schema.json`
- `.claude/geo-audit/contracts/mcp-probe.schema.json`
- `.claude/skills/seo-geo-audit/scripts/init_run.py`
- `.claude/skills/seo-geo-audit/scripts/inspect_mcp_probe.py`
- `.claude/skills/seo-geo-audit/scripts/estimate_sistrix_cost.py`
- `.claude/skills/seo-geo-audit/scripts/preflight.py`
- `.claude/skills/seo-geo-audit/scripts/extract_zip.py`
- `.claude/skills/seo-geo-audit/scripts/parse_mhtml.py`
- `.claude/skills/seo-geo-audit/scripts/inspect_file.py`
- `.claude/skills/seo-geo-audit/scripts/source_adapters.py`
- `.claude/skills/seo-geo-audit/scripts/preflight_common.py`

## Reproducible validation

~~~bash
python3 .claude/geo-audit/scripts/validate_contracts.py
python3 -m unittest discover -s .claude/geo-audit/tests -p 'test_preflight_runtime.py' -v
~~~

Expected evidence at this checkpoint:

- contracts: `18` sources, `129` factors, `2` runtime schemas;
- runtime tests: `15` passed (`18` including contract tests);
- repeated init resumes the same run;
- identical probe input produces a byte-identical verified package;
- source change after readiness blocks and requests a new revision;
- incomplete preflight does not freeze a partial source set;
- malicious ZIP traversal is rejected;
- MHTML is decoded as MIME and reports `remote_resources_loaded=false`;
- English/German/Russian header signatures and stored Dejan HTML are covered;
- unconfirmed zero rows are blocking; explicitly proven valid-empty is accepted;
- unknown SISTRIX request upper bounds remain null; MCP credit bounds are exactly
  zero under the current official MCP policy.

## Gate B live integration checklist

Run this only in Claude with the actual project connections:

1. Invoke the new analytical skill explicitly.
2. Capture harmless live responses for all six Screaming Frog source codes.
3. Capture `ai.models`, minimal `ai.check.overview`, and bounded schema reads for
   the four remaining SISTRIX endpoints.
4. Save exact callable names, non-secret parameters, response artifacts and
   response-shape fingerprints through `inspect_mcp_probe.py`.
5. Confirm the configured model subset, domain, country, crawl timestamp, HTML
   universe and RAW/REN/PSI/GSC availability.
6. Run the full preflight with the mandatory files and confirm all 18 checks.
7. Repeat it once and verify no duplicate artifacts or changed hashes.

Gate B may be marked PASS only after those production captures succeed. Test
fixtures or documentation examples cannot satisfy this checklist.

## Official implementation references

- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Screaming Frog MCP server](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/#mcp-server)
- [SISTRIX MCP technical information](https://www.sistrix.com/api/connection-to-chatbot-ai/technical-information-mcp/)
- [SISTRIX API limitations](https://www.sistrix.com/api/limitations/)
