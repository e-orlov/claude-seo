# Детальный план двух GEO skills

Версия: 1.6
Дата фиксации: 15 сентября 2026 года
Основа анализа: 18 первичных источников, 129 факторов, 6 блоков.
Статус реализации: Gate P0 и Gate A пройдены; Stage 2 реализован offline, Gate B
ожидает production MCP integration. Scoring policy 1.0.0 заморожена с
fingerprint `sha256:77da1451409845f6ba53d97f90071c92a4b26cc248f8d6b2bbc5634aaebe89ed`,
runtime contracts 1.0.0 проверены.

## 1. Зафиксированная архитектура

Создаются ровно два новых пользовательских skill:

1. **seo-geo-audit** — проверяет доступность данных, собирает и нормализует их в DuckDB, автоматически запускает URL-кластеризацию, анализирует все 129 факторов, создаёт evidence и кандидаты рекомендаций.
2. **seo-geo-report-generator** — принимает только завершённый analysis package, применяет версионированную оценочную матрицу, назначает статусы и приоритеты и выпускает GEO-отчёт.

Единственная skill-зависимость аналитического процесса — **seo-url-clustering**. Она вызывается автоматически после загрузки crawl-данных Screaming Frog в DuckDB. После её выполнения `seo-geo-audit` детерминированно строит из текущего URL universe иерархию path-prefix clusters и таблицу many-to-many memberships. Кластеризация и prefix expansion являются производными аналитическими слоями, а не новыми первичными источниками данных и не отдельными GEO-факторами.

Оба новых skill должны быть доступны пользователю как явные slash-команды и не запускаться моделью самопроизвольно:

~~~yaml
user-invocable: true
disable-model-invocation: true
~~~

Report skill не запускается автоматически после анализа. Между skills существует обязательный машинно проверяемый шлюз: отчёт разрешён только для run со статусом **ANALYSIS_COMPLETE** или **ANALYSIS_COMPLETE_WITH_GAPS**, прошедшего contract validation. Отдельное ручное утверждение статусов, приоритетов или оценок для каждого отчёта не требуется; пользователь лишь явно запускает report skill.

~~~mermaid
flowchart TD
    A["/seo-geo-audit"] --> B["Preflight и конфигурация"]
    B --> C["Сбор и staging в DuckDB"]
    C --> D["Автозапуск seo-url-clustering"]
    D --> D2["Path-prefix hierarchy и memberships"]
    D2 --> E["Анализ 129 факторов и evidence"]
    E --> F{"Analysis gate"}
    F -->|пройден| G["Завершённый analysis package"]
    G --> H["/seo-geo-report-generator"]
    H --> I["Scoring, traffic lights, GEO report"]
~~~

## 2. Граница ответственности

| Функция | seo-geo-audit | seo-geo-report-generator |
|---|---:|---:|
| Проверка MCP и файлов | Да | Нет |
| Запрос brand/domain/country | Да | Нет |
| Тест SISTRIX | Да | Нет |
| Оценка SISTRIX credits/requests | Да | Только показывает зафиксированную оценку |
| Сбор данных | Да | Нет |
| Запись аналитических таблиц в DuckDB | Да | Нет |
| Автозапуск URL-кластеризации | Да | Нет |
| Пересчёт path-prefix hierarchy и per-URL memberships | Да | Нет |
| Расчёт HTML parity evidence для T16, T17, S18 и связанных факторов | Да | Нет |
| Расчёт метрик 129 факторов | Да | Нет |
| Выдача evidence numbers | Да | Только валидирует и выводит |
| Формирование кандидатов рекомендаций | Да | Не создаёт новые |
| Красный/жёлтый/зелёный | Нет | Да |
| P0–P3 | Нет | Да |
| DOCX/PDF | Нет | Да |

Главное правило разделения: аналитический skill устанавливает **что наблюдается и чем это доказано**; report skill устанавливает **как это оценивается и как показывается клиенту**.

## 3. Рекомендуемая структура репозитория

Общие контракты находятся вне каталогов skills, чтобы оба skill читали одну версию истины.

~~~text
.claude/
  geo-audit/
    contracts/
      source-catalog.yaml
      factor-catalog.yaml
      scoring-matrix.yaml
      audit-config.schema.json
      analysis-package.schema.json
      report-package.schema.json
      duckdb-schema.sql
      report-contract.yaml
    fixtures/
      minimal-complete/
      over-2000-urls/
      malformed-inputs/

  skills/
    seo-geo-audit/
      SKILL.md
      scripts/
        init_run.py
        preflight.py
        inspect_sistrix.py
        estimate_sistrix_cost.py
        ingest_sources.py
        parse_mhtml.py
        normalize_urls.py
        validate_staging.py
        invoke_url_clustering.py
        build_url_prefix_hierarchy.py
        select_gsc_inspection_urls.py
        compute_html_parity_evidence.py
        analyze_factors.py
        build_evidence.py
        build_recommendations.py
        finalize_analysis.py
      references/
        preflight-rules.md
        source-adapters.md
        analysis-methods.md
        limitations.md

    seo-geo-report-generator/
      SKILL.md
      README.md
      scripts/
        validate_analysis_package.py
        apply_scoring_matrix.py
        aggregate_statuses.py
        build_report_model.py
        render_geo_report.py
        validate_report_content.py
        render_and_inspect.py
      assets/
        geo-report-style.json
        geo-report-template.docx
      references/
        scoring-rules.md
        report-sections.md
        wording-rules-de.md
~~~

Renderer и визуальные helper-функции можно вынести в общий статический модуль или переиспользовать их код. Бизнес-логика GEO, scoring и состав отчёта должны оставаться внутри нового GEO-report skill.

## 4. Каталоги источников и факторов

### 4.1 source-catalog.yaml

Каталог содержит ровно 18 согласованных первичных источников:

**SF, RAW, REN, PSI, GSC-SA, GSC-UI, GSC-GAI, AH-BL, AH-RD, AH-BB, SX-M, SX-O, SX-C, SX-P, SX-PC, SX-S, SX-SENT, DJ.**

Минимальная запись источника:

~~~yaml
source_code: SX-P
label: SISTRIX AI Check Prompts
transport: sistrix_mcp
required: true
required_for:
  - B08
  - B09
grain: one_returned_prompt_record
scope_fields:
  - brand
  - domain
  - country
  - llm_model
freshness_rule: snapshot_date_required
adapter_version: 1
limitations:
  - corpus_contains_observed_mentions_or_citations
  - no_complete_relevant_prompt_denominator
~~~

### 4.2 factor-catalog.yaml

Каталог содержит ровно 129 строк из финальной матрицы:

| Блок | Количество |
|---|---:|
| T — Technical AI Eligibility | 24 |
| B — AI Visibility, Brand Representation & Sentiment | 26 |
| C — Content, Evidence & Brand Truth | 27 |
| S — Structured Data & Entity Consistency | 20 |
| O — Offsite Authority & Source Ecosystem | 15 |
| M — Measurement & Reporting | 17 |
| **Всего** | **129** |

