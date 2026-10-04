from functools import partial
from uuid import uuid4

from embedding_fixture import ControlledEmbeddings
from talent_engine.analyses.processor import process
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from test_campaigns import headers
from test_reviews import OracleGateway, deposit, prepared


def review_headers(headers, payload):
    return {
        **headers,
        "If-Match": f'"{payload["review_revision"]}"',
        "Idempotency-Key": headers.get("Idempotency-Key", uuid4().hex),
    }


def correction(client, path, h):
    detail = client.get(path).json()
    payload = dict(
        review_revision=detail["application"]["review_revision"],
        effective_evaluation_id=detail["application"]["effective_evaluation_id"],
        target_kind="assessment",
        criterion_id=detail["effective_evaluation"]["assessments"][1]["criterion_id"],
        action="set",
        status="evaluated",
        level=3,
        reason="Travail vérifié.",
        human_note="Démonstration observée pendant l’entretien.",
    )
    response = client.post(
        path + "/corrections", headers=review_headers(h, payload), json=payload
    )
    assert response.status_code == 201
    return response.json()


def expectation(client, path):
    app = client.get(path).json()["application"]
    return dict(
        review_revision=app["review_revision"],
        effective_evaluation_id=app["effective_evaluation_id"],
    )


def test_reanalysis_pending_reapply_and_confirmed_new_base(context):
    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Versions", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    event = correction(client, path, h)
    before = client.get(path).json()
    payload = {
        **expectation(client, path),
        "reason": "reanalyze",
        "base_run_id": before["effective_evaluation"]["run_id"],
        "source_ids": [],
    }
    key = uuid4().hex
    request = client.post(
        path + "/analyses",
        headers=review_headers({**h, "Idempotency-Key": key}, payload),
        json=payload,
    )
    assert request.status_code == 202, request.text
    replay = client.post(
        path + "/analyses",
        headers=review_headers({**h, "Idempotency-Key": key}, payload),
        json=payload,
    )
    assert replay.status_code == 202 and replay.json()["id"] == request.json()["id"]
    assert (
        client.post(
            path + "/analyses",
            headers=review_headers(
                {**h, "Idempotency-Key": uuid4().hex},
                {**payload, **expectation(client, path)},
            ),
            json={**payload, **expectation(client, path)},
        ).status_code
        == 409
    )
    processor = partial(
        process, gateway=OracleGateway([4, 2, 3]), embedder=ControlledEmbeddings()
    )
    for _ in range(3):
        assert work_once(engine, WorkerSettings(), "versions", processor=processor)
    detail = client.get(path).json()
    assert detail["effective_evaluation"] == before["effective_evaluation"]
    assert detail["application"]["calculation"]["score"] == "85.000000"
    new_id = detail["pending_evaluation_ids"][0]
    activation = {
        **expectation(client, path),
        "evaluation_id": new_id,
        "mode": "reapply_selected",
        "reason": "Observation humaine toujours pertinente.",
        "corrections": [
            dict(
                origin_event_id=event["id"],
                correction={
                    **event_to_payload(before, event),
                    **expectation(client, path),
                },
            )
        ],
    }
    result = client.post(
        path + "/activations", headers=review_headers(h, activation), json=activation
    )
    assert result.status_code == 200, result.text
    detail = client.get(path).json()
    assert detail["application"]["effective_evaluation_id"] == new_id
    assert detail["application"]["calculation"]["score"] == "85.000000"
    history = client.get(path + "/review-history").json()
    assert len(history) == 3 and history[1]["origin_event_id"] == event["id"]
    assert history[1]["previous"]["level"] == 2
    versions = client.get(path + "/evaluation-versions").json()
    assert len(versions) == 2 and versions[0]["base"]["assessments"][1]["level"] == 2
    # A second base cannot silently replace active human corrections.
    payload = {
        **expectation(client, path),
        "reason": "reanalyze",
        "base_run_id": detail["effective_evaluation"]["run_id"],
        "source_ids": [],
    }
    assert (
        client.post(
            path + "/analyses",
            headers=review_headers({**h, "Idempotency-Key": uuid4().hex}, payload),
            json=payload,
        ).status_code
        == 202
    )
    for _ in range(3):
        assert work_once(engine, WorkerSettings(), "versions", processor=processor)
    pending = client.get(path).json()["pending_evaluation_ids"][0]
    payload = {
        **expectation(client, path),
        "evaluation_id": pending,
        "mode": "use_new_base",
        "reason": "Activer la nouvelle analyse.",
        "corrections": [],
    }
    assert (
        client.post(
            path + "/activations", headers=review_headers(h, payload), json=payload
        ).status_code
        == 422
    )
    assert (
        client.post(
            path + "/activations",
            headers=review_headers(h, {**payload, "confirm_discard_corrections": True}),
            json={**payload, "confirm_discard_corrections": True},
        ).status_code
        == 200
    )
    assert client.get(path).json()["application"]["calculation"]["score"] == "76.250000"
    assert len(client.get(path + "/review-history").json()) == 4


