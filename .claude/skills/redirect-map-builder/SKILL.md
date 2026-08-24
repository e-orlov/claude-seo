---
name: redirect-map-builder
description: >
  Builds, validates and finalises a redirect map for a domain migration or URL restructuring.
  Fetches source and target URL inventories via Screaming Frog MCP, creates two independent
  redirect maps (rule-based and semantic), compares them, merges the best matches into a final
  map, and exports a validated CSV ready for implementation.
user-invokable: true
argument-hint: "[source-domain] [target-domain] [date-slug]"
license: MIT
metadata:
  version: "1.0.0"
  category: redirect-map
---

# Redirect Map Builder

## Purpose

Produce a validated, implementation-ready redirect map for a domain migration or URL restructuring.

The skill covers:
- Source and target URL inventory via Screaming Frog MCP
- Rule-based redirect map (Tier-Logik)
- Semantic redirect map (Jaccard similarity)
- Cross-map comparison and divergence analysis
- Error pattern identification (false positives, wrong clusters, wrong tiers)
- Correction table with justified replacements
- Merge into final map with applied corrections
- Consistency checks across URL families
- Final CSV export

## Operating Constraints

This skill uses **Screaming Frog MCP** as the only live data source.
No other live APIs, crawlers, OAuth connections or browser tools are used.

All intermediate data is staged in DuckDB before analysis.
All exports are written to `clients/<domain>/<date_slug>/work/`.

---

## Phase 0 — Session Setup

### 0.1 Parameters

Collect from user or infer from context:

| Parameter | Description | Example |
|---|---|---|
| `source_domain` | Domain being migrated away from | `www.bitcoin.de` |
| `target_domain` | Domain being migrated to | `www.qal.bitcoin.de` |
| `date_slug` | Audit folder date slug | `2026-06` |
| `client_slug` | Folder name under clients/ | `bitcoin.de` |

Work directory: `clients/<client_slug>/<date_slug>/work/`

### 0.2 DuckDB Session

Use session_id `redirect-map` throughout.
DB: the path configured for the `duckdb` MCP server on this machine (see global `CLAUDE.md`)

Before any query, check for stale tables from other clients:

```sql
SELECT DISTINCT regexp_extract(source_url, 'https?://([^/]+)', 1) AS host
FROM <table>
LIMIT 5;
```

If the host does not match the current `source_domain`, drop and reload the table.

---

## Phase 1 — URL Inventory

### 1.1 Source URL List

Fetch all crawled URLs from `source_domain` via Screaming Frog MCP:

```
sf_export_seo_element_urls(
  seo_element_name = "URL",
  filter_name      = "All",
  data_fields      = ["Address", "Status Code", "Indexability", "Content Type"]
)
```

Save MCP output to: `clients/<client_slug>/<date_slug>/work/sf_source_urls.ndjson`

Load into DuckDB:

```sql
CREATE OR REPLACE TABLE btc_de_url_entities AS
SELECT * FROM read_json_auto('...sf_source_urls.ndjson');
```

Confirm: row count, column names, host distribution.

Keep only HTML pages with status 200, unless the task explicitly requires mapping redirect chains or non-200 URLs.

### 1.2 Target URL List

Fetch all crawled URLs from `target_domain` via Screaming Frog MCP (same export params).

Save to: `clients/<client_slug>/<date_slug>/work/sf_target_urls.ndjson`

Load into DuckDB:

```sql
CREATE OR REPLACE TABLE qal_url_entities AS
SELECT * FROM read_json_auto('...sf_target_urls.ndjson');
```

Confirm: row count, column names, host distribution.

### 1.3 Inventory Summary

Report:
- Source URL count (total / HTML-200 / other)
- Target URL count (total / HTML-200)
- Overlap: source URLs that already exist on target (exact match after host swap)
- Unique source URLs requiring a mapped redirect

---

## Phase 2 — Rule-Based Redirect Map (v1)

### 2.1 Tier Schema

