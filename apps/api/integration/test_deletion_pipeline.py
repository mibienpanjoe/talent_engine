from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from test_campaigns import headers
from test_review_reanalysis import correction, expectation, review_headers
from test_reviews import deposit, prepared


def test_deletion_hides_then_purges_all_review_data(context, tmp_path):
    from talent_engine.applications.data import applications
    from talent_engine.database import metadata
    from talent_engine.deletions.data import purge_once

    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Dossier à supprimer", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    correction(client, path, h)
    detail = client.get(path).json()
    evidence_id = detail["evidence"][0]["id"]
    body = expectation(client, path)
    request = client.request("DELETE", path, headers=review_headers(h, body), json=body)
    assert request.status_code == 202, request.text
    assert client.get(path).status_code == 404
    assert client.get("/api/v1/evidence/" + evidence_id).status_code == 404
    assert client.get(path + "/review-history").status_code == 404
    assert (
        client.get("/api/v1/campaigns/" + data[0]["id"] + "/applications").json()[
            "counts"
        ]["all"]
        == 0
    )
    assert client.delete(path, headers=h).json()["id"] == request.json()["id"]
    assert purge_once(engine, deletion_settings(engine, tmp_path))
    status = client.get("/api/v1/cleanup-requests/" + request.json()["id"])
    assert status.status_code == 200 and status.json()["state"] == "completed"
    assert client.delete(path, headers=h).status_code == 200
    with engine.connect() as db:
        assert (
            db.scalar(
                select(applications.c.id).where(applications.c.id == UUID(app_id))
            )
            is None
        )
        for table in metadata.tables.values():
            if "application_id" in table.c and table.name != "cleanup_requests":
                assert (
                    db.scalar(
                        select(table.c.application_id)
                        .where(table.c.application_id == UUID(app_id))
                        .limit(1)
                    )
                    is None
                ), table.name
    client.cookies.clear()
    assert (
        client.get("/api/v1/cleanup-requests/" + request.json()["id"]).status_code
        == 401
    )


def deletion_settings(engine, tmp_path):
    from talent_engine.config import Settings

    return Settings(
        database_url=engine.url.render_as_string(hide_password=False),
        upload_directory=tmp_path / "uploads",
        public_origin="http://localhost:3003",
        local_development=True,
        csrf_secret="test-only-csrf-" + "x" * 32,
    )


def file_deposit(client):
    from test_uploads import file_campaign, pdf_bytes, upload

    h, campaign, snapshot, token, q, session = file_campaign(client)
    document = upload(client, session, q, pdf_bytes()).json()
    body = dict(
        snapshot_id=snapshot["id"],
        contact=dict(name="Pièce fictive", email="synthetic@example.com"),
        answers=[dict(question_id=q["id"], kind="file", value=[document["id"]])],
        upload_session_id=session["id"],
        upload_token=session["upload_token"],
    )
    from uuid import uuid4

    key = uuid4().hex
    public_path = "/api/v1/public/campaigns/" + token + "/applications"
    assert (
        client.post(
            public_path, headers={"Idempotency-Key": key}, json=body
        ).status_code
        == 201
    )
    app_id = client.get("/api/v1/campaigns/" + campaign["id"] + "/applications").json()[
        "items"
    ][0]["id"]
    return h, app_id, document, public_path, body, key, session, q


