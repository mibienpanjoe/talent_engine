import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from talent_engine.integrations.llm import Gateway, LLMSettings, ProviderFailure


@pytest.fixture
def gateway_server():
    state = {
        "status": 200,
        "body": {
            "model": "actual-model",
            "choices": [{"message": {"content": '{"ok":true}'}}],
        },
        "route": "provider/actual-model",
        "headers": {},
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            state["request"] = json.loads(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            state["authorization_received"] = (
                self.headers.get("Authorization") == "Bearer test-only-key"
            )
            state["compression"] = self.headers.get("X-FreeLLM-Compress")
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            if state["route"]:
                self.send_header("X-Routed-Via", state["route"])
            for k, v in state["headers"].items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(json.dumps(state["body"]).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield (
        Gateway(
            LLMSettings(
                base_url=f"http://127.0.0.1:{server.server_port}/v1",
                api_key="test-only-key",
                model="requested-model",
            )
        ),
        state,
    )
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_adapter_preserves_route_and_minimizes_request(gateway_server):
    gateway, state = gateway_server
    result = gateway.chat([{"role": "user", "content": "Fictitious excerpt"}])
    assert result.content == '{"ok":true}'
    assert result.provider == "provider" and result.effective_model == "actual-model"
    assert result.requested_model == "requested-model" and result.duration_seconds >= 0
    assert state["authorization_received"] and state["compression"] == "off"
    assert state["request"]["stream"] is False
    assert "test-only-key" not in repr(gateway.settings)


def test_rate_limit_and_upstream_errors_are_sanitized(gateway_server):
    gateway, state = gateway_server
    state.update(
        status=429,
        body={"error": {"message": "private upstream secret"}},
        headers={"Retry-After": "20"},
    )
    with pytest.raises(ProviderFailure) as raised:
        gateway.chat([])
    assert raised.value.code == "provider_rate_limited"
    assert raised.value.retryable and raised.value.retry_after == 20
    assert "private" not in str(raised.value)
    state.update(status=503, headers={})
    with pytest.raises(ProviderFailure) as raised:
        gateway.chat([])
    assert raised.value.retryable


def test_missing_provenance_and_invalid_response_never_return_a_result(gateway_server):
    gateway, state = gateway_server
    state["route"] = None
    with pytest.raises(ProviderFailure):
        gateway.chat([])
    state.update(route="provider/model", body={"choices": []})
    with pytest.raises(ProviderFailure):
        gateway.chat([])


def test_gateway_requires_private_http_or_https_and_server_key():
    with pytest.raises(ValueError):
        LLMSettings(base_url="http://public.example/v1", api_key="test-only-key")
    with pytest.raises(ValueError):
        LLMSettings(base_url="https://user:secret@example.com/v1")
    with pytest.raises(ProviderFailure) as raised:
        Gateway(LLMSettings()).chat([])
    assert raised.value.code == "llm_not_configured"


def test_embedding_transport_pins_model_and_validates_indices_and_vectors(
    gateway_server,
):
    from talent_engine.integrations.embeddings import Embeddings

    gateway, state = gateway_server
    settings = gateway.settings.model_copy(
        update={"embedding_model": "test-family", "embedding_dimensions": 2}
    )
    state["body"] = {
        "model": "test-family",
        "provider": "test-provider",
        "data": [{"index": 1, "embedding": [0, 2]}, {"index": 0, "embedding": [2, 0]}],
        "usage": {"prompt_tokens": 4},
    }
    reply = Embeddings(settings).embed(["first", "second"])
    assert reply.vectors == [[1, 0], [0, 1]] and reply.provider == "test-provider"
    assert (
        state["authorization_received"] and state["request"]["model"] == "test-family"
    )
    for body in [
        dict(state["body"], model="other-family"),
        dict(state["body"], data=[{"index": 0, "embedding": [1]}]),
        dict(
            state["body"],
            data=[
                {"index": 0, "embedding": [True, 0]},
                {"index": 1, "embedding": [1, 0]},
            ],
        ),
    ]:
        state["body"] = body
        with pytest.raises(ProviderFailure, match="embedding_response_invalid"):
            Embeddings(settings).embed(["first", "second"])
    state.update(status=429, headers={"Retry-After": "30"})
    with pytest.raises(ProviderFailure) as raised:
        Embeddings(settings).embed(["first"])
    assert raised.value.retryable and raised.value.retry_after == 30