Assign each source URL exactly one tier. Tiers are evaluated top-down; the first matching tier wins.

| Tier | Name | Description |
|---|---|---|
| `tier_0_external` | External | Source URL points to an external domain — no redirect needed |
| `tier_1_entity` | Exact entity match | Direct slug/path match exists on target domain |
| `tier_2_faq_crossref` | FAQ cross-reference | FAQ URL matched to thematically equivalent target page by FAQ ID or topic |
| `tier_2_cluster_match` | Cluster match | Source path matched to a target path cluster by structural pattern |
| `tier_3_cluster_root` | Cluster root | No specific match; redirect to the parent topic cluster root |
| `tier_4_homepage` | Homepage fallback | No cluster match; redirect to domain root |

### 2.2 Tier Logic

**Tier 0 — External**
Source URL host ≠ source_domain → assign `tier_0_external`, target = original URL, no further processing.

**Tier 1 — Exact Entity Match**
Attempt direct path translation: replace `source_domain` with `target_domain` in the URL.
Check if the resulting URL exists in `qal_url_entities`.
Match: assign `tier_1_entity`.

For multilingual sites: also attempt language-path translation (e.g. `/de/` ↔ `/en/`, `/presse` ↔ `/press`).

**Tier 2 — FAQ Cross-Reference**
For FAQ URLs (pattern: `/faq/<slug>/<id>.html`):
- Extract FAQ ID and slug tokens.
- Look up a manually curated or automatically derived FAQ→topic mapping table.
- Map to the thematically most relevant target page.
- Assign `tier_2_faq_crossref`.

Hard rule: `features/registrierungsprozess` (or equivalent registration/onboarding path) is only valid for source URLs that are genuinely about the registration or login flow. It must not be used as a generic fallback for any FAQ URL.

FAQ URLs with no thematic match: assign `tier_2_cluster_match` to `wissen/hilfezentrum` (DE) or `knowledge/help-desk` (EN) initially; these will be revised in the correction phase.

**Tier 2 — Cluster Match**
For non-FAQ, non-entity URLs:
- Extract the primary path segment (e.g. `/de/chart/`, `/de/btceur/`, `/de/api/`).
- Match to a target cluster via a keyword-to-cluster mapping table.
- Assign `tier_2_cluster_match`.

**Tier 3 — Cluster Root**
No specific cluster match found.
Redirect to the closest parent topic root on target (e.g. `/de/kryptowaehrung`, `/de/wissen`).
Assign `tier_3_cluster_root`.

**Tier 4 — Homepage Fallback**
No cluster root available.
Redirect to target domain root.
Assign `tier_4_homepage`.

### 2.3 Output

```sql
CREATE OR REPLACE TABLE btc_de_redirect_map_v2 AS
SELECT
    source_url,
    redirect_target,
    redirect_tier
FROM ...
ORDER BY source_url;
```

Export: `clients/<client_slug>/<date_slug>/work/redirect_map_v1.csv`

---

## Phase 3 — Semantic Redirect Map (v2)

### 3.1 Method: Jaccard Token Similarity

For each source URL, compute Jaccard similarity against all target URLs using URL path tokens.

Tokenisation:
- Extract path segments from both source and target URL.
- Split on `/`, `-`, `_`.
- Lowercase all tokens.
- Remove stop tokens: language codes (`de`, `en`), structural tokens (`faq`, `wissen`, `knowledge`, `features`, `kryptowaehrung`, `cryptocurrency`), and high-frequency trade tokens (`bitcoin`, `buy`, `sell`, `how`, `what`, `does`, `work`, `can`, `the`, `is`, `i`, `a`, `my`).

Stop token rationale: high-frequency tokens inflate Jaccard scores and cause false positives — e.g. `wann-bitcoin-kaufen` matching FAQ URLs about trading because `bitcoin` and `kaufen` appear in both.

Jaccard formula:
```
jaccard(A, B) = |tokens(A) ∩ tokens(B)| / |tokens(A) ∪ tokens(B)|
```