def test_storage_failure_is_durable_and_receipt_is_minimized(
    context, tmp_path, monkeypatch
):
    from pathlib import Path

    from talent_engine.applications.data import receipts
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.deletions.data import cleanup_requests, purge_once

    client, engine = context
    h, app_id, document, public_path, body, key, _, _ = file_deposit(client)
    path = "/api/v1/applications/" + app_id
    request = client.request(
        "DELETE",
        path,
        headers=review_headers(h, expectation(client, path)),
        json=expectation(client, path),
    ).json()
    assert (
        client.get("/api/v1/uploads/" + document["id"] + "/download").status_code == 404
    )
    assert (
        client.post(
            public_path, headers={"Idempotency-Key": key}, json=body
        ).status_code
        == 410
    )
    original_unlink = Path.unlink

    def unavailable(file, *args, **kwargs):
        if file.parent.name == "real":
            raise OSError("synthetic storage failure")
        return original_unlink(file, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unavailable)
    for attempt, delay in ((1, 30), (2, 120), (3, 3600)):
        assert purge_once(engine, deletion_settings(engine, tmp_path))
        row = client.get("/api/v1/cleanup-requests/" + request["id"]).json()
        assert row["state"] == "waiting" and row["attempts"] == attempt
        assert row["incident"] is (attempt >= 3)
        with engine.begin() as db:
            record = db.execute(select(cleanup_requests)).mappings().one()
            assert (
                delay - 1
                <= (record["next_attempt_at"] - now(db)).total_seconds()
                <= delay
            )
            assert record["storage_keys"] and record["completed_at"] is None
            db.execute(cleanup_requests.update().values(next_attempt_at=now(db)))
        assert list((tmp_path / "uploads" / "real").iterdir())
    monkeypatch.setattr(Path, "unlink", original_unlink)
    assert purge_once(engine, deletion_settings(engine, tmp_path))
    assert not list((tmp_path / "uploads" / "real").iterdir())
    with engine.connect() as db:
        tombstone = db.execute(select(receipts)).mappings().one()
        assert all(
            tombstone[k] is None
            for k in (
                "application_id",
                "received_at",
                "receipt_ref",
                "canonical_version",
                "upload_manifest",
            )
        )
        assert (
            tombstone["deleted_at"]
            and tombstone["key_digest"]
            and tombstone["payload_hash"]
        )
    assert (
        client.get("/api/v1/cleanup-requests/" + request["id"]).json()["state"]
        == "completed"
    )


def test_late_evaluation_and_concurrent_purgers_cannot_resurrect_data(
    context, tmp_path
):
    from concurrent.futures import ThreadPoolExecutor
    from functools import partial

    from embedding_fixture import ControlledEmbeddings
    from talent_engine.analyses.processor import process
    from talent_engine.analyses.queue import acquire, complete, heartbeat
    from talent_engine.analyses.settings import WorkerSettings
    from talent_engine.analyses.worker import work_once
    from talent_engine.deletions.data import purge_once
    from talent_engine.evaluations.data import embedding_cache
    from test_reviews import OracleGateway

    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Résultat tardif", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    correction(client, path, h)
    body = {
        **expectation(client, path),
        "reason": "reanalyze",
        "base_run_id": client.get(path).json()["effective_evaluation"]["run_id"],
        "source_ids": [],
    }
    assert (
        client.post(
            path + "/analyses", headers=review_headers(h, body), json=body
        ).status_code
        == 202
    )
    processor = partial(
        process, gateway=OracleGateway([4, 2, 3]), embedder=ControlledEmbeddings()
    )
    for _ in range(2):
        assert work_once(engine, WorkerSettings(), "delayed", processor=processor)
    claim = acquire(engine, WorkerSettings(), "late")
    output = processor(engine, claim)
    body = expectation(client, path)
    request_headers = review_headers(h, body)
    with ThreadPoolExecutor(2) as pool:
        responses = list(
            pool.map(
                lambda _: client.request(
                    "DELETE", path, headers=request_headers, json=body
                ),
                range(2),
            )
        )
    assert (
        all(r.status_code == 202 for r in responses)
        and len({r.json()["id"] for r in responses}) == 1
    )
    assert not heartbeat(engine, WorkerSettings(), claim)
    with ThreadPoolExecutor(2) as pool:
        list(
            pool.map(
                lambda _: purge_once(engine, deletion_settings(engine, tmp_path)),
                range(2),
            )
        )
    assert not complete(engine, WorkerSettings(), claim, output)
    assert client.get(path).status_code == 404
    with engine.connect() as db:
        assert (
            db.scalar(
                select(embedding_cache.c.application_id).where(
                    embedding_cache.c.application_id == UUID(app_id)
                )
            )
            is None
        )
    assert (
        client.get("/api/v1/cleanup-requests/" + responses[0].json()["id"]).json()[
            "state"
        ]
        == "completed"
    )


