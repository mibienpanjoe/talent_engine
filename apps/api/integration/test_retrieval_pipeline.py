from copy import deepcopy
from functools import partial

from embedding_fixture import ControlledEmbeddings
from sqlalchemy import func, select
from talent_engine.analyses.processor import process
from talent_engine.analyses.queue import acquire, complete
from talent_engine.analyses.settings import WorkerSettings
from talent_engine.analyses.worker import work_once
from talent_engine.evaluations.repository import embedding_cache
from talent_engine.evaluations.retrieval import retrieve
from talent_engine.evaluations.service import context as evaluation_context
from test_evaluations import ControlledGateway
from test_worker import queued


def test_cache_requires_live_lease_and_invalidates_for_source_model_and_app(context):
    client, engine = context
    queued(client)
    embedder = ControlledEmbeddings()
    worker = partial(process, gateway=ControlledGateway(), embedder=embedder)
    for _ in range(2):
        work_once(engine, WorkerSettings(), "sources", processor=worker)
    claim = acquire(engine, WorkerSettings(), "retrieval")
    output = worker(engine, claim)
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(embedding_cache)) == 0
    assert complete(engine, WorkerSettings(), claim, output)
    with engine.connect() as db:
        app, snapshot, _, _, _, evidence, _ = evaluation_context(db, claim)
        count = db.scalar(select(func.count()).select_from(embedding_cache))
    assert count > 0
    again, pending = retrieve(
        engine,
        claim.application_id,
        snapshot["policy_snapshot"],
        snapshot["configuration"],
        evidence,
        embedder=embedder,
    )
    assert not pending and again["cache_hits"] == count and again["cache_misses"] == 0
    changed = deepcopy(evidence)
    first = next(iter(changed))
    changed[first]["text"] += " changed source"
    meta, pending = retrieve(
        engine,
        claim.application_id,
        snapshot["policy_snapshot"],
        snapshot["configuration"],
        changed,
        embedder=embedder,
    )
    assert meta["cache_misses"] == 1 and len(pending) == 1
    embedder.model = "different-family"
    meta, pending = retrieve(
        engine,
        claim.application_id,
        snapshot["policy_snapshot"],
        snapshot["configuration"],
        evidence,
        embedder=embedder,
    )
    assert meta["cache_hits"] == 0 and meta["cache_misses"] == count
    from uuid import uuid4

    meta, pending = retrieve(
        engine,
        uuid4(),
        snapshot["policy_snapshot"],
        snapshot["configuration"],
        evidence,
        embedder=ControlledEmbeddings(),
    )
    assert meta["cache_hits"] == 0


def test_invalid_retrieval_cannot_publish_cache_or_assessment(context):
    from talent_engine.evaluations.data import evaluations

    client, engine = context
    queued(client)
    worker = partial(
        process, gateway=ControlledGateway(), embedder=ControlledEmbeddings()
    )
    for _ in range(2):
        work_once(engine, WorkerSettings(), "source", processor=worker)
    claim = acquire(engine, WorkerSettings(), "invalid-retrieval")
    output = worker(engine, claim)
    output["pending_embeddings"][0]["input_hash"] = "f" * 64
    assert complete(engine, WorkerSettings(), claim, output)
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(embedding_cache)) == 0
        assert db.scalar(select(func.count()).select_from(evaluations)) == 0
