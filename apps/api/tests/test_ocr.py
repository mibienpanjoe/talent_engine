import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from talent_engine.integrations.llm import ChatResult, ProviderFailure
from talent_engine.sources.extraction import collect_sources


class Vision:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def chat(self, messages, **kwargs):
        self.calls += 1
        assert messages[1]["content"][1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        if self.error:
            raise ProviderFailure(self.error)
        return ChatResult(
            "Projet fictif : essai puis ajustement.",
            "vision-test",
            "fixture",
            "vision-test",
            "vision-test",
            0.1,
        )


def document(path, media_type):
    return dict(
        id=uuid4(),
        question_id=uuid4(),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        media_type=media_type,
        storage_key=path.name,
    )


def test_text_pdf_never_calls_vision(tmp_path):
    path = tmp_path / "text.pdf"
    path.write_bytes(
        (Path(__file__).parents[3] / "fixtures/documents/textual-demo.pdf").read_bytes()
    )
    vision = Vision()
    rows = collect_sources(
        uuid4(), [], [document(path, "application/pdf")], tmp_path, ocr_gateway=vision
    )
    assert vision.calls == 0 and rows[0]["extraction_metadata"]["ocr"] == []


@pytest.mark.parametrize("media_type", ["application/pdf", "image/png"])
def test_real_scan_render_transcription_and_original_hash(tmp_path, media_type):
    path = tmp_path / ("scan.pdf" if media_type == "application/pdf" else "scan.png")
    Image.new("RGB", (300, 400), "white").save(path)
    vision = Vision()
    rows = collect_sources(
        uuid4(), [], [document(path, media_type)], tmp_path, ocr_gateway=vision
    )
    source = rows[0]
    assert vision.calls == 1 and source["state"] == "available"
    assert source["ocr_pages"] == []
    assert source["excerpts"][0]["locator"]["method"] == "ocr"
    assert source["excerpts"][0]["locator"]["page"] == 1
    assert source["excerpts"][0]["text"] == "Projet fictif : essai puis ajustement."
    assert source["extraction_metadata"]["ocr"][0]["provider"] == "fixture"
    assert source["content_hash"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("code", ["provider_rate_limited", "provider_unavailable"])
def test_ocr_error_keeps_source_without_fabricated_text(tmp_path, code):
    path = tmp_path / "scan.png"
    Image.new("RGB", (300, 400), "white").save(path)
    source = collect_sources(
        uuid4(), [], [document(path, "image/png")], tmp_path, ocr_gateway=Vision(code)
    )[0]
    assert source["state"] == "unavailable" and source["error_code"] == code
    assert source["ocr_pages"] == [1] and source["excerpts"] == []


def test_ocr_model_is_independent_from_text_generation(tmp_path, monkeypatch):
    from talent_engine.integrations.llm import Gateway, LLMSettings

    path = tmp_path / "scan.png"
    Image.new("RGB", (300, 400), "white").save(path)
    observed = []

    def reply(adapter, messages, **kwargs):
        observed.append(adapter.settings.model)
        return Vision().chat(messages, **kwargs)

    monkeypatch.setattr(Gateway, "chat", reply)
    source = collect_sources(
        uuid4(),
        [],
        [document(path, "image/png")],
        tmp_path,
        ocr_gateway=Gateway(
            LLMSettings(model="text-only-model", ocr_model="vision-model")
        ),
    )[0]
    assert observed == ["vision-model"] and source["state"] == "available"
