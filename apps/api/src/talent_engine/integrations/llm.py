"""Server-only, bounded FreeLLMAPI transport. The worker owns retries."""

import ipaddress
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import unquote, urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TALENT_LLM_", hide_input_in_errors=True
    )
    base_url: str | None = None
    api_key: SecretStr = SecretStr("")
    model: str = Field(default="auto:fast", min_length=1, max_length=200)
    timeout_seconds: float = Field(default=40, gt=0, le=45)

    @field_validator("base_url")
    @classmethod
    def server_url(cls, value):
        if value is None:
            return value
        url = urlsplit(value)
        private = url.hostname in {"localhost", "freellmapi", "freellmapi-freellmapi-1"}
        try:
            address = ipaddress.ip_address(url.hostname or "")
            private |= address.is_loopback or address.is_private
        except ValueError:
            pass
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path.rstrip("/") != "/v1"
            or url.scheme not in ("http", "https")
            or (url.scheme == "http" and not private)
        ):
            raise ValueError("HTTPS or a private gateway URL ending in /v1 required")
        _ = url.port
        return value.rstrip("/")

    @field_validator("api_key")
    @classmethod
    def safe_key(cls, value):
        raw = value.get_secret_value()
        if len(raw) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in raw):
            raise ValueError("Invalid gateway key")
        return value

    @field_validator("model")
    @classmethod
    def safe_model(cls, value):
        if any(ord(c) < 32 for c in value):
            raise ValueError("Invalid model identifier")
        return value


class ProviderFailure(Exception):
    def __init__(self, code, *, retryable=False, retry_after=None):
        self.code, self.retryable, self.retry_after = code, retryable, retry_after
        super().__init__(code)


@dataclass(frozen=True)
class ChatResult:
    content: str
    requested_model: str
    provider: str
    effective_model: str
    response_model: str
    duration_seconds: float


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def retry_delay(value):
    if not value:
        return None
    try:
        return max(0, int(value))
    except ValueError:
        try:
            instant = parsedate_to_datetime(value)
            return max(0, int((instant - datetime.now(UTC)).total_seconds()))
        except (ValueError, TypeError, OverflowError):
            return None


class Gateway:
    def __init__(self, settings=None):
        self.settings = settings or LLMSettings()

    def chat(self, messages, *, response_format=None, max_tokens=6000):
        settings = self.settings
        if not settings.base_url or not settings.api_key.get_secret_value():
            raise ProviderFailure("llm_not_configured")
        payload = dict(
            model=settings.model,
            messages=messages,
            stream=False,
            max_tokens=max_tokens,
            temperature=0,
        )
        if response_format is not None:
            payload["response_format"] = response_format
        data = json.dumps(payload, ensure_ascii=False).encode()
        if len(data) > 200000:
            raise ProviderFailure("llm_context_limit")
        request = urllib.request.Request(
            settings.base_url + "/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": "Bearer " + settings.api_key.get_secret_value(),
                "Content-Type": "application/json",
                "X-FreeLLM-Compress": "off",
                "X-FreeLLM-Cache": "off",
            },
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )
        start = time.monotonic()
        try:
            with opener.open(request, timeout=settings.timeout_seconds) as response:
                raw = response.read(1048577)
                route = unquote(response.headers.get("X-Routed-Via", ""))
                if (
                    len(raw) > 1048576
                    or time.monotonic() - start > settings.timeout_seconds
                ):
                    raise ProviderFailure("provider_response_limit")
        except urllib.error.HTTPError as error:
            status = error.code
            delay = retry_delay(error.headers.get("Retry-After"))
            error.close()
            code = (
                "provider_rate_limited"
                if status == 429
                else "provider_unavailable"
                if status >= 500
                else "provider_auth_failed"
                if status in (401, 403)
                else "provider_request_rejected"
            )
            raise ProviderFailure(
                code,
                retryable=status == 429 or status >= 500,
                retry_after=delay if status == 429 else None,
            ) from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            raise ProviderFailure("provider_unavailable", retryable=True) from None
        try:
            decoded = json.loads(raw)
            content = decoded["choices"][0]["message"]["content"]
            response_model = decoded["model"]
            provider, model = route.split("/", 1)
            if (
                not provider
                or not model
                or len(route) > 500
                or any(ord(c) < 32 for c in route)
                or not isinstance(content, str)
                or not isinstance(response_model, str)
            ):
                raise ValueError("Invalid response")
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderFailure("provider_response_invalid") from None
        return ChatResult(
            content,
            settings.model,
            provider,
            model,
            response_model,
            round(time.monotonic() - start, 6),
        )
