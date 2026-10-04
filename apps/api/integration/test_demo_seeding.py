from pathlib import Path

from sqlalchemy import func, select
from talent_engine.applications.data import applications, jobs
from talent_engine.campaigns.data import campaigns
from talent_engine.config import Settings
from talent_engine.evaluations.data import evaluations
from test_campaigns import headers

ROOT = Path(__file__).resolve().parents[3]


def demo_settings(engine, tmp_path):
    return Settings(
        database_url=engine.url.render_as_string(hide_password=False),
        upload_directory=tmp_path / "uploads",
        public_origin="http://localhost:3003",
        local_development=True,
        csrf_secret="test-only-csrf-" + "x" * 32,
    )


def test_preloaded_demos_are_idempotent_sourced_and_preserve_human_changes(
    context, tmp_path
):
    from talent_engine.demo.seeding import seed

    client, engine = context
    settings = demo_settings(engine, tmp_path)
    first = seed(
        engine,
        settings,
        login="reviewer",
        mode="preloaded",
        batch="default",
        fixture_root=ROOT / "fixtures",
    )
    again = seed(
        engine,
        settings,
        login="reviewer",
        mode="preloaded",
        batch="default",
        fixture_root=ROOT / "fixtures",
    )
    assert first == again
    from pydantic import SecretStr

    rotated = settings.model_copy(
        update={"csrf_secret": SecretStr("rotated-demo-test-" + "y" * 32)}
    )
    assert first == seed(
        engine,
        rotated,
        login="reviewer",
        mode="preloaded",
        batch="default",
        fixture_root=ROOT / "fixtures",
    )
    assert len(first) == 2
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(campaigns)) == 2
        assert db.scalar(select(func.count()).select_from(applications)) == 7
        assert db.scalar(select(func.count()).select_from(evaluations)) == 7
        assert (
            db.scalar(
                select(func.count()).select_from(jobs).where(jobs.c.state == "queued")
            )
            == 0
        )
    expected = {
        "Amina": "81.250000",
        "Boris": "65.000000",
        "Chloé": None,
        "David": "93.750000",
        "Fatou": "77.500000",
        "Karim": "76.250000",
        "Lina": None,
    }
    h = headers(client)
    for group in first:
        listing = client.get(
            "/api/v1/campaigns/" + group["campaign_id"] + "/applications"
        ).json()
        assert len(listing["items"]) == len(group["application_ids"])
        for ident in group["application_ids"]:
            detail = client.get("/api/v1/applications/" + ident).json()
            a = detail["application"]
            name = a["contact"]["name"].split(" · ")[0]
            assert a["calculation"]["score"] == expected[name]
            assert detail["effective_evaluation"]["provenance"]["mode"] == "preloaded"
            assert detail["effective_evaluation"]["provenance"]["provider"] is None
            for assessment in detail["effective_evaluation"]["assessments"]:
                for proof in assessment["evidence_ids"]:
                    assert client.get("/api/v1/evidence/" + proof).status_code == 200
    ident = first[0]["application_ids"][0]
    path = "/api/v1/applications/" + ident
    a = client.get(path).json()["application"]
    response = client.patch(
        path + "/decision",
        headers={**h, "If-Match": '"' + str(a["review_revision"]) + '"'},
        json=dict(
            review_revision=a["review_revision"],
            effective_evaluation_id=a["effective_evaluation_id"],
            decision="shortlisted",
            reason="Décision de recette.",
        ),
    )
    assert response.status_code == 200
    seed(
        engine,
        settings,
        login="reviewer",
        mode="preloaded",
        batch="default",
        fixture_root=ROOT / "fixtures",
    )
    assert client.get(path).json()["application"]["decision"] == "shortlisted"


def test_live_demos_create_fresh_queued_dossiers_without_fixture_scores(
    context, tmp_path
):
    from talent_engine.demo.seeding import seed

    client, engine = context
    settings = demo_settings(engine, tmp_path)
    loaded = seed(
        engine,
        settings,
        login="reviewer",
        mode="preloaded",
        batch="default",
        fixture_root=ROOT / "fixtures",
    )
    live = seed(
        engine,
        settings,
        login="reviewer",
        mode="live",
        batch="new-case",
        fixture_root=ROOT / "fixtures",
    )
    assert {g["campaign_id"] for g in loaded}.isdisjoint(g["campaign_id"] for g in live)
    assert live == seed(
        engine,
        settings,
        login="reviewer",
        mode="live",
        batch="new-case",
        fixture_root=ROOT / "fixtures",
    )
    headers(client)
    for group in live:
        assert len(group["application_ids"]) == 1
        detail = client.get(
            "/api/v1/applications/" + group["application_ids"][0]
        ).json()
        assert detail["application"]["processing_state"] == "queued"
        assert detail["effective_evaluation"] is None
        assert detail["application"]["calculation"] is None
        assert detail["uploads"]
        for upload in detail["uploads"]:
            assert (
                client.get("/api/v1/uploads/" + upload["id"] + "/download").status_code
                == 200
            )


def test_reseeding_does_not_resurrect_deleted_fixture_dossier(context, tmp_path):
    from talent_engine.deletions.data import purge_once
    from talent_engine.demo.seeding import seed

    client, engine = context
    settings = demo_settings(engine, tmp_path)
    args = dict(
        login="reviewer",
        mode="preloaded",
        batch="default",
        fixture_root=ROOT / "fixtures",
    )
    groups = seed(engine, settings, **args)
    ident = groups[0]["application_ids"][0]
    h = headers(client)
    detail = client.get("/api/v1/applications/" + ident).json()["application"]
    response = client.delete(
        "/api/v1/applications/" + ident,
        headers={**h, "If-Match": '"' + str(detail["review_revision"]) + '"'},
    )
    assert response.status_code == 202
    assert purge_once(engine, settings)
    groups = seed(engine, settings, **args)
    assert ident not in groups[0]["application_ids"]
    assert client.get("/api/v1/applications/" + ident).status_code == 404
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(applications)) == 6


def test_concurrent_preloaded_seed_creates_one_set(context, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from talent_engine.demo.seeding import seed

    _, engine = context
    settings = demo_settings(engine, tmp_path)

    def run():
        return seed(
            engine,
            settings,
            login="reviewer",
            mode="preloaded",
            batch="concurrent",
            fixture_root=ROOT / "fixtures",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: run(), range(2)))
    assert first == second
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(applications)) == 7
