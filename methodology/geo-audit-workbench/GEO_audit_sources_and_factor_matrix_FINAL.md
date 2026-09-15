# GEO-аудит: финальный реестр источников и матрица факторов

Дата фиксации: 15 сентября 2026 года.
Архитектурная редакция: 1.2.

## 1. Граница анализа

Матрица содержит только факторы, которые можно исследовать на основании согласованного набора данных. Строки с покрытием «Нет», блок Business Impact и отдельно исключённые пользователем строки удалены. Пропуски в ID намеренные и сохраняют трассируемость решений.

Уровни покрытия:

- **Полное** — фактор измеряется непосредственно или однозначно рассчитывается в пределах указанного источника.
- **Полное (snapshot)** — фактор полностью представлен в сохранённом снимке на дату выгрузки, но сам снимок не является временным рядом.
- **Условное** — полнота определяется размером сайта, наличием строк или конкретных полей в выгрузке.
- **Частичное** — доступен доказательный анализ части фактора; граница прямо указана в строке.

## 2. Финальный список источников данных

| Код | Источник | Доступные данные и роль в аудите | Важная граница |
|---|---|---|---|
| `SF` | Screaming Frog SEO Spider | Полный crawl-инвентарь и нативные метрики: URL, статусы, indexability, redirects, canonicals, robots directives, sitemap, depth, inlinks/outlinks, anchors, headings, metadata, word count, readability, hashes/duplicates, hreflang, schema, изображения, формы, accessibility и технические ошибки | Показывает состояние сайта во время crawl, а не фактическое поведение внешнего AI-бота |
| `RAW` | Original HTML из Screaming Frog | Исходный HTML-ответ до выполнения JavaScript | Полнота зависит от crawl scope и выбранного user-agent |
| `REN` | Rendered HTML из Screaming Frog | DOM после выполнения JavaScript, включая JS-контент, ссылки, metadata и schema | Это рендер Chromium/SF, а не доказательство рендеринга конкретным AI-ботом |
| `PSI` | PageSpeed Insights API по URL | Lighthouse lab-аудиты для каждого успешно протестированного URL: performance, accessibility, best practices, SEO, mobile/desktop strategy, audits, diagnostics и opportunities; возвращённые CrUX-поля используются только как дополнительный контекст | Основная URL-level оценка и светофор строятся по Lighthouse lab; отсутствие CrUX не уменьшает покрытие и не меняет lab-статус |
| `GSC-SA` | Google Search Console Search Analytics API | Дата, query, page, country, device, search appearance, clicks, impressions, CTR, position | Это Google Search data; используем только реально возвращённые измерения |
| `GSC-UI` | Google Search Console URL Inspection API | Verdict, coverage/index state, user/Google canonical, crawl/fetch и связанные inspection-поля | Правило аудита: до 2 000 URL; при большем сайте анализируется максимум 2 000 URL |
| `GSC-GAI` | Экспорт Generative AI Performance Report из Search Console | Generative-AI impressions, pages, countries, devices и временная динамика, присутствующие в файле | Файловый snapshot/export, не API-поток |
| `AH-BL` | Ahrefs Backlinks export | Backlink-level поля: referring/target URL, anchor, link attributes и остальные включённые в экспорт метрики | Анализ ограничен датой и составом выгрузки |
| `AH-RD` | Ahrefs Referring Domains export | Domain-level backlink profile и метрики referring domains | Не заменяет анализ нессылочных brand mentions |
| `AH-BB` | Ahrefs Broken Backlinks export | Входящие ссылки на недоступные целевые URL, anchors, referring pages и доступные authority-поля | Полнота соответствует экспорту Ahrefs |
| `SX-M` | SISTRIX `ai.models` | Актуальный перечень доступных AI-моделей и их кодов | Наличие модели в справочнике не гарантирует строки по каждому бренду |
| `SX-O` | SISTRIX `ai.check.overview` | Scope, `prompt_count`, разбивки по модели и стране для mentions/citations/combined | Это число обнаруженных промптов, а не доля от всех релевантных пользовательских запросов |
| `SX-C` | SISTRIX `ai.check.competitors` | Список брендов-конкурентов в том же AI environment с фильтрами model/country | API документирует список брендов, но не полноценный конкурентный SOV denominator |
| `SX-P` | SISTRIX `ai.check.prompts` | Prompt, model, generated answer/message и country для возвращённых записей | В набор попадают промпты, где бренд уже упомянут или домен уже процитирован |
| `SX-PC` | SISTRIX `ai.check.prompts.count` | Исторические пары `date` + `prompt_count`, с фильтрами model/country | История агрегирована по дню; это не история текста каждого ответа |
| `SX-S` | SISTRIX `ai.check.sources` | Cited host/domain/URL, `amount`, `prompt_count`, model и country | Нет гарантированного ключа `prompt → answer → source URL` |
| `SX-SENT` | MHTML страницы SISTRIX Sentiment GUI | Общий sentiment score, Lob/Kritik, распределение, платформенные scores, тематическая балансировка, сильные/слабые стороны, quotes, sources, competitor context и benchmark | Требуется актуальный MHTML для каждого бренда; полный только для зафиксированного snapshot и показанных платформ |
| `DJ` | Dejan AI Agent Access export/result | Интерпретация robots.txt для известных AI crawlers/agents и дополнительный blocking test | Показывает разрешение/блокировку в момент теста, но не фактический crawl |

