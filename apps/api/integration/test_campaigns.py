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


def test_preparation_reports_deleted_source_without_inventing_association(context):
    client, _ = context
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    data = config()
    data["requirements"] = [
        dict(
            id=str(uuid4()),
            family="practical_work",
            expectation="Projet",
            importance="desired",
            evaluation_mode="qualitative",
            assessment_mode="automatic",
            source_question_ids=[],
        )
    ]
    result = client.post("/api/v1/campaigns", headers=h, json={"configuration": data})
    assert result.status_code == 201
    issues = client.get(
        "/api/v1/campaigns/" + result.json()["id"] + "/preparation"
    ).json()["issues"]
    assert {
        "path": "requirements.0.source_question_ids",
        "code": "missing_source",
    } in issues
    assert (
        result.json()["configuration"]["requirements"][0]["source_question_ids"] == []
    )


def publishable():
    data = config()
    q = str(uuid4())
    data["questions"] = [
        dict(
            id=q,
            type="long_text",
            label="Projet",
            required=False,
            position=0,
            constraints={},
        )
    ]
    data["requirements"] = [
        dict(
            id=str(uuid4()),
            family="practical_work",
            expectation="Projet personnel",
            importance="required",
            evaluation_mode="qualitative",
            assessment_mode="automatic",
            source_question_ids=[q],
        )
    ]
    return data


def test_publish_revise_close_and_duplicate_snapshot(context):
    client, _ = context
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    created = client.post(
        "/api/v1/campaigns", headers=h, json={"configuration": publishable()}
    ).json()
    path = "/api/v1/campaigns/" + created["id"]
    assert client.get("/api/v1/public/campaigns/unavailable").status_code == 404
    publish_headers = {**h, "If-Match": '"1"', "Idempotency-Key": uuid4().hex}
    first = client.post(path + "/publications", headers=publish_headers, json={})
    assert first.status_code == 201
    assert first.headers["etag"] == '"2"'
    assert (
        client.post(path + "/publications", headers=publish_headers, json={}).json()
        == first.json()
    )
    active = client.get(path).json()
    public_path = active["public_url"].replace(
        "http://localhost:3003/apply/", "/api/v1/public/campaigns/"
    )
    public = client.get(public_path).json()
    assert public["state"] == "open" and public["snapshot_id"] == first.json()["id"]
    assert (
        "requirements" not in public
        and "owner_id" not in public
        and "policy" not in public
    )
    changed = publishable()
    changed["title"] = "Révisée"
    edited = client.patch(
        path, headers={**h, "If-Match": '"2"'}, json={"configuration": changed}
    )
    assert edited.status_code == 200 and edited.json()["has_unpublished_changes"]
    assert client.get(public_path).json()["title"] == "Formation test"
    second = client.post(
        path + "/publications",
        headers={**h, "If-Match": '"3"', "Idempotency-Key": uuid4().hex},
        json={},
    )
    assert second.status_code == 201 and second.json()["id"] != first.json()["id"]
    copy = client.post(
        path + "/duplicates",
        headers={**h, "If-Match": '"4"', "Idempotency-Key": uuid4().hex},
        json={"source": "published"},
    )
    assert copy.status_code == 201 and copy.json()["state"] == "draft"
    assert (
        copy.json()["configuration"]["questions"][0]["id"]
        != changed["questions"][0]["id"]
    )
    assert copy.json()["configuration"]["deadline"] is None
    closed = client.post(path + "/closures", headers={**h, "If-Match": '"4"'}, json={})
    assert (
        closed.status_code == 200
        and client.get(public_path).json()["state"] == "closed"
    )
    assert (
        client.post(
            path + "/publications",
            headers={**h, "If-Match": '"5"', "Idempotency-Key": uuid4().hex},
            json={},
        ).status_code
        == 409
    )


def test_publication_and_edit_compete_with_revision_check(context):
    client, _ = context
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    created = client.post(
        "/api/v1/campaigns", headers=h, json={"configuration": publishable()}
    ).json()
    path = "/api/v1/campaigns/" + created["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(
            client.post,
            path + "/publications",
            headers={**h, "If-Match": '"1"', "Idempotency-Key": uuid4().hex},
            json={},
        )
        b = pool.submit(
            client.patch,
            path,
            headers={**h, "If-Match": '"1"'},
            json={"configuration": publishable()},
        )
        assert sorted([a.result().status_code, b.result().status_code]) in [
            [200, 409],
            [201, 409],
        ]


def test_test_snapshot_is_private_and_never_activates_public_form(context):
    client, engine = context
    h = headers(client, **{"Idempotency-Key": uuid4().hex})
    created = client.post(
        "/api/v1/campaigns", headers=h, json={"configuration": publishable()}
    ).json()
    path = "/api/v1/campaigns/" + created["id"]
    snapshot = client.post(
        path + "/test-snapshots",
        headers={**h, "If-Match": '"1"', "Idempotency-Key": uuid4().hex},
        json={"source": "draft"},
    )
    assert snapshot.status_code == 201 and snapshot.json()["mode"] == "test"
    assert (
        client.get("/api/v1/test-snapshots/" + snapshot.json()["id"]).status_code == 200
    )
    campaign = client.get(path).json()
    assert (
        campaign["active_snapshot_id"] is None
        and campaign["configuration_locked_at"] is None
    )
    client.cookies.clear()
    assert (
        client.get("/api/v1/test-snapshots/" + snapshot.json()["id"]).status_code == 401
    )


def test_frozen_title_correction_keeps_snapshot_and_audits_author(context):
    from test_submissions import prepare

    client, _ = context
    h, campaign, token, body = prepare(client)
    path = "/api/v1/campaigns/" + campaign["id"]
    original_title = campaign["configuration"]["title"]
    draft = {**campaign["configuration"], "title": "Titre de brouillon non publié"}
    assert (
        client.patch(
            path, headers={**h, "If-Match": '"2"'}, json={"configuration": draft}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/public/campaigns/" + token + "/applications",
            headers={"Idempotency-Key": uuid4().hex},
            json=body,
        ).status_code
        == 201
    )
    before = client.get(path).json()
    assert before["display_title"] == original_title
    result = client.patch(
        path, headers={**h, "If-Match": '"4"'}, json={"title": "Titre corrigé"}
    )
    assert result.status_code == 200, result.text
    after = result.json()
    assert after["active_snapshot_id"] == before["active_snapshot_id"]
    assert after["configuration"] == before["configuration"] and after["revision"] == 5
    assert (
        client.get("/api/v1/public/campaigns/" + token).json()["title"]
        == "Titre corrigé"
    )
    history = client.get(path + "/title-history").json()
    assert len(history) == 1 and history[0]["previous_title"] == original_title
    assert (
        history[0]["title"] == "Titre corrigé"
        and history[0]["author_id"]
        and history[0]["changed_at"]
    )
    assert (
        client.patch(
            path, headers={**h, "If-Match": '"4"'}, json={"title": "Autre"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            path,
            headers={**h, "If-Match": '"5"'},
            json={"title": "Autre", "configuration": draft},
        ).status_code
        == 422
    )
    application_id = client.get(path + "/applications").json()["items"][0]["id"]
    assert (
        client.get("/api/v1/applications/" + application_id).json()["snapshot"][
            "configuration"
        ]["title"]
        == original_title
    )