For each source URL, assign the target URL with the highest Jaccard score as the match.
Minimum threshold: Jaccard ≥ 0.15. Below threshold: fall back to cluster root (same logic as tier_3 in v1).

Tier assignment:
- Jaccard match uses tier name `tier_2_semantic`.
- Cluster root fallback from semantic uses `tier_3_cluster_root`.

### 3.2 Implementation Notes

Run as a DuckDB SQL script using token extraction via `string_split`, `regexp_replace`, `unnest` and set-intersection logic, or as an external Python/Node.js script called from the work directory.

The script reads from `btc_de_url_entities` and `qal_url_entities` in DuckDB and writes results back.

### 3.3 Output

```sql
CREATE OR REPLACE TABLE btc_de_redirect_map02_v2 AS
SELECT
    source_url,
    redirect_target,
    redirect_tier
FROM ...
ORDER BY source_url;
```

Export: `clients/<client_slug>/<date_slug>/work/redirect_map_v2.csv`

---

## Phase 4 — Cross-Map Comparison

### 4.1 Divergence Analysis

Join v1 and v2 on `source_url`. Find all rows where `redirect_target` differs:

```sql
SELECT
    v1.source_url,
    v1.redirect_target AS v1_target,
    v1.redirect_tier   AS v1_tier,
    v2.redirect_target AS v2_target,
    v2.redirect_tier   AS v2_tier
FROM btc_de_redirect_map_v2 v1
JOIN btc_de_redirect_map02_v2 v2 USING (source_url)
WHERE v1.redirect_target <> v2.redirect_target
ORDER BY v1.source_url;
```

Report: number of divergences, tier distribution of diverging rows, top divergence patterns.

### 4.2 Error Pattern Identification

For each diverging group, classify the error type:

| Error Type | Description |
|---|---|
| `jaccard_false_positive` | Semantic map matched on a high-frequency stop token instead of the actual topic |
| `wrong_cluster` | Rule-based map assigned a structurally plausible but thematically wrong cluster |
| `wrong_tier` | Correct topic but wrong specificity (e.g. cluster root instead of entity page) |
| `faq_crossref_wrong_topic` | FAQ cross-reference map chose a registration/onboarding page for a non-registration FAQ |
| `faq_generic_fallback` | FAQ was routed to hilfezentrum/help-desk instead of a topic-specific page |
| `coin_family_inconsistency` | Same coin's URL variants (market, trade, outgoing/fee, chart) route to different targets |
| `language_crossref_error` | DE and EN variants of the same URL point to different targets without valid reason |

Document each error group with:
- affected URL pattern
- incorrect current target
- correct target
- justification

### 4.3 Coin-Family Consistency Check

For all non-FAQ source URLs, extract the coin segment:

```sql
SELECT
    regexp_extract(source_url, 'source_domain/(de|en)/([a-z0-9]+)(?:eur)?/', 2) AS coin_segment,
    redirect_target,
    COUNT(*) AS url_count
FROM redirect_map_final
WHERE source_url NOT LIKE '%/faq/%'
  AND source_url NOT LIKE '%/chart/%'
GROUP BY coin_segment, redirect_target
ORDER BY coin_segment, url_count DESC;
```

Flag any `coin_segment` that routes to more than one distinct `redirect_target`.
Each coin family must be consistent: all URL variants of the same coin go to the same target page.

---

## Phase 5 — Correction Table

### 5.1 Format

Create `redirect_corrections.csv` with:

| Column | Description |
|---|---|
| `Map` | Which map version the correction applies to: `v1`, `v2`, or `both` |
| `Source URL` | Full source URL |
| `Aktuelles Ziel (falsch)` | Current (incorrect) redirect target |
| `Korrektes Ziel` | Correct redirect target |
| `Begründung` | One-sentence justification in German |

### 5.2 Correction Rules

