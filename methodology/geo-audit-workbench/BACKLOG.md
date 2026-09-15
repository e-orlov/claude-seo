# GEO Audit Skills — Final Implementation Backlog

Статус: **Architecture baseline complete; Stage 0 is next**

Рабочая ветка: `work/geo-audit-skills`

Целевые skills: `seo-geo-audit`, `seo-geo-report-generator`

Обязательная skill-зависимость: `seo-url-clustering`

Основа: 18 обязательных источников, 129 факторов, 6 блоков.

## 1. Назначение backlog

Этот файл определяет единственный порядок реализации двух GEO skills. Задача
считается выполненной только после прохождения указанного acceptance gate и
сохранения проверяемого результата в Git. Переход к следующему этапу не должен
скрывать незавершённые blockers предыдущего этапа.

Статусы checklist:

- `[x]` — выполнено и подтверждено артефактом или тестом;
- `[ ]` — не начато либо ещё не прошло acceptance gate;
- `NEXT` — следующая задача по утверждённому порядку;
- `BLOCKED` — продолжение требует конкретного отсутствующего входа или доступа.

## 2. Неподлежащие изменению рамки

- Создаются ровно два новых GEO skills; существующие общие SEO skills не
  превращаются в скрытый orchestration layer.
- `seo-data-foundation` и `seo-file-audit-orchestrator` не используются.
- `seo-url-clustering` вызывается аналитическим skill автоматически через явный
  входной и выходной contract.
- Все 18 источников обязательны на source-level preflight. Отсутствующий источник
  блокирует полный audit; он не превращается в нулевое значение или зелёный статус.
- Аналитический skill измеряет и создаёт evidence. Report skill не перечитывает
  первичные данные и не создаёт новые аналитические выводы.
- Status, Priority и Confidence являются независимыми измерениями.
- `affected / analyzed` называется Betroffenheit и не выдаётся за causal или
  business impact.
- Структурные URL-prefix memberships пересчитываются из текущего crawl. Между
  аудитами можно переиспользовать только подтверждённые semantic labels и
  business criticality стабильных patterns.
- Semrush AI Visibility, server logs, analytics/CRM и удалённые из финальной
  матрицы факторы не возвращаются в scope без отдельного архитектурного решения.
- Lighthouse lab является основной PSI-базой. CrUX — только дополнительный
  контекст и не является coverage gate.
- Runtime не содержит ручного утверждения оценок каждого отчёта: все traffic
  lights и priorities рассчитываются по заранее замороженной policy.

## 3. Критическая цепочка

~~~text
Stage 0 Policy Freeze
  -> Stage 1 Contracts
  -> Stage 2 Preflight and Adapters
  -> Stage 3 Staging and Clustering
  -> Stage 4 Analysis Engine
  -> Stage 5 Deterministic Scoring Engine
  -> Stage 6 GEO Report
  -> Stage 7 End-to-End Validation and Release
  -> Final Workbench Cleanup
~~~

Ни Stage 1, ни написание SKILL.md не начинаются до `GATE P0`. Integration spike
реальных MCP tool names может выполняться только после policy freeze и не имеет
права менять scoring policy незаметно: несовместимость фиксируется как change
request с новой версией policy.

## 4. Stage 0 — Scoring Policy Design and Freeze

Цель: заранее, один раз и проверяемо определить, как каждый из 129 факторов
получает status и priority. Это policy design, а не runtime-анализ.

### GEO-000 — Architecture baseline

- [x] Зафиксированы два skills, их ответственность и handoff.
- [x] Зафиксированы 18 обязательных источников и 129 факторов.
- [x] Зафиксированы evidence model, Betroffenheit, coverage и confidence.
- [x] Зафиксированы URL-prefix hierarchy и запрет parent/child double counting.
- [x] Создан version-controlled workbench в отдельной GitHub branch.

### GEO-001 — Scoring rule schema — `NEXT`

- [ ] Определить обязательные поля одного factor rule:
  `factor_id`, `policy_version`, `rule_type`, `applicability_rule`,
  `canonical_metrics`, `measurement_universe`, `source_requirements`,
  `coverage_gate`, `evidence_grade`, `confidence_rule`, `status_bands`,
  `no_data_rule`, `dependency_role`, `base_priority`, `priority_ceiling`,
  `criticality_modifiers`, `veto_role`, `recommendation_trigger`,
  `threshold_basis`, `rationale` и `citations`.
