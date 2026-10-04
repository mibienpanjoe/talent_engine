from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import func, select
from test_campaigns import headers, publishable


def prepare(client):
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    c = client.post(
        "/api/v1/campaigns", headers=h, json={"configuration": publishable()}
    ).json()
    path = "/api/v1/campaigns/" + c["id"]
    s = client.post(
        path + "/publications",
        headers={**h, "If-Match": '"1"', "Idempotency-Key": uuid4().hex},
        json={},
    ).json()
    campaign = client.get(path).json()
    token = campaign["public_url"].split("/")[-1]
    body = dict(
        snapshot_id=s["id"],
        contact={"name": "Personne fictive", "email": "candidate@example.com"},
        answers=[
            dict(
                question_id=s["configuration"]["questions"][0]["id"],
                kind="long_text",
                value="Projet fictif et contribution personnelle.",
            )
        ],
    )
    return h, campaign, token, body


def test_concurrent_submission_is_one_application_job_and_receipt(context):
    client, engine = context
    h, campaign, token, body = prepare(client)
    public = "/api/v1/public/campaigns/" + token + "/applications"
    key = uuid4().hex
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(
                lambda _: client.post(
                    public, headers={"Idempotency-Key": key}, json=body
                ),
                range(4),
            )
        )
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 201]
    assert len({r.json()["receipt_ref"] for r in responses}) == 1
    from talent_engine.applications.repository import (
        analysis_runs,
        applications,
        jobs,
        receipts,
    )

    with engine.connect() as db:
        for table in [applications, jobs, receipts, analysis_runs]:
            assert db.scalar(select(func.count()).select_from(table)) == 1
    frozen = client.get("/api/v1/campaigns/" + campaign["id"]).json()
    assert frozen["configuration_locked_at"] and frozen["revision"] == 3
    assert (
        client.patch(
            "/api/v1/campaigns/" + campaign["id"],
            headers={**h, "If-Match": '"3"'},
            json={"configuration": publishable()},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/campaigns/" + campaign["id"] + "/closures",
            headers={**h, "If-Match": '"3"'},
            json={},
        ).status_code
        == 200
    )
    assert (
        client.post(public, headers={"Idempotency-Key": key}, json=body).status_code
        == 200
    )
    changed = {**body, "contact": {**body["contact"], "name": "Autre"}}
    assert (
        client.post(public, headers={"Idempotency-Key": key}, json=changed).status_code
        == 409
    )
    assert (
        client.post(
            public, headers={"Idempotency-Key": uuid4().hex}, json=body
        ).status_code
        == 409
    )


def test_invalid_answers_have_no_partial_commit_and_are_localized(context):
    client, engine = context
    _, campaign, token, body = prepare(client)
    body["answers"][0]["kind"] = "number"
    body["answers"][0]["value"] = 12
    result = client.post(
        "/api/v1/public/campaigns/" + token + "/applications",
        headers={"Idempotency-Key": uuid4().hex},
        json=body,
    )
    assert result.status_code == 422
    assert result.json()["error"]["details"][0]["path"].startswith("answers.")
    from talent_engine.applications.repository import applications, jobs

    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(applications)) == 0
        assert db.scalar(select(func.count()).select_from(jobs)) == 0
    assert (
        client.get("/api/v1/campaigns/" + campaign["id"]).json()[
            "configuration_locked_at"
        ]
        is None
    )


def test_republication_competes_with_first_submission(context):
    client, _ = context
    h, campaign, token, body = prepare(client)
    path = "/api/v1/campaigns/" + campaign["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(
            client.post,
            path + "/publications",
            headers={**h, "If-Match": '"2"', "Idempotency-Key": uuid4().hex},
            json={},
        )
        b = pool.submit(
            client.post,
            "/api/v1/public/campaigns/" + token + "/applications",
            headers={"Idempotency-Key": uuid4().hex},
            json=body,
        )
        status = [a.result().status_code, b.result().status_code]
        assert status in [[201, 409], [409, 201]]
    current = client.get(path).json()
    if status[1] == 201:
        assert (
            current["active_snapshot_id"] == body["snapshot_id"]
            and current["configuration_locked_at"]
        )
    else:
        assert (
            current["active_snapshot_id"] != body["snapshot_id"]
            and current["configuration_locked_at"] is None
        )