- A correction is required whenever the current target is thematically wrong, regardless of which map produced it.
- Corrections sourced from v1-only analysis apply only to v1.
- Corrections sourced from divergence analysis apply to whichever map has the wrong target.
- If both maps are wrong but in different ways, create one correction row per map.
- If both maps agree on a wrong target, the correction applies to both.

### 5.3 Loading into DuckDB

```sql
CREATE OR REPLACE TABLE redirect_corrections AS
SELECT * FROM read_csv_auto('...redirect_corrections.csv', header=true);
```

Filter to v2-relevant corrections:

```sql
CREATE OR REPLACE TABLE final_corrections AS
SELECT source_url, "Korrektes Ziel" AS correct_target
FROM redirect_corrections
WHERE Map IN ('v2', 'both');
```

---

## Phase 6 — Final Map

### 6.1 Merge Strategy

Base: v2 (semantic map).
Apply corrections via LEFT JOIN:

```sql
CREATE OR REPLACE TABLE redirect_map_final AS
SELECT
    v2.source_url,
    COALESCE(c.correct_target, v2.redirect_target) AS redirect_target,
    CASE
        WHEN c.correct_target IS NOT NULL THEN v2.redirect_tier || '_corrected'
        ELSE v2.redirect_tier
    END AS redirect_tier
FROM btc_de_redirect_map02_v2 v2
LEFT JOIN final_corrections c ON v2.source_url = c.source_url
ORDER BY v2.source_url;
```

Rationale for v2 as base: the semantic map covers cases the rule-based map misses, and its errors are more systematic (therefore easier to correct en masse). The rule-based map is used as a reference and error-detection source, not as the base.

### 6.2 Post-Merge Consistency Checks

After all corrections are applied, run the following checks before export:

**Check A — Coin-family consistency**
Every URL variant of the same coin (`outgoing/fee`, `market`, `trade/neueste-transaktionen`, `chart`) must point to the same target. Flag any coin with divergent targets.

**Check B — Language pair consistency**
For every DE URL, its EN counterpart should point to the EN equivalent of the same target page (path structure preserved, language segment swapped). Flag language pairs where the target path diverges unexpectedly.

**Check C — FAQ `wissen`/`knowledge` fallback**
All FAQ URLs with no thematically specific target must point to `wissen` (DE) or `knowledge` (EN) — not to `hilfezentrum`/`help-desk` (these are help-centre pages, not topic hubs). Apply en masse:

```sql
UPDATE redirect_map_final
SET redirect_target = CASE
        WHEN source_url LIKE '%/en/%' THEN 'https://<target_domain>/en/knowledge'
        ELSE 'https://<target_domain>/de/wissen'
    END,
    redirect_tier = 'tier_3_cluster_root_corrected'
WHERE source_url LIKE '%/faq/%'
  AND redirect_target IN (
      'https://<target_domain>/de/wissen/hilfezentrum',
      'https://<target_domain>/en/knowledge/help-desk'
  );
```

**Check D — Target URL existence**
Every `redirect_target` in the final map must exist in `qal_url_entities`. Flag any target not in the inventory:

```sql
SELECT f.redirect_target, COUNT(*) AS anzahl
FROM redirect_map_final f
LEFT JOIN qal_url_entities q ON f.redirect_target = q.url
WHERE q.url IS NULL
GROUP BY f.redirect_target
ORDER BY anzahl DESC;
```

For each missing target, either correct to the nearest available page or escalate to the client.

**Check E — No source = target**
No source URL should redirect to its own URL (identity redirect):

```sql
SELECT source_url FROM redirect_map_final
WHERE replace(source_url, '<source_domain>', '<target_domain>') = redirect_target;
```

### 6.3 Tier Distribution Report

Before export, report the final tier distribution:

```sql
SELECT redirect_tier, COUNT(*) AS anzahl
FROM redirect_map_final
GROUP BY redirect_tier
ORDER BY anzahl DESC;
```

Corrected tiers use the `_corrected` suffix. This documents the scope of manual intervention transparently.

### 6.4 Export

