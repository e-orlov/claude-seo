#!/usr/bin/env python3
"""Extract auditable structural signals from Screaming Frog rendered HTML.

The script accepts a Screaming Frog RAW_HTML JSON/NDJSON export or one HTML
file. It intentionally emits observations only; it does not grade content.
It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse


VERSION = "1.0.0"
COUNTED_TAGS = {
    "main",
    "article",
    "section",
    "nav",
    "aside",
    "footer",
    "p",
    "ul",
    "ol",
    "li",
    "table",
    "caption",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "blockquote",
    "dl",
    "dt",
    "dd",
    "figure",
    "figcaption",
    "details",
    "summary",
    "form",
    "iframe",
    "img",
    "video",
    "audio",
    "time",
    "a",
}
URL_KEYS = {"address", "url", "pageurl", "uri", "pageaddress"}
HTML_KEYS = {
    "content",
    "html",
    "rawhtml",
    "renderedhtml",
    "pagecontent",
    "sourcehtml",
    "pagesource",
}
WORD_RE = re.compile(r"[^\W_]+(?:[’'\-][^\W_]+)*", re.UNICODE)
COMMERCIAL_MARKER_RE = re.compile(
    r"(?:^|[\s_-])(ad|ads|advert|advertisement|sponsor|sponsored|affiliate)(?:$|[\s_-])",
    re.IGNORECASE,
)


def clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def canonical_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def looks_like_html(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    sample = value.lstrip()[:500].lower()
    return bool(
        "<!doctype html" in sample
        or "<html" in sample
        or "<body" in sample
        or re.search(r"<(main|article|head|h1|p)(?:\s|>)", sample)
    )


def limited_unique(values: Iterable[str], limit: int = 50) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_space(str(value))
        if not cleaned or cleaned in seen:
            continue
        result.append(cleaned)
        seen.add(cleaned)
        if len(result) >= limit:
            break
    return result


def walk_items(value: Any, depth: int = 0) -> Iterable[tuple[str, Any]]:
    if depth > 3:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key), item
            if isinstance(item, (dict, list)):
                yield from walk_items(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                yield from walk_items(item, depth + 1)


def find_record_value(
    record: dict[str, Any], candidate_keys: set[str], value_kind: str
) -> Any:
    fallback = None
    best_url: tuple[int, str] | None = None
    url_priority = {
        "address": 0,
        "pageaddress": 1,
        "pageurl": 2,
        "url": 3,
        "uri": 4,
    }
    for key, value in walk_items(record):
        normalized = canonical_key(key)
        if normalized not in candidate_keys:
            continue
        if value_kind == "html" and looks_like_html(value):
            return value
        if (
            value_kind == "url"
            and isinstance(value, str)
            and value.startswith(("http://", "https://"))
        ):
            candidate = (url_priority.get(normalized, 99), value)
            if best_url is None or candidate[0] < best_url[0]:
                best_url = candidate
        if fallback is None:
            fallback = value
    return best_url[1] if best_url is not None else fallback


def records_from_json(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("results", "records", "rows", "data", "items"):
        child = value.get(key)
        if isinstance(child, list) and all(isinstance(item, dict) for item in child):
            return child
    return [value]


def load_records(path: Path, supplied_url: str | None) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() in {".html", ".htm"} or looks_like_html(text):
        if not supplied_url:
            raise ValueError("--url is required when the input is a plain HTML file")
        return [{"url": supplied_url, "rendered_html": text}]

    try:
        return records_from_json(json.loads(text))
    except json.JSONDecodeError:
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                records.append(
                    {
                        "_source_line": line_number,
                        "_load_error": f"invalid JSON: {exc.msg}",
                    }
                )
                continue
            if isinstance(item, dict):
                item.setdefault("_source_line", line_number)
                records.append(item)
        return records


def attribute_map(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {str(key).lower(): value or "" for key, value in attrs}


def schema_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        for key in ("name", "headline", "url", "@id"):
            if isinstance(value.get(key), str):
                return [value[key]]
        return []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(schema_names(item))
        return names
    return []


class SignalParser(HTMLParser):
    def __init__(self, page_url: str):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.base_host = urlparse(page_url).netloc.lower()
        self.tag_counts: Counter[str] = Counter()
        self.headings: dict[str, list[str]] = {f"h{i}": [] for i in range(1, 7)}
        self.heading_sequence: list[int] = []
        self.heading_outline: list[dict[str, Any]] = []
        self.title_parts: list[str] = []
        self.meta_description = ""
        self.canonical = ""
        self.html_lang = ""
        self.visible_parts: list[str] = []
        self.main_parts: list[str] = []
        self.main_depth = 0
        self.article_depth = 0
        self.nav_depth = 0
        self.footer_depth = 0
        self.aside_depth = 0
        self.ignore_depth = 0
        self.title_depth = 0
        self.active_heading: str | None = None
        self.heading_parts: list[str] = []
        self.active_link: dict[str, Any] | None = None
        self.links_total = 0
        self.links_internal = 0
        self.links_external = 0
        self.main_external_links: list[dict[str, str]] = []
        self.author_links: list[str] = []
        self.sponsored_link_count = 0
        self.author_markup_count = 0
        self.reviewer_markup_count = 0
        self.image_alt_missing = 0
        self.image_alt_empty = 0
        self.datetime_values: list[str] = []
        self.commercial_marker_candidates = 0
        self.jsonld_active = False
        self.jsonld_parts: list[str] = []
        self.jsonld_blocks: list[str] = []
        self.jsonld_parse_errors = 0

    @property
    def in_main_content(self) -> bool:
        return self.main_depth > 0 or self.article_depth > 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        amap = attribute_map(attrs)
        if tag in COUNTED_TAGS:
            self.tag_counts[tag] += 1
        if tag == "html" and not self.html_lang:
            self.html_lang = amap.get("lang", "")
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.ignore_depth += 1
        if tag == "script" and "ld+json" in amap.get("type", "").lower():
            self.jsonld_active = True
            self.jsonld_parts = []
        if tag == "main":
            self.main_depth += 1
        elif tag == "article":
            self.article_depth += 1
        elif tag == "nav":
            self.nav_depth += 1
        elif tag == "footer":
            self.footer_depth += 1
        elif tag == "aside":
            self.aside_depth += 1
        elif tag == "title":
            self.title_depth += 1

        if tag in self.headings:
            self.active_heading = tag
            self.heading_parts = []

        if tag == "meta" and amap.get("name", "").lower() == "description":
            self.meta_description = amap.get("content", self.meta_description)
        if tag == "link":
            rel_tokens = set(amap.get("rel", "").lower().split())
            href = amap.get("href", "")
            if "canonical" in rel_tokens and href:
                self.canonical = urljoin(self.page_url, href)
            if "author" in rel_tokens and href:
                self.author_links.append(urljoin(self.page_url, href))

        itemprop = amap.get("itemprop", "").lower()
        if "author" in itemprop:
            self.author_markup_count += 1
        if "reviewedby" in canonical_key(itemprop):
            self.reviewer_markup_count += 1
        marker_text = " ".join([amap.get("class", ""), amap.get("id", "")])
        if COMMERCIAL_MARKER_RE.search(marker_text):
            self.commercial_marker_candidates += 1

        if tag == "img":
            if "alt" not in amap:
                self.image_alt_missing += 1
            elif not clean_space(amap.get("alt", "")):
                self.image_alt_empty += 1
        if tag == "time" and amap.get("datetime"):
            self.datetime_values.append(amap["datetime"])

        if tag == "a":
            self.active_link = {
                "href": amap.get("href", ""),
                "rel": set(amap.get("rel", "").lower().split()),
                "parts": [],
                "in_main": self.in_main_content,
            }

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self.active_link is not None:
            self._finish_link()
        if self.active_heading == tag:
            text = clean_space(" ".join(self.heading_parts))
            if text:
                self.headings[tag].append(text)
                level = int(tag[1])
                self.heading_sequence.append(level)
                self.heading_outline.append({"level": level, "text": text})
            self.active_heading = None
            self.heading_parts = []
        if tag == "script" and self.jsonld_active:
            self.jsonld_blocks.append("".join(self.jsonld_parts).strip())
            self.jsonld_active = False
            self.jsonld_parts = []
        if tag == "main" and self.main_depth:
            self.main_depth -= 1
        elif tag == "article" and self.article_depth:
            self.article_depth -= 1
        elif tag == "nav" and self.nav_depth:
            self.nav_depth -= 1
        elif tag == "footer" and self.footer_depth:
            self.footer_depth -= 1
        elif tag == "aside" and self.aside_depth:
            self.aside_depth -= 1
        elif tag == "title" and self.title_depth:
            self.title_depth -= 1
        if tag in {"script", "style", "noscript", "template", "svg"} and self.ignore_depth:
            self.ignore_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.jsonld_active:
            self.jsonld_parts.append(data)
            return
        if self.ignore_depth:
            return
        text = clean_space(data)
        if not text:
            return
        self.visible_parts.append(text)
        if self.in_main_content and not (self.nav_depth or self.footer_depth or self.aside_depth):
            self.main_parts.append(text)
        if self.title_depth:
            self.title_parts.append(text)
        if self.active_heading:
            self.heading_parts.append(text)
        if self.active_link is not None:
            self.active_link["parts"].append(text)

    def _finish_link(self) -> None:
        assert self.active_link is not None
        href = self.active_link["href"]
        rel_tokens: set[str] = self.active_link["rel"]
        anchor = clean_space(" ".join(self.active_link["parts"]))
        absolute = urljoin(self.page_url, href) if href else ""
        parsed = urlparse(absolute)
        if href and parsed.scheme in {"http", "https"}:
            self.links_total += 1
            if parsed.netloc.lower() == self.base_host:
                self.links_internal += 1
            else:
                self.links_external += 1
                if self.active_link["in_main"] and len(self.main_external_links) < 50:
                    self.main_external_links.append({"url": absolute, "anchor": anchor})
        if "author" in rel_tokens and absolute:
            self.author_links.append(absolute)
        if "sponsored" in rel_tokens:
            self.sponsored_link_count += 1
        self.active_link = None

    def schema_signals(self) -> dict[str, Any]:
        collected: dict[str, list[str]] = {
            "types": [],
            "headlines": [],
            "names": [],
            "authors": [],
            "reviewers": [],
            "publishers": [],
            "about": [],
            "keywords": [],
            "date_published": [],
            "date_modified": [],
            "citations": [],
            "breadcrumbs": [],
        }

        def walk(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    walk(item)
                return
            if not isinstance(value, dict):
                return
            node_types = schema_names(value.get("@type"))
            if any(item.lower() == "breadcrumblist" for item in node_types):
                breadcrumb_items = value.get("itemListElement", [])
                if isinstance(breadcrumb_items, dict):
                    breadcrumb_items = [breadcrumb_items]
                ordered_breadcrumbs: list[tuple[int, str]] = []
                if isinstance(breadcrumb_items, list):
                    for fallback_position, entry in enumerate(breadcrumb_items, start=1):
                        if not isinstance(entry, dict):
                            continue
                        names = schema_names(entry.get("name"))
                        if not names and isinstance(entry.get("item"), dict):
                            names = schema_names(entry["item"].get("name"))
                        if not names:
                            continue
                        position = entry.get("position", fallback_position)
                        try:
                            sort_position = int(position)
                        except (TypeError, ValueError):
                            sort_position = fallback_position
                        ordered_breadcrumbs.append((sort_position, names[0]))
                collected["breadcrumbs"].extend(
                    name for _, name in sorted(ordered_breadcrumbs)
                )
            for key, item in value.items():
                key_lower = key.lower()
                if key_lower == "@type":
                    collected["types"].extend(schema_names(item))
                elif key_lower == "headline":
                    collected["headlines"].extend(schema_names(item))
                elif key_lower == "name":
                    collected["names"].extend(schema_names(item))
                elif key_lower == "author":
                    collected["authors"].extend(schema_names(item))
                elif key_lower == "reviewedby":
                    collected["reviewers"].extend(schema_names(item))
                elif key_lower == "publisher":
                    collected["publishers"].extend(schema_names(item))
                elif key_lower == "about":
                    collected["about"].extend(schema_names(item))
                elif key_lower == "keywords":
                    if isinstance(item, str):
                        collected["keywords"].extend(re.split(r"[,;]", item))
                    else:
                        collected["keywords"].extend(schema_names(item))
                elif key_lower == "datepublished":
                    collected["date_published"].extend(schema_names(item))
                elif key_lower == "datemodified":
                    collected["date_modified"].extend(schema_names(item))
                elif key_lower in {"citation", "isbasedon", "isbasedonurl"}:
                    collected["citations"].extend(schema_names(item))
                walk(item)

        for block in self.jsonld_blocks:
            if not block:
                continue
            try:
                walk(json.loads(block))
            except json.JSONDecodeError:
                self.jsonld_parse_errors += 1
        return {key: limited_unique(values) for key, values in collected.items()}

    def result(self) -> dict[str, Any]:
        if self.active_link is not None:
            self._finish_link()
        visible_text = clean_space(" ".join(self.visible_parts))
        main_text = clean_space(" ".join(self.main_parts))
        content_text = main_text or visible_text
        schema = self.schema_signals()
        heading_counts = {key: len(value) for key, value in self.headings.items()}
        return {
            "extractor_version": VERSION,
            "url": self.page_url,
            "html_lang": self.html_lang,
            "title": clean_space(" ".join(self.title_parts)),
            "meta_description": clean_space(self.meta_description),
            "canonical_url": self.canonical,
            "content_text_source": "main_or_article" if main_text else "body_fallback",
            "visible_text_word_count": len(WORD_RE.findall(visible_text)),
            "main_text_word_count": len(WORD_RE.findall(main_text)),
            "text_excerpt": content_text[:1500],
            "heading_counts": heading_counts,
            "heading_sequence": self.heading_sequence,
            "heading_outline": self.heading_outline,
            "headings": self.headings,
            "tag_counts": {tag: self.tag_counts.get(tag, 0) for tag in sorted(COUNTED_TAGS)},
            "image_alt_missing_count": self.image_alt_missing,
            "image_alt_empty_count": self.image_alt_empty,
            "links_total": self.links_total,
            "links_internal": self.links_internal,
            "links_external": self.links_external,
            "main_external_links": self.main_external_links,
            "rel_author_links": limited_unique(self.author_links),
            "author_markup_count": self.author_markup_count,
            "reviewer_markup_count": self.reviewer_markup_count,
            "sponsored_link_count": self.sponsored_link_count,
            "commercial_marker_candidate_count": self.commercial_marker_candidates,
            "datetime_values": limited_unique(self.datetime_values),
            "schema": schema,
            "jsonld_block_count": len(self.jsonld_blocks),
            "jsonld_parse_error_count": self.jsonld_parse_errors,
            "question_mark_count": content_text.count("?"),
        }


def extract_record(record: dict[str, Any], supplied_url: str | None, index: int) -> dict[str, Any]:
    source_line = record.get("_source_line", index + 1)
    if record.get("_load_error"):
        return {
            "extractor_version": VERSION,
            "source_record": source_line,
            "url": supplied_url or "",
            "extraction_error": record["_load_error"],
        }
    page_url = find_record_value(record, URL_KEYS, "url")
    html = find_record_value(record, HTML_KEYS, "html")
    if not isinstance(page_url, str) or not page_url.startswith(("http://", "https://")):
        page_url = supplied_url
    if not page_url:
        return {
            "extractor_version": VERSION,
            "source_record": source_line,
            "url": "",
            "extraction_error": "URL field not found",
        }
    if not looks_like_html(html):
        return {
            "extractor_version": VERSION,
            "source_record": source_line,
            "url": page_url,
            "extraction_error": "RAW_HTML field not found or value is not HTML",
        }
    parser = SignalParser(page_url)
    try:
        parser.feed(str(html))
        parser.close()
        result = parser.result()
        result["source_record"] = source_line
        return result
    except Exception as exc:  # Keep page-level failures visible for audit coverage.
        return {
            "extractor_version": VERSION,
            "source_record": source_line,
            "url": page_url,
            "extraction_error": f"HTML parse failed: {type(exc).__name__}: {exc}",
        }


def self_test() -> None:
    html = """
    <!doctype html><html lang="en"><head>
      <title>Example guide</title><meta name="description" content="A test page">
      <link rel="canonical" href="/guide">
      <script type="application/ld+json">
        {"@type":"Article","headline":"Example guide",
         "author":{"@type":"Person","name":"Ada"}}
      </script>
      <script type="application/ld+json">
        {"@type":"BreadcrumbList","itemListElement":[
          {"@type":"ListItem","position":1,"name":"Guides"},
          {"@type":"ListItem","position":2,
           "item":{"@id":"https://example.com/guide","name":"Example guide"}}]}
      </script>
    </head><body><nav><a href="/">Home</a></nav><main><article>
      <h1>Example guide</h1><h2>Steps</h2><p>Useful text for a reader.</p>
      <ol><li>First</li><li>Second</li></ol><ul><li>Extra</li></ul>
      <table><tr><th>Item</th><td>Value</td></tr></table>
      <a href="https://source.example/reference">Primary source</a>
      <img src="x.jpg"><time datetime="2026-01-02">January 2</time>
    </article></main></body></html>
    """
    parser = SignalParser("https://example.com/guide")
    parser.feed(html)
    result = parser.result()
    assert result["html_lang"] == "en"
    assert result["heading_counts"]["h1"] == 1
    assert result["heading_outline"] == [
        {"level": 1, "text": "Example guide"},
        {"level": 2, "text": "Steps"},
    ]
    assert result["tag_counts"]["ol"] == 1
    assert result["tag_counts"]["ul"] == 1
    assert result["tag_counts"]["li"] == 3
    assert result["tag_counts"]["table"] == 1
    assert result["links_external"] == 1
    assert result["image_alt_missing_count"] == 1
    assert "Article" in result["schema"]["types"]
    assert "Ada" in result["schema"]["authors"]
    assert result["schema"]["breadcrumbs"] == ["Guides", "Example guide"]
    record_result = extract_record(
        {"Address": "https://example.com/guide", "Raw HTML": html}, None, 0
    )
    assert record_result["url"] == "https://example.com/guide"
    assert record_result["tag_counts"]["ol"] == 1
    print("self-test: ok", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="RAW_HTML NDJSON/JSON or one HTML file")
    parser.add_argument("output", nargs="?", type=Path, help="Output NDJSON path")
    parser.add_argument("--url", help="Page URL; required for a plain HTML input")
    parser.add_argument(
        "--self-test", action="store_true", help="Run the built-in deterministic test"
    )
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.input or not args.output:
        parser.error("input and output are required unless --self-test is used")
    if not args.input.exists():
        parser.error(f"input file does not exist: {args.input}")

    try:
        records = load_records(args.input, args.url)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not records:
        print("error: no JSON/NDJSON records found", file=sys.stderr)
        return 2

    results = [extract_record(record, args.url, index) for index, record in enumerate(records)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")

    success_count = sum("extraction_error" not in result for result in results)
    error_count = len(results) - success_count
    print(
        json.dumps(
            {
                "input_records": len(records),
                "output_records": len(results),
                "successful": success_count,
                "errors": error_count,
                "output": str(args.output),
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 0 if success_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
