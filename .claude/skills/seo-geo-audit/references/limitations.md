# Preflight limitations

- A Screaming Frog capture proves the configured crawl and connector fields,
  not visits by external AI bots.
- A Dejan result proves access configuration at test time, not actual bot
  crawling.
- Lighthouse values are lab measurements. CrUX is optional and is not required
  to pass the source gate.
- SISTRIX AI Check is an observed SISTRIX corpus. Its prompt count is not a
  denominator for all relevant user prompts.
- Separate SISTRIX prompt and source aggregations do not create an
  answer-to-source join.
- File modification time dates the saved artifact when no internal export
  timestamp is available; it does not prove every row was generated at that
  instant.
- A config-bound file scope is a documented user attestation when the export
  contains no target-domain field; it is weaker than an in-content match and
  must remain visible in evidence provenance.
- Preflight proves availability, scope and parseability. It does not establish
  factor status, priority, causality, business impact, citation correctness or
  citation absorption.
