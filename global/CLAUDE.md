# Claude Code — Persistent Memory Rules

## File Size Guideline

This file loads in full every session, in every project. Keep it to global operating policy — mechanics that apply everywhere (Qdrant, DuckDB, Humanizer). Project-specific reference material (field taxonomies, schemas, header signatures) belongs in that project's skills, not here and not in per-project CLAUDE.md — skills load lazily, CLAUDE.md files do not. Per-project CLAUDE.md should stay under ~300–400 lines for the same reason.

## Qdrant Memory (MCP: qdrant-memory)

Claude Code uses Qdrant as a persistent semantic memory store via the `qdrant-memory` MCP server.
Collection: `claude_code_memory` | Path: `C:\qdrant-memory` | Embeddings: FastEmbed (all-MiniLM-L6-v2)

---

### WHEN TO SEARCH (qdrant-find)

Call `qdrant-find` at the **start of a session or task** when:
- The user mentions a project, tool, technology, or person you may have encountered before
- The task involves configuration, installation, or setup (search for prior decisions)
- The user says "as before", "like last time", "you know this", or similar
- You are about to make an architectural or tooling decision
- A file path, package name, or service name appears that might have prior context

**Search query**: use natural language that describes what you are looking for, e.g.:
- `"Python installation path Windows"`
- `"npm prefix junction workaround"`
- `"MCP server configuration Claude Desktop"`

---

### WHEN TO STORE (qdrant-store)

Call `qdrant-store` whenever you learn something that will be useful in a future session:

| What happened | Store it |
|---|---|
| Installed a tool / package | Yes — path, version, any quirks |
| Solved a non-obvious problem | Yes — problem + solution summary |
| Discovered a system-specific fact | Yes — e.g. AppData\Roaming junction behavior |
| Made an architectural decision | Yes — what was chosen and why |
| Learned a user preference | Yes — e.g. preferred tools, coding style |
| Wrote a config file | Yes — path and key settings |
| A command that failed with a specific fix | Yes |

**Do NOT store**: trivial facts, information already in official docs, one-off debug output.

### Storage format

Store entries in this format:
```
[CATEGORY] Short title

Context: <1-2 sentences of why this matters>
Detail: <the actual fact, decision, path, command, or solution>
Tags: <comma-separated keywords>
```

Categories: `INSTALL`, `CONFIG`, `FIX`, `DECISION`, `PREFERENCE`, `PATH`, `SYSTEM`

Example:
```
[FIX] AppData\Roaming is a junction in Claude Code sandbox

Context: Any directory written under AppData\Roaming from within Claude Code points to the sandbox cache, not the real filesystem. Normal CMD sessions cannot see these paths.
Detail: Always create directories outside AppData\Roaming for tools installed globally (npm prefix, uv tools, pnpm, etc.). Verify with Get-Item ... | Select-Object LinkType, Target.
Tags: windows, junction, AppData, npm, sandbox, path
```

---

### Session lifecycle

**At session start** (when the user's first message contains a project or task context):
1. Call `qdrant-find` with the topic/project name
2. If results found: summarize briefly what you already know before proceeding
3. If no results: proceed normally
4. Check for `C:\Users\Evgeniy\.claude\qdrant-pending.md` — if it exists, store all entries via `qdrant-store` and delete the file.

**During a session** — store immediately after:
- A successful installation or configuration
- A non-obvious fix or workaround is found
- A user preference or decision is expressed

**At session end** (when the user says "done", "thanks", "that's all", or ends the conversation):
1. Review what was accomplished in the session
2. Store any facts not yet stored
3. Confirm: "Saved X items to memory."

---

### Context window management

**Keep the context window under control throughout the session.**

- Long sessions with many large tool outputs (SQL results, NDJSON exports, file reads) fill the context fast.
- When context reaches ~70 % full: run `/compact` proactively with a focus instruction, e.g. `/compact preserve all analysis results, report paths, and DuckDB table names`.
- Do not wait until 100 % — at 100 % MCP tools (including qdrant-store) may become unavailable.
- Before compacting: store any new Qdrant entries that have not been saved yet.
- After compacting: verify MCP tools are still available by checking if qdrant-store responds.

**Compact Instructions** (always preserve after compaction):
- Active audit domain and date slug (e.g. sos-kartenshop.de / 2026-06)
- DuckDB table names in use for the current audit
- Report script paths under clients/<domain>/<date_slug>/work/
- Any open tasks or issues the user has not yet confirmed as resolved

---

### Do not ask — just do

Do not ask the user "should I save this to memory?" — just save it when the criteria above are met.
Do not ask "should I search memory?" — just search at session start and when context suggests prior knowledge.

---

## DuckDB Data Staging (MCP: duckdb)

Whenever tabular or structured data enters the session — whether uploaded by the user (CSV, XLSX, JSON, Parquet) or fetched via any MCP tool (seospider, pandas-server, APIs, etc.) — **write it into DuckDB first before doing any analysis**.

DB path: `C:\Users\Evgeniy\duckdb-data\main.duckdb`

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