def test_failure_before_job_commit_rolls_back_all_reception_effects(context):
    import pytest
    from sqlalchemy import event
    from talent_engine.applications.repository import applications, jobs, receipts

    client, engine = context
    _, campaign, token, body = prepare(client)

    def fail(db, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO jobs"):
            raise RuntimeError("controlled transaction failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError):
            client.post(
                "/api/v1/public/campaigns/" + token + "/applications",
                headers={"Idempotency-Key": uuid4().hex},
                json=body,
            )
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    with engine.connect() as db:
        for table in [applications, jobs, receipts]:
            assert db.scalar(select(func.count()).select_from(table)) == 0
    assert (
        client.get("/api/v1/campaigns/" + campaign["id"]).json()[
            "configuration_locked_at"
        ]
        is None
    )


def test_test_application_is_private_and_does_not_freeze_campaign(context):
    client, _ = context
    h, campaign, _, body = prepare(client)
    path = "/api/v1/campaigns/" + campaign["id"]
    snapshot = client.post(
        path + "/test-snapshots",
        headers={**h, "If-Match": '"2"', "Idempotency-Key": uuid4().hex},
        json={"source": "published"},
    ).json()
    body["snapshot_id"] = snapshot["id"]
    assert (
        client.post(
            path + "/test-applications",
            headers={**h, "Idempotency-Key": uuid4().hex},
            json=body,
        ).status_code
        == 201
    )
    assert client.get(path).json()["configuration_locked_at"] is None
    assert client.get(path + "/applications").json()["items"] == []
    client.cookies.clear()
    assert (
        client.post(path + "/test-applications", headers=h, json=body).status_code
        == 401
    )


def test_json_limit_and_number_precision_are_rejected(context):
    client, _ = context
    _, _, token, body = prepare(client)
    public = "/api/v1/public/campaigns/" + token + "/applications"
    assert (
        client.post(
            public, headers={"Content-Type": "application/json"}, content=b" " * 262145
        ).status_code
        == 413
    )
    body["answers"][0]["kind"] = "number"
    body["answers"][0]["value"] = 1234567890123456
    assert (
        client.post(
            public, headers={"Idempotency-Key": uuid4().hex}, json=body
        ).status_code
        == 422
    )


def test_private_detail_uses_received_snapshot_and_invalid_unicode_is_rejected(context):
    client, _ = context
    _, campaign, token, body = prepare(client)
    public = "/api/v1/public/campaigns/" + token + "/applications"
    bad = {**body, "contact": {**body["contact"], "name": "bad\x00name"}}
    assert (
        client.post(
            public, headers={"Idempotency-Key": uuid4().hex}, json=bad
        ).status_code
        == 422
    )
    assert (
        client.post(
            public, headers={"Idempotency-Key": uuid4().hex}, json=body
        ).status_code
        == 201
    )
    item = client.get("/api/v1/campaigns/" + campaign["id"] + "/applications").json()[
        "items"
    ][0]
    path = "/api/v1/applications/" + item["id"]
    detail = client.get(path).json()
    assert detail["snapshot"]["id"] == body["snapshot_id"]
    assert detail["answers"] == body["answers"]
    client.cookies.clear()
    assert client.get(path).status_code == 401


def test_application_cursor_binds_campaign_and_revision_without_skips(context):
    client, _ = context
    _, campaign, token, body = prepare(client)
    public = "/api/v1/public/campaigns/" + token + "/applications"
    for _ in range(3):
        assert (
            client.post(
                public, headers={"Idempotency-Key": uuid4().hex}, json=body
            ).status_code
            == 201
        )
    path = "/api/v1/campaigns/" + campaign["id"] + "/applications"
    first = client.get(path, params={"limit": 1}).json()
    cursor = first["next_cursor"]
    second = client.get(path, params={"limit": 1, "cursor": cursor}).json()
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get(path, params={"cursor": cursor + "bad"}).status_code == 400
    assert (
        client.post(
            public, headers={"Idempotency-Key": uuid4().hex}, json=body
        ).status_code
        == 201
    )
    stale = client.get(path, params={"cursor": cursor})
    assert (
        stale.status_code == 409
        and stale.json()["error"]["code"] == "cursor_invalidated"
    )
