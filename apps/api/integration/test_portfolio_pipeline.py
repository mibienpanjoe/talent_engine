from functools import partial
from uuid import uuid4

from sqlalchemy import select
from talent_engine.analyses.processor import process
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from talent_engine.integrations.public_web import Page
from talent_engine.sources.data import sources
from test_campaigns import headers


class Portfolio:
    def get(self, url, **kwargs):
        return Page(
            url,
            200,
            {"content-type": "text/html"},
            b"<h1>Projet fictif</h1>"
            b"<p>Contribution personnelle : formulaire et verification.</p>",
        )


def test_public_url_submission_collects_versioned_private_evidence(context):
    client, engine = context
    h = headers(client)
    qid = str(uuid4())
    config = dict(
        type="training",
        title="Portfolio fictif",
        domain="Développement",
        description="Fictif",
        target_level="Débutant",
        deadline=None,
        questions=[
            dict(
                id=qid,
                type="url",
                label="Portfolio fourni",
                position=0,
                required=True,
                options=[],
                constraints={},
            )
        ],
        requirements=[
            dict(
                id=str(uuid4()),
                family="practical_work",
                expectation="Décrire sa contribution.",
                importance="desired",
                evaluation_mode="qualitative",
                assessment_mode="automatic",
                source_question_ids=[qid],
            )
        ],
    )
    campaign = client.post(
        "/api/v1/campaigns",
        headers={**h, "Idempotency-Key": uuid4().hex},
        json={"configuration": config},
    ).json()
    path = "/api/v1/campaigns/" + campaign["id"]
    snapshot = client.post(
        path + "/publications",
        headers={**h, "If-Match": '"1"', "Idempotency-Key": uuid4().hex},
        json={},
    ).json()
    token = client.get(path).json()["public_url"].split("/")[-1]
    response = client.post(
        "/api/v1/public/campaigns/" + token + "/applications",
        headers={"Idempotency-Key": uuid4().hex},
        json=dict(
            snapshot_id=snapshot["id"],
            contact=dict(name="Portfolio fictif", email="synthetic@example.com"),
            answers=[
                dict(question_id=qid, kind="url", value="https://example.com/projects/")
            ],
        ),
    )
    assert response.status_code == 201
    processor = partial(process, portfolio_web=Portfolio())
    for _ in range(2):
        assert work_once(engine, WorkerSettings(), "portfolio", processor=processor)
    appid = client.get(path + "/applications").json()["items"][0]["id"]
    detail = client.get("/api/v1/applications/" + appid).json()
    source = detail["sources"][0]
    assert source["kind"] == "portfolio" and source["state"] == "available"
    assert source["extraction_metadata"]["web"][0]["content_hash"]
    with engine.connect() as db:
        row = db.execute(select(sources)).mappings().one()
        assert row["pages"][0]["url"] == "https://example.com/projects/"
        assert "Contribution personnelle" in row["pages"][0]["text"]
