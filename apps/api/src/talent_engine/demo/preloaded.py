import json
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from talent_engine.analyses.data import steps
from talent_engine.analyses.queue import PIPELINE
from talent_engine.applications.data import analysis_runs, applications, jobs
from talent_engine.campaigns.lifecycle import now
from talent_engine.evaluations.assessment import build_messages, validate_assessments
from talent_engine.evaluations.data import evaluations
from talent_engine.evaluations.engine import calculate, conditions
from talent_engine.evaluations.schemas import Evaluation, Provenance
from talent_engine.sources.data import persist
from talent_engine.sources.extraction import collect_sources, digest


def initialize(db, app, snapshot, candidate, version, settings):
    run = (
        db.execute(
            select(analysis_runs).where(analysis_runs.c.application_id == app["id"])
        )
        .mappings()
        .one()
    )
    records = collect_sources(
        str(app["id"]), app["answers"], [], settings.upload_directory
    )
    descriptor = SimpleNamespace(application_id=app["id"], run_id=run["id"])
    manifest = persist(
        db,
        descriptor,
        dict(version="sources-v1", snapshot_id=str(snapshot["id"]), sources=records),
    )
    evidence = {
        e["id"]: {
            **e,
            "question_ids": s["question_ids"],
            "extractor_version": s["extractor_version"],
        }
        for s in records
        for e in s["excerpts"]
    }
    policy = snapshot["policy_snapshot"]
    messages, allowed, limits = build_messages(
        policy, snapshot["configuration"], evidence
    )
    rows = []
    for criterion, level in zip(
        [c for c in policy["criteria"] if c["weight"] is not None],
        candidate["levels"],
        strict=True,
    ):
        proofs = [
            key
            for key, e in allowed.items()
            if set(e["question_ids"]).intersection(criterion["source_question_ids"])
        ]
        rows.append(
            dict(
                criterion_id=criterion["criterion_id"],
                status="evaluated" if level is not None else "insufficient_information",
                level=level,
                evidence_ids=proofs[:1] if level is not None else [],
                rationale="Appréciation fictive préchargée : "
                + (
                    criterion["levels"][level]
                    if level is not None
                    else "Réponse attendue absente, à vérifier."
                ),
                uncertainties=[
                    "Exemple pédagogique non calibré sur des candidats réels."
                ],
                policy_version=policy["version"],
                rubric_version=criterion["rubric_version"],
            )
        )
    rows = validate_assessments(dict(assessments=rows), policy, allowed)
    calculation = calculate(policy, rows)
    availability = conditions(snapshot["configuration"], app["answers"])
    for condition in availability["results"]:
        condition["evidence_ids"] = [
            key
            for key, e in evidence.items()
            if condition["question_id"] in e["question_ids"]
        ]
    stamp = now(db)
    result = Evaluation(
        id=uuid4(),
        application_id=app["id"],
        run_id=run["id"],
        snapshot_id=snapshot["id"],
        policy_version=policy["version"],
        assessments=rows,
        conditions=availability["results"],
        eligibility=availability["eligibility"],
        calculation=calculation,
        provenance=Provenance(
            mode="preloaded",
            fixture_version=version,
            requested_model=None,
            provider=None,
            effective_model=None,
            response_model=None,
            prompt_version="fixture-assessment-v1",
            adapter_version="fixture-json-v1",
            prompt_hash=digest(
                json.dumps(messages, sort_keys=True, ensure_ascii=False)
            ),
            evidence_ids=list(allowed),
            **limits,
            extractor_versions=sorted({s["extractor_version"] for s in records}),
            duration_seconds=0,
            started_at=stamp,
            finished_at=stamp,
        ),
        created_at=stamp,
    )
    exact = calculation["score_exact"]
    db.execute(
        evaluations.insert().values(
            **result.model_dump(mode="json"),
            score_numerator=exact["numerator"] if exact else None,
            score_denominator=exact["denominator"] if exact else None,
        )
    )
    state = "completed" if calculation["complete"] else "completed_partial"
    db.execute(
        applications.update()
        .where(applications.c.id == app["id"])
        .values(
            effective_evaluation_id=result.id,
            processing_state=state,
            processing_revision=applications.c.processing_revision + 1,
            review_revision=applications.c.review_revision + 1,
        )
    )
    db.execute(
        analysis_runs.update()
        .where(analysis_runs.c.id == run["id"])
        .values(state=state, finished_at=stamp)
    )
    db.execute(
        jobs.update().where(jobs.c.run_id == run["id"]).values(state="succeeded")
    )
    outputs = [
        dict(
            version="answers-v1",
            snapshot_id=str(snapshot["id"]),
            answers=app["answers"],
        ),
        manifest,
        dict(version="evaluation-v1", evaluation_id=str(result.id)),
    ]
    for position, (name, output) in enumerate(zip(PIPELINE, outputs, strict=True)):
        db.execute(
            steps.insert().values(
                run_id=run["id"],
                name=name,
                position=position,
                state="succeeded",
                attempts=0,
                active_seconds=0,
                finished_at=stamp,
                output=output,
            )
        )
