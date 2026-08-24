# Redirect Map Analysis — Standardprozedur

Erstellt auf Basis der qal.bitcoin.de-Analyse (2026-06).  
Anwendungsfall: Eine Domain wird auf eine andere weitergeleitet. Für die Zieldomain
muss eine vollständige URL-Entitäts-Karte erstellt werden, die als Grundlage für
die Redirect-Zuweisung dient.

---

## Parameter

| Variable | Bedeutung | Beispiel |
|---|---|---|
| `{DOMAIN}` | Zu analysierende Domain | `qal.bitcoin.de` |
| `{DATE_SLUG}` | Audit-Datum (YYYY-MM) | `2026-06` |
| `{WORK_DIR}` | Ausgabepfad | `clients/{DOMAIN}/{DATE_SLUG}/work/` |
| `{MCP_DIR}` | SF-MCP-Exportpfad | `C:/Users/Evgeniy/seo_spider_mcp_server/` |
| `{LANG_PREFIXES}` | Sprachpräfixe in URLs | `/de/`, `/en/` |
| `{CLUSTER_MAP}` | Cluster-Normalisierung | siehe Phase 3 |

---

## Phase 1 — Daten aus Screaming Frog MCP holen

Voraussetzung: SF MCP ist offen, Crawl der Zieldomain ist geladen.

### 1.1 Self-Referencing Canonicals exportieren

```
sf_export_seo_element_urls(
  seo_element_name = "Canonicals",
  filter_name      = "Self Referencing",
  file_path        = "{MCP_DIR}{DOMAIN}_self_ref_canonicals.ndjson"
)
```

Erwartete Felder: `Adresse`, `Canonical-Linkelement 1`, `Indexierbarkeit`, `Meta Robots 1`

### 1.2 Metadaten exportieren (alle crawled URLs)

```
sf_export_seo_element_urls(seo_element_name="Seitentitel",      filter_name="All", file_path="{MCP_DIR}{DOMAIN}_titles.ndjson")
sf_export_seo_element_urls(seo_element_name="Meta Description", filter_name="All", file_path="{MCP_DIR}{DOMAIN}_meta_desc.ndjson")
sf_export_seo_element_urls(seo_element_name="H1",               filter_name="All", file_path="{MCP_DIR}{DOMAIN}_h1.ndjson")
sf_export_seo_element_urls(seo_element_name="H2",               filter_name="All", file_path="{MCP_DIR}{DOMAIN}_h2.ndjson")
```

### 1.3 In DuckDB laden

Jede Datei einzeln, da DuckDB Multi-Statement-Batches nur die erste Anweisung ausführt.

```sql
CREATE OR REPLACE TABLE {PREFIX}_self_ref_canonicals AS
  SELECT * FROM read_json_auto('{MCP_DIR}{DOMAIN}_self_ref_canonicals.ndjson');

CREATE OR REPLACE TABLE {PREFIX}_titles AS
  SELECT * FROM read_json_auto('{MCP_DIR}{DOMAIN}_titles.ndjson');

CREATE OR REPLACE TABLE {PREFIX}_meta_desc AS
  SELECT * FROM read_json_auto('{MCP_DIR}{DOMAIN}_meta_desc.ndjson');

CREATE OR REPLACE TABLE {PREFIX}_h1 AS
  SELECT * FROM read_json_auto('{MCP_DIR}{DOMAIN}_h1.ndjson');

CREATE OR REPLACE TABLE {PREFIX}_h2 AS
  SELECT * FROM read_json_auto('{MCP_DIR}{DOMAIN}_h2.ndjson');
```

**Bestätigung:** Für jede Tabelle `SELECT count(*) FROM {PREFIX}_self_ref_canonicals` ausgeben.  
Zielwert für Self-Referencing Canonicals: muss mit der SF-UI-Zahl übereinstimmen.

---

## Phase 2 — Basis-Join und URL-Analyse

### 2.1 Basis-Join auf Self-Referencing Canonical URLs