- [ ] Определить допустимые rule types: boolean gate, threshold, prevalence,
  comparative gap, consistency и rubric.
- [ ] Формализовать `ND` и `NA` так, чтобы отсутствие данных никогда не давало
  red/yellow и не улучшало block status.
- [ ] Создать schema validation и один полный exemplar rule без placeholder-полей.

### GEO-002 — Evidence strength and confidence policy

- [ ] Определить evidence grades для direct field, deterministic calculation,
  source-limited observation, supported inference и not verifiable.
- [ ] Определить правила high/medium/low confidence через source quality,
  coverage, join quality, sample type и freshness.
- [ ] Назначить priority ceilings по confidence/evidence так, чтобы слабое evidence
  не могло автоматически создавать P0/P1, кроме явно перечисленных hard gates.
- [ ] Запретить повышение confidence за счёт количества повторов одного и того же
  зависимого источника.

### GEO-003 — Betroffenheit, coverage and materiality policy

- [ ] Зафиксировать denominator для sitewide, path-prefix cluster, semantic
  cluster, template, URL sample и source corpus.
- [ ] Определить versioned Betroffenheit bands и правила absolute-count floor.
- [ ] Разделить `full`, `representative_sample`, `diagnostic_sample` и
  `source_corpus`; определить допустимые экстраполяции для каждого scope type.
- [ ] Определить minimum coverage gates и поведение при partial record coverage.
- [ ] Зафиксировать `COUNT(DISTINCT page_url)` для sitewide roll-up и запрет
  суммирования parent/child cluster counts.

### GEO-004 — Dependency roles and causal chain

- [ ] Классифицировать каждый фактор как eligibility gate, direct observed
  outcome или supporting driver.
- [ ] Для каждого правила записать доказательную цепочку:
  `observation -> mechanism -> affected scope -> consequence -> action`.
- [ ] Отметить места, где consequence является internal policy inference, а не
  доказанной внешней причинностью.
- [ ] Создать cross-factor dependency map и правила предотвращения двойного
  приоритизирования одной root cause.

### GEO-005 — Exact rules: T block

- [ ] Определить thresholds/rubrics для всех 24 факторов T.
- [ ] Выделить hard technical veto: crawl/index/render eligibility и опасные
  canonical/robots contradictions.
- [ ] Зафиксировать GSC URL Inspection coverage при `<= 2 000` и sampling при
  большем URL universe.
- [ ] Зафиксировать Lighthouse-lab terminology и запрет подмены TBT полевым INP.

### GEO-006 — Exact rules: B block

- [ ] Определить правила всех 26 факторов B в пределах наблюдаемого SISTRIX
  corpus и sentiment snapshot.
- [ ] Не создавать полного relevant-prompt denominator из SX-P/SX-O.
- [ ] Не создавать недоказанный join `prompt -> answer -> source URL`.
- [ ] Разделить visibility, representation accuracy, prominence и sentiment.

### GEO-007 — Exact rules: C block

- [ ] Определить правила всех 27 факторов C.
- [ ] Разделить автоматически измеряемые признаки и rubric-based content review.
- [ ] Зафиксировать Site-declared Brand Truth как позицию сайта, а не независимую
  юридическую или фактическую верификацию.
- [ ] Зафиксировать handling YMYL/trust risk без недоказанных E-E-A-T scores.

### GEO-008 — Exact rules: S block

- [ ] Определить правила всех 20 факторов S.
- [ ] Разделить syntax/validation, type applicability, entity consistency и
  schema-visible-content consistency.
- [ ] Зафиксировать raw/rendered schema parity как S18 и supporting evidence, а
  не как дополнительный 130-й фактор.

### GEO-009 — Exact rules: O block

- [ ] Определить правила всех 15 факторов O.
- [ ] Разделить backlink quantities, quality distribution, recovery opportunity
  и AI source ecosystem.
- [ ] Ограничить выводы составом Ahrefs/SISTRIX exports и не подменять ими
  unlinked mentions или полное содержимое внешних страниц.

### GEO-010 — Exact rules: M block

- [ ] Определить правила всех 17 факторов M.
- [ ] Сохранить названия Observed Prompt Count вместо недоступных universal rates.
- [ ] Разделить snapshot, time series, first-party GAI export и source coverage.
- [ ] Не возвращать Business Impact и причинную атрибуцию.

### GEO-011 — Deterministic priority policy

- [ ] Определить base priority для каждого factor/dependency role.
- [ ] Определить priority floors только для доказанных hard gates и accuracy/
  reputational risks.