Semrush AI Visibility не используется. Server logs, web analytics/CRM, Microsoft first-party AI reports и Business Impact в матрицу не входят.

Все 18 перечисленных источников являются обязательными для source-level preflight. Отсутствующий файл, недоступный MCP, authentication failure, scope mismatch или нераспознанная schema блокируют полный audit и вызывают явное напоминание с требуемым действием. Record-level failures внутри присутствующего источника отражаются через coverage/ND и не превращаются ни в ноль, ни в отрицательную оценку.

## 3. Матрица анализируемых GEO-факторов

### T — Technical AI Eligibility

| ID | Фактор | Что анализируем | Источники | Покрытие |
|---|---|---|---|---|
| `T01` | Crawl-инвентарь | Полнота списка внутренних HTML-URL, типы ресурсов, поддомены и границы crawl | `SF` | Полное |
| `T02` | HTTP-доступность | 2xx/3xx/4xx/5xx, no-response, конечные URL и ошибки загрузки | `SF` | Полное |
| `T03` | Robots.txt для поисковых краулеров | Allow/Disallow, sitemap directives и конфликтующие правила | `SF`, `RAW` | Полное |
| `T04` | Доступ AI-агентов | Разрешение или блокировка известных AI crawlers и agents | `DJ`, `SF` | Полное для конфигурации доступа |
| `T05` | Meta Robots и X-Robots-Tag | `index/noindex`, `follow/nofollow`, snippet/image/translation directives и конфликты | `SF`, `RAW`, `REN` | Полное |
| `T06` | Indexability | Итоговый indexability status и техническая причина исключения | `SF` | Полное |
| `T08` | XML Sitemap | Валидность, статусы sitemap URL, indexable/non-indexable URLs, пропуски и лишние URL | `SF` | Полное |
| `T09` | Canonicalization | Self-canonical, canonical targets, chains, loops, non-indexable targets и raw/rendered mismatch | `SF`, `RAW`, `REN` | Полное |
| `T10` | Google index status | Indexed/not indexed, coverage state, selected canonical, crawl/fetch state для проверяемых URL | `GSC-UI`, `SF` | Полное при ≤2 000 URL; максимум 2 000 URL при большем сайте |
| `T11` | Redirect integrity | Redirect chains, loops, temporary/permanent redirects, redirect targets и internal links to redirects | `SF` | Полное |
| `T12` | Crawl depth | Распределение URL по глубине и удалённость коммерчески важных страниц | `SF` | Полное |
| `T13` | Internal link graph | Inlinks, unique inlinks, outlinks, anchors, link position и распределение внутренних ссылок | `SF` | Полное |
| `T14` | Orphan-page candidates | URL из sitemap/GSC без внутренних crawlable inlinks | `SF`, `GSC-SA`, `GSC-UI` | Частичное: выявляет кандидатов в пределах объединённого инвентаря |
| `T15` | Rendered-content availability | Наличие основного текста, ссылок, metadata и schema в отрендерованном DOM | `REN`, `SF` | Полное |
| `T16` | Зависимость от JavaScript | Контент и элементы, отсутствующие в raw HTML и появляющиеся только после JS | `RAW`, `REN`, `SF` | Полное |
| `T17` | Raw/rendered parity | JS-изменения title, description, H1, canonical, robots, hreflang, links и structured data | `RAW`, `REN`, `SF` | Полное |
| `T18` | JS и resource errors | Ошибки JavaScript, blocked resources, неуспешные resource requests и последствия для DOM | `SF`, `REN` | Полное |
| `T19` | Hreflang integrity | Коды языка/региона, return links, canonicals, non-200 targets и конфликтующие annotations | `SF`, `RAW`, `REN` | Полное |
| `T20` | Mobile/desktop rendering | Различия доступности, финального URL и ключевых элементов между Lighthouse lab-запусками mobile/desktop и crawl-представлением | `PSI`, `SF`, `REN` | Полное в пределах фактически запущенных PSI strategies; CrUX не требуется |
| `T21` | Page performance — Lighthouse lab | Lighthouse performance score, lab-метрики FCP, LCP, Speed Index, TBT и CLS, audits, diagnostics, opportunities, runtime errors и URL-level bottlenecks | `PSI`, `SF` | Полное для Lighthouse lab по каждому успешно протестированному URL; отсутствие CrUX не уменьшает покрытие |
| `T22` | Crawl-budget risk | Масштаб дублей, глубина, redirect/error URLs, параметры и технически ненужные crawlable URL | `SF` | Полное |
| `T23` | Duplicate-content mechanics | Exact/near duplicates, hashes, duplicated titles/descriptions/H1 и canonical handling | `SF`, `RAW`, `REN` | Полное |
| `T24` | URL и response efficiency | URL parameters, длина/формат URL, response time, page size и тяжёлые ресурсы | `SF`, `PSI` | Полное |
| `T25` | Agent-friendly accessibility | Labels, roles, accessible names, forms/controls, WCAG/axe issues и PSI accessibility audits | `SF`, `PSI`, `REN` | Полное для автоматизированных проверок |