```sql
CREATE OR REPLACE TABLE {PREFIX}_redirect_map_base AS
SELECT
  c."Adresse"                         AS url,
  t."Titel 1"                         AS title,
  t."Länge von Titel 1"               AS title_len,
  d."Meta Description 1"              AS meta_description,
  d."Länge von Meta Description 1"    AS meta_desc_len,
  h1."H1-1"                           AS h1,
  length(h1."H1-1")                   AS h1_len,
  h2."H2-1"                           AS h2
FROM {PREFIX}_self_ref_canonicals c
LEFT JOIN {PREFIX}_titles    t  ON t."Adresse"  = c."Adresse"
LEFT JOIN {PREFIX}_meta_desc d  ON d."Adresse"  = c."Adresse"
LEFT JOIN {PREFIX}_h1        h1 ON h1."Adresse" = c."Adresse"
LEFT JOIN {PREFIX}_h2        h2 ON h2."Adresse" = c."Adresse";
```

### 2.2 Sprachslug bestimmen

Logik: URL-Pfad auf Sprachpräfix prüfen.  
Sonderfälle: Root-URLs wie `/de` oder `/en` (kein Subpfad nach Präfix) separat behandeln.

```sql
CREATE OR REPLACE TABLE {PREFIX}_redirect_map_analysis AS
SELECT *,
  CASE
    WHEN url LIKE '%/en/%' OR regexp_matches(url, '/en$') THEN 'en'
    WHEN url LIKE '%/de/%' OR regexp_matches(url, '/de$') THEN 'de'
    ELSE 'unknown'
  END AS lang,
  -- URL-Pfadsegmente für Cluster/Subcuster/Entity
  regexp_replace(url, '^https?://[^/]+', '')         AS path,
  split_part(regexp_replace(url, '^https?://[^/]+(/[a-z]{2}/)?' , ''), '/', 1) AS seg1,
  split_part(regexp_replace(url, '^https?://[^/]+(/[a-z]{2}/)?' , ''), '/', 2) AS seg2
FROM {PREFIX}_redirect_map_base;
```

**Prüfung:** `SELECT lang, count(*) FROM {PREFIX}_redirect_map_analysis GROUP BY lang`  
Ergebnis darf kein `unknown` für reguläre Seiten enthalten. Root-Sprach-URLs ggf. per UPDATE korrigieren:

```sql
UPDATE {PREFIX}_redirect_map_analysis
SET lang = 'en' WHERE url ~ '/en$';

UPDATE {PREFIX}_redirect_map_analysis
SET lang = 'de' WHERE url ~ '/de$';
```

---

## Phase 3 — Cluster-Normalisierung

### 3.1 Cluster-Map definieren

Anhand der Pfadsegmente URLs in inhaltliche Cluster einteilen.  
**Immer EN- und DE-Varianten desselben Clusters auf einen gemeinsamen Bezeichner normalisieren.**

Schablone — Werte an die konkrete Domain anpassen:

```sql
ALTER TABLE {PREFIX}_redirect_map_analysis ADD COLUMN cluster VARCHAR;
ALTER TABLE {PREFIX}_redirect_map_analysis ADD COLUMN sub_cluster VARCHAR;
ALTER TABLE {PREFIX}_redirect_map_analysis ADD COLUMN entity_slug VARCHAR;

UPDATE {PREFIX}_redirect_map_analysis SET
  cluster = CASE seg1
    WHEN '{DE_CLUSTER_1}' THEN '{NORMALIZED_CLUSTER_1}'
    WHEN '{EN_CLUSTER_1}' THEN '{NORMALIZED_CLUSTER_1}'
    WHEN '{DE_CLUSTER_2}' THEN '{NORMALIZED_CLUSTER_2}'
    WHEN '{EN_CLUSTER_2}' THEN '{NORMALIZED_CLUSTER_2}'
    -- ...
    ELSE 'other'
  END,
  sub_cluster = NULLIF(seg2, ''),
  entity_slug = NULLIF(seg2, '');
```