- [ ] Определить ceilings по confidence, coverage и sample type.
- [ ] Формализовать modifiers для Betroffenheit, absolute affected count,
  confirmed cluster criticality, model/country scope, reversibility и risk.
- [ ] Effort хранить отдельно; разрешить Quick Win label, но запретить effort
  повышать важность проблемы.
- [ ] Определить deterministic tie-break и порядок сортировки Summary.

### GEO-012 — Block veto and block roll-up policy

- [ ] Для каждого из шести блоков определить red veto, yellow conditions,
  material combinations и minimum coverage gate.
- [ ] Запретить простое среднее цветов и скрытое числовое усреднение ordinal
  traffic-light labels.
- [ ] Определить поведение red с low confidence и конфликтующего evidence.
- [ ] Проверить, что block green невозможен при недостаточном coverage.

### GEO-013 — Overall roll-up policy

- [ ] Определить overall veto и допустимые комбинации block statuses.
- [ ] Определить общий coverage gate.
- [ ] Зафиксировать порядок `red / yellow / green / ND` без преобразования ND в
  негативную оценку.
- [ ] Проверить, что один supporting-driver factor не может без специального veto
  сделать весь audit red.

### GEO-014 — Human-readable policy and provenance

- [ ] Создать полную понятную policy для будущего
  `seo-geo-report-generator/README.md`.
- [ ] Для каждого threshold указать basis category: official hard rule,
  official guidance, empirical association, deterministic derivation или
  internal audit policy.
- [ ] Не выдавать internal audit policy за научно доказанную универсальную
  важность.
- [ ] Обеспечить однозначную трассировку README rule ↔ YAML rule ↔ factor ID.

### GEO-015 — Boundary and adversarial fixtures

- [ ] Создать тесты на значение точно на границе и по обе стороны каждого
  threshold.
- [ ] Создать fixtures для zero denominator, partial coverage, low confidence,
  conflicting sources, valid empty export, nested clusters и stale mappings.
- [ ] Создать priority tests для одинакового status при разных Betroffenheit и
  cluster criticality.
- [ ] Создать roll-up tests для veto, insufficient coverage и all-green cases.
- [ ] Проверить повторяемость: одинаковый scored input всегда даёт byte-stable
  normalized scoring output.

### GATE P0 — Scoring Policy Freeze

- [ ] Ровно 129 уникальных factor IDs имеют полный rule.
- [ ] Ни одно обязательное поле не заполнено placeholder или runtime discretion.
- [ ] Все thresholds имеют basis и rationale.
- [ ] Все priority ceilings и veto перечислены явно.
- [ ] README-policy и machine-policy совпадают по version, hash и rule IDs.
- [ ] Все boundary/adversarial fixtures проходят.
- [ ] Policy получает immutable version; последующее изменение требует version
  bump, rationale и regression tests.

## 5. Stage 1 — Contracts and repository skeleton

### GEO-100 — Create final project structure

- [ ] Создать `.claude/geo-audit/contracts/`, fixtures и ровно два новых skill
  directories.
- [ ] Держать SKILL.md компактными; подробные schemas/methods разместить в
  references, повторяемую детерминированную обработку — в scripts.
- [ ] Зафиксировать explicit-only invocation обоих новых skills.

### GEO-101 — Source and factor catalogs

- [ ] Перенести 18 sources в `source-catalog.yaml` с `required: true`.
- [ ] Перенести 129 factors в `factor-catalog.yaml` без изменения ID.
- [ ] Для каждого factor связать sources, method, coverage, applicability,
  evidence contract и scoring rule ID.

### GEO-102 — Frozen scoring artifacts

- [ ] Разместить frozen machine policy в `scoring-matrix.yaml`.
- [ ] Разместить human-readable policy в README report skill.
- [ ] Добавить version/hash cross-validation.

### GEO-103 — Schemas and DuckDB DDL

- [ ] Создать audit config, analysis package и report package JSON Schemas.
- [ ] Создать versioned DuckDB DDL для raw, staging, canonical, derived,
  clustering, evidence, factors и recommendations.
- [ ] Определить migrations и backward-compatibility policy.

### GEO-104 — Contract validation

- [ ] Проверить counts `18 / 129` и распределение `24/26/27/20/15/17`.
- [ ] Проверить все references и rule IDs.
- [ ] Добавить negative fixtures для missing/duplicate/unknown IDs.

### GATE A — Contracts