### B — AI Visibility, Brand Representation & Sentiment

| ID | Фактор | Что анализируем | Источники | Покрытие |
|---|---|---|---|---|
| `B01` | Целостность scope SISTRIX | Домен/бренд, выбранные модели, страны и фильтры, к которым относятся результаты | `SX-O`, `SX-P`, `SX-S`, `SX-C`, `SX-SENT` | Полное в пределах выгрузок и snapshot |
| `B02` | Observed Brand Prompt Count | Число обнаруженных промптов, в ответах на которые бренд упомянут | `SX-O` | Полное для метрики SISTRIX |
| `B03` | Observed Domain Citation Prompt Count | Число обнаруженных промптов, в ответах на которые процитирован анализируемый домен | `SX-O` | Полное для метрики SISTRIX |
| `B04` | Observed Combined Visibility Prompt Count | Число обнаруженных промптов с упоминанием бренда и/или цитированием домена согласно полю scope | `SX-O` | Полное для метрики SISTRIX |
| `B06` | Покрытие AI-моделей | Какие модели доступны в SISTRIX и по каким моделям реально возвращены результаты | `SX-M`, `SX-O`, `SX-P`, `SX-S` | Полное в пределах SISTRIX |
| `B07` | Географическое покрытие | Страны в scope и распределение найденной видимости по странам | `SX-O`, `SX-P`, `SX-S` | Полное в пределах возвращённых данных |
| `B08` | Инвентарь обнаруженных промптов | Формулировки prompt, model, country и связанные с ними сгенерированные ответы | `SX-P` | Полное для возвращённых SISTRIX записей |
| `B09` | Текст AI-ответов | Содержание generated answer/message по каждому возвращённому prompt record | `SX-P` | Полное для возвращённых SISTRIX записей |
| `B10` | Контекст упоминания бренда | За что, для кого и в каком утверждении бренд упоминается в доступном ответе | `SX-P`, `SX-SENT` | Полное для доступных текстов ответов и примеров snapshot |
| `B11` | Ландшафт цитируемых источников | Hosts, domains, URLs, их `amount` и `prompt_count`, включая собственные и внешние источники | `SX-S` | Полное на агрегированном уровне SISTRIX |
| `B12` | Набор AI-конкурентов | Бренды, которые SISTRIX относит к конкурентам в выбранном AI environment | `SX-C`, `SX-SENT` | Полное в пределах SISTRIX |
| `B13` | Конкурентный контекст | В каких формулировках, категориях и сравнениях появляются бренд и конкуренты | `SX-P`, `SX-C`, `SX-SENT` | Полное для доступных ответов и snapshot |
| `B14` | Prominence в доступных ответах | Порядок, раздел, роль и заметность упоминания бренда внутри возвращённого текста ответа | `SX-P` | Полное для возвращённых ответов; не является общей долей всех ответов |
| `B15` | Атрибуты и narrative бренда | Повторяющиеся свойства, преимущества, ограничения и целевые аудитории, приписываемые бренду | `SX-P`, `SX-SENT` | Полное для доступного корпуса |
| `B16` | Сравнения и альтернативы | С какими брендами сравнивают, по каким критериям и в какой роли рекомендуют | `SX-P`, `SX-C`, `SX-SENT` | Полное для доступного корпуса |
| `B17` | Фактическая согласованность AI-представления | Совпадают ли доступные AI-утверждения с фактами, явно заявленными на сайте: продукты, аудитории, цены, регионы, условия и ограничения | `SX-P`, `SX-SENT`, `REN`, `RAW`, `SF` | Частичное: проверяет согласованность с сайтом, но не внешнюю истинность утверждений |
| `B18` | Brand sentiment в AI-ответах | Общий sentiment score и преобладающая тональность бренда | `SX-SENT` | Полное (snapshot) |
| `B19` | Sentiment по AI-платформам | Отдельные sentiment scores для платформ, показанных на странице SISTRIX Sentiment | `SX-SENT` | Полное (snapshot) для показанных платформ |
| `B20` | Lob/Kritik distribution | Число и доля позитивных и критических оценочных упоминаний | `SX-SENT` | Полное (snapshot) |
| `B21` | Тематический sentiment | Mention counts и баланс по темам, например продукт, сервис, функциональность и цена | `SX-SENT` | Полное (snapshot) |
| `B22` | Сильные и слабые стороны | Сформулированные SISTRIX позитивные и негативные brand themes | `SX-SENT` | Полное (snapshot) |
| `B23` | Sentiment benchmark | Percentile/позиция бренда относительно показанной группы сравнения и размер базы | `SX-SENT` | Полное (snapshot) |
| `B24` | Примеры и источники sentiment | Доступные фрагменты ответов, платформы, cited URLs и source types, которыми иллюстрируется оценка | `SX-SENT` | Полное для примеров snapshot |
| `B25` | Историческая динамика prompt count | Дневной ряд обнаруженных промптов в заданном model/country scope | `SX-PC` | Полное для агрегированного временного ряда SISTRIX |
| `B26` | First-party Generative AI visibility | Показы в Generative AI surfaces Google и их динамика | `GSC-GAI` | Полное в пределах предоставленного экспорта |
| `B27` | First-party GAI landing-page coverage | Страницы, страны и устройства, по которым Google зафиксировал Generative AI impressions | `GSC-GAI` | Полное в пределах предоставленного экспорта |

