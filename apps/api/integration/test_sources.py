import hashlib
from functools import partial

# Committed synthetic PDF, with a real text stream on each page.
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from talent_engine.analyses.processor import process
from talent_engine.analyses.queue import acquire, complete
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from talent_engine.sources.data import excerpts, run_evidence, sources
from test_uploads import file_campaign, pdf_bytes, upload


def text_pdf():
    return (
        Path(__file__).parents[3] / "fixtures/documents/textual-demo.pdf"
    ).read_bytes()


def receive_pdf(client, content, *, twice=False):
    _, campaign, snapshot, token, q, session = file_campaign(client)
    first = upload(client, session, q, content)
    assert first.status_code == 201
    ids = [first.json()["id"]]
    if twice:
        ids.append(upload(client, session, q, content).json()["id"])
    response = client.post(
        "/api/v1/public/campaigns/" + token + "/applications",
        headers={"Idempotency-Key": uuid4().hex},
        json=dict(
            snapshot_id=snapshot["id"],
            contact=dict(name="Fictif", email="synthetic@example.com"),
            answers=[dict(question_id=q["id"], kind="file", value=ids)],
            upload_session_id=session["id"],
            upload_token=session["upload_token"],
        ),
    )
    assert response.status_code == 201
    return client.get("/api/v1/campaigns/" + campaign["id"] + "/applications").json()[
        "items"
    ][0]["id"]


def test_received_pdf_worker_persists_original_pages_and_deduplicates(
    context, tmp_path
):
    client, engine = context
    data = text_pdf()
    app_id = receive_pdf(client, data, twice=True)
    worker = partial(process, upload_directory=tmp_path / "uploads")
    for _ in range(2):
        assert work_once(engine, WorkerSettings(), "source-worker", processor=worker)
    with engine.connect() as db:
        source = db.execute(select(sources)).mappings().one()
        rows = (
            db.execute(
                select(excerpts).order_by(excerpts.c.locator["page"].as_integer())
            )
            .mappings()
            .all()
        )
        assert str(source["application_id"]) == app_id
        assert source["content_hash"] == hashlib.sha256(data).hexdigest()
        assert source["text_hash"] != source["content_hash"]
        assert source["pages"][0]["text"] == rows[0]["text"]
        assert [r["locator"]["page"] for r in rows] == [1, 2]
        assert rows[0]["nature"] == "declaration"
        assert db.scalar(select(func.count()).select_from(run_evidence)) == 2


def test_scan_has_no_fabricated_excerpts(context, tmp_path):
    client, engine = context
    receive_pdf(client, pdf_bytes())
    for _ in range(2):
        work_once(
            engine,
            WorkerSettings(),
            "scan-worker",
            processor=partial(process, upload_directory=tmp_path / "uploads"),
        )
    with engine.connect() as db:
        source = db.execute(select(sources)).mappings().one()
        assert (
            source["state"] == "unavailable"
            and source["error_code"] == "llm_not_configured"
        )
        assert db.scalar(select(func.count()).select_from(excerpts)) == 0


def test_deleted_application_fences_source_writes(context, tmp_path):
    from talent_engine.applications.data import applications
    from talent_engine.campaigns.lifecycle import now

    client, engine = context
    receive_pdf(client, text_pdf())
    settings = WorkerSettings()
    worker = partial(process, upload_directory=tmp_path / "uploads")
    work_once(engine, settings, "answers", processor=worker)
    claim = acquire(engine, settings, "late-extractor")
    output = worker(engine, claim)
    with engine.begin() as db:
        db.execute(
            applications.update().values(deleted_at=now(db), processing_generation=2)
        )
    assert not complete(engine, settings, claim, output)
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(sources)) == 0


def test_foreign_application_cannot_reference_source_or_excerpt(context, tmp_path):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from talent_engine.applications.data import analysis_runs
    from talent_engine.sources.data import run_sources
    from test_worker import queued

    client, engine = context
    receive_pdf(client, text_pdf())
    for _ in range(2):
        work_once(
            engine,
            WorkerSettings(),
            "source-worker",
            processor=partial(process, upload_directory=tmp_path / "uploads"),
        )
    other_id = queued(client)
    with engine.connect() as db:
        source = db.execute(select(sources)).mappings().one()
        excerpt = db.execute(select(excerpts).limit(1)).mappings().one()
        other_run = db.scalar(
            select(analysis_runs.c.id).where(analysis_runs.c.application_id == other_id)
        )
    with pytest.raises(IntegrityError), engine.begin() as db:
        db.execute(
            excerpts.insert().values(
                id=uuid4(),
                application_id=other_id,
                source_version_id=source["id"],
                text="Invented",
                locator={},
                nature="declaration",
                excerpt_hash="0" * 64,
            )
        )
    with pytest.raises(IntegrityError), engine.begin() as db:
        db.execute(
            run_sources.insert().values(
                run_id=other_run,
                application_id=other_id,
                source_version_id=source["id"],
            )
        )
    with pytest.raises(IntegrityError), engine.begin() as db:
        db.execute(
            run_evidence.insert().values(
                run_id=other_run, application_id=other_id, excerpt_id=excerpt["id"]
            )
        )
