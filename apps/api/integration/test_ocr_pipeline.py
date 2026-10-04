from functools import partial
from io import BytesIO

from PIL import Image
from sqlalchemy import select
from talent_engine.analyses.processor import process
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from talent_engine.applications.data import jobs
from talent_engine.campaigns.lifecycle import now
from talent_engine.integrations.llm import ChatResult, ProviderFailure
from talent_engine.sources.data import sources
from test_sources import receive_pdf


class Transcription:
    def __init__(self, limited=False):
        self.limited = limited

    def chat(self, messages, **kwargs):
        if self.limited:
            raise ProviderFailure(
                "provider_rate_limited", retryable=True, retry_after=0
            )
        return ChatResult(
            "Projet fictif : essai et ajustement.",
            "vision",
            "fixture",
            "vision",
            "vision",
            0.1,
        )


def test_scan_is_persisted_and_quota_retries_preserve_application(context, tmp_path):
    client, engine = context
    out = BytesIO()
    Image.new("RGB", (300, 400), "white").save(out, format="PDF")
    app_id = receive_pdf(client, out.getvalue())
    gateway = Transcription(limited=True)
    processor = partial(
        process, upload_directory=tmp_path / "uploads", ocr_gateway=gateway
    )
    settings = WorkerSettings(retry_base_seconds=0, retry_second_seconds=0)
    assert work_once(engine, settings, "answers", processor=processor)
    assert work_once(engine, settings, "ocr-quota", processor=processor)
    detail = client.get("/api/v1/applications/" + app_id).json()
    step = detail["analyses"][0]["steps"][1]
    assert step["state"] == "waiting"
    assert step["error_code"] == "provider_rate_limited"
    assert detail["analyses"][0]["next_attempt_at"] is not None
    with engine.begin() as db:
        db.execute(jobs.update().values(next_attempt_at=now(db)))
    gateway.limited = False
    assert work_once(engine, settings, "ocr-recovered", processor=processor)
    detail = client.get("/api/v1/applications/" + app_id).json()
    assert (
        detail["sources"][0]["extraction_metadata"]["ocr"][0]["status"] == "succeeded"
    )
    with engine.connect() as db:
        record = db.execute(select(sources)).mappings().one()
        assert record["pages"][0]["text"] == "Projet fictif : essai et ajustement."
        assert record["pages"][0]["method"] == "ocr"
        assert db.scalar(select(jobs.c.state)) == "queued"