### C — Content, Evidence & Brand Truth

| ID | Фактор | Что анализируем | Источники | Покрытие |
|---|---|---|---|---|
| `C01` | Семантическая релевантность | Соответствие страниц темам, intents и формулировкам, наблюдаемым в GSC и SISTRIX | `REN`, `RAW`, `SF`, `GSC-SA`, `SX-P` | Полное в пределах наблюдаемого спроса и prompt corpus |
| `C02` | Прямота ответа | Есть ли ясный ответ, определение или вывод рядом с формулировкой пользовательского вопроса | `REN`, `RAW`, `SX-P` | Полное |
| `C03` | Информационная архитектура | H1–H6, порядок секций, абзацы, списки, таблицы, навигация и логика раскрытия темы | `SF`, `REN`, `RAW` | Полное |
| `C04` | Title и description | Уникальность, соответствие intent, ясность объекта страницы и согласованность raw/rendered metadata | `SF`, `RAW`, `REN`, `GSC-SA` | Полное |
| `C05` | Тематическая полнота | Предпосылки, варианты, исключения, преимущества/риски, аудитории, альтернативы и следующие вопросы | `REN`, `RAW`, `GSC-SA`, `SX-P` | Полное в пределах доступного корпуса запросов и промптов |
| `C06` | Извлекаемые определения | Ясные определения сущностей, услуг, процессов и терминов | `REN`, `RAW` | Полное |
| `C07` | Извлекаемые факты | Числа, спецификации, цены, сроки, география, требования, условия и другие проверяемые утверждения | `REN`, `RAW`, `SF` | Полное |
| `C08` | Сравнения и таблицы | Явные критерии сравнения, структурированные альтернативы и корректно размеченные таблицы | `REN`, `RAW` | Полное |
| `C09` | Процессы и шаги | Последовательности действий, prerequisites, outcomes и исключения | `REN`, `RAW` | Полное |
| `C10` | FAQ-контент | Реальные вопросы пользователей, качество ответов, отсутствие дублирования и соответствие странице | `REN`, `RAW`, `GSC-SA`, `SX-P` | Полное |
| `C11` | Явность сущности и бренда | Однозначные название, тип организации, сфера деятельности, география и связи с продуктами/услугами | `REN`, `RAW`, `SF` | Полное |
| `C12` | Продукты, услуги и аудитории | Что предлагается, кому, где, в каких вариантах и для каких use cases | `REN`, `RAW`, `SX-P` | Полное |
| `C13` | Дифференциация | Конкретные и подтверждаемые отличия бренда от альтернатив вместо общего маркетингового текста | `REN`, `RAW`, `SX-P`, `SX-C` | Полное в пределах наблюдаемого конкурентного корпуса |
| `C14` | Условия и ограничения | Цены, доступность, eligibility, exclusions, риски, региональные и продуктовые ограничения | `REN`, `RAW` | Полное |
| `C17` | Идентификация автора | Имя автора/редакции, author page, publisher и связь с материалом | `REN`, `RAW`, `SF` | Полное |
| `C18` | Наблюдаемые сигналы экспертизы | Биография, должность, квалификация, опыт, профиль и способы проверки авторства | `REN`, `RAW`, `SF` | Частичное: наличие сигналов проверяется, реальная квалификация не подтверждается автоматически |
| `C19` | Даты и актуальность | Published/modified dates, устаревшие факты, признаки обновления и согласованность дат | `REN`, `RAW`, `SF` | Полное |
| `C20` | Доказательность и источники | Наличие методики, первичных данных, ссылок и соответствие внешней ссылки соседнему утверждению | `REN`, `RAW`, `SF` | Частичное: соответствие можно проверить, но не гарантировать истинность всех внешних материалов |
| `C21` | Оригинальный информационный вклад | Собственные данные, исследования, расчёты, кейсы, опыт, методология и уникальные примеры | `REN`, `RAW` | Частичное: наблюдаемая оригинальность без доказательства авторства данных |
| `C22` | Trust и ответственность | Контакты, Impressum/legal pages, policies, редакционная ответственность, поддержка и прозрачность организации | `REN`, `RAW`, `SF` | Полное |
| `C23` | Межстраничная согласованность | Противоречия в названиях, ценах, свойствах, условиях, географии, лицах и датах | `REN`, `RAW`, `SF` | Полное |
| `C24` | Site-declared Brand Truth Set | Нормализованный набор явно заявленных на сайте фактов о бренде, продуктах, аудиториях, ценах, географии и ограничениях | `REN`, `RAW`, `SF` | Полное как описание позиции сайта; не является независимой верификацией |
| `C25` | Локализованная субстанция | Язык, локальные продукты, валюты, законы, примеры, терминология и пользовательские проблемы | `REN`, `RAW`, `GSC-SA`, `SX-P` | Полное |
| `C26` | Читаемость и сканируемость | Длина предложений/абзацев, readability, структура, ясность терминов и визуальная иерархия | `SF`, `REN`, `RAW` | Полное |
| `C27` | Контекст и доступность медиа | Alt text, captions, surrounding text, dimensions, loadability и дублирование информации из изображений/видео в HTML | `SF`, `REN`, `RAW`, `PSI` | Полное для автоматизированно наблюдаемых признаков |
| `C28` | Thin, duplicate и scaled content | Шаблонные вариации, слабый информационный вклад, exact/near duplicates и массовые URL-patterns | `SF`, `REN`, `RAW` | Полное |
| `C29` | Freshness относительно спроса | Соответствие актуальности контента темам/запросам с текущими GSC-показами и обнаруженными AI prompts | `REN`, `RAW`, `SF`, `GSC-SA`, `SX-P`, `SX-PC` | Полное в пределах доступных дат и корпусов |