**Beispiel qal.bitcoin.de:**
```sql
CASE seg1
  WHEN 'knowledge'      THEN 'knowledge/wissen'
  WHEN 'wissen'         THEN 'knowledge/wissen'
  WHEN 'cryptocurrency' THEN 'cryptocurrency/kryptowaehrung'
  WHEN 'kryptowaehrung' THEN 'cryptocurrency/kryptowaehrung'
  WHEN 'features'       THEN 'features'
  WHEN 'news'           THEN 'news/nachrichten'
  WHEN 'nachrichten'    THEN 'news/nachrichten'
  ELSE 'legal/other'
END
```

---

## Phase 4 — Entity-Extraktion aus URL-Slugs

### 4.1 Slug-Token-Zerlegung

```sql
CREATE OR REPLACE TABLE {PREFIX}_slug_tokens AS
WITH tokens AS (
  SELECT
    url, lang, cluster, sub_cluster, entity_slug,
    unnest(string_split(lower(entity_slug), '-')) AS token
  FROM {PREFIX}_redirect_map_analysis
  WHERE entity_slug IS NOT NULL
),
labeled AS (
  SELECT url, lang, cluster, sub_cluster, entity_slug, token,
    CASE
      -- Coins
      WHEN token IN ('bitcoin','btc')             THEN 'Bitcoin'
      WHEN token IN ('ethereum','eth')             THEN 'Ethereum'
      WHEN token IN ('xrp','ripple')               THEN 'XRP'
      WHEN token IN ('solana','sol')               THEN 'Solana'
      WHEN token IN ('cardano','ada')              THEN 'Cardano'
      WHEN token IN ('litecoin','ltc')             THEN 'Litecoin'
      WHEN token IN ('dogecoin','doge')            THEN 'Dogecoin'
      WHEN token IN ('bnb','binance')              THEN 'BNB'
      WHEN token IN ('altcoin','altcoins')         THEN 'Altcoin'
      -- Konzepte
      WHEN token IN ('mining')                    THEN 'Mining'
      WHEN token IN ('halving')                   THEN 'Halving'
      WHEN token IN ('staking','stake')           THEN 'Staking'
      WHEN token IN ('defi')                      THEN 'DeFi'
      WHEN token IN ('nft','nfts')                THEN 'NFT'
      WHEN token IN ('blockchain')                THEN 'Blockchain'
      WHEN token IN ('wallet','wallets')          THEN 'Wallet'
      WHEN token IN ('trading','trade','trader')  THEN 'Trading'
      WHEN token IN ('swap')                      THEN 'Swap'
      WHEN token IN ('liquidity','liquiditaet')   THEN 'Liquidity'
      WHEN token IN ('lightning')                 THEN 'Lightning Network'
      WHEN token IN ('dominanz','dominance')      THEN 'Bitcoin Dominance'
      WHEN token IN ('layer')                     THEN 'Layer-2'
      WHEN token IN ('etf')                       THEN 'ETF'
      WHEN token IN ('stablecoin','stablecoins')  THEN 'Stablecoin'
      WHEN token IN ('dex')                       THEN 'DEX'
      WHEN token IN ('taxes','steuern','steuer')  THEN 'Taxes'
      WHEN token IN ('validator')                 THEN 'Validator'
      WHEN token IN ('smart')                     THEN 'Smart Contract'
      WHEN token IN ('proof')                     THEN 'Consensus'
      WHEN token IN ('dapp','dapps')              THEN 'dApp'
      WHEN token IN ('mev')                       THEN 'MEV'
      WHEN token IN ('utxo')                      THEN 'UTXO'
      WHEN token IN ('bot')                       THEN 'Trading Bot'
      ELSE NULL
    END AS entity_from_slug
  FROM tokens
)
SELECT * FROM labeled WHERE entity_from_slug IS NOT NULL;
```

### 4.2 Aggregation pro URL

```sql
CREATE OR REPLACE TABLE {PREFIX}_slug_entities_agg AS
SELECT
  url,
  string_agg(DISTINCT entity_from_slug, '; ' ORDER BY entity_from_slug) AS entities_from_slug,
  count(DISTINCT entity_from_slug) AS slug_entity_count
FROM {PREFIX}_slug_tokens
GROUP BY url;
```

