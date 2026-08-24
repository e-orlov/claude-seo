# File-Based SEO Audit Skills for Claude Code

This package contains a project-level `CLAUDE.md` and a modular `.claude/skills/` structure for file-based SEO audits.

## Core Design

This framework is intentionally different from URL/API/MCP-based SEO skill packages.

It assumes:
- no live crawling
- no APIs
- no OAuth
- no MCPs
- no DataForSEO / Ahrefs API / Google API calls
- no hidden automation
- uploaded files are the only data basis

## Included Files

```text
CLAUDE.md

.claude/skills/
  seo-file-audit-orchestrator/
    SKILL.md

  seo-data-foundation/
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

1. Upload exports into an analysis folder.
2. Ask Claude Code to use the file-based SEO audit framework.
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
