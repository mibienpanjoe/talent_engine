import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from talent_engine.applications.data import analysis_runs, applications, jobs
from talent_engine.campaigns.data import campaigns, snapshots
from talent_engine.campaigns.lifecycle import now
from talent_engine.integrations.llm import Gateway
from talent_engine.sources.data import excerpts, run_evidence, run_sources, sources

from .assessment import (
    PROMPT_VERSION,
    build_messages,
    parse_response,
    validate_assessments,
)
from .engine import calculate, conditions
from .repository import evaluations
from .retrieval import persist, persist_and_verify, retrieve
from .schemas import Evaluation, Provenance, Retrieval


def evidence_for_run(db, claim):
    rows = (
        db.execute(
            select(excerpts, sources.c.question_ids, sources.c.extractor_version)
            .join(sources, sources.c.id == excerpts.c.source_version_id)
            .join(run_evidence, run_evidence.c.excerpt_id == excerpts.c.id)
            .join(
                run_sources,
                (run_sources.c.source_version_id == sources.c.id)
                & (run_sources.c.run_id == run_evidence.c.run_id),
            )
            .where(
                (run_evidence.c.run_id == claim.run_id)
                & (run_evidence.c.application_id == claim.application_id)
            )
            .order_by(
                sources.c.source_key,
                excerpts.c.locator["page"].as_integer(),
                excerpts.c.locator["start"].as_integer(),
                excerpts.c.id,
            )
        )
        .mappings()
        .all()
    )
    return {
        str(r["id"]): {
            **r,
            "id": str(r["id"]),
            "source_version_id": str(r["source_version_id"]),
        }
        for r in rows
    }


