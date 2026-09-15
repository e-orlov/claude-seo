# SEO Audit Skills for Claude Code

This package contains a project-level `CLAUDE.md` and a modular
`.claude/skills/` structure for SEO audits. The established shared audit runs in
mixed mode with Screaming Frog plus file exports. The separately invoked GEO
workflow has its own closed source contract and additionally uses SISTRIX MCP.

## Core Design

The established shared framework runs in **mixed mode**, not purely file-based:

- **Screaming Frog** — crawl/technical data, either via a live connection to Screaming Frog's own built-in MCP server (`seospider`, port 11435 — the one sanctioned live source) or via uploaded exports. When the GSC, Analytics or PageSpeed Insights APIs are connected within Screaming Frog itself, that connector-enriched data (GSC, GA4, PSI/CrUX fields) rides along on the same crawl — live or exported, same as the rest of the crawl.
- **Ahrefs** — backlink data via uploaded file exports
- **Semrush AI Visibility** — GEO / AI-visibility data via uploaded `.mhtml` exports
- **Standalone GSC / GA4 / WebPageTest / Lighthouse / HAR exports** — via uploaded file exports, when not already pulled in through a Screaming Frog connector above

Infrastructure, not audit data sources: DuckDB MCP for staging/querying tabular data, Qdrant MCP for persistent memory and the SEO background-knowledge base.

chrome-devtools MCP is available but not part of the standard audit pipeline — the user invokes it explicitly for a specific one-off task (e.g. a live rendering/layout check), and its output only becomes audit evidence if the user asks for that.

The shared workflow assumes:
- no OAuth
- no Google / Ahrefs / Sistrix / Moz / DataForSEO API calls
- no hidden automation
- data basis is exactly the mixed set above — not arbitrary live lookups

The explicit `/seo-geo-audit` workflow is a narrow exception: it uses
Screaming Frog MCP, OAuth-managed SISTRIX MCP and the mandatory uploaded files
in `.claude/geo-audit/contracts/source-catalog.yaml`. That catalog is the closed
and authoritative source list for the dedicated workflow.

## Included Files

```text
CLAUDE.md

.claude/skills/
  seo-file-audit-orchestrator/
    SKILL.md

  seo-data-foundation/
    SKILL.md

  seo-url-clustering/
    SKILL.md

  seo-geo-audit/
    SKILL.md
    references/
    scripts/

  seo-geo-report-generator/
    SKILL.md
    README.md

  seo-helpful-content-audit/
    SKILL.md
    references/

  seo-technical-file-diagnosis/
    SKILL.md

  seo-content-file-diagnosis/
    SKILL.md

  seo-backlink-file-diagnosis/
    SKILL.md

  seo-geo-file-diagnosis/
    SKILL.md

  seo-performance-file-diagnosis/
    SKILL.md

  seo-scoring-recommendations/
    SKILL.md

  seo-report-generator/
    SKILL.md
    report_renderer.py
    docx_helpers.py
    report_config.py

  redirect-map-builder/
    SKILL.md
```

## Recommended Project Structure

```text
seo-analysis-framework/
  CLAUDE.md
  .claude/
    skills/
      ...
  clients/
    example.com/
      2026-05-technical-audit/
        input/
        work/
        output/
```

## Main Workflow

1. Upload exports into an analysis folder (or connect Screaming Frog's MCP server for live crawl data).
2. Ask Claude Code to use the SEO audit framework.
3. The framework first inventories files.
4. It maps fields, checks data quality and normalizes URLs.
5. It joins sources only when join coverage is sufficient.
6. It computes metrics only when data supports them.
7. It produces diagnoses, scores and recommendations.
8. It separates SEO health from audit coverage.

## Standalone Helpful Content Audit

`/seo-helpful-content-audit` audits one URL, an explicit URL list, or every
eligible page in a domain crawl against Google's helpful, reliable,
people-first content guidance and the Search Quality Rater Guidelines. It uses
Screaming Frog MCP data and stored rendered HTML as its only site evidence,
infers each page's focus and user task automatically, and adds a
purpose-dependent content-recency assessment based on observed date and temporal
signals. Seer's 2026 AI-citation study is used only as empirical context, not as
a pass/fail benchmark or prediction. The skill keeps its independent working
data, evidence, assessments and findings in skill-local DuckDB tables.
The skill ends after its SQL completion gate with a validated `run_id`; CSV and
NDJSON snapshots are produced only when explicitly requested.

This skill is independent of the main audit workflow. It does not invoke or
write to the data-foundation, clustering, diagnosis, scoring or orchestration
contracts. It does not generate reports or invoke `seo-report-generator`.
Report generation is a separate task started manually by the user.

## Standalone GEO Audit

`/seo-geo-audit` and `/seo-geo-report-generator` are an independent two-skill
workflow for 18 mandatory sources and 129 canonical GEO factors. The analytical
skill owns preflight, collection, URL clustering, measurements, evidence and
recommendation candidates. The report skill later applies the frozen
deterministic traffic-light/priority policy and renders the dedicated report;
it cannot read primary sources or improvise scoring.

Current feature-branch implementation status is recorded in
`methodology/geo-audit-workbench/BACKLOG.md`. Gate B remains open until harmless
production reads from the connected Screaming Frog and SISTRIX MCP servers
validate their actual callable names and response schemas.

## Key Rule

Missing data is not a negative SEO finding.

Missing data affects:
- coverage
- confidence
- non-computable metrics

Observed defects affect:
- health score
- priority
- recommendations
