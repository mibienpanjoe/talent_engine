import time

import pytest
from talent_engine.integrations.public_web import (
    PublicWeb,
    WebFailure,
    normalize_url,
    public_addresses,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://2130706433/",
        "http://user:secret@example.com/",
        "http://example.com:8000/",
        "file:///etc/passwd",
        "http://example.com/\r\nHost:internal",
        "http://[64:ff9b::7f00:1]/",
    ],
)
def test_private_and_ambiguous_urls_are_blocked(url):
    with pytest.raises(WebFailure):
        normalized = normalize_url(url)
        public_addresses(normalized[1], resolver=lambda h, p: [("127.0.0.1", 2)])


def test_all_dns_answers_checked_not_only_first():
    with pytest.raises(WebFailure):
        public_addresses(
            "example.com", resolver=lambda h, p: [("93.184.216.34", 2), ("10.0.0.1", 2)]
        )


def test_redirects_are_revalidated_and_connection_uses_pinned_ip():
    calls = []

    def resolve(host, port):
        return [("93.184.216.34", 2)] if host == "example.com" else [("127.0.0.1", 2)]

    def exchange(url, hostname, address, port, deadline):
        calls.append((hostname, address))
        return 302, {"location": "http://internal.invalid/secret"}, b""

    with pytest.raises(WebFailure):
        PublicWeb(resolver=resolve, exchange=exchange).get(
            "https://example.com/", deadline=time.monotonic() + 5
        )
    assert calls == [("example.com", "93.184.216.34")]


def test_rebinding_cannot_change_connected_address():
    resolved = []
    connected = []

    def resolve(host, port):
        resolved.append(host)
        return [("93.184.216.34", 2)] if len(resolved) == 1 else [("127.0.0.1", 2)]

    def exchange(url, hostname, address, port, deadline):
        connected.append(address)
        return 200, {"content-type": "text/html"}, b"<p>Projet personnel fictif</p>"

    page = PublicWeb(resolver=resolve, exchange=exchange).get(
        "https://example.com/", deadline=time.monotonic() + 5
    )
    assert page.status == 200 and connected == ["93.184.216.34"] and len(resolved) == 1


def test_actual_transport_pins_address_preserves_host_and_tls(monkeypatch):
    from talent_engine.integrations import public_web

    calls = []

    class Socket:
        def settimeout(self, value):
            pass

        def connect(self, address):
            calls.append(("connect", address))

        def close(self):
            pass

    class TLS:
        def wrap_socket(self, sock, *, server_hostname):
            calls.append(("sni", server_hostname))
            return sock

    class Response:
        status = 200

        def getheaders(self):
            return [("Content-Type", "text/html")]

        def read1(self, size):
            return b""

        def close(self):
            pass

    class Connection:
        def __init__(self, *args, **kwargs):
            self.sock = None

        def request(self, method, path, headers):
            calls.append(("host", headers["Host"]))

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(public_web.socket, "socket", lambda *args: Socket())
    monkeypatch.setattr(
        public_web.socket,
        "getaddrinfo",
        lambda *args: (_ for _ in ()).throw(AssertionError("Second DNS lookup")),
    )
    monkeypatch.setattr(public_web.ssl, "create_default_context", lambda: TLS())
    monkeypatch.setattr(public_web, "PinnedConnection", Connection)
    public_web.exchange(
        "https://example.com/work",
        "example.com",
        "93.184.216.34",
        443,
        time.monotonic() + 5,
    )
    assert calls == [
        ("connect", ("93.184.216.34", 443)),
        ("sni", "example.com"),
        ("host", "example.com"),
    ]


def test_real_http_close_response_body_and_size_limit():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from talent_engine.integrations.public_web import exchange

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Connection", "close")
            self.send_header("Content-Type", "text/plain")
            self.send_header(
                "Content-Length", "2097153" if self.path == "/large" else "5"
            )
            self.end_headers()
            if self.path != "/large":
                self.wfile.write(b"proof")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        result = exchange(
            f"http://example.com:{port}/",
            "example.com",
            "127.0.0.1",
            port,
            time.monotonic() + 5,
        )
        assert result[2] == b"proof"
        with pytest.raises(WebFailure, match="source_response_limit"):
            exchange(
                f"http://example.com:{port}/large",
                "example.com",
                "127.0.0.1",
                port,
                time.monotonic() + 5,
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_encoded_url_and_api_tls_downgrade_are_blocked():
    with pytest.raises(WebFailure):
        normalize_url("https://example.com/" + "é" * 1000)
    web = PublicWeb(
        allowed_hosts={"api.github.com"},
        resolver=lambda *a: [("8.8.8.8", 2)],
        exchange=lambda *a: (
            302,
            {"location": "http://api.github.com/repos/demo/project"},
            b"",
        ),
    )
    with pytest.raises(WebFailure, match="url_blocked"):
        web.get(
            "https://api.github.com/repos/demo/project", deadline=time.monotonic() + 5
        )