def context(db, claim, *, selected_ids=None):
    app = (
        db.execute(
            select(applications).where(applications.c.id == claim.application_id)
        )
        .mappings()
        .one()
    )
    snapshot = (
        db.execute(select(snapshots).where(snapshots.c.id == app["snapshot_id"]))
        .mappings()
        .one()
    )
    evidence = evidence_for_run(db, claim)
    messages, allowed, limits = build_messages(
        snapshot["policy_snapshot"],
        snapshot["configuration"],
        evidence,
        selected_ids=selected_ids,
    )
    prompt_hash = hashlib.sha256(
        json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    return app, snapshot, messages, allowed, limits, evidence, prompt_hash


def evaluate(engine, claim, *, gateway=None, embedder=None):
    with engine.connect() as db:
        app, snapshot, messages, allowed, limits, evidence, prompt_hash = context(
            db, claim
        )
    policy = snapshot["policy_snapshot"]
    automatic = [
        c
        for c in policy["criteria"]
        if c["weight"] is not None and c["assessment_mode"] == "automatic"
    ]
    started = datetime.now(UTC)
    retrieval = None
    pending = []
    reply = None
    if automatic and allowed:
        retrieval, pending = retrieve(
            engine,
            claim.application_id,
            policy,
            snapshot["configuration"],
            evidence,
            embedder=embedder,
        )
        with engine.connect() as db:
            _, _, messages, allowed, limits, _, prompt_hash = context(
                db, claim, selected_ids=retrieval["selected_ids"]
            )
        reply = (gateway or Gateway()).chat(
            messages, response_format={"type": "json_object"}
        )
        response = parse_response(reply.content)
    else:
        response = dict(
            assessments=[
                dict(
                    criterion_id=c["criterion_id"],
                    status="source_unavailable"
                    if not allowed
                    else "insufficient_information",
                    level=None,
                    evidence_ids=[],
                    rationale="Aucun extrait autorisé disponible.",
                    uncertainties=["Vérifier les sources et leurs limites."],
                    policy_version=policy["version"],
                    rubric_version=c["rubric_version"],
                )
                for c in automatic
            ]
        )
    rows = validate_assessments(response, policy, allowed)
    provenance = Provenance(
        mode="live",
        requested_model=reply.requested_model if reply else None,
        provider=reply.provider if reply else None,
        effective_model=reply.effective_model if reply else None,
        response_model=reply.response_model if reply else None,
        prompt_version=PROMPT_VERSION,
        adapter_version="freellmapi-chat-v1",
        prompt_hash=prompt_hash,
        evidence_ids=list(allowed),
        **limits,
        extractor_versions=sorted({e["extractor_version"] for e in evidence.values()}),
        duration_seconds=reply.duration_seconds if reply else 0,
        started_at=started,
        finished_at=datetime.now(UTC),
        retrieval=retrieval,
    )
    return dict(
        version="evaluation-v2",
        assessments=rows,
        provenance=provenance.model_dump(mode="json"),
        pending_embeddings=pending,
    )


def finalize(db, claim, output):
    """Caller has campaign -> application -> job locks and has checked fencing."""
    app, snapshot, _, allowed, limits, evidence, prompt_hash = context(db, claim)
    metadata = output["provenance"].get("retrieval")
    if output.get("version") == "evaluation-v2" and allowed and metadata is None:
        raise ValueError("Retrieval provenance required")
    if metadata:
        metadata = Retrieval.model_validate(metadata).model_dump(mode="json")
        selected = persist_and_verify(
            db,
            claim.application_id,
            snapshot["policy_snapshot"],
            snapshot["configuration"],
            evidence,
            metadata,
            output.get("pending_embeddings", []),
        )
        app, snapshot, _, allowed, limits, evidence, prompt_hash = context(
            db, claim, selected_ids=selected
        )
    policy = snapshot["policy_snapshot"]
    automatic_ids = {
        c["criterion_id"]
        for c in policy["criteria"]
        if c["weight"] is not None and c["assessment_mode"] == "automatic"
    }
    rows = validate_assessments(
        {
            "assessments": [
                a for a in output["assessments"] if a["criterion_id"] in automatic_ids
            ]
        },
        policy,
        allowed,
    )
    provenance = Provenance.model_validate(output["provenance"])
    if (
        provenance.prompt_hash != prompt_hash
        or set(str(x) for x in provenance.evidence_ids) != set(allowed)
        or set(str(x) for x in provenance.blocked_evidence_ids)
        != set(limits["blocked_evidence_ids"])
        or set(str(x) for x in provenance.omitted_evidence_ids)
        != set(limits["omitted_evidence_ids"])
    ):
        raise ValueError("Analysis evidence changed")
    calculation = calculate(policy, rows)
    availability = conditions(snapshot["configuration"], app["answers"])
    for condition in availability["results"]:
        condition["evidence_ids"] = [
            k
            for k, e in evidence.items()
            if e["locator"].get("question_id") == condition["question_id"]
        ]
    result = Evaluation(
        id=uuid4(),
        application_id=app["id"],
        run_id=claim.run_id,
        snapshot_id=app["snapshot_id"],
        policy_version=policy["version"],
        assessments=rows,
        conditions=availability["results"],
        eligibility=availability["eligibility"],
        calculation=calculation,
        provenance=provenance,
        created_at=now(db),
    )
    values = result.model_dump(mode="json")
    score = calculation["score_exact"]
    if metadata:
        persist(
            db, claim.application_id, metadata, output.get("pending_embeddings", [])
        )
    db.execute(
        evaluations.insert().values(
            **values,
            score_numerator=score["numerator"] if score else None,
            score_denominator=score["denominator"] if score else None,
        )
    )
    state = "completed" if calculation["complete"] else "completed_partial"
    updates = dict(
        processing_state=state,
        processing_revision=applications.c.processing_revision + 1,
    )
    if app["effective_evaluation_id"] is None:
        updates.update(
            effective_evaluation_id=result.id,
            review_revision=applications.c.review_revision + 1,
        )
        db.execute(
            campaigns.update()
            .where(campaigns.c.id == app["campaign_id"])
            .values(list_revision=campaigns.c.list_revision + 1)
        )
    db.execute(
        applications.update().where(applications.c.id == app["id"]).values(**updates)
    )
    db.execute(
        analysis_runs.update()
        .where(analysis_runs.c.id == claim.run_id)
        .values(state=state, error_code=None, finished_at=now(db))
    )
    db.execute(
        jobs.update()
        .where(jobs.c.id == claim.job_id)
        .values(
            state="succeeded",
            lease_token=None,
            lease_until=None,
            error_code=None,
            next_attempt_at=None,
        )
    )
    return dict(version="evaluation-v1", evaluation_id=str(result.id))