- [ ] Все contracts валидируются автономно.
- [ ] Нет циклической или несуществующей ссылки между catalogs/schemas/policy.
- [ ] Ни один runtime step не требует придумать отсутствующее правило.

## 6. Stage 2 — Preflight and source adapters

### GEO-200 — Audit skill entrypoint and state machine

- [ ] Создать `seo-geo-audit/SKILL.md` и run states.
- [ ] Реализовать safe resume, idempotency и blocking actions.
- [ ] Запрашивать только отсутствующие brand/domain/country/language/model/scope
  параметры.

### GEO-201 — Screaming Frog MCP probe

- [ ] Выполнить реальный harmless read, а не проверку имени tool.
- [ ] Подтвердить crawl timestamp/domain/HTML universe и наличие SF, RAW, REN,
  PSI, GSC-SA и GSC-UI данных.
- [ ] Зафиксировать реальные callable names и response schemas adapter version.

### GEO-202 — SISTRIX MCP probe and cost plan

- [ ] Запросить `ai.models`, проверить необходимые модели.
- [ ] Выполнить минимальный `ai.check.overview` для brand/domain/country.
- [ ] Зафиксировать schemas overview/competitors/prompts/prompts.count/sources.
- [ ] Рассчитать requests и credit lower/expected/upper bound без придуманной
  точности.

### GEO-203 — Mandatory file inventory

- [ ] Обнаружить Ahrefs Backlinks, Referring Domains и Broken Backlinks.
- [ ] Обнаружить Dejan export/result, SISTRIX Sentiment MHTML и GSC-GAI export.
- [ ] Для каждого файла сохранить path, SHA-256, size, schema fingerprint,
  snapshot date, row count, scope и freshness.
- [ ] Для каждого отсутствующего источника выдать точное напоминание о требуемом
  подключении или файле.

### GEO-204 — Secure parsers and adapters

- [ ] Реализовать ZIP path-traversal protection.
- [ ] Разбирать MHTML как MIME multipart/related с transfer decoding.
- [ ] Реализовать multilingual Ahrefs/GSC/Dejan tabular adapters.
- [ ] Запретить remote resource loading из MHTML.

### GEO-205 — Readiness and source coverage

- [ ] Реализовать access/data/scope/freshness/blocking status для всех 18 sources.
- [ ] Различать missing source и доказанный valid empty export.
- [ ] Разрешать `READY_WITH_GAPS` только для документированных record-level gaps.

### GATE B — Preflight

- [ ] Реальные MCP probes и file fingerprints проходят.
- [ ] Source-level absence переводит run в WAITING/BLOCKED.
- [ ] Cost plan и ограничения сохранены в manifest.
- [ ] Resume не дублирует запросы или artifacts.

## 7. Stage 3 — Staging, normalization and clustering

### GEO-300 — Layered ingestion

- [ ] Сохранять immutable raw artifact/reference, staging, canonical и derived
  layers с provenance.
- [ ] Один writer владеет DuckDB; каждый source adapter использует transaction.
- [ ] Реализовать row counts, duplicate checks и schema drift handling.

### GEO-301 — URL normalization and joins

- [ ] Версионировать URL normalization rules.
- [ ] Сохранять original URL и canonical join URL.
- [ ] Каждый non-exact join получает method, confidence и join-quality result.
- [ ] Запретить fuzzy join как автоматическое direct evidence.

### GEO-302 — Clustering invocation contract

- [ ] Обновить `seo-url-clustering` так, чтобы он принимал явные run/table/field
  параметры без `seo-data-foundation` и `seo-file-audit-orchestrator`.
- [ ] `seo-geo-audit` вызывает clustering автоматически после SF staging.
- [ ] Пользователь подтверждает только новые/изменившиеся semantic labels и
  business criticality; structural processing автоматическое.

### GEO-303 — Prefix hierarchy and memberships

- [ ] Для каждого normalized HTML URL создать memberships во всех prefixes,
  включая root `/`.
- [ ] Проверить unique `(page_url, cluster_id)`, valid parent, acyclic tree и
  current crawl-universe hash.
- [ ] Не переносить URL lists/counts/numerators/denominators между runs.
- [ ] Применять project mapping только к совпавшим stable patterns.

### GEO-304 — GSC URL Inspection selection

- [ ] При `<= 2 000` HTML URL выбирать полный universe.
- [ ] При большем сайте строить deterministic cluster-stratified selection не
  более 2 000 URL с отдельно помеченными diagnostic/critical additions.
