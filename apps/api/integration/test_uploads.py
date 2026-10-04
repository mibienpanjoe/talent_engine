from io import BytesIO
from uuid import uuid4

from test_campaigns import headers, publishable


def file_campaign(client):
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    config = publishable()
    q = dict(
        id=str(uuid4()),
        type="file",
        label="Document",
        position=1,
        required=True,
        help=None,
        options=[],
        constraints={},
    )
    config["questions"].append(q)
    campaign = client.post(
        "/api/v1/campaigns", headers=h, json={"configuration": config}
    ).json()
    path = "/api/v1/campaigns/" + campaign["id"]
    snapshot = client.post(
        path + "/publications",
        headers={**h, "If-Match": '"1"', "Idempotency-Key": uuid4().hex},
        json={},
    ).json()
    token = client.get(path).json()["public_url"].split("/")[-1]
    session = client.post(
        "/api/v1/public/campaigns/" + token + "/upload-sessions",
        json={"snapshot_id": snapshot["id"]},
    )
    assert session.status_code == 201
    return h, campaign, snapshot, token, q, session.json()


def pdf_bytes():
    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(output)
    return output.getvalue()


def upload(client, session, q, content, name="test.pdf"):
    return client.post(
        "/api/v1/upload-sessions/" + session["id"] + "/files",
        headers={"X-Upload-Token": session["upload_token"]},
        data={"question_id": q["id"]},
        files={"file": (name, content)},
    )


def test_private_file_reception_replay_and_download(context):
    client, engine = context
    _, campaign, snapshot, token, q, session = file_campaign(client)
    result = upload(client, session, q, pdf_bytes(), "../../test.pdf")
    assert result.status_code == 201, result.text
    document = result.json()
    body = dict(
        snapshot_id=snapshot["id"],
        contact=dict(name="Test", email="test@example.com"),
        answers=[dict(question_id=q["id"], kind="file", value=[document["id"]])],
        upload_session_id=session["id"],
        upload_token=session["upload_token"],
    )
    path = "/api/v1/public/campaigns/" + token + "/applications"
    key = uuid4().hex
    assert (
        client.post(path, headers={"Idempotency-Key": key}, json=body).status_code
        == 201
    )
    from sqlalchemy import select
    from talent_engine.applications.repository import applications
    from talent_engine.documents.repository import uploads

    with engine.connect() as db:
        application_id = db.scalar(select(applications.c.id))
        assert db.scalar(select(uploads.c.application_id)) == application_id
    detail = client.get("/api/v1/applications/" + str(application_id)).json()
    assert detail["uploads"][0]["id"] == document["id"]
    download = client.get("/api/v1/uploads/" + document["id"] + "/download")
    assert download.status_code == 200 and download.content == pdf_bytes()
    assert download.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in download.headers["content-disposition"]
    assert (
        client.post(path, headers={"Idempotency-Key": key}, json=body).status_code
        == 200
    )
    client.cookies.clear()
    assert (
        client.get("/api/v1/uploads/" + document["id"] + "/download").status_code == 401
    )


def test_invalid_type_size_capability_and_foreign_references(context):
    client, _ = context
    _, _, snapshot, token, q, session = file_campaign(client)
    assert upload(client, session, q, b"<svg/>", "cv.pdf").status_code == 415
    assert upload(client, session, q, b"x" * (10485760 + 1)).status_code == 413
    assert (
        upload(
            client, {**session, "upload_token": "x" * 43}, q, pdf_bytes()
        ).status_code
        == 404
    )
    document = upload(client, session, q, pdf_bytes()).json()
    other = client.post(
        "/api/v1/public/campaigns/" + token + "/upload-sessions",
        json={"snapshot_id": snapshot["id"]},
    ).json()
    body = dict(
        snapshot_id=snapshot["id"],
        contact=dict(name="Test", email="test@example.com"),
        answers=[dict(question_id=q["id"], kind="file", value=[document["id"]])],
        upload_session_id=other["id"],
        upload_token=other["upload_token"],
    )
    result = client.post(
        "/api/v1/public/campaigns/" + token + "/applications",
        headers={"Idempotency-Key": uuid4().hex},
        json=body,
    )
    assert result.status_code == 422


def test_rollback_keeps_upload_reusable_and_replay_survives_expiry(context):
    from datetime import timedelta

    import pytest
    from sqlalchemy import event, select
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.documents.repository import upload_sessions, uploads

    client, engine = context
    _, _, snapshot, token, q, session = file_campaign(client)
    document = upload(client, session, q, pdf_bytes()).json()
    body = dict(
        snapshot_id=snapshot["id"],
        contact=dict(name="Test", email="test@example.com"),
        answers=[dict(question_id=q["id"], kind="file", value=[document["id"]])],
        upload_session_id=session["id"],
        upload_token=session["upload_token"],
    )
    path = "/api/v1/public/campaigns/" + token + "/applications"
    key = uuid4().hex

    def fail(db, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO jobs"):
            raise RuntimeError("controlled rollback")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError):
            client.post(path, headers={"Idempotency-Key": key}, json=body)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    with engine.connect() as db:
        assert db.scalar(select(uploads.c.application_id)) is None
    assert (
        client.post(path, headers={"Idempotency-Key": key}, json=body).status_code
        == 201
    )
    with engine.begin() as db:
        db.execute(
            upload_sessions.update().values(expires_at=now(db) - timedelta(hours=1))
        )
        db.execute(uploads.update().values(expires_at=now(db) - timedelta(hours=1)))
    assert (
        client.post(path, headers={"Idempotency-Key": key}, json=body).status_code
        == 200
    )


