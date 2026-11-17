# Claude Code — Global Operating Rules

## File Size Guideline

This file loads in full every session, in every project. Keep it to global operating policy — mechanics that apply everywhere (DuckDB, Humanizer). Project-specific reference material (field taxonomies, schemas, header signatures) belongs in that project's skills, not here and not in per-project CLAUDE.md — skills load lazily, CLAUDE.md files do not. Per-project CLAUDE.md should stay under ~300–400 lines for the same reason.

## DuckDB Data Staging (MCP: duckdb)

Whenever tabular or structured data enters the session — whether uploaded by the user (CSV, XLSX, JSON, Parquet) or fetched via any MCP tool (seospider, pandas-server, APIs, etc.) — **write it into DuckDB first before doing any analysis**.

DB path: `%USERPROFILE%\duckdb-data\main.duckdb` (as configured for the `duckdb` MCP server on this machine — adjust if configured elsewhere)

### Rule: stage before you analyze

1. **Identify the data source** — file path, MCP tool result, or inline payload.
2. **Load into a named table** via the `duckdb` MCP server:
   - Files: `CREATE OR REPLACE TABLE <name> AS SELECT * FROM read_csv_auto(...)` / `read_xlsx(...)` / `read_json_auto(...)` / `read_parquet(...)`
   - MCP result sets (JSON/records): write to a temp file first, then load with `read_json_auto`
   - Excel: `INSTALL excel; LOAD excel;` then `read_xlsx(...)`
3. **Name tables descriptively** — use the filename stem or the MCP tool + entity, e.g. `crawl_pages`, `sales_2024`, `orders_raw`.
4. **Confirm the load** — run `SELECT count(*), * FROM <name> LIMIT 3` and show the user the shape (row count, column names).
5. **All subsequent analysis** (aggregations, filters, joins, exports) runs as SQL against DuckDB — not in-memory Python or ad-hoc string manipulation.

### When this applies

| Trigger | Action |
|---|---|
| User uploads or references a file (CSV, XLSX, JSON, Parquet, TSV) | Stage into DuckDB immediately |
| MCP tool returns a list/table of records (seospider export, API response) | Stage into DuckDB before analysis |
| User pastes tabular data inline | Write to a temp file → load via DuckDB |
| User asks to "analyze", "explore", "compare", or "query" data | Ensure it is already staged; if not, stage first |

### When this does NOT apply

- Single scalar values or short key-value responses (no table structure)
- Code files, logs without tabular structure, free-form text
- Data that is only being previewed/passed through without analysis

### Do not ask — just stage

Do not ask "should I load this into DuckDB?" — stage it automatically whenever the rule above triggers.
After staging, briefly confirm: table name, row count, columns — then proceed with the analysis.

---

## Humanizer Skill (mandatory for all written output)

The `/humanizer` skill (`~/.claude/skills/humanizer/SKILL.md`) MUST be applied to **every written task** — regardless of language (German, English, or any other). This includes:

- Emails, messages, social media posts
- Articles, blog posts, reports, summaries
- Marketing copy, product descriptions
- Cover letters, proposals, documentation
- Any other text intended for human readers

**How to apply:**
1. Complete the writing task as normal.
2. Before delivering the final output, run it through the humanizer skill automatically — no need for the user to ask.
3. The humanizer's draft → audit → final loop applies in full.
4. Deliver only the final humanized version (plus the change summary the skill produces).

**Do not ask** "should I humanize this?" — apply it automatically to every written task.