### S — Structured Data & Entity Consistency

| ID | Фактор | Что анализируем | Источники | Покрытие |
|---|---|---|---|---|
| `S01` | Наличие и форматы schema | JSON-LD, Microdata/RDFa и покрытие разметкой по шаблонам страниц | `SF`, `RAW`, `REN` | Полное |
| `S02` | Ошибки валидации | Syntax, required/recommended properties, validation warnings и invalid items | `SF`, `RAW`, `REN` | Полное |
| `S03` | Соответствие type странице | Соответствует ли тип сущности реальному visible content и назначению URL | `SF`, `RAW`, `REN` | Полное |
| `S04` | Organization | Name, legalName, URL, logo, contactPoint, address, identifiers и sameAs | `SF`, `RAW`, `REN` | Полное |
| `S05` | WebSite | Name, URL, publisher и согласованность основной website entity | `SF`, `RAW`, `REN` | Полное |
| `S06` | WebPage и Article | MainEntity, headline, author, publisher, dates, image и связь со страницей | `SF`, `RAW`, `REN` | Полное |
| `S07` | Product и Offer | Product identity, brand, model, price, currency, availability, seller и offer validity | `SF`, `RAW`, `REN` | Полное |
| `S08` | Service | Service type, provider, audience, areaServed, offers и реальная применимость типа | `SF`, `RAW`, `REN` | Полное |
| `S09` | LocalBusiness | Business type, NAP, geo, opening hours, service area и consistency | `SF`, `RAW`, `REN` | Полное |
| `S10` | Person и author entity | Author/person identifiers, affiliation, credentials, profile URL и sameAs | `SF`, `RAW`, `REN` | Полное |
| `S11` | BreadcrumbList | Полнота trail, порядок, URLs и соответствие видимой навигации | `SF`, `RAW`, `REN` | Полное |
| `S12` | FAQPage и HowTo | Применимость типа, соответствие visible content, полнота вопросов/шагов и отсутствие искусственной разметки | `SF`, `RAW`, `REN` | Полное |
| `S13` | Review и AggregateRating | Наличие реальных отзывов, корректный subject, counts, scale и отсутствие self-serving misuse | `SF`, `RAW`, `REN` | Полное для наблюдаемой реализации |
| `S14` | SameAs и entity identifiers | Качество внешних entity links, устойчивые IDs и отсутствие смешения разных сущностей | `SF`, `RAW`, `REN` | Полное |
| `S15` | Author/publisher/date consistency | Совпадение author, publisher, datePublished/dateModified с видимым HTML и site-declared truth | `SF`, `RAW`, `REN` | Полное |
| `S16` | Offer consistency | Совпадение цен, валют, availability, условий и продукта между schema и visible content | `SF`, `RAW`, `REN` | Полное |
| `S17` | ImageObject и VideoObject | URL, thumbnail, caption, uploadDate, duration и доступность media assets | `SF`, `RAW`, `REN` | Полное |
| `S18` | Raw/rendered schema parity | Добавление, удаление или изменение structured data после выполнения JavaScript | `RAW`, `REN`, `SF` | Полное |
| `S19` | Schema-visible content consistency | Поддерживается ли каждое значимое размеченное свойство видимым содержанием страницы | `RAW`, `REN`, `SF` | Полное |
| `S20` | Дубли и конфликты сущностей | Повторные entity nodes, разные IDs, противоречивые properties и несвязанные graphs | `RAW`, `REN`, `SF` | Полное |