def test_equivalent_upload_replay_validates_new_capability_without_attachment(context):
    from sqlalchemy import select
    from talent_engine.documents.repository import uploads

    client, engine = context
    _, _, snapshot, token, q, session = file_campaign(client)
    first = upload(client, session, q, pdf_bytes()).json()
    other = client.post(
        "/api/v1/public/campaigns/" + token + "/upload-sessions",
        json={"snapshot_id": snapshot["id"]},
    ).json()
    second = upload(client, other, q, pdf_bytes()).json()
    body = dict(
        snapshot_id=snapshot["id"],
        contact=dict(name="Test", email="test@example.com"),
        answers=[dict(question_id=q["id"], kind="file", value=[first["id"]])],
        upload_session_id=session["id"],
        upload_token=session["upload_token"],
    )
    path = "/api/v1/public/campaigns/" + token + "/applications"
    key = uuid4().hex
    result = client.post(path, headers={"Idempotency-Key": key}, json=body)
    body["answers"][0]["value"] = [second["id"]]
    assert (
        client.post(path, headers={"Idempotency-Key": key}, json=body).status_code
        == 422
    )
    body.update(upload_session_id=other["id"], upload_token=other["upload_token"])
    replay = client.post(path, headers={"Idempotency-Key": key}, json=body)
    assert replay.status_code == 200 and replay.json() == result.json()
    with engine.connect() as db:
        assert (
            db.scalar(
                select(uploads.c.application_id).where(uploads.c.id == second["id"])
            )
            is None
        )


def test_collector_skips_locked_then_collects_expired(context, tmp_path):
    from datetime import timedelta

    from sqlalchemy import select
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.config import Settings
    from talent_engine.documents.cleanup import collect
    from talent_engine.documents.repository import uploads

    client, engine = context
    _, _, _, _, q, session = file_campaign(client)
    upload(client, session, q, pdf_bytes())
    with engine.begin() as db:
        db.execute(uploads.update().values(expires_at=now(db) - timedelta(hours=1)))
    with engine.begin() as db:
        db.execute(select(uploads).with_for_update()).all()
        # No filesystem walk needed: skip lock is independently verified.
        settings = Settings(
            database_url=str(engine.url),
            upload_directory=tmp_path / "uploads",
            public_origin="http://localhost:3003",
            local_development=True,
            csrf_secret="x" * 32,
        )
        assert collect(engine, settings) == 0
    assert collect(engine, settings) == 1
    with engine.connect() as db:
        assert db.scalar(select(uploads.c.id)) is None


def test_encrypted_pdf_and_image_pixel_limits_are_enforced(context):
    from PIL import Image
    from pypdf import PdfWriter

    client, _ = context
    _, _, _, _, q, session = file_campaign(client)
    encrypted = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    writer.write(encrypted)
    assert upload(client, session, q, encrypted.getvalue()).status_code == 415
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, format="PNG")
    result = upload(client, session, q, image.getvalue(), "photo.pdf")
    assert result.status_code == 201 and result.json()["media_type"] == "image/png"
    oversized = BytesIO()
    Image.new("1", (5001, 5000)).save(oversized, format="PNG")
    assert (
        upload(client, session, q, oversized.getvalue(), "large.png").status_code == 415
    )


def test_test_upload_capability_cannot_be_used_on_real_route(context):
    from test_submissions import prepare

    client, _ = context
    h, campaign, _, _ = prepare(client)
    path = "/api/v1/campaigns/" + campaign["id"]
    snapshot = client.post(
        path + "/test-snapshots",
        headers={**h, "If-Match": '"2"', "Idempotency-Key": uuid4().hex},
        json={"source": "published"},
    ).json()
    session = client.post(
        "/api/v1/test-snapshots/" + snapshot["id"] + "/upload-sessions",
        headers=h,
        json={"snapshot_id": snapshot["id"]},
    ).json()
    q = snapshot["configuration"]["questions"][0]
    assert upload(client, session, q, pdf_bytes()).status_code == 404
    client.cookies.clear()
    assert (
        client.post(
            "/api/v1/test-upload-sessions/" + session["id"] + "/files",
            headers={"X-Upload-Token": session["upload_token"]},
            data={"question_id": q["id"]},
            files={"file": ("test.pdf", pdf_bytes())},
        ).status_code
        == 401
    )


def test_truncated_jpeg_is_rejected_after_full_isolated_decode(context):
    from PIL import Image

    client, _ = context
    _, _, _, _, q, session = file_campaign(client)
    data = BytesIO()
    Image.new("RGB", (50, 50)).save(data, format="JPEG")
    assert upload(client, session, q, data.getvalue(), "valid.jpg").status_code == 201
    assert (
        upload(client, session, q, data.getvalue()[:-20], "truncated.jpg").status_code
        == 415
    )
