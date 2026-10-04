"""Pinned embedding family, finite dimensions, bounded server-only transport."""

import json
import math
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from talent_engine.integrations.llm import (
    Gateway,
    NoRedirect,
    ProviderFailure,
    retry_delay,
)

VERSION = "freellmapi-embeddings-v1"


def normalized_vectors(vectors, dimensions):
    result = []
    for vector in vectors:
        if (
            not isinstance(vector, list)
            or len(vector) != dimensions
            or any(type(x) not in (float, int) or not math.isfinite(x) for x in vector)
        ):
            raise ValueError("Invalid embedding vector")
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or norm <= 0:
            raise ValueError("Invalid vector norm")
        result.append(
            list(vector)
            if math.isclose(norm, 1, abs_tol=1e-12)
            else [x / norm for x in vector]
        )
    return result


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list
    model: str
    dimensions: int
    provider: str | None
    duration_seconds: float
    input_tokens: int | None


class Embeddings:
    def __init__(self, settings=None):
        self.settings = (Gateway(settings)).settings
        self.model = self.settings.embedding_model
        self.dimensions = self.settings.embedding_dimensions

    def embed(self, texts):
        settings = self.settings
        if not settings.base_url or not settings.api_key.get_secret_value():
            raise ProviderFailure("llm_not_configured")
        if not 0 < len(texts) <= 16 or any(
            not isinstance(t, str) or not t.strip() or len(t) > 8000 for t in texts
        ):
            raise ProviderFailure("embedding_context_limit")
        body = json.dumps(
            dict(model=self.model, input=texts, dimensions=self.dimensions),
            ensure_ascii=False,
        ).encode()
        if len(body) > 200000:
            raise ProviderFailure("embedding_context_limit")
        request = urllib.request.Request(
            settings.base_url + "/embeddings",
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer " + settings.api_key.get_secret_value(),
                "Content-Type": "application/json",
            },
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )
        started = time.monotonic()
        try:
            with opener.open(request, timeout=settings.timeout_seconds) as response:
                raw = response.read(4194305)
                if (
                    len(raw) > 4194304
                    or time.monotonic() - started > settings.timeout_seconds
                ):
                    raise ProviderFailure("provider_response_limit")
        except urllib.error.HTTPError as error:
            status = error.code
            delay = retry_delay(error.headers.get("Retry-After"))
            error.close()
            raise ProviderFailure(
                "embedding_rate_limited"
                if status == 429
                else "embedding_unavailable"
                if status >= 500
                else "embedding_request_rejected",
                retryable=status == 429 or status >= 500,
                retry_after=delay if status == 429 else None,
            ) from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            raise ProviderFailure("embedding_unavailable", retryable=True) from None
        try:
            data = json.loads(raw)
            if data.get("model") != self.model:
                raise ValueError()
            rows = data["data"]
            if not isinstance(rows, list) or len(rows) != len(texts):
                raise ValueError()
            indexed = {
                r["index"]: r["embedding"] for r in rows if type(r.get("index")) is int
            }
            if set(indexed) != set(range(len(texts))):
                raise ValueError()
            vectors = normalized_vectors(
                [indexed[i] for i in range(len(texts))], self.dimensions
            )
            provider = data.get("provider")
            if provider is not None and (
                not isinstance(provider, str)
                or len(provider) > 100
                or any(ord(c) < 32 for c in provider)
            ):
                raise ValueError()
            tokens = data.get("usage", {}).get("prompt_tokens")
            if tokens is not None and (type(tokens) is not int or tokens < 0):
                raise ValueError()
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ProviderFailure("embedding_response_invalid") from None
        return EmbeddingResult(
            vectors,
            self.model,
            self.dimensions,
            provider,
            round(time.monotonic() - started, 6),
            tokens,
        )