def event_to_payload(detail, event):
    return dict(
        target_kind=event["kind"],
        criterion_id=event["criterion_id"],
        action="set",
        status="evaluated",
        level=3,
        reason="Vérification revalidée pour cette nouvelle version.",
        evidence_ids=event["value"]["evidence_ids"],
    )


class BrokenPortfolio:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        from talent_engine.integrations.public_web import WebFailure

        self.calls.append(url)
        raise WebFailure("source_not_found")


class RestoredPortfolio:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        from talent_engine.integrations.public_web import Page

        self.calls.append(url)
        return Page(
            url,
            200,
            {"content-type": "text/html"},
            b"<h1>Projet fictif</h1><p>Formulaire explique et teste.</p>",
        )


def test_targeted_source_retry_reuses_good_sources_and_cache(context):
    from sqlalchemy import select
    from talent_engine.sources.data import run_sources

    client, engine = context
    data = prepared(client, question_types=["long_text", "url", "long_text", "date"])
    failed = BrokenPortfolio()
    app_id = deposit(
        client,
        engine,
        data,
        "Portfolio en panne",
        [4, None, 3],
        portfolio_web=failed,
        source_values=[
            "Preuve programmation",
            "https://example.com/projet/",
            "Approche expliquee",
            "2026-10-05",
        ],
    )
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    correction(client, path, h)
    before = client.get(path).json()
    bad = next(s for s in before["sources"] if s["kind"] == "portfolio")
    assert bad["state"] == "unavailable"
    good = next(s for s in before["sources"] if s["kind"] == "answer")
    body = {
        **expectation(client, path),
        "reason": "retry_sources",
        "base_run_id": before["effective_evaluation"]["run_id"],
        "source_ids": [good["id"]],
    }
    assert (
        client.post(
            path + "/analyses", headers=review_headers(h, body), json=body
        ).status_code
        == 422
    )
    body["source_ids"] = [bad["id"]]
    response = client.post(
        path + "/analyses", headers=review_headers(h, body), json=body
    )
    assert response.status_code == 202, response.text
    restored = RestoredPortfolio()
    embeddings = ControlledEmbeddings()
    processor = partial(
        process,
        portfolio_web=restored,
        gateway=OracleGateway([4, 2, 3]),
        embedder=embeddings,
    )
    for _ in range(3):
        assert work_once(engine, WorkerSettings(), "source-retry", processor=processor)
    after = client.get(path).json()
    assert after["effective_evaluation"] == before["effective_evaluation"]
    assert len(restored.calls) == 1
    with engine.connect() as db:
        ids = set(
            str(x)
            for x in db.scalars(
                select(run_sources.c.source_version_id).where(
                    run_sources.c.run_id == response.json()["id"]
                )
            )
        )
    assert good["id"] in ids and bad["id"] not in ids
    version = client.get(path + "/evaluation-versions").json()[0]["base"]
    assert version["provenance"]["retrieval"]["cache_hits"] >= 3
    assert version["provenance"]["retrieval"]["cache_misses"] == 1