**Erweiterungsregel:** Neue Token, die beim konkreten Domain-Durchlauf auftauchen (z.B. branchenspezifische Begriffe), in die CASE-Liste aufnehmen und die Tabelle neu erstellen.

---

## Phase 5 — Entity-Extraktion aus Textfeldern

Zwei Muster je nach Cluster-Typ:

### 5.1 Strukturierte Seiten (z.B. Kurs-/Preisseiten)

Ticker und Coin-Name stehen in Klammern im Titel oder H1:
`"Ethereum-Kurs (ETH/EUR)"` → `ETH`  
`"Avalanche price (AVAX/EUR)"` → `AVAX`

```sql
-- Ticker aus Klammern (Title und H1)
regexp_extract(title, '\(([A-Z0-9][A-Z0-9.]+)(?:/EUR)?\)', 1) AS ticker_from_title,
regexp_extract(h1,    '\(([A-Z0-9][A-Z0-9.]+)(?:/EUR)?\)', 1) AS ticker_from_h1,

-- Coin-Name: alles vor "-Kurs (", " Kurs (", " price (" oder direkt vor "("
COALESCE(
  NULLIF(regexp_extract(title, '^(.+?)(?:-Kurs| Kurs| price| Price)\s*\(', 1), ''),
  NULLIF(trim(regexp_extract(title, '^(.+?)\s*\([A-Z0-9][A-Z0-9.]+/EUR\)', 1)), '')
) AS coin_name_from_title
```

**Abdeckung prüfen:** Alle Seiten des Clusters ohne Treffer einzeln anzeigen — es gibt immer Ausreißer im Titelformat.

### 5.2 Freitext-Seiten (Artikel, Glossar, News, Features)

Bekannte Entities per `regexp_matches` mit `\b`-Wortgrenzen suchen.  
DuckDB nutzt RE2 — `\b` wird unterstützt, Lookbehind (`(?<!`) nicht.

```sql
regexp_matches(
  title || ' ' || COALESCE(meta_description,'') || ' ' || COALESCE(h1,'') || ' ' || COALESCE(h2,''),
  '(?i)\bBitcoin\b'
) AS mentions_bitcoin,

-- Muster für Coins mit mehreren Varianten:
regexp_matches(..., '(?i)\bXRP\b|\bRipple\b')      AS mentions_xrp,
regexp_matches(..., '(?i)\bSolana\b|\bSOL\b')      AS mentions_solana,
regexp_matches(..., '(?i)BTC\.D|Bitcoin.?Dominan') AS mentions_btc_dominance,
```

**Vollständige Entity-Liste** anhand der domain-spezifischen Wissensartikel vor Implementierung prüfen:  
→ Welche Begriffe kommen in Titeln/H1 vor, die nicht im generischen Wörterbuch stehen?

### 5.3 Entity-Flags zu lesbarer Liste zusammenfassen

```sql
trim(
  CASE WHEN mentions_bitcoin   THEN 'Bitcoin; '   ELSE '' END ||
  CASE WHEN mentions_ethereum  THEN 'Ethereum; '  ELSE '' END ||
  -- alle weiteren Flags...
  '', '; '
) AS entities_in_text
```

---

## Phase 6 — Finale Tabelle zusammenführen

```sql
CREATE OR REPLACE TABLE {PREFIX}_url_entities AS
SELECT
  r.url, r.lang, r.cluster, r.sub_cluster, r.entity_slug,

  -- Ticker aus URL-Slug (Phase 3)
  r.ticker_symbol          AS ticker_from_url,

  -- Entities aus Textfeldern (Phase 5)
  r.coin_name_from_title,
  r.ticker_from_title,
  r.ticker_from_h1,

  -- [alle mentions_* Flags aus Phase 5]
  -- entities_in_text String (Phase 5.3)

  -- Entities aus Slug-Tokens (Phase 4)
  s.entities_from_slug,
  s.slug_entity_count,

  r.title, r.meta_description, r.h1, r.h2

FROM {PREFIX}_redirect_map_analysis r
LEFT JOIN {PREFIX}_slug_entities_agg s USING (url);
```