### O — Offsite Authority & Source Ecosystem

| ID | Фактор | Что анализируем | Источники | Покрытие |
|---|---|---|---|---|
| `O01` | Backlink volume | Число входящих ссылок, динамические поля snapshot и распределение по target URLs | `AH-BL` | Полное в пределах экспорта |
| `O02` | Referring domains | Число и состав уникальных ссылающихся доменов | `AH-RD`, `AH-BL` | Полное в пределах экспорта |
| `O03` | Authority distribution | Распределение доступных authority/rating метрик referring pages и domains | `AH-RD`, `AH-BL` | Полное в пределах экспортированных полей |
| `O04` | Follow/nofollow distribution | Follow/nofollow и связанные link attributes для обнаруженных ссылок | `SF` | Полное; прямые поля Screaming Frog |
| `O05` | Anchor text profile | Брендовые, коммерческие, URL, generic и прочие anchor patterns | `AH-BL`, `AH-RD` | Полное в пределах экспорта |
| `O06` | Broken backlinks | Referring pages и anchors, ведущие на недоступные URL сайта, с приоритизацией восстановления | `AH-BB` | Полное |
| `O07` | Распределение target pages | Какие страницы аккумулируют ссылки и какие стратегические URL недополучают внешнее подтверждение | `AH-BL`, `AH-RD`, `SF` | Полное |
| `O08` | Link concentration и sitewide patterns | Зависимость профиля от малого числа доменов/страниц, повторяющиеся и sitewide links | `AH-BL`, `AH-RD` | Полное в пределах экспорта |
| `O09` | Типы ссылок и платформ | Text/image/redirect и иные экспортированные типы, TLD/platform patterns и link attributes | `AH-BL`, `AH-RD` | Полное в пределах экспортированных полей |
| `O10` | Давность и свежесть ссылок | First seen, last seen, lost/new и иные временные поля, если они присутствуют в выгрузке | `AH-BL`, `AH-RD`, `AH-BB` | Условное: по фактически экспортированным time fields |
| `O11` | Географическая и языковая релевантность | Country/TLD/language и тематический контекст referring sources, доступные прямо или выводимые из URL/страницы | `AH-BL`, `AH-RD` | Частичное: зависит от полей экспорта и доступного контекста источника |
| `O12` | Пересечение с AI-конкурентами | Какие конкуренты и внешние источники повторяются в AI environment бренда | `SX-C`, `SX-S`, `SX-P`, `SX-SENT` | Полное в пределах SISTRIX corpus |
| `O13` | AI-cited hosts/domains/URLs | Конкретные источники, которые SISTRIX фиксирует в AI-ответах | `SX-S`, `SX-SENT` | Полное на уровне доступного списка источников |
| `O14` | Source mix | Доля собственных, конкурентных и сторонних hosts/domains/URLs, а также доступных source types | `SX-S`, `SX-SENT` | Полное для доступных source records и snapshot |
| `O17` | Source и citation opportunities | Внешние источники и типы страниц, где конкуренты представлены, а бренд отсутствует или слабее | `SX-C`, `SX-S`, `SX-P`, `SX-SENT`, `AH-BL`, `AH-RD` | Частичное: opportunity определяется, но отсутствие бренда на всей внешней странице не всегда подтверждается |

