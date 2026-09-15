# GEO preflight rules

## Closed gate

Every run must emit one check, in canonical order, for each of these source
codes:

`SF`, `RAW`, `REN`, `PSI`, `GSC-SA`, `GSC-UI`, `GSC-GAI`, `AH-BL`,
`AH-RD`, `AH-BB`, `SX-M`, `SX-O`, `SX-C`, `SX-P`, `SX-PC`, `SX-S`,
`SX-SENT`, `DJ`.

The source catalog is authoritative for `required_for`, grain, freshness class
and limitations. A source-level absence is never converted to a zero, green
factor, or `ANALYSIS_COMPLETE_WITH_GAPS`.

## State decisions

| Condition | State |
|---|---|
| Required config value missing | `WAITING_FOR_CONFIG` |
| Mandatory file missing/malformed/stale, or a required file scope is not proven | `WAITING_FOR_INPUTS` |
| MCP access/authentication/schema/scope is not proven by a real response capture | `BLOCKED` |
| Every source-level gate passes and no record gap exists | `READY` |
| Every source-level gate passes and only documented record-level gaps remain | `READY_WITH_GAPS` |
| A checkpointed source hash changes | `BLOCKED`; create a new run revision |
| Unexpected technical failure | `FAILED`; preserve the prior checkpoint |

`READY_WITH_GAPS` is not a waiver for a missing export, missing MCP response,
wrong domain/country, malformed schema, or an unconfirmed empty result.

## Source-level PASS

PASS requires all of the following:

1. access succeeded;
2. the response/artifact is readable and its adapter signature matches;
3. domain, country, model and crawl scope match where applicable;
4. a snapshot timestamp or date range exists;
5. extraction completed and the response/artifact hash is stable.

For `crawl_14d`, a snapshot older than 14 days is stale. For
`visibility_30d`, a snapshot older than 30 days is stale. Historical-window
data is assessed against its requested period rather than the age of its oldest
row.

The file adapter records filesystem modification time as the immutable saved
artifact snapshot when no internal export time exists. Later staging must keep
an internal date range separately if the export contains one.

## Valid empty

Zero rows are a valid result only when:

- the source exists;
- access, schema and scope pass;
- the date/snapshot is proven;
- the zero is explicitly returned by the source or attested with
  `--valid-empty` for the mapped file;
- no truncation/pagination error occurred.

An empty file, headerless file, failed request, or missing page is not a valid
empty source.

## Idempotence

- `init_run.py` resumes the newest run with the same normalized config hash.
- `preflight.py` replaces source-check/artifact projections rather than
  appending duplicate records.
- The source-set hash is frozen only after the run first reaches a ready state.
- A per-run exclusive lock prevents concurrent manifest writers.
- Any later source-set change requires `init_run.py --new-revision`.
- Completed runs are immutable.

## Required user actions

Each blocking row must name exactly what is missing: connection/authentication,
export type, current snapshot, corrected scope, corrected schema, or a new run
revision. Do not ask the user again for values already present in the normalized
config.