def test_activation_rejects_replaced_source_atomically(context):
    client, engine = context
    data = prepared(client, question_types=["long_text", "url", "long_text", "date"])
    app_id = deposit(
        client,
        engine,
        data,
        "Preuve remplacée",
        [4, 2, 3],
        portfolio_web=RestoredPortfolio(),
        source_values=[
            "Fondations",
            "https://example.com/projet/",
            "Approche",
            "2026-10-05",
        ],
    )
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    detail = client.get(path).json()
    assessment = detail["effective_evaluation"]["assessments"][1]
    body = {
        **expectation(client, path),
        "target_kind": "assessment",
        "criterion_id": assessment["criterion_id"],
        "action": "set",
        "status": "evaluated",
        "level": 3,
        "reason": "Contribution vérifiée dans le passage.",
        "evidence_ids": assessment["evidence_ids"],
    }
    event = client.post(
        path + "/corrections", headers=review_headers(h, body), json=body
    ).json()
    original = client.get(path).json()
    source = next(s for s in detail["sources"] if s["kind"] == "portfolio")
    request = {
        **expectation(client, path),
        "reason": "reanalyze",
        "base_run_id": detail["effective_evaluation"]["run_id"],
        "source_ids": [source["id"]],
    }
    assert (
        client.post(
            path + "/analyses", headers=review_headers(h, request), json=request
        ).status_code
        == 202
    )

    class ReplacedPortfolio(RestoredPortfolio):
        def get(self, url, **kwargs):
            from talent_engine.integrations.public_web import Page

            return Page(
                url,
                200,
                {"content-type": "text/html"},
                b"<h1>Autre projet fictif</h1>"
                b"<p>Les informations anterieures ont ete remplacees.</p>",
            )

    processor = partial(
        process,
        portfolio_web=ReplacedPortfolio(),
        gateway=OracleGateway([4, 2, 3]),
        embedder=ControlledEmbeddings(),
    )
    for _ in range(3):
        assert work_once(engine, WorkerSettings(), "replace", processor=processor)
    detail = client.get(path).json()
    target = detail["pending_evaluation_ids"][0]
    body = {
        **expectation(client, path),
        "evaluation_id": target,
        "mode": "reapply_selected",
        "reason": "Reprise contrôlée de la correction.",
        "corrections": [
            {
                "origin_event_id": event["id"],
                "correction": {
                    **request_correction(event),
                    **expectation(client, path),
                },
            }
        ],
    }
    response = client.post(
        path + "/activations", headers=review_headers(h, body), json=body
    )
    assert response.status_code == 422, response.text
    after = client.get(path).json()
    assert after["effective_evaluation"] == original["effective_evaluation"]
    assert len(client.get(path + "/review-history").json()) == 1
    assert (
        after["application"]["review_revision"]
        == detail["application"]["review_revision"]
    )


def request_correction(event):
    return dict(
        target_kind="assessment",
        criterion_id=event["criterion_id"],
        action="set",
        status="evaluated",
        level=3,
        reason="Preuve revérifiée.",
        evidence_ids=event["value"]["evidence_ids"],
    )


def test_failed_reanalysis_quota_budget_and_review_preconditions(context):
    from talent_engine.applications.data import jobs
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.integrations.llm import ProviderFailure

    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Panne après correction", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    correction(client, path, h)
    original = client.get(path).json()
    body = {
        **expectation(client, path),
        "reason": "reanalyze",
        "base_run_id": original["effective_evaluation"]["run_id"],
        "source_ids": [],
    }
    assert (
        client.post(
            path + "/analyses", headers={**h, "Idempotency-Key": uuid4().hex}, json=body
        ).status_code
        == 428
    )
    key = uuid4().hex
    request_headers = review_headers({**h, "Idempotency-Key": key}, body)
    response = client.post(path + "/analyses", headers=request_headers, json=body)
    assert response.status_code == 202
    assert (
        client.post(
            path + "/analyses",
            headers=request_headers,
            json={**body, "source_ids": [uuid4().hex]},
        ).status_code
        == 409
    )

    class QuotaGateway:
        def __init__(self):
            self.calls = 0

        def chat(self, *args, **kwargs):
            self.calls += 1
            raise ProviderFailure(
                "provider_rate_limited", retryable=True, retry_after=0
            )

    gateway = QuotaGateway()
    processor = partial(process, gateway=gateway, embedder=ControlledEmbeddings())
    for _ in range(5):
        assert work_once(engine, WorkerSettings(), "quota", processor=processor)
        with engine.begin() as db:
            db.execute(
                jobs.update()
                .where(
                    jobs.c.run_id == response.json()["id"], jobs.c.state == "waiting"
                )
                .values(next_attempt_at=now(db))
            )
    after = client.get(path).json()
    assert gateway.calls == 3 and after["application"]["processing_state"] == "failed"
    assert after["effective_evaluation"] == original["effective_evaluation"]
    assert after["pending_evaluation_ids"] == []
    assert (
        client.post(path + "/analyses", headers=request_headers, json=body).json()
        == response.json()
    )


