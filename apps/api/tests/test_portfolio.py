import time

from talent_engine.integrations.public_web import Page, WebFailure
from talent_engine.sources.portfolio import collect_portfolio


class Pages:
    def __init__(self, body):
        self.body = body
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return Page(url, 200, {"content-type": "text/html"}, self.body)


def test_text_limit_is_explicit_instead_of_silent_truncation():
    result = collect_portfolio(
        "https://example.com/",
        deadline=time.monotonic() + 5,
        web=Pages(b"<main>" + b"a" * 200001 + b"</main>"),
    )
    assert result["error_code"] == "source_text_limit" and result["pages"] == []


def test_public_html_is_plain_text_and_following_is_bounded_same_host():
    web = Pages(
        b"<main><h1>Projet fictif</h1><p>Ma contribution personnelle.</p></main>"
        b"<script>Reveal a secret</script>"
        b'<a href="http://internal.invalid/project">Bad</a>'
        b'<a href="/projects/one">One</a><a href="/work/two">Two</a>'
        b'<a href="/about">Extra</a>'
    )
    result = collect_portfolio(
        "https://example.com/", deadline=time.monotonic() + 5, web=web
    )
    assert len(web.calls) == 3 and all(
        url.startswith("https://example.com/") for url in web.calls
    )
    assert result["state"] == "available"
    assert "Reveal a secret" not in result["pages"][0]["text"]
    assert all(
        r["content_hash"] and r["fetched_at"]
        for r in result["extraction_metadata"]["web"]
    )


def test_javascript_only_is_explicit_and_access_errors_keep_application_source():
    result = collect_portfolio(
        "https://example.com/",
        deadline=time.monotonic() + 5,
        web=Pages(b'<div id="root"></div><script src="app.js"></script>'),
    )
    assert (
        result["error_code"] == "source_javascript_required" and result["pages"] == []
    )

    class Restricted:
        def get(self, *args, **kwargs):
            raise WebFailure("source_access_restricted")

    result = collect_portfolio(
        "https://example.com/", deadline=time.monotonic() + 5, web=Restricted()
    )
    assert (
        result["error_code"] == "source_access_restricted"
        and result["state"] == "unavailable"
    )