- [ ] Не экстраполировать diagnostic sample как representative sample.

### GATE C/D — Staging and Clustering

- [ ] Canonical schemas, transactions, hashes и joins валидны.
- [ ] Vertical/horizontal rows покрывают весь HTML universe.
- [ ] Prefix tree и memberships проходят invariants.
- [ ] Sitewide counts воспроизводятся через distinct URLs без double counting.

## 8. Stage 4 — Analysis engine and evidence

### GEO-400 — Shared analysis methods

- [ ] Реализовать raw/rendered parity и mapping в T16, T17, S18 и supporting
  factors без создания дополнительного factor ID.
- [ ] Реализовать Site-declared Brand Truth extraction с provenance.
- [ ] Реализовать cluster-level affected/analyzed/coverage metrics.

### GEO-401–406 — Factor methods by block

- [ ] `GEO-401`: T — 24 factor methods.
- [ ] `GEO-402`: B — 26 factor methods.
- [ ] `GEO-403`: C — 27 factor methods.
- [ ] `GEO-404`: S — 20 factor methods.
- [ ] `GEO-405`: O — 15 factor methods.
- [ ] `GEO-406`: M — 17 factor methods.
- [ ] Каждая из 129 строк создаётся даже при ND/NA/source error.

### GEO-407 — Evidence ledger

- [ ] Создать evidence UUIDs, source hash, locator/query fingerprint, grain,
  numerator/denominator, examples, method version и limitations.
- [ ] После data-quality gate атомарно выделять финальные E-NNNN.
- [ ] Проверить глобальную уникальность и отсутствие recycling evidence ID.

### GEO-408 — Findings and recommendations

- [ ] Создавать finding только из factor result и evidence.
- [ ] Создавать recommendation candidates без status/priority improvisation.
- [ ] Дедуплицировать root causes и сохранять factor/evidence linkage.
- [ ] Запретить unsupported causal, bot-visit и citation-absorption claims.

### GEO-409 — Analysis package

- [ ] Создать единственный официальный handoff `analysis-package.json`.
- [ ] Зафиксировать source coverage, factors, evidence, findings,
  recommendations, clusters и limitations.
- [ ] Report skill не получает права читать chat notes или первичные exports.

### GATE E — Analysis

- [ ] Ровно 129 factor results и все evidence references разрешены.
- [ ] Counts/denominators/coverage воспроизводимы.
- [ ] Нет запрещённых joins и причинных утверждений.
- [ ] Package имеет `ANALYSIS_COMPLETE` или допустимый
  `ANALYSIS_COMPLETE_WITH_GAPS`.

## 9. Stage 5 — Deterministic scoring engine

### GEO-500 — Report input gate

- [ ] Валидировать run status, schemas, catalogs, 129 factor IDs, evidence,
  source-level gate и cluster arithmetic.
- [ ] При несовместимости выдавать repair actions и не строить report.

### GEO-501 — Apply frozen factor rules

- [ ] Загружать только совместимую frozen `scoring-matrix.yaml`.
- [ ] Проверять policy version/hash до scoring.
- [ ] Рассчитывать factor Status, Priority и Confidence без model discretion.
- [ ] Сохранять rule ID/version, inputs, thresholds и result.

### GEO-502 — Roll-ups and scored package

- [ ] Применять frozen block/overall veto и coverage rules.
- [ ] Создать versioned scored-factor output.
- [ ] Обеспечить deterministic sorting и byte-stable normalized output.

### GATE F — Scoring

- [ ] Все boundary/adversarial tests проходят на исполняемом engine.
- [ ] Engine полностью воспроизводит frozen policy examples.
- [ ] Ни один status/priority не возникает из свободного текста модели.

## 10. Stage 6 — Dedicated GEO report skill

### GEO-600 — Report skill entrypoint

- [ ] Создать новый `seo-geo-report-generator`; не расширять generic SEO skill
  GEO-логикой.
- [ ] Принимать только validated scored analysis package.
- [ ] Зафиксировать explicit user invocation и read-only DuckDB access.

### GEO-601 — Report model

- [ ] Summary: scope, overall/block lights, coverage и только red findings.
- [ ] Gesamtbericht: все 129 факторов с Status, Priority, Confidence,
  Betroffenheit/Abdeckung, rationale, recommendation и evidence.
- [ ] Добавить appendices источников, методов, limitations и scoring policy.

### GEO-602 — German wording policy

