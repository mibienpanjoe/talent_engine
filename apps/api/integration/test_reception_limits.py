from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from talent_engine.errors import AccessError
from test_submissions import prepare
from test_uploads import file_campaign, pdf_bytes, upload


def test_shared_request_limits_count_replays_and_ignore_forwarded_ip(context):
    client, _ = context
    _, _, token, body = prepare(client)
    path = "/api/v1/public/campaigns/" + token + "/applications"
    key = uuid4().hex
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(
            pool.map(
                lambda i: client.post(
                    path,
                    json=body,
                    headers={"Idempotency-Key": key, "X-Forwarded-For": f"192.0.2.{i}"},
                ),
                range(12),
            )
        )
    assert sorted(r.status_code for r in responses) == [200] * 9 + [201] + [429] * 2
    assert all(
        int(r.headers["Retry-After"]) >= 1 for r in responses if r.status_code == 429
    )


def test_two_upload_slots_are_shared_and_expire_after_crash(context):
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.documents.repository import upload_sessions, uploads
    from talent_engine.reception_limits.repository import transfers
    from talent_engine.reception_limits.service import reserve_transfer

    client, engine = context
    _, _, _, _, q, session = file_campaign(client)
    with engine.begin() as db:
        db.execute(select(upload_sessions).with_for_update()).all()
        reserve_transfer(db, session["id"])
        reserve_transfer(db, session["id"])
    result = upload(client, session, q, pdf_bytes())
    assert result.status_code == 429 and int(result.headers["Retry-After"]) >= 1
    with engine.begin() as db:
        assert db.scalar(select(uploads.c.id)) is None
        db.execute(transfers.update().values(expires_at=now(db) - timedelta(seconds=1)))
    assert upload(client, session, q, pdf_bytes()).status_code == 201
    with engine.connect() as db:
        assert db.scalar(select(transfers.c.id)) is None


def test_campaign_request_quota_is_atomic_across_different_ips(context):
    from talent_engine.config import Settings
    from talent_engine.reception_limits.service import requests

    client, engine = context
    _, _, token, _ = prepare(client)
    settings = Settings(
        database_url=engine.url.render_as_string(hide_password=False),
        public_origin="http://localhost:3003",
        local_development=True,
        csrf_secret="test-only-csrf-" + "x" * 32,
    )

    def attempt(i):
        try:
            requests(
                engine,
                settings,
                [
                    (f"submission-ip:192.0.2.{i}", 10),
                    (f"submission-campaign:{token}", 100),
                ],
            )
            return True
        except AccessError as error:
            assert error.status == 429
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(105)))
    assert sum(results) == 100
