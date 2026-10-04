import json
from dataclasses import replace
from functools import partial
from uuid import uuid4

from sqlalchemy import func, select
from talent_engine.analyses.processor import process
from talent_engine.analyses.queue import acquire, complete
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from talent_engine.applications.data import applications
from talent_engine.evaluations.data import evaluations
from talent_engine.integrations.llm import ChatResult
from test_sources import receive_pdf, text_pdf


class ControlledGateway:
    """Test-only model boundary; real source extraction/calculation/persistence."""

    def __init__(self, invalid=False):
        self.invalid = invalid

    def chat(self, messages, **kwargs):
        request = json.loads(messages[1]["content"])
        rows = [
            dict(
                criterion_id=c["criterion_id"],
                status="evaluated" if c["evidence_ids"] else "source_unavailable",
                level=3 if c["evidence_ids"] else None,
                evidence_ids=c["evidence_ids"][:1],
                rationale="Réponse contrôlée de test.",
                uncertainties=[],
                policy_version=request["policy_version"],
                rubric_version=c["rubric_version"],
            )
            for c in request["criteria"]
        ]
        if self.invalid:
            rows[0]["evidence_ids"] = [str(uuid4())]
        return ChatResult(
            json.dumps(dict(assessments=rows)),
            "test-model",
            "test-provider",
            "test-model",
            "test-model",
            0.01,
        )


def test_pdf_to_immutable_effective_calculation_and_private_api(context, tmp_path):
    client, engine = context
    app_id = receive_pdf(client, text_pdf())
    worker = partial(
        process, upload_directory=tmp_path / "uploads", gateway=ControlledGateway()
    )
    for _ in range(3):
        assert work_once(engine, WorkerSettings(), "evaluation-test", processor=worker)
    assert not work_once(engine, WorkerSettings(), "finished", processor=worker)
    with engine.connect() as db:
        base = db.execute(select(evaluations)).mappings().one()
        app = db.execute(select(applications)).mappings().one()
        assert (
            base["calculation"]["score"] is None
        )  # PDF not linked to existing qualitative question.
        assert base["calculation"]["coverage"] == "0.000000"
        assert app["effective_evaluation_id"] == base["id"]
        assert app["processing_state"] == "completed_partial"
        assert len(base["provenance"]["evidence_ids"]) == 0
    detail = client.get("/api/v1/applications/" + app_id).json()
    assert detail["effective_evaluation"]["id"] == str(base["id"])
    assert detail["effective_evaluation"]["calculation"]["score"] is None
    assert detail["application"]["views"] == ["all", "needs_review"]
    assert detail["analyses"][0]["state"] == "completed_partial"


def test_real_answers_model_result_exact_score_and_invalid_citations(context):
    from test_worker import queued

    client, engine = context
    app_id = queued(client)
    worker = partial(process, gateway=ControlledGateway())
    for _ in range(3):
        work_once(engine, WorkerSettings(), "controlled-model", processor=worker)
    detail = client.get("/api/v1/applications/" + app_id).json()
    assert detail["effective_evaluation"]["calculation"]["score"] == "75.000000"
    assert detail["effective_evaluation"]["provenance"]["provider"] == "test-provider"
    second = queued(client)
    invalid = partial(process, gateway=ControlledGateway(invalid=True))
    for _ in range(3):
        work_once(engine, WorkerSettings(), "invalid-model", processor=invalid)
    detail = client.get("/api/v1/applications/" + second).json()
    assert detail["application"]["processing_state"] == "failed"
    assert detail["effective_evaluation"] is None
    assert detail["analyses"][0]["error_code"] == "assessment_invalid"
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(evaluations)) == 1


def test_lost_lease_cannot_publish_evaluation(context):
    from test_worker import queued

    client, engine = context
    queued(client)
    worker = partial(process, gateway=ControlledGateway())
    for _ in range(2):
        work_once(engine, WorkerSettings(), "sources", processor=worker)
    claim = acquire(engine, WorkerSettings(), "evaluating")
    output = worker(engine, claim)
    assert not complete(engine, WorkerSettings(), replace(claim, token=uuid4()), output)
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(evaluations)) == 0
    assert complete(engine, WorkerSettings(), claim, output)
    assert not complete(engine, WorkerSettings(), claim, output)
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(evaluations)) == 1


def test_evidence_owner_guard_and_effective_pointer_scope(context):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from talent_engine.access import hasher, reviewers
    from test_worker import queued

    client, engine = context
    app_id = queued(client)
    worker = partial(process, gateway=ControlledGateway())
    for _ in range(3):
        work_once(engine, WorkerSettings(), "owner-test", processor=worker)
    detail = client.get("/api/v1/applications/" + app_id).json()
    evidence_id = detail["effective_evaluation"]["assessments"][0]["evidence_ids"][0]
    response = client.get("/api/v1/evidence/" + evidence_id)
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    assert response.json()["text"] == "Projet fictif et contribution personnelle."
    second = queued(client)
    with pytest.raises(IntegrityError), engine.begin() as db:
        db.execute(
            applications.update()
            .where(applications.c.id == second)
            .values(effective_evaluation_id=detail["effective_evaluation"]["id"])
        )
    client.cookies.clear()
    assert client.get("/api/v1/evidence/" + evidence_id).status_code == 401
    with engine.begin() as db:
        db.execute(
            reviewers.insert().values(
                id=uuid4(),
                login="other",
                password_hash=hasher.hash("test-only-password"),
            )
        )
    result = client.post(
        "/api/v1/access/session",
        headers={"Origin": "http://localhost:3003"},
        json={"login": "other", "password": "test-only-password"},
    )
    assert result.status_code == 200
    assert client.get("/api/v1/evidence/" + evidence_id).status_code == 404
    assert client.get("/api/v1/applications/" + app_id).status_code == 404