### M — Measurement & Reporting

| ID | Метрика | Определение | Источники | Покрытие |
|---|---|---|---|---|
| `M01` | Observed Brand Prompt Count | Число обнаруженных SISTRIX промптов с упоминанием бренда в заданном scope | `SX-O` | Полное для метрики SISTRIX |
| `M02` | Observed Domain Citation Prompt Count | Число обнаруженных SISTRIX промптов с цитированием домена в заданном scope | `SX-O` | Полное для метрики SISTRIX |
| `M03` | Observed Combined Visibility Prompt Count | Число обнаруженных промптов, соответствующих combined scope SISTRIX | `SX-O` | Полное для метрики SISTRIX |
| `M04` | Model distribution | Распределение `prompt_count`/records по фактически представленным моделям | `SX-M`, `SX-O`, `SX-P`, `SX-S` | Полное в пределах SISTRIX |
| `M05` | Country distribution | Распределение `prompt_count`/records по странам | `SX-O`, `SX-P`, `SX-S` | Полное в пределах SISTRIX |
| `M06` | Competitor set/count | Число и список AI-конкурентов в заданном model/country scope | `SX-C` | Полное для списка SISTRIX |
| `M07` | Returned prompt record count | Число записей `SX-P`; используется как размер доступного prompt corpus, но не как доля всех релевантных промптов | `SX-P` | Полное для выгрузки |
| `M08` | Unique cited sources | Число уникальных cited URLs, domains и hosts в `SX-S` | `SX-S` | Полное для выгрузки |
| `M09` | Source amount | Значение `amount` по source record и его агрегирование в документированном scope | `SX-S` | Полное для метрики SISTRIX |
| `M10` | Source prompt count | Число обнаруженных промптов, связанных с source record согласно SISTRIX | `SX-S` | Полное для метрики SISTRIX |
| `M11` | Owned cited-source share | Доля source records/amount, принадлежащих анализируемому домену, с явно указанным знаменателем | `SX-S` | Полное для выгрузки и выбранного знаменателя |
| `M12` | Source concentration | Доля top hosts/domains/URLs в суммарном `amount` или `prompt_count` | `SX-S` | Полное для выгрузки |
| `M13` | Historical prompt-count trend | Изменение дневного `prompt_count`, абсолютное и процентное, в стабильном scope | `SX-PC` | Полное для агрегированного ряда |
| `M14` | Google Generative AI impressions | Сумма и динамика first-party показов из предоставленного GSC-GAI экспорта | `GSC-GAI` | Полное в пределах экспорта |
| `M15` | GAI distribution | Распределение Generative AI impressions по pages, countries и devices | `GSC-GAI` | Полное в пределах экспорта |
| `M16` | SISTRIX Sentiment Score | Общий net score, рассчитываемый из Lob и Kritik по методике, отображённой на sentiment page | `SX-SENT` | Полное (snapshot) |
| `M17` | Topic Sentiment Balance | Net balance и mention counts по каждой показанной тематике | `SX-SENT` | Полное (snapshot) |

## 4. Правила интерпретации

