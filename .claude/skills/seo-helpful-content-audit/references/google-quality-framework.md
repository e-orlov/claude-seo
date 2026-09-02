# Google Quality Framework

## Source role and version

This audit uses two Google sources with different roles:

1. [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content),
   Google Search Central, last updated December 10, 2025. This is direct
   publisher guidance and the primary source for the audit questions.
2. [Search Quality Rater Guidelines](https://guidelines.raterhub.com/searchqualityevaluatorguidelines.pdf),
   September 11, 2025 edition. Use Part 1, especially sections 2.2-3.4 and
   4-8, to interpret purpose, YMYL, main content, reputation, E-E-A-T and
   quality levels.

Do not treat the rater guidelines as Google's ranking algorithm. Do not assign
an official Page Quality rating. The framework below turns their concepts into
an evidence-led publisher audit, with explicit limits.

Photowant is not a source for this skill.

## Governing principles

- Begin with the page's purpose. A page type is not inherently high or low
  quality; judge how well the content supports its particular beneficial purpose.
- Judge the main content, not the page's word count in isolation.
- Trust is the central E-E-A-T consideration. The type and amount of experience
  or expertise needed depends on the page topic and purpose.
- Apply more scrutiny when inaccurate or misleading content could cause material
  harm. YMYL is a spectrum, not a binary site label.
- Distinguish what the page claims about its creator from independent evidence
  about the creator or publisher.
- Self-published testimonials are not independent reputation evidence.
- A people-first assessment asks whether the content would remain useful to its
  intended audience without search traffic.
- The presence of SEO elements is compatible with people-first content. Their
  presence alone does not demonstrate search-engine-first intent.

## Criterion matrix

Apply only criteria that fit the page's purpose and type. Each page-assessment
record uses these stable criterion IDs.

| ID | Criterion | Questions to answer | Stronger observable evidence | Common limit |
|---|---|---|---|---|
| `HC01` | Beneficial purpose | What is the page trying to help the visitor do? Does its main content serve that purpose? | Main content, title/H1, primary calls to action, functional output | True publisher motive is not observable |
| `HC02` | Audience and task completion | Is the intended audience identifiable, and can it complete the apparent task without a major information gap? | Complete steps, decision inputs, conditions, examples, expected outcomes | Actual user satisfaction requires user evidence |
| `HC03` | Original contribution | Does the page expose original research, experience, testing, data, reporting or analysis? If it synthesizes sources, what does it add? | Named method, original data, calculations, first-party media, attributed analysis | External originality needs a comparison corpus |
| `HC04` | Completeness and substantive value | Does the main content cover the material questions implied by the page purpose and focus? | Coverage of prerequisites, process, exceptions, consequences, next steps | Length alone cannot establish completeness |
| `HC05` | Accuracy and support | Are material factual claims supported, internally consistent and appropriately sourced? | Primary-source links, citations, dates, method, consistent values, corrections | A crawl cannot prove every claim true |
| `HC06` | Descriptive presentation | Do title, main heading and outline accurately summarize and organize the content without shock or exaggeration? | Title/H1/body agreement, logical headings, clear labels | Engagement quality remains partly interpretive |
| `HC07` | Site focus and people-first fit | Does the page fit a coherent site purpose and an identifiable audience? Does it appear useful without search traffic? | Topical consistency, audience language, direct utility, navigation/site context | Publishing intent remains an inference |
| `HC08` | Search-engine-first risk | Are there observable patterns of broad unfocused production, low-value summarization, artificial freshness or unsupported answers? | Repeated templates, near duplicates, unchanged body with changed date, contradictory/unanswered promise | Automation or motive cannot be inferred from volume alone |
| `HC09` | Who | Is responsibility for the content clear where a reader would reasonably expect it? | Byline, author/reviewer schema, linked profile, publisher/about/contact data | Displayed identity or credentials may be unverified |
| `HC10` | How | Where method matters, does the page explain how information, testing, reviews, calculations or automated content were produced? | Method section, sample size, test protocol, source data, automation disclosure | Disclosure is not required for every page type |
| `HC11` | Why | Does the page expose a user-serving reason through its content and site context? | Clear task utility, audience fit, transparent commercial purpose | The creator's private motivation is not observable |
| `HC12` | Experience | Does the content show appropriate first-hand experience for its purpose? | Specific observations, original examples/media, constraints and outcomes | These signals do not prove the experience happened |
| `HC13` | Expertise | Does the topic require expert knowledge, and is suitable expertise or reliable sourcing visible? | Relevant credentials, expert review, technical accuracy signals, primary sources | Credential authenticity needs independent verification |
| `HC14` | Authority and reputation | Is there independent evidence that the publisher or creator is recognized for this topic? | Independent sources already present in the crawl | On-site claims cannot establish independent reputation |
| `HC15` | Trust and transparency | Can the reader identify responsibility, sourcing, commercial interests, dates and applicable customer-service information? | Publisher/contact/policy pages, citations, disclosures, consistent transactional terms | Trust is broader than any checklist |
| `HC16` | Main-content integrity | Is main content identifiable and sufficiently prominent relative to supplementary, repeated and monetized content? | Semantic containers, DOM order, content ratios, ad/sponsored markers | Stored HTML does not fully establish visual prominence |
| `HC17` | Readability and automated accessibility | Is the text linguistically suitable for its audience, and did automated checks find contrast or text-size barriers? | Flesch fields, spelling/grammar, axe contrast results, `Illegible Font Size` | These do not prove total readability, legibility or WCAG compliance |
| `HC18` | Harm, deception and severe trust failures | Does direct evidence show harmful, deceptive, unsafe or materially misleading content? | Contradictions, disguised purpose, dangerous unsupported instructions, false interface behavior | Apply only with strong direct evidence and appropriate expertise |

## How to interpret key dimensions

### Purpose and satisfaction

State the apparent purpose in concrete user terms, such as "compare two service
plans", "learn how to complete a task" or "purchase a specified product". Avoid
empty labels such as "informational" when a more precise task is visible.

Check whether the main content provides the inputs needed for that task. A page
may be concise and complete, or long and still leave the central question
unanswered. Never use a universal minimum word count.

### Originality and added value

Directly observable positive signals include original measurements, unique
examples, named testing procedures, primary documents, calculations, first-party
photographs and a clearly attributable analysis. Treat generic specificity,
first-person grammar or stock images as weak signals.

Screaming Frog exact and near-duplicate data can establish internal similarity.
It cannot establish that a page is copied from, or better than, pages outside the
crawl. Use `not_verifiable` for external originality unless a suitable comparison
corpus is present in the selected crawl.

### Who, How and Why

Apply "Who" where readers would reasonably expect authorship or responsibility.
A byline is often useful for editorial, review and YMYL advice pages, but its
absence is not automatically a defect on a calculator, category listing or
ordinary product page.

Apply "How" when method affects trust: product reviews, comparisons, tests,
rankings, calculations, research and substantial automation. Record the presence
and specificity of a disclosed process. Do not speculate that AI was used merely
because prose seems generic.

Treat "Why" as an inference from utility, audience fit and production patterns.
Never claim to know the creator's intent. A commercial page can have a beneficial
purpose when it accurately helps users evaluate or buy a product or service.

### E-E-A-T and Trust

Do not require all E-E-A-T components equally on every page. Choose what the
purpose demands:

- Personal experience may be the relevant basis for a first-person account.
- Formal expertise matters more for consequential factual advice.
- Authority is more relevant where recognized institutional or subject-matter
  standing is expected.
- Trust can fail even when experience or expertise appears strong.

Record on-page claims as claims. Verify external reputation only from independent
pages whose rendered content is included in the selected crawl. A manufacturer's
own praise, embedded testimonial or affiliate endorsement is not independent.

## YMYL classification

Assign one of four values per page, not once per domain:

| Value | Use when |
|---|---|
| `clear` | Incorrect content could directly and materially affect health, safety, financial security, civic participation or societal welfare |
| `possible` | Harm is plausible but depends on context, user action or the level of advice offered |
| `unlikely` | The topic and task are not reasonably consequential in the YMYL sense |
| `not_verifiable` | The page purpose or content available is insufficient for classification |

For clear YMYL informational or advisory content, require stronger sourcing,
accuracy and appropriate expertise. First-hand experience can still be valuable,
but it must not be presented as expert advice when doing so could be unsafe.

Do not label an entire site YMYL merely because it contains a few YMYL pages.

## Page-type applicability

Use this as a routing aid, not a fixed scorecard.

| Page type | Emphasize | Usually secondary or conditional |
|---|---|---|
| Editorial guide/article | Purpose, completeness, sources, dates, Who, expertise/experience | Customer-service information |
| Product/service page | Accurate offer details, conditions, responsibility, support, commercial disclosure | Personal author byline |
| Review/comparison | Method, tested set, evidence, conflicts, author/reviewer, update date | Word count |
| YMYL advice | Accuracy, primary sourcing, expert review, safe boundaries, freshness | Informal popularity signals |
| Tool/calculator | Correct task completion, inputs, method/assumptions, ownership | Long narrative content |
| Category/listing page | Selection logic, useful differentiation, navigation, current item data | Article-style authorship |
| Homepage/About/Contact | Site purpose, ownership, responsibility, topical focus | Per-article depth |
| Forum/UGC | Provenance, moderation/context, experience value, safety | Formal expertise for every personal post |

## Reading and accessibility evidence

Treat these as distinct concepts:

- **Textual readability:** Screaming Frog Flesch Reading Ease, average words per
  sentence and its readability class. Report the exact value and page language.
- **Visual text legibility:** the Mobile/Lighthouse `Illegible Font Size` result.
- **Color contrast:** axe/WCAG violations in Screaming Frog Accessibility.
- **Overall accessibility:** not established by the three checks above.

Flesch is a formula based on sentence length and syllable complexity. Its
threshold meaning can vary by language and audience. A difficult score may be
appropriate for expert material; it is not automatically a defect.

Do not confuse the PageSpeed overview field named `Font Size`, which describes
font-resource bytes, with rendered text size.

## Prohibited shortcuts

Do not:

- total the criteria into a purported Google score;
- require a fixed word count, heading count, list count or external-link count;
- call content unhelpful merely because it is commercial, AI-assisted or SEO-aware;
- infer AI generation from writing style;
- infer experience or expertise from a bio alone;
- treat schema markup as proof that the marked-up claim is true;
- treat internal near duplication as external plagiarism;
- treat a missing byline as an issue without page-type justification;
- recommend adding lists, tables or FAQs unless they improve the identified user task;
- claim a page is fully accessible because automated violations equal zero;
- claim positive or negative independent reputation from first-party material.