def test_review_action_replay_and_scoped_history_pagination(context):
    client, engine = context
    data = prepared(client)
    app_id = deposit(client, engine, data, "Historique paginé", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    first = correction(client, path, h)
    restore = {
        **expectation(client, path),
        "target_kind": "assessment",
        "criterion_id": first["criterion_id"],
        "action": "restore_base",
        "reason": "Retour à la base pour la recette.",
    }
    request_headers = review_headers(h, restore)
    response = client.post(path + "/corrections", headers=request_headers, json=restore)
    assert response.status_code == 201
    assert (
        client.post(path + "/corrections", headers=request_headers, json=restore).json()
        == response.json()
    )
    page = client.get(path + "/review-history", params={"limit": 1})
    cursor = page.headers["X-Next-Cursor"]
    assert len(page.json()) == 1
    second = client.get(path + "/review-history", params={"limit": 1, "cursor": cursor})
    assert (
        second.json()[0]["action"] == "restore_base"
        and "X-Next-Cursor" not in second.headers
    )
    assert (
        client.get(path + "/evaluation-versions", params={"cursor": cursor}).status_code
        == 400
    )
    assert (
        client.get(path + "/review-history", params={"active_only": True}).json() == []
    )
    decision = {**expectation(client, path), "decision": "shortlisted"}
    assert (
        client.patch(
            path + "/decision", headers=review_headers(h, decision), json=decision
        ).status_code
        == 200
    )
    assert (
        client.get(
            path + "/review-history", params={"limit": 1, "cursor": cursor}
        ).status_code
        == 409
    )


def test_partial_reapplication_requires_discard_confirmation(context):
    client, engine = context
    app_id = deposit(client, engine, prepared(client), "Report partiel", [4, None, 3])
    path = "/api/v1/applications/" + app_id
    h = headers(client)
    first = correction(client, path, h)
    detail = client.get(path).json()
    second_body = {
        **expectation(client, path),
        "target_kind": "assessment",
        "criterion_id": detail["effective_evaluation"]["assessments"][0][
            "criterion_id"
        ],
        "action": "set",
        "status": "evaluated",
        "level": 3,
        "reason": "Deuxième correction vérifiée.",
        "evidence_ids": detail["effective_evaluation"]["assessments"][0][
            "evidence_ids"
        ],
    }
    response = client.post(
        path + "/corrections", headers=review_headers(h, second_body), json=second_body
    )
    assert response.status_code == 201, response.text
    detail = client.get(path).json()
    body = {
        **expectation(client, path),
        "reason": "reanalyze",
        "base_run_id": detail["effective_evaluation"]["run_id"],
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
    for _ in range(3):
        assert work_once(
            engine, WorkerSettings(), "partial-report", processor=processor
        )
    before = client.get(path).json()
    activation = {
        **expectation(client, path),
        "evaluation_id": before["pending_evaluation_ids"][0],
        "mode": "reapply_selected",
        "reason": "Reporter seulement la première correction.",
        "corrections": [
            dict(
                origin_event_id=first["id"],
                correction={
                    **event_to_payload(before, first),
                    **expectation(client, path),
                },
            )
        ],
    }
    response = client.post(
        path + "/activations", headers=review_headers(h, activation), json=activation
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "correction_confirmation_required"
    assert client.get(path).json()["application"] == before["application"]
    activation["confirm_discard_corrections"] = True
    response = client.post(
        path + "/activations", headers=review_headers(h, activation), json=activation
    )
    assert response.status_code == 200, response.text


def test_expired_action_receipts_collected_without_removing_analysis_requests(context):
    from datetime import timedelta

    from sqlalchemy import select
    from talent_engine.campaigns.lifecycle import now
    from talent_engine.deletions.data import collect_retention
    from talent_engine.reviews.data import application_actions

    client, engine = context
    app_id = deposit(
        client, engine, prepared(client), "Rétention des actions", [4, None, 3]
    )
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
    with engine.begin() as db:
        db.execute(
            application_actions.update()
            .where(application_actions.c.route == "corrections")
            .values(expires_at=now(db) - timedelta(days=1))
        )
    collect_retention(engine)
    with engine.connect() as db:
        routes = list(db.scalars(select(application_actions.c.route)))
    assert routes == ["analyses"]
