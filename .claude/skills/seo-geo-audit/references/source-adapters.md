# Mandatory file adapters

## Discovery and binding

Explicit paths in `audit.yaml` win. If a path is absent, `preflight.py` may
inspect supplied `--input-root` directories or ZIP containers. Classification
uses the normalized header signature; filename terms are only tie-break hints.
Two equal candidates remain a blocker and must not be guessed.

| Source | Required signature |
|---|---|
| `AH-BL` | referring-page URL + target URL |
| `AH-RD` | referring domain; backlink count is mapped when exported |
| `AH-BB` | referring-page URL + broken target URL + HTTP/lost signal |
| `GSC-GAI` | date + impressions + at least one page/country/device dimension |
| `DJ` | agent/user-agent + access/crawlability status |
| `SX-SENT` | multipart/related MHTML with sentiment score/tonality, praise/positive, criticism/negative and platform signals |

Header aliases cover common English, German and Russian labels. The exact
source headers and their canonical mapping are retained in the artifact
profile. Unknown schemas fail closed and require an adapter update or a fresh
export; they are not coerced positionally.

An explicit config mapping is treated as the user's scope binding when a report
such as Ahrefs Referring Domains contains no target-domain column. Where target
URLs exist, the adapter also records an in-content domain match.

## Formats

- CSV/TSV/text: encoding and delimiter are detected and recorded.
- XLSX/XLSM: every sheet with a recognized header signature is read in safe
  data-only/read-only mode; the artifact profile retains per-sheet headers and
  row counts and combines complementary GSC dimensions without inventing joins.
- HTML: only a stored table is parsed; no remote resources are requested.
- ZIP: extracted only by `extract_zip.py` into a run-specific directory.
- MHTML: parsed only by `parse_mhtml.py` as MIME `multipart/related`.

Legacy binary `.xls` is deliberately unsupported. Export it as CSV or XLSX.

## ZIP safety

Reject absolute paths, `..`, Windows drive paths, backslashes, NULs, symlinks,
encrypted entries, case-colliding names, excessive entry counts/sizes and
suspicious compression ratios. The original archive remains immutable. A
checkpointed extraction is reused only when the archive and every extracted
member still match their hashes.

## MHTML safety and semantics

Use Python's MIME transfer decoding. Select the first archived `text/html` root,
extract visible text locally, and fingerprint both root HTML and text. Do not
open `Content-Location`, stylesheets, images, frames or any other remote URL.

One valid main-brand/domain sentiment page is required. Additional configured
competitor sentiment pages may have other domains, but a malformed or stale
configured page remains visible and blocks readiness. The preflight artifact
count is the number of page snapshots, not the number of praise/criticism
mentions; detailed sentiment extraction belongs to the analysis stage.

## Freshness and empty exports

File modification time is stored as the saved artifact snapshot. Internal data
ranges are extracted during staging. A zero-row table is accepted only with a
valid header signature and explicit `--valid-empty SOURCE_CODE` attestation;
otherwise it remains partial/blocking.