Обязательные поля каждой записи:

~~~yaml
factor_id: T16
block_id: T
ordinal: 16
label_de: JavaScript-Abhängigkeit
definition: Контент и элементы, отсутствующие в raw HTML и появляющиеся после JS
grain: url_and_cluster
primary_sources:
  - RAW
  - REN
  - SF
applicability_rule: html_url
analysis_method_id: html_parity_v1
metrics:
  - js_only_main_text_ratio
  - js_only_internal_links
  - metadata_changed
coverage_rule_id: crawl_html_coverage
evidence_requirements:
  minimum_examples: 1
  denominator_required: true
scoring_rule_id: T16_v1
cluster_applicable: true
limitations:
  - chromium_render_does_not_prove_rendering_by_each_ai_bot
~~~

Для каждого ID обязательны источник, метод расчёта, правило применимости, правило покрытия, evidence requirements, ограничение интерпретации и ссылка на scoring rule. Наличие 129 ID проверяется автоматическим contract test.

## 5. Вызовы skills

Рекомендуемый пользовательский интерфейс:

~~~text
/seo-geo-audit clients/example.com/2026-09/geo/config/audit.yaml

/seo-geo-report-generator clients/example.com/2026-09/geo/output/analysis-package.json
~~~

Если config отсутствует, первый skill создаёт черновик и запрашивает только отсутствующие обязательные параметры.

## 6. Audit config

Минимальный контракт конфигурации:

~~~yaml
schema_version: 1
client_id: example-com
brand: Example
domain: example.com
country: de
language: de
report_language: de

crawl:
  expected_scope: example.com
  include_subdomains: false

sistrix:
  connection_mode: mcp
  models: all_available
  country: de
  direct_api_fallback: false
  max_credit_cost: null

gsc_url_inspection:
  max_urls: 2000
  selection: cluster_stratified

clustering:
  auto_invoke: true
  build_path_prefix_hierarchy: true
  recompute_memberships_each_run: true
  require_url_type_confirmation: true
  confirmation_scope: semantic_labels_and_criticality_only
  require_zero_unresolved: true

inputs:
  ahrefs_backlinks: null
  ahrefs_refdomains: null
  ahrefs_broken_backlinks: null
  dejan: null
  sistrix_sentiment_mhtml: []
  gsc_generative_ai_export: null

report:
  output_docx: true
  output_pdf: true
~~~

Секреты и API keys не записываются в YAML, DuckDB, manifest или evidence. Используются только настроенные MCP/OAuth connections либо специально настроенные переменные окружения.

## 7. State machine аналитического skill

Skill обязан быть resumable и idempotent.

| Состояние | Значение |
|---|---|
| CREATED | Run создан, но проверки не начаты |
| PREFLIGHT | Проверяются конфигурация, MCP и файлы |
| WAITING_FOR_CONFIG | Не хватает brand/domain/country или другого решения |
| WAITING_FOR_INPUTS | Не хватает обязательного файла |
| READY | Все обязательные проверки пройдены |
| READY_WITH_GAPS | Все 18 обязательных источников доступны, но есть допустимые record-level gaps или неполное URL/row coverage |
| COLLECTING | Идёт чтение и staging |
| STAGED | Источники загружены и прошли schema checks |
| CLUSTERING | Автоматически выполняется URL-кластеризация |
| WAITING_FOR_CLUSTER_CONFIRMATION | Пользователь подтверждает предложенные url_type labels |
| ANALYZING | Рассчитываются факторы, findings и evidence |
| VALIDATING | Выполняются финальные инварианты |
| ANALYSIS_COMPLETE | Полный допустимый analysis package |
| ANALYSIS_COMPLETE_WITH_GAPS | Package завершён с явно принятыми ограничениями |
| BLOCKED | Нельзя корректно продолжить без внешнего входа |
| FAILED | Техническая ошибка с сохранённым checkpoint |

Повторный запуск с теми же config hash и source hashes продолжает run, а не создаёт дубли. Изменение домена, страны, crawl universe или важных файлов создаёт новый run revision.

## 8. Preflight: точная последовательность

### 8.1 Проверка конфигурации

Skill проверяет:

- brand;
- canonical domain;
- SISTRIX country;
- язык анализа и отчёта;
- допустимые модели;
- crawl scope;
- даты и временные окна;
- список sentiment MHTML: один или несколько брендов;
- список конкурентов, если пользователь хочет фиксированный сравнительный набор.

Запрашиваются только отсутствующие значения. Домены нормализуются до host без протокола и пути, но исходное значение сохраняется в manifest.

### 8.2 Проверка Screaming Frog MCP

Нельзя считать MCP доступным по одному факту наличия имени tool. Нужен небольшой реальный read.

Проверяются:

1. доступность crawl;
2. crawl timestamp и domain match;
3. число HTML URL и общий scope;
4. наличие native SF metrics;
5. наличие raw HTML;
6. наличие rendered HTML;
7. наличие JS/rendering fields и ошибок ресурсов;
8. наличие PSI mobile/desktop результатов;
9. наличие GSC Search Analytics;
10. наличие URL Inspection полей либо возможность их запросить.

Если raw или rendered HTML отсутствует, T16, T17 и S18 не могут считаться полностью измеренными. Skill не подменяет сравнение одним rendered HTML.

### 8.3 Проверка SISTRIX MCP

Предпочтительный транспорт — MCP с OAuth. Preflight делает:

1. справочный запрос **ai.models**;
2. проверку наличия требуемых моделей;
3. минимальный запрос **ai.check.overview** для brand/domain/country;
4. проверку формы ответа и scope;
5. сохранение timestamp, параметров и версии adapter;
6. расчёт плана запросов для overview, competitors, prompts, prompts.count и sources.

При текущем MCP-режиме оценка API credits фиксируется как 0 только если это подтверждено актуальной документацией или ответом сервиса на дату запуска. Одновременно показывается плановое число MCP requests, поскольку нулевая credit cost не означает отсутствие rate/fair-use limits.

Если включён прямой API fallback, skill:

- делает минимальный репрезентативный запрос;
- считывает реально возвращённое поле credits used;
- определяет количество страниц/итераций для каждого endpoint;
- выдаёт lower bound, expected и upper bound;
- требует подтверждение пользователя, если upper bound выше max_credit_cost;
- не выдаёт точную сумму, если pagination или стоимость endpoint не доказаны.

### 8.4 Проверка файлов

Файлы определяются по schema fingerprint, а не только по имени:

- Ahrefs Backlinks;
- Ahrefs Referring Domains;
- Ahrefs Broken Backlinks;
- Dejan AI Agent Access;
- SISTRIX Sentiment MHTML;
- GSC Generative AI export.

Для каждого файла фиксируются:

- absolute path;
- SHA-256;
- размер;
- encoding и delimiter для tabular formats;
- snapshot/export date;
- domain/brand/country, если они присутствуют;
- число строк;
- schema fingerprint;
- adapter match;
- freshness status.

