---
name: seo-url-clustering
description: >
  Builds vertical (status/indexability) and horizontal (structural + semantic)
  URL clusters from a staged crawl export for any site. Vertical clustering is
  a fixed 3-way split. Horizontal clustering empirically probes URL structure
  and proposes semantic cross-variant groupings with mandatory full
  classification coverage. Works for any site — no site- or industry-specific
  vocabulary is hardcoded. Run standalone via /seo-url-clustering, typically
  after seo-data-foundation and before the diagnosis skills.
user-invokable: true
argument-hint: "[crawl-table-or-folder]"
license: MIT
metadata:
  version: "1.0.0"
  category: seo-file-audit
---

# SEO URL Clustering

## Purpose

Group the URL universe of a staged crawl into two independent, non-overlapping
cluster layers — **vertical** (technical state: status code / indexability)
and **horizontal** (structural and topical: what kind of page, what
region/language, what topic or category) — so that findings can be expressed
as "this affects cluster X (n URLs, y%)" instead of only naming individual
URLs. This is consistent with the project's existing Cluster Naming Rule
(CLAUDE.md; `seo-technical-file-diagnosis`): report tables must name clusters
by pattern, not by individual URL.

This skill is standalone and user-invocable (`/seo-url-clustering`). It is
typically run after `seo-data-foundation` (so `file_inventory` and
`schema_registry` are available) and before the diagnosis skills (so findings
can be scoped by cluster), but it is not a pipeline gate — running it is
recommended when cluster-scoped findings add value (large crawls, multiple
locales/languages, high page-type diversity), not mandatory for every audit.

Vertical clustering is a fixed, generic 3-way split and works identically for
any site. Horizontal clustering is a data-driven **methodology**, not a fixed
set of rules — every site-specific value (folder names, locale patterns,
category labels) is discovered empirically from the loaded data and confirmed
by the user, never assumed or hardcoded in this skill's own text.

## Datenbasis: DuckDB

This skill reads exclusively from tables already staged in DuckDB (Phase 0 of
`seo-file-audit-orchestrator`, or staged manually before invoking this
skill) — typically the Screaming Frog "Internal"/"Intern" HTML export.

**Step 0 of this skill: discover the base table.**

```sql
SHOW TABLES;
DESCRIBE crawl_internal;
```

Column names may be German or English depending on Screaming Frog's UI
language (e.g. `Adresse`/`Address`, `Status-Code`/`Status Code`,
`Indexierbarkeit`/`Indexability`, `Inhaltstyp`/`Content Type`). Resolve via
the same canonical-field alias mechanism defined in `seo-data-foundation`
Step 5 — do not hardcode a single language's column name anywhere in this
skill's SQL. Use these canonical names throughout this skill's prose and SQL:

| Canonical name | Typical source column |
|---|---|
| `page_url` | `Address` / `Adresse` |
| `status_code` | `Status Code` / `Status-Code` |
| `indexability` | `Indexability` / `Indexierbarkeit` |
| `content_type` | `Content Type` / `Inhaltstyp` |

Value strings can also be localized (e.g. `Indexable` vs. `Indexierbar`) —
resolve at the value level too, not only at the column-name level.

## Core Rules

- All clustering in this skill (vertical and horizontal) is scoped to HTML
  documents only. Filter to `content_type` indicating `text/html` (or
  equivalent) before building any cluster. Non-HTML rows (images, CSS, JS,
  PDF, other assets) are excluded from both cluster layers entirely — they do
  not get a "not applicable" cluster row, they are out of scope.
- Every in-scope URL receives exactly one vertical cluster label and exactly
  one horizontal structural cluster label. No URL may be silently dropped.
- Every slug/segment considered for semantic grouping (Step 5) must reach an
  explicit `classification_status`. Never use a silent catch-all bucket (no
  unlabeled "Sonstige"/"Other"/"Misc" dump). Genuinely ambiguous items get the
  explicit status `unclassified_needs_review`, not a vague default group.
- Semantic group names must be consistent across every structural layer or
  sub-cluster in which the same slug appears. This is a mandatory, named
  check (Step 6) — not an implicit side effect of Step 5.
- Iterate the semantic grouping proposal (Step 5) until 0 items remain in
  `unclassified_needs_review`, or every remaining item has been individually
  reviewed and confirmed as a genuine, irreducible edge case with a stated
  reason. Do not stop iterating just because most items are classified.