- [ ] German по умолчанию, configurable.
- [ ] Для каждой строки объяснить почему фактор важен и почему получена оценка.
- [ ] Не использовать causal language сверх evidence.
- [ ] ND/NA показывать серым с точной причиной.

### GEO-603 — DOCX/PDF renderer

- [ ] Переиспользовать только подходящие статические rendering helpers; GEO
  business logic остаётся в новом skill.
- [ ] Создать landscape A4 layouts, page breaks, legends и accessible tables.
- [ ] Сгенерировать DOCX и PDF из одного report model.

### GEO-604 — Content and visual validation

- [ ] Проверить 129 строк, red-only Summary, evidence IDs и recommendations.
- [ ] Проверить отсутствие truncation, overflow, broken tables и пустых страниц.
- [ ] Render-and-inspect все страницы до release.

### GATE G/H — Report and Visual

- [ ] Summary и Gesamtbericht соответствуют contract.
- [ ] README policy совпадает с YAML policy.
- [ ] DOCX/PDF content checks и visual QA проходят.

## 11. Stage 7 — End-to-end validation and release

### GEO-700 — Synthetic fixture suite

- [ ] Minimal complete, >2 000 URLs, malformed input, valid empty export,
  missing source, stale source, conflicting data и nested-prefix fixtures.
- [ ] Проверить WAITING/BLOCKED/READY/COMPLETE transitions.

### GEO-701 — Reproducibility and recovery

- [ ] Два runs на идентичных inputs дают идентичные normalized metrics, scoring
  и report model.
- [ ] Проверить interruption/resume на каждом долгом этапе.
- [ ] Проверить отсутствие duplicate API requests/evidence IDs после resume.

### GEO-702 — Sanitised real audit

- [ ] Выполнить полный аудит на обезличенном realistic dataset всех 18 sources.
- [ ] Проверить каждый red finding до source artifact и evidence locator.
- [ ] Проверить разумность recommendations без ручной коррекции traffic lights.

### GEO-703 — Security and operational validation

- [ ] Secret scan, ZIP traversal, hostile MHTML, oversized input и schema drift.
- [ ] Проверить SISTRIX credit guard, retries и rate-limit handling.
- [ ] Проверить, что репозиторий не содержит client inputs или credentials.

### GEO-704 — Documentation and release

- [ ] Обновить root README только для новых GEO skills и их invocation.
- [ ] Запустить skill validators, contract/unit/E2E tests и repository checks.
- [ ] Создать reviewable PR из рабочей ветки; merge только после зелёных checks.
- [ ] Зафиксировать release/version и immutable policy version.

### GATE I — Production-ready Definition of Done

- [ ] Аналитический skill собирает данные и выдаёт validated analysis package.
- [ ] Report skill детерминированно применяет policy и создаёт DOCX/PDF.
- [ ] Любая оценка трассируется до factor rule и evidence.
- [ ] Все 18 sources, 129 factors и шесть блоков проходят contracts.
- [ ] Missing data не превращается в negative finding.
- [ ] URL clusters и Betroffenheit не содержат double counting.
- [ ] Полный E2E run воспроизводим и восстанавливается после interruption.

## 12. Final workbench cleanup

Эта секция выполняется только после `GATE I`.

- [ ] Перенести долговечные policies, schemas и methods в final contracts,
  skill README и references.
- [ ] Проверить, что ни один final file не ссылается на workbench как runtime
  dependency.
- [ ] Удалить `methodology/geo-audit-workbench/` отдельным cleanup commit.
- [ ] Сохранить ссылку на последний pre-cleanup commit/PR как исторический audit
  trail.
- [ ] Удалить рабочую branch только после merge и проверки доступности истории.

## 13. Текущая следующая задача

Начать с `GEO-001 — Scoring rule schema`. До завершения `GATE P0` не создавать
implementation skeleton новых skills и не распределять thresholds во время
runtime. Это делает аргументацию traffic lights и priorities заранее
опубликованной, версионированной и воспроизводимой.

## 14. Нормативные ссылки для реализации

- [GEO architecture](GEO_SKILLS_DETAILED_IMPLEMENTATION_PLAN.md)
- [GEO source and factor matrix](GEO_audit_sources_and_factor_matrix_FINAL.md)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [RFC 3986, URI path hierarchy](https://www.rfc-editor.org/rfc/rfc3986#section-3.3)
- [DuckDB transactions](https://duckdb.org/docs/stable/sql/statements/transactions)
- [GitHub branches](https://docs.github.com/en/pull-requests/reference/branches)
