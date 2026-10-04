from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from test_submissions import prepare


def queued(client):
    _, campaign, token, body = prepare(client)
    assert (
        client.post(
            "/api/v1/public/campaigns/" + token + "/applications",
            headers={"Idempotency-Key": uuid4().hex},
            json=body,
        ).status_code
        == 201
    )
    return client.get("/api/v1/campaigns/" + campaign["id"] + "/applications").json()[
        "items"
    ][0]["id"]


def test_competing_workers_fencing_and_checkpoint_reuse(context):
    from talent_engine.analyses.queue import acquire, complete, heartbeat
    from talent_engine.analyses.settings import WorkerSettings
    from talent_engine.applications.repository import jobs
    from talent_engine.campaigns.lifecycle import now

    client, engine = context
    queued(client)
    settings = WorkerSettings()
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(
            pool.map(lambda name: acquire(engine, settings, name), ["a", "b"])
        )
    first = next(c for c in claims if c)
    assert sum(c is not None for c in claims) == 1
    assert heartbeat(engine, settings, first)
    with engine.begin() as db:
        db.execute(jobs.update().values(lease_until=now(db) - timedelta(seconds=1)))
    second = acquire(engine, settings, "replacement")
    assert second.generation == first.generation + 1 and second.attempt == 2
    assert not heartbeat(engine, settings, first)
    assert not complete(engine, settings, first, {"obsolete": True})
    assert complete(engine, settings, second, {"valid": True})
    third = acquire(engine, settings, "next")
    assert third.step == "source_manifest" and third.attempt == 1


def test_three_crashed_acquisitions_exhaust_budget_without_result(context):
    from talent_engine.analyses.queue import acquire
    from talent_engine.analyses.settings import WorkerSettings
    from talent_engine.applications.repository import applications, jobs
    from talent_engine.campaigns.lifecycle import now

    client, engine = context
    queued(client)
    settings = WorkerSettings()
    for attempt in range(1, 4):
        claim = acquire(engine, settings, "crashes")
        assert claim.attempt == attempt
        with engine.begin() as db:
            db.execute(jobs.update().values(lease_until=now(db) - timedelta(seconds=1)))
    assert acquire(engine, settings, "after-budget") is None
    with engine.connect() as db:
        assert db.scalar(select(jobs.c.state)) == "failed"
        app = db.execute(select(applications)).mappings().one()
        assert (
            app["processing_state"] == "failed"
            and app["effective_evaluation_id"] is None
        )


def test_worker_checkpoints_real_answers_and_reports_missing_evaluation(context):
    from talent_engine.analyses.repository import steps
    from talent_engine.analyses.settings import WorkerSettings
    from talent_engine.analyses.worker import work_once
    from talent_engine.applications.repository import applications, jobs

    client, engine = context
    application_id = queued(client)
    for _ in range(3):
        assert work_once(engine, WorkerSettings(), "real-worker")
    assert not work_once(engine, WorkerSettings(), "finished")
    with engine.connect() as db:
        rows = db.execute(select(steps).order_by(steps.c.position)).mappings().all()
        assert [r["state"] for r in rows] == ["succeeded", "succeeded", "failed"]
        assert (
            rows[0]["output"]["answers"][0]["value"]
            == "Projet fictif et contribution personnelle."
        )
        assert db.scalar(select(jobs.c.error_code)) == "evaluation_unavailable"
        assert db.scalar(select(applications.c.effective_evaluation_id)) is None
    detail = client.get("/api/v1/applications/" + application_id).json()
    assert detail["application"]["processing_state"] == "failed"
    assert detail["analyses"][0]["error_code"] == "evaluation_unavailable"
    assert len(detail["analyses"][0]["steps"]) == 3
    assert all("output" not in step for step in detail["analyses"][0]["steps"])


def test_waiting_retry_budget_and_generation_deletion_fence(context):
    from talent_engine.analyses.queue import acquire, fail
    from talent_engine.analyses.settings import WorkerSettings
    from talent_engine.applications.repository import jobs
    from talent_engine.campaigns.lifecycle import now

    client, engine = context
    queued(client)
    settings = WorkerSettings()
    for attempt in range(1, 4):
        claim = acquire(engine, settings, "retry")
        assert claim.attempt == attempt
        assert fail(
            engine,
            settings,
            claim,
            "provider_rate_limited",
            retryable=True,
            retry_after=10,
        )
        if attempt < 3:
            assert acquire(engine, settings, "too-early") is None
            with engine.begin() as db:
                assert db.scalar(select(jobs.c.state)) == "waiting"
                db.execute(
                    jobs.update().values(next_attempt_at=now(db) - timedelta(seconds=1))
                )
    with engine.connect() as db:
        assert db.scalar(select(jobs.c.state)) == "failed"
    assert acquire(engine, settings, "exhausted") is None


