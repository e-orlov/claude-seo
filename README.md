# SEO Audit Skills for Claude Code

This package contains a project-level `CLAUDE.md` and a modular `.claude/skills/` structure for SEO audits, run in mixed mode (one sanctioned live connection plus file-based exports).

## Core Design

This framework runs in **mixed mode**, not purely file-based:

- **Screaming Frog** — crawl/technical data, either via a live connection to Screaming Frog's own built-in MCP server (`seospider`, port 11435 — the one sanctioned live source) or via uploaded exports
- **Ahrefs** — backlink data via uploaded file exports
- **Semrush AI Visibility** — GEO / AI-visibility data via uploaded `.mhtml` exports
- **GSC / GA4 / WebPageTest / Lighthouse / HAR** — via uploaded file exports, as before

Infrastructure, not audit data sources: DuckDB MCP for staging/querying tabular data, Qdrant MCP for persistent memory and the SEO background-knowledge base.

chrome-devtools MCP is available but not part of the standard audit pipeline — the user invokes it explicitly for a specific one-off task (e.g. a live rendering/layout check), and its output only becomes audit evidence if the user asks for that.

It assumes:
- no OAuth
- no Google / Ahrefs / Sistrix / Moz / DataForSEO API calls
- no hidden automation
- data basis is exactly the mixed set above — not arbitrary live lookups

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