ZIP может быть входным контейнером. Его содержимое извлекается в run-specific raw directory с защитой от path traversal; исходный ZIP остаётся неизменным.

### 8.5 Readiness result и обязательное напоминание

Preflight выдаёт machine-readable таблицу:

| Поле | Возможные значения |
|---|---|
| access_status | pass / fail / auth_required |
| data_status | present / missing / partial / malformed |
| scope_status | match / mismatch / unknown |
| freshness_status | current / stale / unknown |
| blocking | true / false |
| affected_factors | список ID |
| action | конкретный следующий шаг |

Run переходит в READY только после устранения blockers. Допустимые gaps не маскируются: affected factors заранее получают потенциальный статус ND или partial coverage.

Каталог из 18 источников является закрытым обязательным checklist, а не набором рекомендаций. При каждом запуске preflight показывает все 18 кодов и их статус. Если отсутствует целый источник, требуется авторизация, обнаружен scope mismatch или файл не проходит schema fingerprint, skill переходит в `WAITING_FOR_INPUTS` либо `BLOCKED` и формулирует конкретное действие: что подключить, выгрузить или загрузить. Такой источник нельзя молча заменить `ND` и продолжить как полный audit.

`READY_WITH_GAPS` допустим только когда все 18 источников присутствуют и прошли source-level gate, но внутри источника имеются документированные record-level failures или неполное URL/row coverage, разрешённые соответствующим `coverage_rule_id`. Valid empty export должен явно подтверждать нулевой результат в заданном scope; отсутствие файла или строк без доказанного scope не считается нулём.

## 9. Сбор и staging

### 9.1 Правило слоёв

Для каждого источника сохраняются:

1. **Raw artifact** — неизменённый JSON/XML/CSV/MHTML либо reference на MCP extraction с hash.
2. **Staging table** — максимально близкое представление исходных полей.
3. **Canonical table** — нормализованные типы, URL, даты, model/country и field aliases.
4. **Derived table** — только документированные расчёты.

Каждый adapter пишет в отдельной DuckDB transaction. При ошибке источник откатывается целиком; ранее успешно загруженные источники остаются валидными.

Один процесс владеет записью в DuckDB. Report skill открывает завершённую базу read-only. Это предотвращает конкурирующие записи и повреждение run.

### 9.2 SISTRIX

Сбор выполняется по реально возвращённому **ai.models**, заданной стране и согласованному scope. Для каждого вызова сохраняются request parameters, timestamp, pagination cursor/page, response hash, returned row count и credits used, если поле существует.

Запрещён недоказанный join:

~~~text
SX-P prompt/answer  ×  SX-S source URL
~~~

Пока API не даёт документированный общий ключ, ответы и sources анализируются как два самостоятельных агрегированных корпуса. Citation correctness и citation absorption не рассчитываются.

### 9.3 MHTML

SISTRIX Sentiment MHTML разбирается как MIME archive, а не как обычный HTML:

1. определяется boundary и декодируется Content-Transfer-Encoding;
2. выбирается основная часть text/html;
3. извлекаются видимые таблицы, labels, scores, Lob/Kritik, темы, examples и sources;
4. при наличии embedded JSON он сохраняется отдельно с provenance;
5. удалённые ресурсы не загружаются;
6. арифметика score и topic balance перепроверяется по показанным counts;
7. snapshot date и список показанных платформ обязательны.

### 9.4 URL normalization

Для всех URL сохраняются как минимум:

- source_url;
- canonical_join_url;
- scheme;
- host;
- normalized host;
- path;
- normalized query policy;
- fragment removed;
- redirect-final URL, если доказан;
- normalization rule version.

Никакой fuzzy join не становится доказательным автоматически. Все неидеальные joins получают method, match confidence и отдельный join-quality report.

## 10. Автоматическая URL-кластеризация

### 10.1 Момент запуска

Кластеризация запускается после загрузки и валидации SF URL universe, но до:

- отбора URL для GSC URL Inspection;
- расчёта cluster scope;
- приоритизации affected scope;
- финального factor analysis.

### 10.2 Контракт вызова

Аналитический skill передаёт:

~~~yaml
audit_run_id: geo-example-com-2026-09-15-r1
duckdb_path: clients/example.com/2026-09/geo/work/geo_audit.duckdb
source_table: geo_sf_urls
html_scope_filter: is_html = true
canonical_fields:
  page_url: page_url
  status_code: status_code
  indexability: indexability
  content_type: content_type
output_prefix: geo_url_clusters
~~~

URL-clustering skill должен принимать эти параметры прямо. Ему не следует искать неявные служебные таблицы или угадывать базовую таблицу.

### 10.3 Детерминированная path-prefix hierarchy

Текущий crawl является единственным источником состава structural clusters. После `seo-url-clustering` аналитический skill заново разбирает нормализованный path каждого HTML URL на сегменты и создаёт все вложенные prefixes.

| URL | Prefix memberships |
|---|---|
| `https://example.com/a/b/` | `/`, `/a/`, `/a/b/` |
| `https://example.com/a/e/` | `/`, `/a/`, `/a/e/` |
| `https://example.com/c/d/` | `/`, `/c/`, `/c/d/` |

Один URL получает несколько structural memberships — по одному на каждый уровень path. Root `/` представляет sitewide baseline. Query и fragment не образуют path-prefix clusters; правила URL normalization применяются до построения дерева и фиксируются версией.

Каждый prefix node содержит как минимум:

~~~yaml
cluster_id: path-prefix:/a/b/
cluster_type: path_prefix
normalized_prefix: /a/b/
depth: 2
parent_cluster_id: path-prefix:/a/
crawl_universe_hash: sha256:...
~~~

Path-prefix hierarchy является структурной, а не семантической: из `/a/` нельзя автоматически заключать, что это product, editorial или support cluster. Все nodes и memberships пересчитываются для каждого crawl независимо от предыдущих counts и URL lists.

### 10.4 Semantic labels, criticality и reuse

Автоматическими являются запуск, structural probing и path-prefix expansion. Пользователь подтверждает только:

- значения `url_type` для предложенных structural patterns;
- смысловые labels для prefixes/patterns, используемые в клиентском тексте;
- значение residual pattern;
- при необходимости business criticality подтверждённых semantic clusters.

На project level разрешено сохранять только правило интерпретации стабильного pattern:

