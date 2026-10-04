"""Public HTTP only: validate all DNS answers, pin socket IP and preserve TLS SNI."""

import http.client
import ipaddress
import json
import os
import socket
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit


class WebFailure(Exception):
    def __init__(self, code, *, retryable=False, retry_after=None):
        self.code, self.retryable, self.retry_after = code, retryable, retry_after
        super().__init__(code)


def normalize_url(value):
    try:
        if len(value) > 2048 or any(ord(c) <= 32 or ord(c) == 127 for c in value):
            raise ValueError()
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").encode("idna").decode().lower().rstrip(".")
        if (
            parsed.scheme not in ("http", "https")
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or "%" in hostname
        ):
            raise ValueError()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in (80, 443):
            raise ValueError()
        # Only default ports: no confusion between schemes/protocols.
        if port != (443 if parsed.scheme == "https" else 80):
            raise ValueError()
        authority = "[" + hostname + "]" if ":" in hostname else hostname
        url = urlunsplit(
            (
                parsed.scheme,
                authority,
                quote(parsed.path or "/", safe="/%:@-._~!$&'()*+,;="),
                quote(parsed.query, safe="%/:?@-._~!$&'()*+,;="),
                "",
            )
        )
        return url, hostname, port
    except (ValueError, UnicodeError):
        raise WebFailure("url_blocked") from None


def resolve(host, port):
    try:
        child = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("dns_child.py")),
                host,
                str(port),
            ],
            capture_output=True,
            env={"PATH": os.defpath},
            timeout=3,
            check=True,
        )
        return json.loads(child.stdout)
    except (subprocess.SubprocessError, ValueError, OSError):
        raise WebFailure("source_dns_unavailable", retryable=True) from None


def public_addresses(host, port=443, *, resolver=resolve):
    try:
        entries = resolver(host, port)
        if not entries or len(entries) > 32:
            raise ValueError()
        for value, family in entries:
            address = ipaddress.ip_address(value)
            if (
                not address.is_global
                or address.is_multicast
                or address.is_unspecified
                or address.is_reserved
            ):
                raise ValueError()
            if family not in (socket.AF_INET, socket.AF_INET6):
                raise ValueError()
            if address.version == 6 and (
                address.ipv4_mapped
                or address.sixtofour
                or address.teredo
                or address in ipaddress.ip_network("64:ff9b::/96")
                or address in ipaddress.ip_network("64:ff9b:1::/48")
            ):
                raise ValueError()
        return entries
    except (ValueError, TypeError):
        raise WebFailure("url_blocked") from None


@dataclass(frozen=True)
class Page:
    url: str
    status: int
    headers: dict
    body: bytes


def remaining(deadline):
    value = min(30, deadline - time.monotonic())
    if value <= 0:
        raise WebFailure("source_budget_exceeded")
    return value


class PinnedConnection(http.client.HTTPConnection):
    def close(self):
        # Exchange owns the socket, including while reading Connection: close.
        pass


def exchange(url, hostname, address, port, deadline):
    """No getaddrinfo, proxy, cookie, credential or implicit redirect at connection."""
    parsed = urlsplit(url)
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    connection = PinnedConnection(hostname, port, timeout=remaining(deadline))
    raw = socket.socket(family, socket.SOCK_STREAM)
    response = None
    try:
        raw.settimeout(remaining(deadline))
        raw.connect((address, port))
        if parsed.scheme == "https":
            raw.settimeout(remaining(deadline))
            raw = ssl.create_default_context().wrap_socket(
                raw, server_hostname=hostname
            )
        connection.sock = raw
        target = parsed.path + ("?" + parsed.query if parsed.query else "")
        host = "[" + hostname + "]" if ":" in hostname else hostname
        connection.request(
            "GET",
            target,
            headers={
                "Host": host,
                "User-Agent": "TalentEngine/1.0 (public portfolio review)",
                "Accept-Encoding": "identity",
                "Accept": "text/html,text/plain,application/json",
                "Connection": "close",
            },
        )
        raw.settimeout(remaining(deadline))
        response = connection.getresponse()
        headers = {k.lower(): v for k, v in response.getheaders()}
        if response.status != 200:
            return response.status, headers, b""
        if headers.get("content-encoding", "identity").lower() not in ("identity", ""):
            raise WebFailure("source_encoding_unsupported")
        length = headers.get("content-length")
        if length and int(length) > 2097152:
            raise WebFailure("source_response_limit")
        chunks = []
        size = 0
        while True:
            raw.settimeout(remaining(deadline))
            chunk = response.read1(min(65536, 2097153 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > 2097152:
                raise WebFailure("source_response_limit")
            chunks.append(chunk)
        remaining(deadline)
        return response.status, headers, b"".join(chunks)
    except (OSError, http.client.HTTPException, ValueError):
        raise WebFailure("source_network_unavailable", retryable=True) from None
    finally:
        if response is not None:
            response.close()
        raw.close()


class PublicWeb:
    def __init__(self, *, resolver=resolve, exchange=exchange, allowed_hosts=None):
        self.resolver, self.exchange = resolver, exchange
        self.allowed_hosts = allowed_hosts

    def get(self, value, *, deadline):
        from talent_engine.integrations.llm import retry_delay

        for hop in range(4):
            remaining(deadline)
            url, host, port = normalize_url(value)
            if self.allowed_hosts is not None and host not in self.allowed_hosts:
                raise WebFailure("url_blocked")
            addresses = public_addresses(host, port, resolver=self.resolver)
            remaining(deadline)
            status, headers, body = self.exchange(
                url, host, addresses[0][0], port, deadline
            )
            if status in (301, 302, 303, 307, 308):
                if hop == 3 or not headers.get("location"):
                    raise WebFailure("source_redirect_limit")
                value = urljoin(url, headers["location"])
                continue
            if status == 403 and headers.get("x-ratelimit-remaining") == "0":
                raise WebFailure("source_rate_limited", retryable=True, retry_after=60)
            if status in (401, 403):
                raise WebFailure("source_access_restricted")
            if status == 429:
                raise WebFailure(
                    "source_rate_limited",
                    retryable=True,
                    retry_after=retry_delay(headers.get("retry-after")),
                )
            if status >= 500:
                raise WebFailure("source_unavailable", retryable=True)
            if status != 200:
                raise WebFailure("source_http_error")
            if len(body) > 2097152:
                raise WebFailure("source_response_limit")
            remaining(deadline)
            return Page(url, status, headers, body)
        raise WebFailure("source_redirect_limit")