---

## Phase 7 — Export

```sql
COPY (
  SELECT
    url, lang, cluster, sub_cluster, entity_slug,
    ticker_from_url,
    coin_name_from_title, ticker_from_title, ticker_from_h1,
    entities_from_slug, slug_entity_count,
    entities_in_text,
    title, meta_description, h1, h2
  FROM {PREFIX}_url_entities
  ORDER BY cluster, lang, url
) TO '{WORK_DIR}url_entities.csv' (HEADER, DELIMITER ',');
```

---

## Qualitätschecks (nach jeder Phase)

| Check | SQL | Erwartung |
|---|---|---|
| Zeilenzahl stimmt mit SF überein | `SELECT count(*) FROM {PREFIX}_self_ref_canonicals` | = SF-UI-Wert |
| Kein `lang = unknown` für reguläre Seiten | `SELECT count(*) FROM ... WHERE lang = 'unknown'` | 0 (Root-URLs manuell korrigiert) |
| Ticker-Abdeckung im Kurs-Cluster | `SELECT count(*) FILTER (WHERE ticker_from_title IS NOT NULL)` | ≥ 99 % der Nicht-Kategorie-Seiten |
| Coin-Name nicht leer | wie oben für `coin_name_from_title` | gleich |
| Alle Cluster bekannt | `SELECT cluster, count(*) GROUP BY 1` | kein `other` für bekannte Seiten |
| Slug-Entity-Abdeckung | `SELECT count(*) FROM {PREFIX}_slug_entities_agg` | plausibel vs. Gesamtanzahl |

---

## Tabellen-Namenskonvention

Präfix `{PREFIX}` = Domain ohne Punkte, z.B. `qal_bitcoin_de` oder `bitcoin_de`.

| Tabelle | Inhalt |
|---|---|
| `{PREFIX}_self_ref_canonicals` | Rohdaten SF-Export Self-Ref |
| `{PREFIX}_titles` | Rohdaten Titles |
| `{PREFIX}_meta_desc` | Rohdaten Meta Descriptions |
| `{PREFIX}_h1` | Rohdaten H1 |
| `{PREFIX}_h2` | Rohdaten H2 |
| `{PREFIX}_redirect_map_base` | JOIN aller Felder auf Self-Ref-URLs |
| `{PREFIX}_redirect_map_analysis` | + lang, seg1, seg2, cluster, entity_slug |
| `{PREFIX}_slug_tokens` | Einzelne Slug-Tokens mit Entity-Label |
| `{PREFIX}_slug_entities_agg` | Aggregierte Slug-Entities pro URL |
| `{PREFIX}_url_entities` | Finale Tabelle mit allen Entity-Spalten |

---

## Bekannte Fallstricke

- **DuckDB Multi-Statement**: Jeden `CREATE TABLE`-Aufruf einzeln absetzen.
- **Root-Sprach-URLs** (`/de`, `/en` ohne Subpfad): LIKE-Muster schlägt an, Regex `url ~ '/de$'` nötig.
- **EN/DE-Titelformate**: DE = `"-Kurs ("`, EN = `" price ("` — beide Varianten im Regex oder COALESCE.
- **Ticker beginnen mit Ziffer**: Regex `[A-Z0-9]` statt `[A-Z]` als erstes Zeichen (z.B. `1INCH`).
- **Slug-Tokens die keine Entities sind**: `vs`, `oder`, `or`, `und`, `and` — nicht in CASE aufnehmen.
- **RE2 kein Lookbehind**: Wortgrenze mit `\b` statt `(?<![A-Za-z])`.
- **DuckDB persistent**: DB enthält Daten anderer Clients — vor Analyse Host-Spalte prüfen oder Präfix nutzen.
- **MCP-Export zuerst als Datei speichern**: Exports immer nach `{MCP_DIR}` schreiben, dann in DuckDB laden — nie direkt im Kontext verarbeiten.
