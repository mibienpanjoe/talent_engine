from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import select
from talent_engine.access import reviewers


def config():
    return dict(
        type="training",
        title="Formation test",
        domain="Développement",
        description="Bases",
        target_level="Débutant",
        deadline=None,
        requirements=[],
        questions=[],
    )


def headers(client, **extra):
    result = client.post(
        "/api/v1/access/session",
        headers={"Origin": "http://localhost:3003"},
        json={"login": "reviewer", "password": "test-only-password"},
    )
    assert result.status_code == 200
    return {
        "Origin": "http://localhost:3003",
        "X-CSRF-Token": result.json()["csrf_token"],
        **extra,
    }


def test_draft_create_replay_reload_update_and_conflict(context):
    client, _ = context
    assert client.get("/api/v1/campaigns").status_code == 401
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    assert (
        client.post("/api/v1/campaigns", json={"configuration": config()}).status_code
        == 403
    )
    first = client.post(
        "/api/v1/campaigns", headers=h, json={"configuration": config()}
    )
    assert first.status_code == 201
    assert first.headers["etag"] == '"1"'
    body = first.json()
    assert body["state"] == "draft" and body["public_url"] is None
    assert (
        client.post(
            "/api/v1/campaigns", headers=h, json={"configuration": config()}
        ).json()
        == body
    )
    changed = config()
    changed["title"] = "Changed"
    assert (
        client.post(
            "/api/v1/campaigns", headers=h, json={"configuration": changed}
        ).status_code
        == 409
    )
    path = "/api/v1/campaigns/" + body["id"]
    assert client.get(path).json() == body
    assert (
        client.patch(path, headers=h, json={"configuration": changed}).status_code
        == 428
    )
    updated = client.patch(
        path, headers={**h, "If-Match": '"1"'}, json={"configuration": changed}
    )
    assert updated.status_code == 200 and updated.json()["revision"] == 2
    assert (
        client.patch(
            path, headers={**h, "If-Match": '"1"'}, json={"configuration": config()}
        ).status_code
        == 409
    )
    assert client.get(path).json()["configuration"]["title"] == "Changed"
    assert client.get("/api/v1/campaigns").json()["items"][0]["id"] == body["id"]


def test_concurrent_create_and_owner_isolation(context):
    client, engine = context
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(
            pool.map(
                lambda _: client.post(
                    "/api/v1/campaigns", headers=h, json={"configuration": config()}
                ),
                range(4),
            )
        )
    assert all(x.status_code == 201 for x in rows)
    assert len({x.json()["id"] for x in rows}) == 1
    from talent_engine.campaigns.repository import campaigns

    with engine.begin() as db:
        owner = db.scalar(select(reviewers.c.id))
        assert len(db.execute(select(campaigns.c.id)).all()) == 1
        # Simulate an owned record inaccessible to the authenticated reviewer.
        db.execute(
            reviewers.insert().values(
                id=uuid4(), login="other", password_hash="disabled", disabled_at=None
            )
        )
        other = db.scalar(select(reviewers.c.id).where(reviewers.c.id != owner))
        db.execute(campaigns.update().values(owner_id=other))
    assert client.get("/api/v1/campaigns/" + rows[0].json()["id"]).status_code == 404
    assert client.get("/api/v1/campaigns").json()["items"] == []