def test_upload_already_in_flight_is_unlinked_and_cannot_attach(
    context, tmp_path, monkeypatch
):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from talent_engine.deletions.data import purge_once
    from talent_engine.documents import router as documents
    from test_uploads import pdf_bytes, upload

    client, engine = context
    h, app_id, _, _, _, _, session, q = file_deposit(client)
    started = threading.Event()
    release = threading.Event()

    def pause_detection(path):
        started.set()
        assert release.wait(10)
        return "application/pdf"

    monkeypatch.setattr(documents, "detect_file", pause_detection)
    path = "/api/v1/applications/" + app_id
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(upload, client, session, q, pdf_bytes(), "late.pdf")
        assert started.wait(5)
        try:
            body = expectation(client, path)
            response = client.request(
                "DELETE", path, headers=review_headers(h, body), json=body
            )
            assert response.status_code == 202
            assert purge_once(engine, deletion_settings(engine, tmp_path))
            assert not list((tmp_path / "uploads" / "real").iterdir())
        finally:
            release.set()
        assert future.result(timeout=5).status_code in (404, 410)
    assert not list((tmp_path / "uploads" / "real").iterdir())
    assert client.get(path).status_code == 404


def test_retention_and_cleanup_ownership(context, tmp_path):
    from talent_engine.access import hasher, reviewers
    from talent_engine.applications.data import applications, receipts
    from talent_engine.campaigns.data import campaigns
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.deletions.data import (
        cleanup_requests,
        collect_retention,
        purge_once,
    )

    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Échéance", [4, 3, 3])
    path = "/api/v1/applications/" + app_id
    assert collect_retention(engine) == 0
    with engine.begin() as db:
        db.execute(
            applications.update()
            .where(applications.c.id == UUID(app_id))
            .values(received_at=now(db) - timedelta(days=91))
        )
        db.execute(receipts.update().values(expires_at=now(db) - timedelta(days=1)))
    assert collect_retention(engine) == 1 and client.get(path).status_code == 404
    assert purge_once(engine, deletion_settings(engine, tmp_path))
    request = client.get(
        "/api/v1/campaigns/" + data[0]["id"] + "/cleanup-requests"
    ).json()[0]
    assert request["state"] == "completed"
    with engine.connect() as db:
        owner = db.scalar(
            select(campaigns.c.owner_id).where(campaigns.c.id == UUID(data[0]["id"]))
        )
    from uuid import uuid4

    with engine.begin() as db:
        db.execute(
            reviewers.insert().values(
                id=uuid4(),
                login="foreign",
                password_hash=hasher.hash("synthetic-foreign-password"),
            )
        )
    with engine.begin() as db:
        foreign_id = db.scalar(
            select(reviewers.c.id).where(reviewers.c.login == "foreign")
        )
        db.execute(
            campaigns.update()
            .where(campaigns.c.id == UUID(data[0]["id"]))
            .values(owner_id=foreign_id)
        )
    assert client.get("/api/v1/cleanup-requests/" + request["id"]).status_code == 404
    with engine.begin() as db:
        db.execute(
            campaigns.update()
            .where(campaigns.c.id == UUID(data[0]["id"]))
            .values(owner_id=owner)
        )
        db.execute(
            cleanup_requests.update().values(completed_at=now(db) - timedelta(days=8))
        )
    assert client.get("/api/v1/cleanup-requests/" + request["id"]).status_code == 404
    assert client.delete(path, headers=headers(client)).status_code == 404
    collect_retention(engine)
    assert client.get("/api/v1/cleanup-requests/" + request["id"]).status_code == 404


def test_sql_failure_after_file_removal_retries_safely(context, tmp_path, monkeypatch):
    import talent_engine.deletions.purge as purge
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.deletions.data import cleanup_requests

    client, engine = context
    h, app_id, *_ = file_deposit(client)
    path = "/api/v1/applications/" + app_id
    body = expectation(client, path)
    request = client.request(
        "DELETE", path, headers=review_headers(h, body), json=body
    ).json()
    original = purge.remove_rows

    def interrupted(db, record):
        original(db, record)
        raise ValueError("synthetic_abort")

    monkeypatch.setattr(purge, "remove_rows", interrupted)
    assert purge.purge_once(engine, deletion_settings(engine, tmp_path))
    status = client.get("/api/v1/cleanup-requests/" + request["id"]).json()
    assert status["state"] == "waiting"
    assert status["error_code"] == "cleanup_database_unavailable"
    assert not list((tmp_path / "uploads").rglob("*.pdf"))
    with engine.begin() as db:
        db.execute(cleanup_requests.update().values(next_attempt_at=now(db)))
    monkeypatch.setattr(purge, "remove_rows", original)
    assert purge.purge_once(engine, deletion_settings(engine, tmp_path))
    assert (
        client.get("/api/v1/cleanup-requests/" + request["id"]).json()["state"]
        == "completed"
    )
