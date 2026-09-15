# MCP probe protocol

## Principle

Tool discovery is not evidence of access. Make a harmless live read, save the
actual response, and bind every source PASS to assertions against that saved
response. Never place OAuth tokens, API keys, authorization headers, cookies or
other credentials in the request capture.

The runtime stores exact callable names and response-shape fingerprints per
run. It does not assume that an MCP wrapper will preserve names or schemas
across versions.

## Screaming Frog

Use the live server's advertised schemas. The official server currently
documents operations such as `sf_list_crawls`, but exact availability and
arguments must be discovered at run time.

Perform bounded reads that prove:

1. matching completed crawl, crawl ID, host, timestamp and HTML URL count;
2. native Internal/HTML fields (`SF`);
3. stored original response HTML (`RAW`);
4. stored rendered DOM for the same URL (`REN`);
5. Lighthouse/PageSpeed lab fields and device context (`PSI`);
6. Search Analytics data and date range (`GSC-SA`);
7. URL Inspection fields or successful bounded inspection read (`GSC-UI`).

Discover export filters and fields before requesting them; preserve their exact
returned names. A normal source body is not rendered HTML. A rendered DOM is
not original HTML. Use the same confirmed HTML URL for the RAW/REN bounded
probe. A crawl row proves crawler state, not an AI-bot visit.

Official reference:
[Screaming Frog MCP server and tools](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/#mcp-server).

## SISTRIX

Use OAuth-managed SISTRIX MCP authentication. Run, in order:

1. `ai.models`;
2. minimal `ai.check.overview` for the configured brand/domain/country;
3. bounded schema reads for `ai.check.competitors`, `ai.check.prompts`,
   `ai.check.prompts.count` and `ai.check.sources`;
4. `estimate_sistrix_cost.py` before full pagination.

Map these endpoint semantics to source codes exactly:

| Source | Endpoint |
|---|---|
| `SX-M` | `ai.models` |
| `SX-O` | `ai.check.overview` |
| `SX-C` | `ai.check.competitors` |
| `SX-P` | `ai.check.prompts` |
| `SX-PC` | `ai.check.prompts.count` |
| `SX-S` | `ai.check.sources` |

The selected model set must be contained in the live `ai.models` result. For
`all_available`, store the exact returned model codes; do not substitute the
six historically known labels.

SISTRIX documents that MCP calls consume zero API credits. Still record the
planned number of MCP calls and preserve unknown request upper bounds as null.
For direct-API fallback, use the documented 10 credits for overview and one
credit per returned entry where documented. Never turn an unknown page/entry
count into an exact estimate. Apply at least 300 ms between calls and respect
429 retry/reset signals.

Official references:

- [SISTRIX MCP authentication and credit behavior](https://www.sistrix.com/api/connection-to-chatbot-ai/technical-information-mcp/)
- [SISTRIX API limits](https://www.sistrix.com/api/limitations/)
- [SISTRIX AI models](https://www.sistrix.com/api/ai/ai-models/)
- [AI Check overview](https://www.sistrix.com/api/ai-check/ai-check-overview/)
- [AI Check competitors](https://www.sistrix.com/api/ai-check/ai-check-competitors/)
- [AI Check prompts](https://www.sistrix.com/api/ai-check/ai-check-prompts/)
- [AI Check prompt counts](https://www.sistrix.com/api/ai-check/ai-check-prompts-count/)
- [AI Check sources](https://www.sistrix.com/api/ai-check/ai-check-sources/)

## Capture package

Save each raw MCP response as UTF-8 JSON, XML or text in the run's `probes/`
directory. Create a draft matching `mcp-probe.schema.json`, with:

- exact callable name and non-secret request parameters;
- response path;
- six canonical source results in order;
- one or more response locators/assertions per result;
- snapshot, record count, valid-empty flag and limitations;
- the SISTRIX request/credit plan for a SISTRIX package.

Run `inspect_mcp_probe.py`. It recalculates response hashes and response-shape
fingerprints, executes JSON Pointer/XML/text assertions, verifies scope/model
and endpoint mappings, and writes a hashed package. `preflight.py` accepts only
that verified package and rechecks every referenced response hash.

Every source result needs proof roles for schema, snapshot and record count.
Screaming Frog results additionally need `scope_domain`; `SX-M` needs
`scope_model`; the other SISTRIX results need `scope_domain` and
`scope_country`. Use `request_parameter` locators when an endpoint does not echo
its requested scope. A `record_count` assertion must equal the count stored in
the source result; `length_equals` is available for returned arrays/nodes.

Synthetic fixtures are for unit tests only. A client audit requires responses
created by MCP calls made during that audit run.
