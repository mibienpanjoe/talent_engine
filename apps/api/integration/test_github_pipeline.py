from functools import partial
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from talent_engine.analyses.processor import process
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from talent_engine.sources.data import sources
from test_campaigns import headers

spec = spec_from_file_location(
    "github_fixture", Path(__file__).parents[1] / "tests" / "test_github.py"
)
module = module_from_spec(spec)
spec.loader.exec_module(module)
GitHub = module.GitHub


def test_github_submission_persists_commit_and_proof(context):
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
                dict(
                    question_id=qid, kind="url", value="https://github.com/demo/project"
                )
            ],
        ),
    )
    assert response.status_code == 201
    processor = partial(process, github_web=GitHub())
    for _ in range(2):
        assert work_once(engine, WorkerSettings(), "portfolio", processor=processor)
    appid = client.get(path + "/applications").json()["items"][0]["id"]
    detail = client.get("/api/v1/applications/" + appid).json()
    source = detail["sources"][0]
    assert source["kind"] == "github" and source["state"] == "available"
    assert source["extraction_metadata"]["github"]["commit"] == "a" * 40
    with engine.connect() as db:
        row = db.execute(select(sources)).mappings().one()
        assert row["pages"][0]["commit"] == "a" * 40
        assert "equipe collective" in row["pages"][0]["text"]
