import json
from functools import partial
from uuid import uuid4

from embedding_fixture import ControlledEmbeddings
from sqlalchemy import select
from talent_engine.analyses.processor import process
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from talent_engine.applications.data import applications
from talent_engine.integrations.llm import ChatResult
from test_campaigns import headers


def prepared(client, *, question_types=None):
    h = headers(client)
    qids = [str(uuid4()) for _ in range(4)]
    families = ["programming_foundations", "practical_work", "learning_approach"]
    requirements = [
        dict(
            id=str(uuid4()),
            family=f,
            expectation=f,
            importance="desired",
            evaluation_mode="qualitative",
            assessment_mode="automatic",
            source_question_ids=[qids[i]],
        )
        for i, f in enumerate(families)
    ]
    requirements.append(
        dict(
            id=str(uuid4()),
            family="available_by_date",
            expectation="Disponible au plus tard le 5 octobre",
            importance="required",
            evaluation_mode="deterministic",
            source_question_ids=[qids[3]],
            condition_rule=dict(
                kind="available_by_date", question_id=qids[3], date="2026-10-05"
            ),
        )
    )
    config = dict(
        type="training",
        title="Revue fictive",
        domain="Développement",
        description="Fictif",
        target_level="Débutant",
        deadline=None,
        questions=[
            dict(
                id=qid,
                type=question_types[i]
                if question_types
                else "long_text"
                if i < 3
                else "date",
                label=f"Question {i}",
                position=i,
                required=False,
                options=[],
                constraints={},
            )
            for i, qid in enumerate(qids)
        ],
        requirements=requirements,
    )
    campaign = client.post(
        "/api/v1/campaigns",
        headers={**h, "Idempotency-Key": uuid4().hex},
        json={"configuration": config},
    ).json()
    path = "/api/v1/campaigns/" + campaign["id"]
    result = client.post(
        path + "/publications",
        headers={**h, "If-Match": '"1"', "Idempotency-Key": uuid4().hex},
        json={},
    )
    assert result.status_code == 201, result.text
    snapshot = result.json()
    token = client.get(path).json()["public_url"].split("/")[-1]
    return campaign, snapshot, token, qids


class OracleGateway:
    def __init__(self, levels):
        self.levels = levels

    def chat(self, messages, **kwargs):
        payload = json.loads(messages[1]["content"])
        assessments = [
            dict(
                criterion_id=c["criterion_id"],
                status="evaluated" if level is not None else "insufficient_information",
                level=level,
                evidence_ids=c["evidence_ids"][:1] if level is not None else [],
                rationale="Oracle de revue fictif, sortie contrôlée.",
                uncertainties=[],
                policy_version=payload["policy_version"],
                rubric_version=c["rubric_version"],
            )
            for c, level in zip(payload["criteria"], self.levels, strict=True)
        ]
        return ChatResult(
            json.dumps({"assessments": assessments}),
            "fixture",
            "fixture",
            "fixture",
            "fixture",
            0,
        )


def deposit(
    client,
    engine,
    prepared_data,
    name,
    levels,
    *,
    unmet=False,
    portfolio_web=None,
    source_values=None,
):
    _, snapshot, token, qids = prepared_data
    answers = [
        dict(
            question_id=qid,
            kind=snapshot["configuration"]["questions"][i]["type"],
            value=source_values[i]
            if source_values
            else "Preuve fictive pour " + name
            if i < 3
            else "2026-10-06"
            if unmet
            else "2026-10-05",
        )
        for i, qid in enumerate(qids)
    ]
    assert (
        client.post(
            "/api/v1/public/campaigns/" + token + "/applications",
            headers={"Idempotency-Key": uuid4().hex},
            json=dict(
                snapshot_id=snapshot["id"],
                contact=dict(name=name, email="synthetic@example.com"),
                answers=answers,
            ),
        ).status_code
        == 201
    )
    for _ in range(3):
        assert work_once(
            engine,
            WorkerSettings(),
            "review-oracle",
            processor=partial(
                process,
                gateway=OracleGateway(levels),
                embedder=ControlledEmbeddings(),
                portfolio_web=portfolio_web,
            ),
        )
    with engine.connect() as db:
        return str(
            db.scalar(
                select(applications.c.id).where(
                    applications.c.contact["name"].as_string() == name
                )
            )
        )


def test_review_views_overlap_exact_ties_pagination_and_decision_filter(context):
    client, engine = context
    prepared_data = prepared(client)
    ids = {}
    for name, levels, unmet in [
        ("Amina", [3, 3, 4], False),
        ("Boris", [2, 3, 3], False),
        ("Chloé", [4, None, 3], False),
        ("David", [4, 4, 3], True),
        ("Partiel incompatible", [4, None, 3], True),
        ("Ex aequo", [3, 3, 4], False),
    ]:
        ids[name] = deposit(client, engine, prepared_data, name, levels, unmet=unmet)
    path = "/api/v1/campaigns/" + prepared_data[0]["id"] + "/applications"
    page = client.get(path).json()
    assert page["counts"] == {
        "all": 6,
        "ready": 3,
        "needs_review": 2,
        "condition_unmet": 2,
    }
    assert [x["contact"]["name"] for x in page["items"]] == list(reversed(ids))
    assert all(x["rank"] is None for x in page["items"])
    ready = client.get(path, params={"view": "ready"}).json()["items"]
    assert [x["rank"] for x in ready] == [1, 1, 3]
    assert [x["id"] for x in ready] == [ids["Amina"], ids["Ex aequo"], ids["Boris"]]
    first = client.get(path, params={"view": "ready", "limit": 1}).json()
    second = client.get(
        path, params={"view": "ready", "limit": 1, "cursor": first["next_cursor"]}
    ).json()
    assert second["items"][0]["id"] == ids["Ex aequo"]
    assert (
        client.get(
            path, params={"view": "all", "cursor": first["next_cursor"]}
        ).status_code
        == 400
    )
    with engine.begin() as db:
        db.execute(
            applications.update()
            .where(applications.c.id == ids["Boris"])
            .values(decision="shortlisted")
        )
    filtered = client.get(
        path, params={"view": "ready", "decision": "shortlisted"}
    ).json()["items"]
    assert len(filtered) == 1 and filtered[0]["rank"] == 3
    detail = client.get("/api/v1/applications/" + ids["Chloé"]).json()
    assert detail["application"]["calculation"]["coverage"] == "65.000000"
    assert detail["application"]["calculation"]["score"] is None
    assert detail["effective_evaluation"]["calculation"]["lower_bound"] == "58.750000"
    assert detail["sources"] and detail["evidence"]


def test_new_technical_failure_preserves_ready_result_and_invalidates_cursor(context):
    client, engine = context
    data = prepared(client)
    first = deposit(client, engine, data, "Premier", [3, 3, 4])
    deposit(client, engine, data, "Deuxième", [2, 3, 3])
    path = "/api/v1/campaigns/" + data[0]["id"] + "/applications"
    cursor = client.get(path, params={"limit": 1}).json()["next_cursor"]
    with engine.begin() as db:
        db.execute(
            applications.update()
            .where(applications.c.id == first)
            .values(
                processing_state="failed",
                processing_revision=applications.c.processing_revision + 1,
            )
        )
    assert client.get(path, params={"limit": 1, "cursor": cursor}).status_code == 409
    ready = client.get(
        path, params={"view": "ready", "processing_state": "failed"}
    ).json()["items"]
    assert len(ready) == 1 and ready[0]["id"] == first
    assert ready[0]["calculation"]["score"] == "81.250000" and ready[0]["rank"] == 1
