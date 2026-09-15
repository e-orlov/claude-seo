# GEO Audit Workbench

This directory is the temporary, version-controlled source of truth for the
design and implementation of the dedicated GEO audit skills:

- `seo-geo-audit`
- `seo-geo-report-generator`

## Canonical working documents

| Document | Purpose | Current revision |
|---|---|---:|
| `GEO_SKILLS_DETAILED_IMPLEMENTATION_PLAN.md` | Architecture, contracts, data flow, evidence model, scoring handoff, tests and Definition of Done | 1.2 |
| `GEO_audit_sources_and_factor_matrix_FINAL.md` | Closed registry of 18 required data sources and 129 auditable GEO factors | 1.2 |

## Working rules

1. Commit every materially agreed architecture or policy change before skill
   implementation proceeds from it.
2. Preserve factor IDs, source codes and policy versions so findings remain
   traceable across revisions.
3. Recalculate crawl-derived URL memberships, cluster sizes, numerators and
   denominators for every audit run. Only confirmed semantic labels and
   business criticality mappings may be reused at project level.
4. Do not store client exports, credentials, API responses, crawl HTML or other
   audit inputs in this repository.
5. The two documents above remain authoritative until their rules are migrated
   into executable contracts, skill references and tests.

## Cleanup rule

After both GEO skills pass their Definition of Done, move any still-useful
material into the final skill documentation and remove this workbench in a
separate cleanup commit. Git history remains the audit trail; the temporary
directory must not remain as a competing source of truth.