~~~yaml
domain: example.com
pattern: /produkte/**
label: Produktseiten
criticality: high
confirmation_status: confirmed
mapping_version: 1
~~~

В project-level mapping запрещено сохранять конкретный URL membership, numerator, denominator или размер кластера как значение для следующего run. На каждом новом crawl memberships и counts вычисляются заново. Ранее подтверждённое правило применяется автоматически только к тому же domain и совпавшему structural pattern; новые, изменившиеся, конфликтующие или low-confidence patterns возвращаются в `proposed` и требуют подтверждения. До подтверждения используется raw prefix/pattern, а не придуманная бизнес-метка.

### 10.5 Инварианты handoff

- один vertical cluster на каждый HTML URL;
- один horizontal structural row на каждый HTML URL;
- не менее одного path-prefix membership на каждый HTML URL, включая root `/`;
- уникальность каждой пары `(page_url, cluster_id)`;
- ноль дублей `page_url` в per-URL vertical/horizontal tables;
- число per-URL vertical и horizontal rows равно baseline HTML URL;
- parent-child graph prefix nodes не содержит циклов;
- каждый non-root prefix имеет существующий parent;
- cluster member count рассчитывается как `COUNT(DISTINCT page_url)`;
- все prefix nodes и memberships имеют текущий crawl-universe hash;
- project-level semantic mapping не содержит сохранённых URL lists, numerator или denominator;
- ноль скрытых catch-all значений;
- ноль unresolved cross-layer conflicts либо каждый остаток индивидуально документирован;
- crawl-universe hash совпадает с hash, переданным аналитическим skill;
- cluster_run_id и cluster schema version сохранены.

### 10.6 Роль кластеров и правила подсчёта

Кластеры используются для:

- `affected_count`, `analyzed_count` и `affected_rate` на каждом path-prefix level;
- обнаружения template-level проблем;
- сравнения commercial/editorial/support/locale page types;
- стратифицированной выборки GSC URL Inspection;
- cluster-level recommendations;
- расчёта observed scope в priority matrix.

Один URL может входить одновременно в parent и child clusters, поэтому их counts и numerators нельзя складывать. Sitewide показатель всегда рассчитывается по уникальным URL, а parent/child rates выводятся как отдельные срезы. Все cluster metrics сохраняются в DuckDB; в основной отчёт попадают только material clusters по версионированному reporting rule, чтобы не превращать каждый единичный leaf prefix в отдельный finding.

Кластеры не подменяют prompt, model, sentiment или source-level grain.

## 11. GSC URL Inspection при лимите 2 000

Если HTML URL не больше 2 000, проверяется весь universe.

Если HTML URL больше 2 000, выборка строится после кластеризации:

1. обязательные critical URLs: homepage, ключевые money pages, sitemaps/GSC conflicts;
2. минимум по каждому material horizontal или path-prefix cluster;
3. пропорциональная стратификация по horizontal, material path-prefix и vertical clusters без двойного включения одного URL;
4. повышенная доля noindex/canonical/redirect/orphan candidates;
5. deterministic seed;
6. итог не больше 2 000;
7. сохранение inclusion reason для каждого URL.

Выводы T10 для большого сайта маркируются как выборочные и содержат denominator всего universe, inspected count и cluster coverage. Targeted URLs сохраняют отдельный `sample_role` и не используются как репрезентативная оценка sitewide prevalence без корректного inclusion weighting. Нельзя экстраполировать редкую проблему на весь сайт без доверительного основания.

## 12. Shared analysis method: HTML parity

HTML parity является общим методом расчёта внутри аналитического skill, а не дополнительным фактором, отдельным блоком или 130-й строкой матрицы. Метод создаёт производные метрики и evidence, которые затем оцениваются исключительно в составе существующих 129 факторов.

Основное распределение результатов метода:

| Фактор | Роль HTML parity |
|---|---|
| T16 — Зависимость от JavaScript | Определяет контент и элементы, отсутствующие в raw HTML и появляющиеся только после JS |
| T17 — Raw/rendered parity | Оценивает изменения metadata, indexing directives, hreflang, links и других HTML-элементов |
| S18 — Raw/rendered schema parity | Оценивает добавление, удаление и изменение structured data после JavaScript |

Эти же результаты могут выступать supporting evidence для других существующих факторов, включая T09, T15 и C04. Это не создаёт новых factor IDs и не приводит к повторной оценке одной проблемы.

Для каждого HTML URL сравниваются:

| Область | Примеры метрик |
|---|---|
| Основной контент | raw/rendered text length, main text hash, JS-only text ratio |
| Metadata | title, description, H1/H2 |
| Indexing controls | canonical, robots, hreflang |
| Links | raw/rendered internal outlinks, JS-only links |
| Structured data | types, entity IDs, properties, validation deltas |
| Brand facts | цены, продукты, geography, conditions, dates |
| Trust signals | author, publisher, sources, contact/legal elements |
| Media/accessibility | alt, captions, controls, labels |

Вывод должен различать:

- элемент отсутствует в raw и появляется в rendered;
- элемент присутствует в обоих без изменения;
- элемент изменён JavaScript;
- элемент удалён после rendering;
- сравнение невозможно.

Допустимый вывод: «ключевой контент зависит от JavaScript в X из Y URL».
Недопустимый вывод без дополнительных данных: «конкретный AI-бот не увидел этот контент».

## 13. DuckDB data model

### 13.1 Управление run

| Таблица | Grain |
|---|---|
| geo_audit_runs | один audit run/revision |
| geo_analysis_events | одно состояние или событие run |
| geo_source_manifest | один физический artifact или MCP extraction |
| geo_source_checks | одна preflight/data-quality проверка |
| geo_schema_registry | одна schema version источника |
| geo_join_quality | одна комбинация source pair и join method |

### 13.2 Источники

| Таблица | Grain |
|---|---|
| geo_sf_urls | один crawled URL |
| geo_html_raw | один raw HTML snapshot на URL |
| geo_html_rendered | один rendered HTML snapshot на URL |
| geo_html_parity | один URL и одна comparison dimension |
| geo_psi_lab | один URL, strategy и run |
| geo_gsc_search_analytics | строка GSC dimensions/date |
| geo_gsc_url_inspection | один inspected URL |
| geo_gsc_gai | строка экспортированных GAI dimensions/date |
| geo_ahrefs_backlinks | одна backlink record |
| geo_ahrefs_refdomains | одна referring-domain record |
| geo_ahrefs_broken | одна broken-backlink record |
| geo_sistrix_models | одна model record |
| geo_sistrix_overview | одна scope/model/country record |
| geo_sistrix_competitors | один competitor в scope |
| geo_sistrix_prompts | одна returned prompt/answer record |
| geo_sistrix_prompt_counts | одна date/model/country record |
| geo_sistrix_sources | одна source record |
| geo_sistrix_sentiment | один brand/platform/topic/snapshot record |
| geo_dejan_agents | один agent и rule result |

### 13.3 Кластеры и результаты

| Таблица | Grain |
|---|---|
| geo_cluster_runs | один clustering run |
| geo_url_clusters_vertical | один HTML URL |
| geo_url_clusters_horizontal | один HTML URL |
| geo_url_prefix_clusters | один path-prefix node текущего crawl |
| geo_url_cluster_memberships | одна уникальная пара HTML URL × path-prefix cluster |
| geo_cluster_semantic_map | один semantic token/group |
| geo_cluster_label_mappings | одно подтверждённое domain × structural pattern × mapping version без URL memberships/counts |
| geo_factor_results | один factor ID на audit run |
| geo_factor_metrics | один factor ID и metric |
| geo_factor_cluster_metrics | один factor ID × cluster ID с affected/analyzed/coverage |
| geo_evidence_drafts | один внутренний evidence object |
| geo_evidence | один финальный evidence number |
| geo_findings | один доказанный вывод |
| geo_recommendation_candidates | одна нормализованная рекомендация |
| geo_analysis_limitations | одно ограничение |

Большие HTML bodies можно хранить как immutable compressed artifacts с path и SHA-256 в DuckDB. В базе обязательно остаются извлечённые поля и hash, необходимые для воспроизводимости.

## 14. Factor analysis contract

Аналитический skill обязан создать строку для каждого из 129 факторов, даже если фактор неприменим или данных недостаточно.

Минимальная структура factor result:

~~~yaml
factor_id: T16
audit_run_id: geo-example-com-2026-09-15-r1
applicability: applicable
measurement_status: measured
coverage_type: complete
observed:
  affected_count: 84
  analyzed_count: 10000
  affected_rate: 0.0084
  applicable_universe_count: 10000
  coverage_rate: 1.0
  scope_type: full
  counting_rule: distinct_page_url
scope:
  site: example.com
  clusters:
    - cluster_id: path-prefix:/produkte/rechtsschutz/
      label: Rechtsschutz-Produktseiten
      affected_count: 84
      analyzed_count: 400
      affected_rate: 0.21
      applicable_universe_count: 400
      coverage_rate: 1.0
confidence: high
finding: Ключевой контент появляется только после JS на 84 URL.
evidence_ids:
  - E-1042
recommendation_candidate_ids:
  - R-T16-001
limitations:
  - Rendering Chromium не доказывает поведение каждого AI-бота.
~~~

Допустимые measurement_status:

- measured;
- partially_measured;
- not_determined;
- not_applicable;
- source_error.

Недостаток данных не превращается в отрицательный finding.

`affected_count / analyzed_count` называется **Betroffenheit**, а не доказанным impact. Метрики рассчитываются отдельно для sitewide scope и каждого material cluster. При вложенных path-prefix memberships sitewide и cross-cluster roll-up используют `COUNT(DISTINCT page_url)`; parent и child cluster counts никогда не суммируются.

## 15. Evidence model

### 15.1 Evidence object

Каждая доказательная единица содержит:

- provisional evidence UUID;
- final evidence number;
- audit_run_id;
- factor_id;
- source_code;
- source artifact ID и SHA-256;
- table/view/path;
- exact filter или SQL fingerprint;
- grain;
- numerator и denominator;
- observed value;
- affected clusters;
- 1–3 representative examples;
- extraction/calculation timestamp;
- method version;
- confidence;
- limitations.

### 15.2 Выдача evidence numbers

Во время расчётов используются UUID. После прохождения data-quality gate skill:

1. блокирует реестр;
2. резервирует следующий непрерывный диапазон **E-NNNN**;
3. сопоставляет UUID с final IDs;
4. обновляет factors, findings и recommendations;
5. запрещает повторное использование ID;
6. сохраняет mapping в manifest.

Это предотвращает конфликт при параллельных или прерванных run и не позволяет модели придумывать evidence numbers из памяти.

### 15.3 Evidence gate

Finding считается доказанным, только если:

- его evidence существует;
- источник входит в согласованные 18;
- source hash разрешается;
- metric grain соответствует factor grain;
- numerator не больше denominator;
- примеры действительно входят в рассчитанное множество;
- limitation не противоречит формулировке finding;
- query/filter воспроизводим.

## 16. Findings и Handlungsempfehlungen

Аналитический skill создаёт только evidence-backed findings. Гипотезы допустимы во внутреннем поле, но не становятся оценённым клиентским finding без evidence.

Структура recommendation candidate:

~~~yaml
recommendation_id: R-T16-001
factor_ids:
  - T16
  - T17
root_cause_key: product-template-js-only-core-content
problem: Основной product content отсутствует в raw HTML.
why_important: Retrieval зависит от системы, способной выполнить JS.
action: Вывести критический текст и внутренние ссылки в server-rendered HTML.
affected_scope:
  urls: 80
  denominator: 400
  clusters:
    - product
expected_effect: Снизить зависимость извлекаемости от JS.
effort: medium
risk: medium
confidence: high
validation_method: Повторить raw/rendered crawl и сравнить те же URL.
evidence_ids:
  - E-1042
  - E-1043
~~~

Рекомендации дедуплицируются по root_cause_key. Одна системная рекомендация может закрывать несколько factors, но каждый factor сохраняет собственную оценку и evidence.

Запрещено:

- выдавать общую best practice без наблюдаемой проблемы или opportunity gap;
- обещать рост AI citations как причинный результат;
- превращать source correlation в доказанную ranking causality;
- писать «бот не crawled URL» на основании robots configuration;
- утверждать correctness/absorption без связи statement-to-source.

## 17. Analysis completion gate

Run может получить ANALYSIS_COMPLETE только при выполнении всех инвариантов:

- факторный реестр содержит ровно 129 ожидаемых ID;
- нет неизвестных или дублированных ID;
- каждый factor имеет applicability и measurement status;
- все source artifacts имеют hash и scope;
- все required schema checks пройдены;
- URL normalization и join-quality отчёты завершены;
- cluster invariants пройдены, включая prefix tree, уникальные memberships и запрет parent/child double counting;
- GSC sample имеет inclusion reason и не превышает 2 000;
- нет недоказанных prompt-to-source joins;
- каждый доказанный finding имеет evidence;
- каждая recommendation имеет finding и evidence;
- все final evidence IDs разрешаются;
- HTML parity evidence для T16, T17, S18 и связанных факторов рассчитан для URL, где доступны RAW и REN;
- PSI результаты явно помечены как Lighthouse lab;
- limitations включены в package;
- config hash, source hashes, catalog versions и code versions зафиксированы;
- DuckDB commit завершён.

Отсутствие любого из 18 обязательных источников не допускает `ANALYSIS_COMPLETE_WITH_GAPS`: run остаётся `WAITING_FOR_INPUTS` или `BLOCKED`. Этот статус разрешён только при наличии всех source-level artifacts и документированных record-level gaps/partial coverage, разрешённых соответствующими coverage rules. Affected factors остаются ND/partial, а не окрашиваются негативно.

## 18. Выходы аналитического skill

~~~text
clients/<domain>/<date_slug>/geo/
  config/
    audit.yaml
  raw/
    <immutable source artifacts>
  work/
    geo_audit.duckdb
  output/
    run-manifest.json
    analysis-package.json
    factor-results.jsonl
    evidence-ledger.csv
    evidence-ledger.jsonl
    findings.json
    recommendations.json
    source-coverage.csv
    cluster-summary.csv
    cluster-prefix-summary.csv
    analysis-limitations.md
~~~

**analysis-package.json** является единственным официальным handoff report skill. Report skill не читает произвольные заметки или чат как источник аналитических значений.

## 19. Report skill: входной gate

Перед scoring report skill проверяет:

1. run status;
2. schema versions;
3. factor catalog version;
4. scoring matrix compatibility;
5. ровно 129 factor results;
6. уникальность factor IDs;
7. разрешение всех evidence IDs;
8. отсутствие recommendation без evidence;
9. отсутствие unsupported metrics;
10. непротиворечивость counts/denominators;
11. наличие и успешный source-level gate всех 18 обязательных источников;
12. source and cluster coverage;
13. отсутствие parent/child double counting в sitewide roll-up;
14. явно зафиксированную Lighthouse-lab basis для PSI-derived оценок в методологии и соответствующем блоке отчёта.

При провале gate отчёт не строится. Skill выдаёт список repair actions и не заполняет пробелы собственными предположениями.

## 20. Оценочная матрица

Полная человекочитаемая policy публикуется в `seo-geo-report-generator/README.md`: определения, evidence grades, Betroffenheit/coverage, status и priority rules, ceilings, veto, sensitivity, block roll-up и таблица всех 129 factors. Исполняемым источником истины остаётся `scoring-matrix.yaml`. README генерируется либо contract-валидируется против `policy_version` и content hash YAML; расхождение блокирует release.

### 20.1 Три независимых измерения

| Поле | Вопрос | Значения |
|---|---|---|
| Status | Насколько здорово текущее состояние? | red / yellow / green / ND / NA |
| Priority | Насколько срочно исправлять? | P0 / P1 / P2 / P3 / null |
| Confidence | Насколько надёжен вывод? | high / medium / low |

Красный не всегда автоматически P0, а жёлтый может стать P1 на критическом коммерческом кластере. Green, ND и NA обычно имеют priority null.

`affected_count / analyzed_count` является **Betroffenheitsquote** — измеренным масштабом затронутости, а не доказанным causal или business impact. Для каждой применимой метрики также сохраняются `applicable_universe_count`, `coverage_rate` и `scope_type` (`full`, `representative_sample`, `diagnostic_sample`, `source_corpus`). Sitewide и cluster-level scopes показываются отдельно.

### 20.2 Типы factor scoring rules

Каждый из 129 factors ссылается ровно на одно версионированное правило одного из типов:

| Тип | Применение |
|---|---|
| Boolean gate | robots block, invalid canonical, отсутствующий обязательный элемент |
| Threshold | latency, depth, duplicate rate, accessibility score |
| Prevalence | доля affected URL |
| Comparative gap | отличие от конкурентов, моделей, стран или кластеров |
| Consistency | raw/rendered, schema/visible HTML, site/AI statements |
| Rubric | качество provenance, answer clarity, brand truth completeness |

Каждая оценка сохраняет:

- scoring_rule_id и version;
- observed value;
- denominator;
- threshold или rubric result;
- applicable cluster;
- resulting status;
- confidence;
- evidence IDs.

Порог не может находиться только в тексте SKILL.md. Он живёт в scoring-matrix.yaml и покрыт boundary tests.

### 20.3 Priority logic

Priority рассчитывается после status и использует:

- factor dependency role: eligibility gate / direct observed outcome / supporting driver;
- severity;
- affected absolute count;
- affected percentage;
- business criticality подтверждённого URL cluster;
- модельное/страновое покрытие;
- reversibility и риск;
- confidence.

Effort не повышает важность проблемы. Он показывается отдельно и может дать label **Quick Win**, но не превращает слабый фактор в высокий приоритет.

Рекомендуемая семантика:

| Priority | Значение |
|---|---|
| P0 | Критическая блокировка, фактическая опасная ошибка или тяжёлый reputational/accuracy риск на важном scope |
| P1 | Материальная проблема или gap с большим/стратегическим scope |
| P2 | Значимое улучшение ограниченного scope или supporting driver |
| P3 | Низкоэффектная hygiene/opportunity задача |

Универсальная важность всех 129 факторов не объявляется как научно доказанный линейный рейтинг. Приоритет — воспроизводимая условная оценка для конкретного сайта на основании evidence, scope и зависимости.

### 20.4 Lighthouse lab

Для PSI factors основой статуса является Lighthouse lab. Отсутствие CrUX:

- не создаёт ND;
- не уменьшает coverage;
- не меняет traffic light;
- не заставляет показывать отдельную пометку «lab» в каждой строке, если basis один раз ясно указан в методологии и соответствующем блоке.

При этом:

- lab TBT не называется INP;
- lab metrics не называются field Core Web Vitals;
- доступный CrUX можно показать только как дополнительный контекст.

### 20.5 ND и NA

- **ND** — фактор применим, но данных недостаточно или источник сломан.
- **NA** — фактор неприменим по документированному applicability rule.

Оба статуса серые. Они не конвертируются в red/yellow. Coverage показывается отдельно, чтобы зелёный блок с большим объёмом ND не выглядел полностью проверенным.

## 21. Roll-up блока и общего аудита

Нельзя использовать простое среднее цветов.

Каждый блок получает:

- block status;
- measured applicable factors / applicable factors;
- high-confidence coverage;
- counts red/yellow/green/ND/NA;
- critical veto results;
- top affected clusters.

Версионированные правила roll-up:

1. **Red** — сработал red veto factor с достаточной confidence либо комбинация material red factors превысила правило блока.
2. **Yellow** — red rule не сработало, но существует material yellow/red-low-confidence condition.
3. **Green** — нет material red/yellow и выполнен minimum coverage gate блока.
4. **ND** — minimum coverage gate не выполнен; отсутствие данных не маскируется жёлтым.

Overall status:

- red, если выполнено хотя бы одно overall veto или критическая red комбинация блоков;
- yellow, если overall red отсутствует, но есть material yellow block;
- green, если все применимые блоки прошли coverage gates и не имеют material red/yellow;
- ND, если общий coverage gate не пройден.

Точные veto, materiality и coverage thresholds задаются отдельно для каждого блока в scoring-matrix.yaml. Они не импровизируются при генерации отчёта.

## 22. Структура GEO-отчёта

### 22.1 Часть 1 — Summary

Summary содержит:

1. scope, дата, brand/domain/country;
2. общий traffic light;
3. traffic light шести блоков;
4. counts red/yellow/green/ND/NA и coverage;
5. **только красные findings**;
6. ограничения, которые меняют интерпретацию красных findings.

Таблица красных findings:

| Block | ID | Priority | Formulierung | Betroffenheit / Abdeckung | Warum wichtig | Was ist falsch / warum rot | Handlungsempfehlung | Evidenz |
|---|---|---|---|---|---|---|---|---|

Если красных findings нет, раздел явно сообщает об этом. Жёлтые строки в Summary не подмешиваются.

### 22.2 Часть 2 — Gesamtbericht

Общий отчёт содержит все 129 factors:

| Block | ID | Status | Priority | Confidence | Faktor | Betroffenheit / Abdeckung | Warum wichtig / Bewertung | Handlungsempfehlung | Evidenz |
|---|---|---|---|---|---|---|---|---|---|

Правила:

- recommendations выводятся только когда есть действие;
- green может иметь пустую recommendation;
- ND/NA показываются серым и содержат причину;
- PSI раздел один раз указывает, что basis — Lighthouse lab;
- cluster-scoped rows показывают `affected/analyzed`, процент, cluster label либо raw prefix и coverage;
- при вложенных prefixes report не суммирует parent и child counts;
- evidence number всегда последняя колонка;
- при нескольких evidence используются компактные IDs, а детали вынесены в appendix;
- длинные URL не перегружают основную таблицу.

### 22.3 Приложения

- методология и границы;
- source coverage;
- scoring legend;
- evidence register;
- cluster coverage;
- GSC sampling;
- SISTRIX request scope;
- limitations;
- action roadmap, сгруппированный по root cause, priority, effort и validation method.

## 23. Report rendering

Последовательность scripts:

~~~text
validate_analysis_package.py
  -> apply_scoring_matrix.py
  -> aggregate_statuses.py
  -> build_report_model.py
  -> render_geo_report.py
  -> validate_report_content.py
  -> render_and_inspect.py
~~~

Renderer получает полностью подготовленные строки и ничего не рассчитывает. Scoring engine не находится в renderer.

Минимальные выходы:

~~~text
report/
  GEO_Audit_<domain>_<YYYY-MM-DD>.docx
  GEO_Audit_<domain>_<YYYY-MM-DD>.pdf
  scored-factors.json
  block-rollups.json
  report-manifest.json
  rendered-pages/
~~~

## 24. Content validation отчёта

До визуального QA автоматически проверяется:

- 129 уникальных factor rows в Gesamtbericht;
- Summary содержит только red factors;
- каждая Summary row существует в Gesamtbericht;
- status, priority и confidence совпадают между JSON и DOCX model;
- цвет соответствует status;
- ND/NA не окрашены в red/yellow;
- все evidence IDs существуют;
- recommendations не появились без analysis package;
- counts на summary совпадают с factor rows;
- sitewide affected counts используют distinct URL и не суммируют nested parent/child memberships;
- cluster Betroffenheit и coverage совпадают с `geo_factor_cluster_metrics`;
- block/overall rollups воспроизводятся;
- нет запрещённых причинных утверждений;
- нет термина INP для TBT;
- SISTRIX observed counts не названы полным market denominator;
- нет statement-to-source утверждения без доказанного join.

## 25. Visual QA

DOCX обязательно рендерится в PDF и page images. Проверяются:

- cover и footer;
- отсутствие обрезанных строк и колонок;
- повтор header row на новых страницах;
- читаемость 129-row tables;
- consistent traffic-light colors;
- различимость ND/NA;
- перенос длинных немецких слов;
- перенос URLs/evidence IDs;
- отсутствие пустых страниц;
- корректность page breaks;
- соответствие ширины таблиц printable area;
- совпадение номера страниц PDF и preview.

Report считается готовым только после успешного content validation и visual QA.

## 26. Тестовая стратегия

### 26.1 Contract tests

- source catalog содержит ровно 18 codes;
- factor catalog содержит ровно 129 согласованных IDs;
- распределение 24/26/27/20/15/17;
- каждый factor имеет source, method, coverage, evidence и scoring rule;
- все scoring_rule_id существуют;
- все 18 источников имеют `required: true` и source-level preflight rule;
- README scoring policy совпадает с `scoring-matrix.yaml` по version, hash и 129 rule IDs;
- schema versions совместимы.

### 26.2 Unit tests аналитического skill

- multilingual CSV headers и values;
- encoding/delimiter;
- ZIP path traversal;
- MHTML MIME boundaries и transfer encoding;
- SISTRIX pagination, empty response, 429/retry;
- SISTRIX cost lower/expected/upper;
- URL normalization;
- path-prefix generation for root, parent and leaf levels;
- unique URL × prefix memberships;
- project mapping reuse without persisted URL lists/counts;
- detection of new, changed and low-confidence patterns;
- `COUNT(DISTINCT page_url)` protection against parent/child double counting;
- join confidence;
- duplicate rows;
- raw/rendered deltas;
- schema graph comparison;
- GSC deterministic 2 000 sample;
- evidence UUID-to-E-ID mapping;
- recommendation deduplication.

### 26.3 Unit tests report skill

- threshold boundaries;
- boolean veto;
- prevalence;
- comparative gap;
- rubric completeness;
- status/priority independence;
- confidence handling;
- ND/NA;
- block roll-up;
- overall roll-up;
- summary red-only filter;
- exact factor counts;
- evidence resolution.

### 26.4 Failure fixtures

- wrong domain in crawl;
- partial crawl;
- RAW without REN и REN without RAW;
- SISTRIX auth/OAuth failure;
- unsupported/empty model;
- malformed Ahrefs schema;
- duplicate backlink rows;
- malformed sentiment MHTML;
- sentiment score arithmetic mismatch;
- missing GSC-GAI export;
- PSI failure for subset;
- no CrUX but valid Lighthouse;
- site above 2 000 URLs;
- nested path prefixes with overlapping parent/child memberships;
- stale project mapping whose structural pattern no longer matches;
- clustering confirmation interrupted;
- source file changed after staging.

### 26.5 End-to-end fixtures

1. Minimal full dataset with all 18 sources.
2. Multilingual site above 2 000 HTML URLs with a multi-level path-prefix tree.
3. Valid audit with accepted gaps and ND factors.
4. SISTRIX corpus with prompts but no joinable source IDs.
5. Sentiment MHTML with several platforms and competitors.
6. Raw/rendered site with a JS-only commercial template.

### 26.6 Resume/idempotence

Run прерывается и возобновляется:

- после preflight;
- после SISTRIX collection;
- до и после clustering confirmation;
- во время factor analysis;
- до final evidence allocation;
- после scoring, до rendering.

Повторный запуск не должен дублировать rows, evidence или recommendations.

## 27. Acceptance gates

| Gate | Критерий |
|---|---|
| P0 — Scoring Policy Freeze | 129 complete rules, thresholds/rubrics, priority ceilings, veto, roll-ups и boundary fixtures заморожены до implementation |
| A — Contracts | 18 sources и 129 factors валидны |
| B — Preflight | Реальные probes, scope/freshness и blockers корректны |
| C — Staging | Row counts, schemas, hashes, joins и transactions валидны |
| D — Clustering | Full URL coverage, valid prefix tree/memberships и подтверждённые semantic labels |
| E — Analysis | 129 factor results, evidence и limitations |
| F — Scoring | Boundary tests и roll-ups воспроизводимы |
| G — Report | Red-only Summary, full 129-row report, evidence traceability |
| H — Visual | DOCX/PDF прошли render-and-inspect |
| I — E2E | Повторяемый audit на sanitised fixture без ручных скрытых расчётов |

## 28. Порядок реализации

Исполнимый checklist с task IDs, зависимостями и gate criteria находится в
[BACKLOG.md](BACKLOG.md). Этот раздел фиксирует milestone order; при расхождении
деталей архитектурные инварианты этого документа и acceptance criteria backlog
должны быть согласованы отдельным versioned change до продолжения работ.

### Этап 0 — Scoring Policy Design and Freeze

- определить полный scoring rule schema;
- зафиксировать evidence/confidence policy, Betroffenheit, coverage и
  materiality;
- создать exact thresholds/rubrics для всех 129 факторов;
- определить dependency roles, priority floors/ceilings и modifiers;
- определить block/overall veto и roll-ups;
- создать human-readable policy, machine policy и boundary/adversarial fixtures;
- заморозить policy version/hash до написания implementation skeleton skills.

### Этап 1 — Зафиксировать контракты

- перенести финальный реестр 18 источников и 129 факторов в YAML;
- создать JSON Schemas;
- создать DuckDB DDL;
- определить versioning и migration policy;
- написать contract tests.

### Этап 2 — Preflight и adapters

- реализовать run state machine;
- SF и SISTRIX probes;
- cost/request estimator;
- file discovery и fingerprints;
- ZIP/MHTML/table adapters;
- source coverage report.

### Этап 3 — Staging и кластеризация

- canonical field mapping;
- URL normalization;
- DuckDB transactions;
- явный contract автоматического вызова URL clustering;
- пересчёт path-prefix tree и per-URL memberships из текущего crawl;
- project-level reuse только для semantic labels/criticality, без URL lists и counts;
- confirmation/resume flow;
- GSC 2 000 stratified selection.

### Этап 4 — Analysis engine

- shared HTML parity method и его mapping в T16, T17, S18 и связанные факторы;
- factor methods по блокам T/B/C/S/O/M;
- evidence drafts;
- findings;
- recommendation deduplication;
- final evidence allocation;
- analysis completion gate.

### Этап 5 — Deterministic scoring engine

- валидировать analysis package и совместимость policy version/hash;
- применить замороженные factor rules без model discretion;
- применить замороженные priority ceilings, block/overall veto и roll-ups;
- повторно выполнить boundary/adversarial tests на исполняемом engine;
- создать deterministic versioned scored-factor output.

### Этап 6 — GEO report

- report model;
- Summary red-only;
- Gesamtbericht 129 rows;
- appendices;
- DOCX/PDF renderer;
- content checks;
- visual QA.

### Этап 7 — End-to-end validation

- synthetic fixtures;
- sanitised real audit;
- interruption/resume tests;
- documentation;
- release checklist.

## 29. Зафиксированные решения и обязательные проверки до production-ready реализации

1. **Решено:** имена — **seo-geo-audit** и **seo-geo-report-generator**.
2. **Решено:** основной язык отчёта — German по умолчанию, configurable.
3. **Решено:** обязательные клиентские форматы — DOCX и PDF.
4. **Решено:** глобальный формат evidence IDs — **E-NNNN**.
5. **Решено:** глобальный counter/registry хранится в `clients/evidence_registry.md`; диапазон резервируется атомарно аналитическим skill до handoff.
6. **Решено:** READY требует source-level gate всех 18 обязательных источников; отсутствующий целый источник блокирует run.
7. **Решено:** Summary при любых условиях остаётся red-only и сортируется по priority.
8. **Решено:** пользователь подтверждает semantic labels и business criticality patterns; structural prefix tree и memberships всегда рассчитываются автоматически заново.
9. **Пройдено — Gate P0:** exact thresholds/rubrics и priority ceilings для каждой из 129 строк, block/overall veto и boundary/adversarial fixtures заморожены в scoring policy 1.0.0; это не runtime-решение пользователя.
10. **Обязательная integration spike:** зафиксировать реальные имена и response schemas Screaming Frog и SISTRIX MCP tools безопасными тестовыми reads.
11. **Решено:** полная человекочитаемая scoring policy находится в README GEO-report skill и contract-валидируется против машинной YAML policy.
12. **Пройдено — Gate A:** source/factor catalogs, config/analysis/report schemas, 41-table DDL, report contract, positive fixtures и 11 negative mutations валидируются автономно; следующий этап — реальные MCP probes и adapters.
13. **Реализовано — Stage 2 offline:** state machine, 18-source readiness, response-anchored probe contracts, SISTRIX cost bounds, secure ZIP/MHTML и multilingual file adapters покрыты runtime tests. Gate B не закрыт до реальных reads подключённых Screaming Frog и SISTRIX MCP.

Integration spike из пункта 10 нельзя корректно заполнить заранее: точные callable tool names и response schemas зависят от фактически подключённых MCP servers и должны быть подтверждены безопасными тестовыми reads.

## 30. Definition of Done

Система готова, когда:

- аналитический skill из одних и тех же входов создаёт идентичные normalized metrics;
- любой factor в отчёте трассируется до source artifact, query/method и evidence ID;
- URL clustering запускается автоматически, но семантические labels подтверждаются человеком;
- structural path-prefix tree и URL memberships пересчитываются из текущего crawl, а project mapping хранит только подтверждённые labels/criticality;
- cluster-level Betroffenheit использует affected/analyzed, а sitewide roll-up не допускает parent/child double counting;
- HTML parity evidence для T16, T17, S18 и связанных факторов рассчитывается на URL и cluster level без создания дополнительного фактора;
- GSC >2 000 обрабатывается воспроизводимой cluster-stratified выборкой;
- Lighthouse lab служит согласованной PSI-базой;
- report skill не собирает и не переинтерпретирует исходные данные;
- traffic lights, priorities и confidence разделены;
- missing data не становится негативной оценкой;
- Summary содержит только red findings;
- Gesamtbericht содержит все 129 factors;
- DOCX/PDF проходит content и visual QA;
- весь run можно возобновить после прерывания без дублей и потери provenance.

## 31. Документальная основа

- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [SISTRIX MCP technical information](https://www.sistrix.com/api/connection-to-chatbot-ai/technical-information-mcp/)
- [SISTRIX API limitations](https://www.sistrix.com/api/limitations/)
- [Google Search Console API usage limits](https://developers.google.com/webmaster-tools/limits)
- [Screaming Frog tabs and raw/rendered fields](https://www.screamingfrog.co.uk/seo-spider/user-guide/tabs/)
- [DuckDB concurrency](https://duckdb.org/docs/stable/connect/concurrency)
- [DuckDB transactions](https://duckdb.org/docs/stable/sql/statements/transactions)
- [URL clustering skill](https://github.com/e-orlov/claude-seo/blob/main/.claude/skills/seo-url-clustering/SKILL.md)
- [Existing static report renderer](https://github.com/e-orlov/claude-seo/blob/main/.claude/skills/seo-report-generator/report_renderer.py)
- [Frozen GEO scoring policy](scoring-policy/README.md)
- [Gate P0 validation record](GATE_P0_CLOSEOUT.md)
- [Gate A validation record](GATE_A_CLOSEOUT.md)
- [Stage 2 preflight checkpoint](STAGE2_PREFLIGHT_CHECKPOINT.md)