1. **SISTRIX не даёт полного denominator релевантного спроса.** `SX-P` содержит уже найденные случаи упоминания бренда или цитирования домена. Поэтому значения `M01–M03` называются *Observed Prompt Count*, а не Brand Mention Rate или Citation Coverage всех релевантных ответов.
2. **Агрегаты источников нельзя искусственно соединять с ответами.** Без документированного общего ключа между `SX-P` и `SX-S` не строится недоказанная связь `prompt → утверждение → source URL`; citation correctness и citation absorption не заявляются.
3. **Sentiment теперь является полноценным snapshot-фактором.** Для приложенного MHTML арифметика общего score и тематических balances проверяется по показанным Lob/Kritik counts. Вывод относится к дате снимка и представленным на странице платформам.
4. **Brand Truth Set строится из HTML как site-declared truth.** Этого достаточно для выявления противоречий между собственными страницами и AI-ответами, но не для независимого подтверждения юридической или фактической истинности каждого заявления.
5. **URL Inspection ограничивается правилом аудита.** Для сайта до 2 000 URL проверяется весь инвентарь; для большего сайта — приоритетная выборка максимум 2 000 URL. Официальная квота API составляет 2 000 запросов в день на property.
6. **Accessibility считается полностью покрытой для автоматизированного аудита.** Lighthouse accessibility в PSI является lab-аудитом. Это не равнозначно ручному WCAG-аудиту с assistive technologies и пользовательским тестированием.
7. **Page performance оценивается по Lighthouse lab.** Для `T20`, `T21`, `T24` и связанных PSI-проверок lab-результат является основной согласованной базой светофора по каждому URL. Возвращённые `loadingExperience` и `originLoadingExperience` можно показывать отдельно как дополнительный CrUX-контекст, но их отсутствие не создаёт `ND`, не снижает покрытие и не меняет lab-оценку. Lab-метрики нельзя подписывать как полевые Core Web Vitals; в частности, TBT остаётся lab-proxy и не переименовывается в INP.
8. **Raw/rendered comparison является методом расчёта, а не дополнительным фактором.** Сравнение RAW и REN формирует основные метрики и evidence для T16, T17 и S18, а также supporting evidence для связанных факторов, включая T09, T15 и C04. Отдельная строка сверх 129 факторов не создаётся.
9. **Dejan оценивает crawlability configuration, а не визиты.** Без server logs нельзя утверждать, что конкретный AI-бот фактически посещал URL; такого фактора в матрице нет.
10. **Path-prefix clustering пересчитывается из текущего crawl.** Для каждого нормализованного HTML URL создаются memberships во всех вложенных structural prefixes: например, `/a/b/` входит в `/`, `/a/` и `/a/b/`. Готовые URL memberships, counts и denominators не переносятся между аудитами. На project level разрешено переиспользовать только подтверждённые semantic labels и criticality стабильных patterns; новые или изменившиеся patterns подтверждаются отдельно. `Affected/analyzed` является Betroffenheitsquote, а не causal impact. Parent и child counts не суммируются: sitewide roll-up использует уникальные URL, а cluster rates показываются раздельно.

## 5. Официальная документация источников

- [Screaming Frog SEO Spider — Configuration](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/)
- [Screaming Frog — Accessibility Audit](https://www.screamingfrog.co.uk/blog/seo-spider-21/)
- [Google Search Console API — Usage Limits](https://developers.google.com/webmaster-tools/limits)
- [PageSpeed Insights API — runPagespeed](https://developers.google.com/speed/docs/insights/v5/reference/pagespeedapi/runpagespeed)
- [Google Search Console — Generative AI Performance Reports](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)
- [SISTRIX — `ai.models`](https://www.sistrix.com/api/ai/ai-models/)
- [SISTRIX — `ai.check.overview`](https://www.sistrix.com/api/ai-check/ai-check-overview/)
- [SISTRIX — `ai.check.competitors`](https://www.sistrix.com/api/ai-check/ai-check-competitors/)
- [SISTRIX — `ai.check.prompts`](https://www.sistrix.com/api/ai-check/ai-check-prompts/)
- [SISTRIX — `ai.check.prompts.count`](https://www.sistrix.com/api/ai-check/ai-check-prompts-count/)
- [SISTRIX — `ai.check.sources`](https://www.sistrix.com/api/ai-check/ai-check-sources/)
- [Ahrefs — Referring Domains vs Backlinks](https://help.ahrefs.com/en/articles/2791107-what-s-the-difference-between-referring-domains-and-backlinks)
- [Ahrefs — Broken Backlinks](https://help.ahrefs.com/en/articles/72842-what-are-broken-backlinks)
- [Ahrefs — Exporting Backlinks and Referring Domains](https://help.ahrefs.com/en/articles/1077560-how-to-use-link-intersect-and-export-the-referring-domains-and-backlinks-report)
- [Dejan AI Agent Access](https://dejan.ai/tools/agents/)
- [RFC 3986 — URI path segments and hierarchy](https://www.rfc-editor.org/rfc/rfc3986#section-3.3)

## 6. Итоговая применимость

Эта конфигурация данных достаточна для **GEO Readiness & AI Visibility Audit** с техническими, контентными, structured-data, AI-visibility, sentiment, source-ecosystem и offsite-рекомендациями на уровне сайта, path-prefix/semantic cluster, шаблона и URL.

Она не используется для утверждений о полном share of model voice, реальном crawling AI-ботов, автоматической citation correctness/absorption или причинном бизнес-эффекте. Эти утверждения намеренно не включены в матрицу.