- Do not hardcode site-specific vocabulary, folder names, or language lists
  anywhere in this skill's own text. Every site-specific value is discovered
  at runtime from the loaded data and documented in this skill's output
  artifacts.
- `url_type` values (Step 4) must be `confirmed` by the user before being
  used in the final output. An unconfirmed pattern is reported under its raw
  segment value (e.g. `segment_value = "pd"`), never under an invented
  business label (e.g. "Produktseite") that the user has not confirmed.
- Table names proposed in Step 7 are conventions, not mandatory names,
  matching the project-wide rule in CLAUDE.md's Data Staging Rule — the
  actual name used is recorded in `file_inventory`.
- Do not load the full per-URL cluster table into context as a "summary".
  Export small aggregated tables per dimension instead (Output section).

## Status Taxonomy

Two skill-local typed status fields, additional to (not replacing) Families
A–F defined in `seo-data-foundation`.

### `classification_status`

Describes the semantic-grouping outcome (Step 5) for a single slug/segment
value.

| Value | Meaning |
|---|---|
| `classified` | Assigned to a canonical group with a stated basis (cross-locale coincidence, lexical match, content-signal corroboration, or link co-occurrence) |
| `classified_low_confidence` | Assigned to a canonical group, but the basis is weak (e.g. a single-locale slug with no cross-language corroboration) — retained and visible, not hidden, but flagged |
| `unclassified_needs_review` | No canonical group could be assigned after iteration; requires analyst input |
| `not_applicable` | The segment carries no semantic content (e.g. numeric ID, UUID, pagination token) — excluded from semantic grouping by design, not by omission |

### `pattern_confirmation_status`

Describes the confirmation state of a proposed dominant folder/pattern (Step 4).

| Value | Meaning |
|---|---|
| `proposed` | Pattern detected empirically by this skill; not yet confirmed |
| `confirmed` | User/analyst confirmed the pattern's real-world meaning |
| `rejected` | User/analyst reviewed and rejected the pattern as noise, not a real structural type |

## Step 1: Scope to HTML and Discover the Base Table

1. Identify the crawl table from `file_inventory` (field `duckdb_table`) or
   via `SHOW TABLES` if `seo-data-foundation` was not run.
2. Filter to HTML-only using the canonical `content_type` signal. If no
   explicit content-type field is available, document the fallback used
   (e.g. inferring from URL/file-extension patterns) and flag reduced
   confidence for the whole clustering output.
