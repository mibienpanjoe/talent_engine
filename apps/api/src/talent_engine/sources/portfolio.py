"""Read the supplied public page and at most two relevant same-host links."""

import hashlib
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from talent_engine.integrations.public_web import PublicWeb, WebFailure, normalize_url

VERSION = "portfolio-html-v1"
SKIP = {"script", "style", "noscript", "template", "svg", "head", "nav", "footer"}


class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.hidden = []
        self.script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.script = True
        if tag in SKIP:
            self.hidden.append(tag)
        if tag == "a" and attrs.get("href") and len(self.links) < 100:
            self.links.append(attrs["href"])
        if (
            tag in ("p", "div", "br", "li", "h1", "h2", "h3", "section", "article")
            and not self.hidden
        ):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        if tag in ("p", "div", "li", "section", "article") and not self.hidden:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return "\n".join(
            " ".join(line.split())
            for line in "".join(self.parts).replace("\x00", "\ufffd").splitlines()
            if line.strip()
        )


def page_text(page):
    content_type = page.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in ("text/html", "application/xhtml+xml", "text/plain"):
        raise WebFailure("source_type_unsupported")
    charset = re.search(
        r'charset=["\']?([a-zA-Z0-9_-]+)', page.headers.get("content-type", "")
    )
    try:
        raw = page.body.decode(charset[1] if charset else "utf-8", errors="replace")
    except LookupError:
        raise WebFailure("source_encoding_unsupported") from None
    if content_type == "text/plain":
        return raw.replace("\r\n", "\n").replace("\r", "\n").replace(
            "\x00", "\ufffd"
        ), []
    parsed = VisibleHTML()
    parsed.feed(raw)
    text = parsed.text()
    if len(text) < 20 and parsed.script:
        raise WebFailure("source_javascript_required")
    return text, parsed.links


def collect_portfolio(value, *, deadline, web=None, retry_errors=False):
    web = web or PublicWeb()
    records = []
    pages = []
    hashes = []
    pending = [value]
    seen = set()
    initial_host = None
    for index in range(3):
        if index >= len(pending):
            break
        target = pending[index]
        record = dict(url=target, fetched_at=datetime.now(UTC).isoformat())
        records.append(record)
        try:
            normalized, host, _ = normalize_url(target)
            if initial_host is None:
                initial_host = host
            if normalized in seen:
                continue
            seen.add(normalized)
            page = web.get(normalized, deadline=deadline)
            text, links = page_text(page)
            if not text.strip():
                raise WebFailure("source_text_unavailable")
            if sum(len(p["text"]) for p in pages) + len(text) > 200000:
                raise WebFailure("source_text_limit")
            content_hash = hashlib.sha256(page.body).hexdigest()
            hashes.append(content_hash)
            record.update(
                url=page.url,
                status="succeeded",
                http_status=page.status,
                content_hash=content_hash,
            )
            pages.append(
                dict(
                    page=len(pages) + 1,
                    text=text,
                    url=page.url,
                    nature="contextual_explanation",
                )
            )
            if index == 0:
                for link in links:
                    try:
                        candidate, candidate_host, _ = normalize_url(
                            urljoin(page.url, link)
                        )
                    except WebFailure:
                        continue
                    # Do not crawl accounts, action URLs, assets or arbitrary links.
                    if (
                        candidate_host == initial_host
                        and candidate not in pending
                        and re.search(
                            r"/(?:projects?|projets?|portfolio|work|realisations?|about|a-propos)(?:/|$)",
                            urlsplit(candidate).path,
                            re.I,
                        )
                        and not urlsplit(candidate).query
                    ):
                        pending.append(candidate)
                    if len(pending) == 3:
                        break
        except WebFailure as error:
            if error.retryable and retry_errors:
                raise
            record.update(status="failed", error_code=error.code)
    return dict(
        state="available"
        if pages
        else "blocked"
        if any(r.get("error_code") == "url_blocked" for r in records)
        else "unavailable",
        error_code=next(
            (r["error_code"] for r in records if r.get("status") == "failed"), None
        ),
        pages=pages,
        ocr_pages=[],
        content_hash=hashlib.sha256("".join(hashes).encode()).hexdigest(),
        extraction_metadata={"ocr": [], "web": records, "source_url": value},
    )