def test_deleted_or_changed_generation_discards_late_outputs(context):
    from talent_engine.analyses.queue import acquire, complete, heartbeat
    from talent_engine.analyses.settings import WorkerSettings
    from talent_engine.applications.repository import applications
    from talent_engine.campaigns.lifecycle import now

    client, engine = context
    queued(client)
    settings = WorkerSettings()
    claim = acquire(engine, settings, "in-flight")
    with engine.begin() as db:
        db.execute(
            applications.update().values(deleted_at=now(db), processing_generation=2)
        )
    assert not heartbeat(engine, settings, claim)
    assert not complete(engine, settings, claim, {"late": True})
    assert acquire(engine, settings, "deleted") is None


def test_killed_process_resumes_checkpoint_with_two_real_workers(context, tmp_path):
    import os
    import select as selector
    import subprocess
    import sys
    import time

    from sqlalchemy import text
    from talent_engine.analyses.repository import steps
    from talent_engine.applications.repository import jobs

    client, engine = context
    queued(client)
    with engine.connect() as db:
        schema = db.scalar(text("SELECT current_schema()"))
    program = tmp_path / "worker_crash_probe.py"
    program.write_text("""
import os, sys, time
from sqlalchemy import create_engine
from talent_engine.main import create_app
from talent_engine.config import Settings
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.queue import acquire, complete
from talent_engine.analyses.processor import process
from talent_engine.analyses.worker import work_once
engine = create_engine(os.environ['PROBE_DATABASE_URL'],
    connect_args={'options': '-c search_path=' + os.environ['PROBE_SCHEMA']})
settings = Settings(database_url=os.environ['PROBE_DATABASE_URL'],
    public_origin='http://localhost:3003', local_development=True,
    csrf_secret='test-only-csrf-' + 'x' * 32)
create_app(settings, engine=engine)
worker = WorkerSettings(lease_seconds=1, heartbeat_seconds=0.1)
if sys.argv[1] == 'crash':
    first = acquire(engine, worker, 'process-to-kill')
    complete(engine, worker, first, process(engine, first))
    second = acquire(engine, worker, 'process-to-kill')
    assert second.step == 'source_manifest'
    print('checkpoint-durable-lease-acquired', flush=True)
    sys.stdin.readline()
else:
    for _ in range(6):
        work_once(engine, worker, 'replacement-' + sys.argv[1])
        time.sleep(0.05)
engine.dispose()
""")
    environment = {
        **os.environ,
        "PROBE_DATABASE_URL": engine.url.render_as_string(hide_password=False),
        "PROBE_SCHEMA": schema,
    }
    victim = subprocess.Popen(
        [sys.executable, str(program), "crash"],
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready, _, _ = selector.select([victim.stdout], [], [], 10)
        assert (
            ready
            and victim.stdout.readline().strip() == "checkpoint-durable-lease-acquired"
        )
    finally:
        victim.kill()
        victim.wait(timeout=5)
    time.sleep(1.1)
    replacements = [
        subprocess.Popen(
            [sys.executable, str(program), str(i)],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i in range(2)
    ]
    try:
        for worker in replacements:
            stdout, stderr = worker.communicate(timeout=15)
            assert worker.returncode == 0, stderr
    finally:
        for worker in replacements:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=5)
    with engine.connect() as db:
        rows = db.execute(select(steps).order_by(steps.c.position)).mappings().all()
        assert [r["attempts"] for r in rows] == [1, 2, 1]
        assert [r["state"] for r in rows] == ["succeeded", "succeeded", "failed"]
        assert rows[0]["output"]["version"] == "answers-v1"
        assert db.scalar(select(jobs.c.error_code)) == "evaluation_unavailable"


def test_heartbeat_keeps_long_step_owned_and_timeout_discards_late_output(context):
    import time

    from talent_engine.analyses.processor import process
    from talent_engine.analyses.repository import steps
    from talent_engine.analyses.settings import WorkerSettings
    from talent_engine.analyses.worker import work_once

    client, engine = context
    queued(client)

    def slower(engine, claim):
        time.sleep(1.2)
        return process(engine, claim)

    settings = WorkerSettings(
        lease_seconds=1, heartbeat_seconds=0.1, step_timeout_seconds=2
    )
    assert work_once(engine, settings, "renewing", processor=slower)
    with engine.connect() as db:
        assert (
            db.scalar(select(steps.c.state).where(steps.c.name == "extract_answers"))
            == "succeeded"
        )

    def timeout(engine, claim):
        time.sleep(0.3)
        return {"late": True}

    assert work_once(
        engine,
        settings.model_copy(update={"step_timeout_seconds": 0.1}),
        "timeout",
        processor=timeout,
    )
    time.sleep(0.3)
    with engine.connect() as db:
        row = (
            db.execute(select(steps).where(steps.c.name == "source_manifest"))
            .mappings()
            .one()
        )
        assert row["state"] == "waiting" and row["output"] is None
        assert row["error_code"] == "step_timeout"
