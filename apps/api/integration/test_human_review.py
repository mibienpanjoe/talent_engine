from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from sqlalchemy import select
from talent_engine.evaluations.data import evaluations
from test_campaigns import headers
from test_reviews import deposit, prepared


def test_correction_projection_restore_and_stale_write(context):
    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Chloé", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    before = client.get(path).json()
    evaluation = before["effective_evaluation"]
    target = evaluation["assessments"][1]["criterion_id"]
    payload = dict(
        review_revision=before["application"]["review_revision"],
        effective_evaluation_id=evaluation["id"],
        target_kind="assessment",
        criterion_id=target,
        action="set",
        status="evaluated",
        level=3,
        reason="Vérification du projet pendant l’entretien fictif.",
        human_note="Le projet a été expliqué et exécuté devant le responsable.",
    )
    h = headers(client)
    response = client.post(path + "/corrections", headers=h, json=payload)
    assert response.status_code == 201, response.text
    after = client.get(path).json()
    assert after["application"]["calculation"]["score"] == "85.000000"
    assert after["application"]["calculation"]["coverage"] == "100.000000"
    assert after["application"]["views"] == ["all", "ready"]
    assert after["application"]["rank"] == 1
    with engine.connect() as db:
        base = (
            db.execute(
                select(evaluations).where(evaluations.c.id == UUID(evaluation["id"]))
            )
            .mappings()
            .one()
        )
        assert base["calculation"]["score"] is None
        assert base["assessments"][1]["level"] is None
    assert (
        client.post(path + "/corrections", headers=h, json=payload).status_code == 409
    )
    history = client.get(path + "/review-history").json()
    assert len(history) == 1 and history[0]["previous"]["level"] is None
    assert history[0]["value"]["level"] == 3 and history[0]["author_id"]
    restore = {
        **payload,
        "review_revision": after["application"]["review_revision"],
        "action": "restore_base",
        "status": None,
        "level": None,
        "human_note": None,
    }
    assert (
        client.post(path + "/corrections", headers=h, json=restore).status_code == 201
    )
    restored = client.get(path).json()
    assert restored["application"]["calculation"]["score"] is None
    assert len(client.get(path + "/review-history").json()) == 2


def test_invalid_and_concurrent_corrections_are_atomic(context):
    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Concurrent", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    detail = client.get(path).json()
    payload = dict(
        review_revision=detail["application"]["review_revision"],
        effective_evaluation_id=detail["effective_evaluation"]["id"],
        target_kind="assessment",
        criterion_id=detail["effective_evaluation"]["assessments"][1]["criterion_id"],
        action="set",
        status="evaluated",
        level=3,
        reason="Observation vérifiée.",
        human_note="Démonstration du travail observée.",
    )
    h = headers(client)
    for change in (
        {"reason": " "},
        {"level": 5},
        {"human_note": None},
        {"status": "source_unavailable", "level": 3},
    ):
        assert (
            client.post(
                path + "/corrections", headers=h, json={**payload, **change}
            ).status_code
            == 422
        )
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda _: (
                    client.post(
                        path + "/corrections", headers=h, json=payload
                    ).status_code
                ),
                range(2),
            )
        )
    assert sorted(results) == [201, 409]
    assert len(client.get(path + "/review-history").json()) == 1
    client.cookies.clear()
    assert (
        client.post(path + "/corrections", headers=h, json=payload).status_code == 401
    )
    assert client.get(path + "/review-history").status_code == 401


def test_condition_correction_and_evidence_boundaries(context):
    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Indisponible", [4, 4, 3], unmet=True)
    foreign_id = deposit(client, engine, data, "Autre dossier", [4, 4, 3])
    path = "/api/v1/applications/" + app_id
    detail = client.get(path).json()
    foreign = client.get("/api/v1/applications/" + foreign_id).json()
    condition = detail["effective_evaluation"]["conditions"][0]
    payload = dict(
        review_revision=detail["application"]["review_revision"],
        effective_evaluation_id=detail["effective_evaluation"]["id"],
        target_kind="condition",
        criterion_id=condition["criterion_id"],
        action="set",
        status="met",
        reason="Date confirmée pendant l’entretien.",
        evidence_ids=[foreign["evidence"][0]["id"]],
    )
    h = headers(client)
    assert (
        client.post(path + "/corrections", headers=h, json=payload).status_code == 422
    )
    assert client.get(path + "/review-history").json() == []
    assert (
        client.post(
            path + "/corrections", headers={"Origin": h["Origin"]}, json=payload
        ).status_code
        == 403
    )
    payload.update(
        evidence_ids=[],
        human_note="Le candidat confirme sa disponibilité au 5 octobre.",
    )
    assert (
        client.post(path + "/corrections", headers=h, json=payload).status_code == 201
    )
    after = client.get(path).json()
    assert after["effective_evaluation"]["conditions"][0]["status"] == "met"
    assert after["application"]["views"] == ["all", "ready"]
    assert after["application"]["calculation"] == detail["application"]["calculation"]
    note = after["effective_evaluation"]["conditions"][0]["evidence_ids"][0]
    evidence = client.get("/api/v1/evidence/" + note).json()
    assert (
        evidence["nature"] == "human_verification"
        and evidence["locator"]["kind"] == "human"
    )


def test_decisions_preserve_evaluation_alerts_and_detect_conflicts(context):
    client, engine = context
    data = prepared(client)
    app_id = deposit(
        client, engine, data, "Décision indépendante", [4, None, 3], unmet=True
    )
    path = "/api/v1/applications/" + app_id
    before = client.get(path).json()
    h = headers(client)
    expectation = dict(
        review_revision=before["application"]["review_revision"],
        effective_evaluation_id=before["application"]["effective_evaluation_id"],
    )
    for choice in ("shortlisted", "not_selected", "to_review"):
        response = client.post(
            path + "/decisions", headers=h, json={**expectation, "decision": choice}
        )
        assert response.status_code == 201, response.text
        after = client.get(path).json()
        assert after["application"]["decision"] == choice
        assert after["effective_evaluation"] == before["effective_evaluation"]
        assert after["application"]["views"] == before["application"]["views"]
        assert (
            client.post(
                path + "/decisions", headers=h, json={**expectation, "decision": choice}
            ).status_code
            == 409
        )
        expectation["review_revision"] = after["application"]["review_revision"]
    history = client.get(path + "/review-history").json()
    assert [x["value"]["decision"] for x in history] == [
        "shortlisted",
        "not_selected",
        "to_review",
    ]
    client.cookies.clear()
    assert (
        client.post(
            path + "/decisions",
            headers=h,
            json={**expectation, "decision": "shortlisted"},
        ).status_code
        == 401
    )