3. Report the resulting HTML-in-scope row count. This is the fixed baseline
   for every percentage this skill reports (state it explicitly, per
   CLAUDE.md's baseline rule — do not mix baselines across sections).

## Step 2: Vertical Cluster (fixed, generic — do not modify per site)

This step is identical for every site. It is a 3-way split on status code and
indexability:

```sql
CASE
  WHEN status_code = 200 AND indexability = 'Indexable' THEN '200_indexable'
  WHEN status_code = 200 AND indexability != 'Indexable' THEN '200_non_indexable'
  ELSE 'non_200'
END AS vertical_cluster
```

Resolve the `indexability`-value ("indexable") through the canonical value
mapping so localized values (`Indexable`/`Indexierbar`) resolve identically.
Use whatever localized cluster labels fit the audit's working language for
display, but keep the 3-way logic itself unchanged.

Output: one row per in-scope URL with `vertical_cluster`, plus a 3-row
aggregate table (count and percentage per cluster, baseline stated).

## Step 3: Structural Segment Probing (generalized — no fixed segment positions)

This step replaces any fixed assumption such as "region is always segment 1,
locale is always segment 2." Every position is discovered empirically:

1. **Depth distribution.** Split each in-scope URL's path on `/` and count
   segments. Group by segment count to learn the dominant depth(s) for this
   site. Do not assume a fixed depth across all URLs.
2. **Per-position cardinality profile.** For each segment position up to the
   dominant depth, compute the distinct-value count and value-length/pattern
   profile at that position. Low-cardinality, fixed-vocabulary positions are
   candidate region/section markers; high-cardinality positions are candidate
   slug/entity positions.
3. **Locale detection.** Test every early segment position (not only
   position 2) for a locale-like pattern (e.g. `xx_YY`, `xx-YY`, or a bare
   two-letter code). Record which position, if any, matches, and at what
   match rate across all in-scope URLs. If no position matches above a
   stated threshold (e.g. 80%), conclude the site has no locale-prefix
   structure and do not force one — set `locale_detected = false`.
4. **Derive language/country.** Only for an empirically confirmed locale
   segment: derive `language` and `country_code` by splitting on the
   separator character. Otherwise leave both `null`.
5. **Document the structural map.** Record the discovered depth and
   per-position role (e.g. "segment 1 = locale, 87% match; segment 2 =
   section, 12 distinct values; segment 3+ = slug, high cardinality") as a
   site-specific output artifact — this map is a *result* of this step, not
   logic built into the skill.

## Step 4: Dominant Folder / Pattern Detection

This step replaces any hardcoded folder-name list with an empirical
detect-then-confirm workflow:

1. At the segment position(s) identified in Step 3 as low/medium
   cardinality "section" markers, run `GROUP BY` / `COUNT` to find which
   values cover a large share of the HTML-in-scope population.
2. Flag any value covering at least a stated materiality threshold (e.g. 2%
   of in-scope URLs, or the top-N by volume) as a candidate dominant
   pattern with `pattern_confirmation_status = proposed`.
3. Present the candidate list to the user with volume and example URLs per
   candidate, and ask what each candidate structurally represents (e.g.
   "is this folder a product-detail pattern, a content/editorial pattern,
   a support/FAQ pattern, something else?").
4. Once confirmed, assign `url_type` using the confirmed labels. Anything
   not covered by a confirmed dominant pattern falls into a residual group —
   name that residual group descriptively from the data too (e.g.
   "content_campaign" for an e-commerce site, "editorial" for a news site,
   "docs" for a SaaS site); it is a confirmed default label, not a built-in
   constant.
5. Do not ship a fixed enum of `url_type` values in this skill's own text.
   This skill defines the procedure for arriving at labels, not the labels
   themselves — a prior client's confirmed labels belong to that client, not
   to this skill.

## Step 5: Semantic Cross-Variant Grouping (optional refinement of Steps 3–4)

This step is a **downstream, optional refinement** of the raw slug values
already produced by Steps 3–4 — it does not replace path-splitting, it groups
its output further when doing so adds value. Raw path-splitting alone cannot
know that `ring`, `bague`, and `anillo` mean the same thing; this step adds
the signal needed to make that connection, and only runs where it is
justified.

1. **Scope.** Apply this step only to structural sub-clusters (from Steps
   3–4) whose slug cardinality is above a stated threshold (e.g. more than
   30 distinct slugs at the entity-position segment). Below the threshold,
   the raw slug values from Step 3–4 stand as-is; grouping them further
   would not add value.
2. **Collect.** Extract the full distinct list of slug/segment values within
   each in-scope sub-cluster, with occurrence counts and — if available —
   the associated locale/language per occurrence.
3. **Propose candidate groups**, trying each signal in this priority order
   and using whichever signals the data actually supports (document which
   were used and which were unavailable):
   - **a. Cross-locale coincidence** — if the same conceptual page exists
     under multiple locale segments (from Step 3), slugs occupying the same
     structural position across locales for an otherwise identical URL
     shape are treated as translation evidence for the same canonical
     group. This is the strongest signal when the site is multilingual —
     it is the general form of "the same product category appears under a
     different word per language," and it works for any industry, not only
     e-commerce.
   - **b. Lexical/pattern similarity within one language** — shared stem,
     shared substring, or edit-distance proximity — used when cross-locale
     alignment is unavailable or insufficient (monolingual sites, or slugs
     with no cross-locale counterpart).
   - **c. Content-signal corroboration** — page title, H1, breadcrumb, or
     structured-data type/name fields already staged for URLs that share a
     slug or structural position. Use only already-staged canonical fields;
     never fetch anything live.
   - **d. Internal-linking co-occurrence** — if inlink/outlink export tables
     are staged, URLs frequently linked from the same hub page are treated
     as candidates for the same category.
   - Do not hardcode vocabulary for any specific industry. On a
     non-multilingual, non-e-commerce site (SaaS docs, blogs, marketplaces),
     signal (a) will simply be unavailable — the procedure falls through to
     (b), (c), and (d) instead. State explicitly in the output which
     signal(s) were actually usable for this site.
4. **Assign and iterate to zero leftover.** Assign each slug a canonical
   group and a `classification_status`. Re-run the proposal step, refining
   candidate groups, until `unclassified_needs_review` reaches 0 — or every
   remaining item has been individually reviewed and retained as a
   documented edge case with a stated reason. Never leave a leftover item in
   a silent default bucket.
5. **Track provenance.** For every assigned group, record which signal (a–d)
   justified the assignment, so a reviewer can audit why two slugs were
   merged into one group.

## Step 6: Cross-Structural-Layer Consistency Check (named, mandatory)

A standalone checkpoint, not folded into Step 5: if the same slug value
appears under more than one structural pattern from Step 4 (e.g. the same
word appears both as a landing-page folder and as a product-category slug),
its assigned canonical group must be identical in both places.

1. After Step 5 completes for all in-scope sub-clusters, build a lookup that
   maps every slug value to the list of canonical groups assigned to it
   across every structural layer in which it appears.
2. Flag every slug value that appears in more than one structural layer.
3. For each flagged slug, verify all its occurrences share the same
   canonical group name. If they do not, this is a consistency violation:
   resolve it using Step 5's signal priority order (a > b > c > d) — keep
   the assignment backed by the stronger signal, overwrite the weaker one,
   then re-run this check.
4. Report the outcome as an explicit artifact: count of cross-layer slugs
   checked, count consistent, count corrected, count still unresolved. The
   unresolved count must be 0 at hand-off, or each remaining case must be
   explicitly flagged as `unclassified_needs_review` with a stated reason —
   never left as a silent mismatch.

## Step 7: Cluster Assembly and Materialization

Combine the vertical, horizontal-structural, and horizontal-semantic layers
and materialize into DuckDB. Proposed table names (convention, not mandatory
— record the actual name used in `file_inventory`):

| Table | Grain | Key fields |
|---|---|---|
| `url_clusters_vertical` | one row per in-scope URL | `page_url`, `vertical_cluster` |
| `url_clusters_horizontal` | one row per in-scope URL | `page_url`, discovered structural fields from Step 3 (`locale_segment`, `language`, `country_code`, `section_segment`, `entity_segment`), `url_type`, `pattern_confirmation_status` |
| `url_clusters_semantic_group_map` | one row per distinct slug value (not per URL) | `slug_value`, `structural_layers_seen_in`, `canonical_group`, `classification_status`, `assignment_signal`, `notes` |
| `url_clusters_full` | one row per in-scope URL (optional, derived) | join of the three tables above, for reporting convenience |

## Output

```markdown
# URL Clustering Summary

## Scope and Baseline
## Vertical Cluster Distribution
## Structural Map (discovered segment roles)
## Dominant Pattern Candidates (proposed / confirmed / rejected)
## url_type Distribution
## Semantic Group Summary (per structural sub-cluster)
## Cross-Layer Consistency Check Result
## Unclassified / Needs Review Items
## Artifact Table Names Used
```

Export small aggregated CSVs per dimension (vertical distribution, `url_type`
distribution, semantic group sizes) — never re-export the full per-URL
table as the "summary." This matches the project's context-budget
discipline: load better context, not more context.

## Handoff to Diagnosis Skills

Diagnosis skills may join their findings against `url_clusters_vertical` /
`url_clusters_horizontal` on `page_url` to express affected scope by cluster
name (pattern-level, per the existing Cluster Naming Rule) instead of by
individual URL, and to feed the Cross-Area Priority Matrix's "Affected
Scope" dimension more precisely than a raw percentage alone. If this skill
has not been run for a given audit, diagnosis skills fall back to ad hoc
URL-pattern naming as today — this skill is recommended, not a hard gate.

## Basis für erweiterte Cluster mit weiteren Datenquellen

The tables materialized in Step 7 are deliberately built as a **stable
foundation**, not an end product. Once further sources are staged (GSC, GA4,
Ahrefs, WebPageTest/Lighthouse), their metrics can be joined onto the
existing cluster tables via `page_url` — without re-running the clustering
logic (Steps 1–6). Examples:

- `url_clusters_horizontal` ⋈ `gsc_pages` on `page_url` → aggregate clicks /
  impressions per `url_type` / `canonical_group` (e.g. "which product
  category group drives the most clicks despite a high non-indexable rate").
- `url_clusters_semantic_group_map` ⋈ `ahrefs_backlinks` via the join key
  from `join_key_report` → backlink equity per semantic group instead of per
  individual URL.
- `url_clusters_vertical` ⋈ `ga4_landing_pages` → sessions/conversions per
  vertical cluster (e.g. traffic share landing on `non_200` URLs as a sign
  of misconfigured internal links).

These joins are not performed by this skill itself — this skill only
guarantees that its output tables are stably named and joinable on
`page_url`, so diagnosis skills and later ad hoc analyses can build on them
instead of recomputing cluster assignment for every new question.