```sql
COPY (
    SELECT source_url, redirect_target, redirect_tier
    FROM redirect_map_final
    ORDER BY source_url
) TO 'clients/<client_slug>/<date_slug>/work/redirect_map_final.csv'
(HEADER, DELIMITER ',');
```

---

## Phase 7 — Validation

### 7.1 Coverage Validation

| Metric | Expected |
|---|---|
| Total source URLs mapped | = source URL inventory count |
| Tier-0 (external) | ≥ 0; review if unexpectedly high |
| Tier-1 entity matches | document share |
| Tier-2 semantic / crossref / cluster | document share |
| Tier-3 cluster root | acceptable as fallback; high share indicates missing entity targets |
| Tier-4 homepage | should be 0 or near-0; any homepage fallback is a quality defect |
| `_corrected` tiers | document total count and share |

### 7.2 Quality Gates

The final map passes quality gates when:

- [ ] 0 source URLs mapped to non-existent target pages
- [ ] 0 identity redirects (source = target after host swap)
- [ ] 0 tier-4 homepage fallbacks (or explicitly justified)
- [ ] All coin families are internally consistent
- [ ] All DE/EN language pairs are consistent
- [ ] No FAQ URL points to `hilfezentrum`/`help-desk`
- [ ] `features/registrierungsprozess` (or equivalent) used only for registration/login-flow URLs

### 7.3 Open Items Log

If any issues cannot be resolved without client input (e.g. no target page exists for a coin), document them in:
`clients/<client_slug>/<date_slug>/work/redirect_open_items.md`

Format:
```
| Source URL pattern | Current target | Issue | Recommended action |
```

---

## Deliverables

| File | Description |
|---|---|
| `redirect_map_v1.csv` | Rule-based map |
| `redirect_map_v2.csv` | Semantic map |
| `redirect_corrections.csv` | Correction table with justifications |
| `redirect_map_final.csv` | Final merged map, implementation-ready |
| `redirect_open_items.md` | Unresolved cases requiring client decision (if any) |

All files in `clients/<client_slug>/<date_slug>/work/`.

---

## DuckDB Table Reference

| Table | Source |
|---|---|
| `btc_de_url_entities` | Source domain URL inventory (column: `url`) |
| `qal_url_entities` | Target domain URL inventory (column: `url`) |
| `btc_de_redirect_map_v2` | Rule-based map |
| `btc_de_redirect_map02_v2` | Semantic map |
| `redirect_corrections` | Correction table loaded from CSV |
| `final_corrections` | v2-relevant corrections only |
| `redirect_map_final` | Working final map |

Table names follow the `<client_slug>_<entity>` convention. Adapt for each client.

---

## Error Pattern Reference

Quick lookup for the most common errors encountered in practice:

| Pattern | Root Cause | Fix |
|---|---|---|
| FAQ → `registrierungsprozess` for non-registration topic | Rule over-fires on verbs like `start`, `begin`, `account` in FAQ slug | Re-route to topic-specific page |
| FAQ → `wissen/hilfezentrum` | No FAQ→topic mapping entry; rule falls back to help-centre | Apply Phase 6.2 Check C en masse, then fix specific cases |
| Semantic → `wann-bitcoin-kaufen` for unrelated FAQ | Jaccard false positive on `bitcoin` + `kaufen` stop tokens | Remove these tokens from Jaccard tokenisation; correct affected rows |
| `outgoing/fee` → `gebuehren` instead of coin page | Rule assigns fee URLs to fee cluster; misses entity tier | Route to coin entity page (same as `market`/`trade` siblings) |
| Coin → cluster root (`kryptowaehrung`) instead of coin page | No entity match found; fell back to cluster root | Check if coin page exists on target; route to it |
| `api/<coin>` → coin entity page | Jaccard matches coin name in API path; `api/` paths have no SEO content | Route `api/` URLs to `wissen` or `features` topic hub |
| DE → different target than EN variant | v1/v2 maps processed language variants independently | Enforce language pair consistency check in Phase 6.2 Check B |
