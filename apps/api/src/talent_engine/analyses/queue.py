"""Short PostgreSQL transactions; application -> job is the common lock order."""

import hashlib
import json
import logging
import random
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import or_, select
from talent_engine.applications.data import analysis_runs, applications, jobs
from talent_engine.campaigns.data import campaigns
from talent_engine.campaigns.lifecycle import now
from talent_engine.evaluations.data import finalize
from talent_engine.sources.data import persist

from .repository import steps

PIPELINE = ("extract_answers", "source_manifest", "evaluate")
logger = logging.getLogger("talent_engine.worker")


@dataclass(frozen=True)
class Claim:
    job_id: object
    run_id: object
    application_id: object
    application_generation: int
    token: object
    generation: int
    step: str
    attempt: int
    input_hash: str


def event(name, claim=None, **fields):
    data = {"event": name, **fields}
    if claim:
        data.update(
            job_id=str(claim.job_id),
            run_id=str(claim.run_id),
            step=claim.step,
            attempt=claim.attempt,
            generation=claim.generation,
        )
    logger.info(json.dumps(data, sort_keys=True))


def terminal(db, job, timestamp, code):
    db.execute(
        jobs.update()
        .where(jobs.c.id == job["id"])
        .values(
            state="failed",
            error_code=code,
            lease_token=None,
            lease_until=None,
            next_attempt_at=None,
        )
    )
    db.execute(
        analysis_runs.update()
        .where(analysis_runs.c.id == job["run_id"])
        .values(state="failed", error_code=code, finished_at=timestamp)
    )
    db.execute(
        applications.update()
        .where(applications.c.id == job["application_id"])
        .values(
            processing_state="failed",
            processing_revision=applications.c.processing_revision + 1,
        )
    )


def acquire(engine, settings, worker_id):
    with engine.begin() as db:
        timestamp = now(db)
        eligible = (
            jobs.c.state.in_(["queued", "running", "waiting"])
            & or_(jobs.c.next_attempt_at.is_(None), jobs.c.next_attempt_at <= timestamp)
            & or_(jobs.c.lease_until.is_(None), jobs.c.lease_until <= timestamp)
        )
        app = (
            db.execute(
                select(applications)
                .where(
                    applications.c.deleted_at.is_(None)
                    & applications.c.id.in_(
                        select(jobs.c.application_id).where(eligible)
                    )
                )
                .order_by(applications.c.received_at, applications.c.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            .mappings()
            .first()
        )
        if not app:
            return None
        job = (
            db.execute(
                select(jobs)
                .where(eligible & (jobs.c.application_id == app["id"]))
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            .mappings()
            .first()
        )
        if not job:
            return None
        if job["application_generation"] != app["processing_generation"]:
            db.execute(
                jobs.update()
                .where(jobs.c.id == job["id"])
                .values(state="cancelled", lease_token=None, lease_until=None)
            )
            return None
        existing = (
            db.execute(
                select(steps)
                .where(steps.c.run_id == job["run_id"])
                .order_by(steps.c.position)
            )
            .mappings()
            .all()
        )
        if not existing:
            for position, name in enumerate(PIPELINE):
                db.execute(
                    steps.insert().values(
                        run_id=job["run_id"],
                        name=name,
                        position=position,
                        state="queued",
                        attempts=0,
                        active_seconds=0,
                    )
                )
            existing = (
                db.execute(
                    select(steps)
                    .where(steps.c.run_id == job["run_id"])
                    .order_by(steps.c.position)
                )
                .mappings()
                .all()
            )
        step = next((s for s in existing if s["state"] != "succeeded"), None)
        if not step:
            # A valid evaluation must be published atomically by its adapter.
            terminal(db, job, timestamp, "evaluation_unavailable")
            return None
        active = step["active_seconds"]
        if step["state"] == "running" and step["started_at"]:
            active += min(
                settings.step_timeout_seconds,
                max(0, (timestamp - step["started_at"]).total_seconds()),
            )
        total_active = active + sum(
            s["active_seconds"] for s in existing if s["name"] != step["name"]
        )
        if step["attempts"] >= 3 or total_active >= settings.run_budget_seconds:
            code = (
                "attempts_exhausted"
                if step["attempts"] >= 3
                else "run_budget_exhausted"
            )
            db.execute(
                steps.update()
                .where(
                    (steps.c.run_id == job["run_id"]) & (steps.c.name == step["name"])
                )
                .values(
                    state="failed",
                    finished_at=timestamp,
                    active_seconds=active,
                    error_code=code,
                )
            )
            terminal(db, job, timestamp, code)
            event(
                "job_exhausted",
                job_id=str(job["id"]),
                run_id=str(job["run_id"]),
                code=code,
            )
            return None
        payload = {
            "snapshot_id": str(app["snapshot_id"]),
            "answers": app["answers"],
            "application_generation": app["processing_generation"],
            "step": step["name"],
        }
        input_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        token = uuid4()
        generation = job["lease_generation"] + 1
        claim = Claim(
            job["id"],
            job["run_id"],
            app["id"],
            app["processing_generation"],
            token,
            generation,
            step["name"],
            step["attempts"] + 1,
            input_hash,
        )
        db.execute(
            jobs.update()
            .where(jobs.c.id == job["id"])
            .values(
                state="running",
                lease_generation=generation,
                lease_token=token,
                lease_until=timestamp + timedelta(seconds=settings.lease_seconds),
                worker_id=worker_id,
                next_attempt_at=None,
                error_code=None,
            )
        )
        db.execute(
            steps.update()
            .where((steps.c.run_id == claim.run_id) & (steps.c.name == claim.step))
            .values(
                state="running",
                attempts=claim.attempt,
                active_seconds=active,
                started_at=timestamp,
                finished_at=None,
                input_hash=input_hash,
                error_code=None,
            )
        )
        state = "evaluating" if claim.step == "evaluate" else "collecting"
        db.execute(
            analysis_runs.update()
            .where(analysis_runs.c.id == claim.run_id)
            .values(state=state)
        )
        db.execute(
            applications.update()
            .where(applications.c.id == app["id"])
            .values(
                processing_state=state,
                processing_revision=applications.c.processing_revision + 1,
            )
        )
    event("job_acquired", claim)
    return claim


def fenced(db, claim):
    app = (
        db.execute(
            select(applications)
            .where(applications.c.id == claim.application_id)
            .with_for_update()
        )
        .mappings()
        .first()
    )
    if (
        not app
        or app["deleted_at"]
        or app["processing_generation"] != claim.application_generation
    ):
        return None
    job = (
        db.execute(select(jobs).where(jobs.c.id == claim.job_id).with_for_update())
        .mappings()
        .first()
    )
    if (
        not job
        or job["state"] != "running"
        or job["lease_token"] != claim.token
        or (
            job["lease_generation"] != claim.generation or job["lease_until"] <= now(db)
        )
    ):
        return None
    return job


def heartbeat(engine, settings, claim):
    with engine.begin() as db:
        if not fenced(db, claim):
            return False
        db.execute(
            jobs.update()
            .where(jobs.c.id == claim.job_id)
            .values(lease_until=now(db) + timedelta(seconds=settings.lease_seconds))
        )
    return True


def complete(engine, settings, claim, output):
    with engine.begin() as db:
        if claim.step == "evaluate":
            campaign_id = db.scalar(
                select(applications.c.campaign_id).where(
                    applications.c.id == claim.application_id
                )
            )
            db.execute(
                select(campaigns.c.id)
                .where(campaigns.c.id == campaign_id)
                .with_for_update()
            ).first()
        if not fenced(db, claim):
            return False
        step = (
            db.execute(
                select(steps).where(
                    (steps.c.run_id == claim.run_id) & (steps.c.name == claim.step)
                )
            )
            .mappings()
            .one()
        )
        if step["state"] != "running" or step["input_hash"] != claim.input_hash:
            return False
        timestamp = now(db)
        elapsed = max(0, (timestamp - step["started_at"]).total_seconds())
        total = (
            sum(
                db.scalars(
                    select(steps.c.active_seconds).where(steps.c.run_id == claim.run_id)
                )
            )
            + elapsed
        )
        if (
            elapsed > settings.step_timeout_seconds
            or total > settings.run_budget_seconds
        ):
            return fail_locked(
                db, settings, claim, step, timestamp, "step_timeout", retryable=True
            )
        if claim.step == "source_manifest" and output.get("version") in {
            "received-sources-v2",
            "received-sources-v3",
        }:
            output = persist(db, claim, output)
        final = claim.step == "evaluate"
        if final:
            if output.get("version") not in ("evaluation-v1", "evaluation-v2"):
                return fail_locked(
                    db, settings, claim, step, timestamp, "assessment_invalid"
                )
            try:
                output = finalize(db, claim, output)
            except ValueError:
                return fail_locked(
                    db, settings, claim, step, timestamp, "assessment_invalid"
                )
        # Checkpoint output is immutable once succeeded.
        db.execute(
            steps.update()
            .where((steps.c.run_id == claim.run_id) & (steps.c.name == claim.step))
            .values(
                state="succeeded",
                output=output,
                finished_at=timestamp,
                active_seconds=step["active_seconds"] + elapsed,
            )
        )
        if not final:
            db.execute(
                jobs.update()
                .where(jobs.c.id == claim.job_id)
                .values(
                    state="queued", lease_token=None, lease_until=None, error_code=None
                )
            )
        if claim.step == "source_manifest":
            db.execute(
                analysis_runs.update()
                .where(analysis_runs.c.id == claim.run_id)
                .values(manifest=output)
            )
    event("step_checkpointed", claim)
    return True


def fail_locked(
    db, settings, claim, step, timestamp, code, *, retryable=False, retry_after=None
):
    active = step["active_seconds"] + min(
        settings.step_timeout_seconds,
        max(0, (timestamp - step["started_at"]).total_seconds()),
    )
    if retry_after is not None and not 0 <= retry_after <= 3600:
        retryable, code = False, "quota_wait_exceeded"
    total = sum(
        db.scalars(select(steps.c.active_seconds).where(steps.c.run_id == claim.run_id))
    )
    total += active - step["active_seconds"]
    retry = retryable and claim.attempt < 3 and total < settings.run_budget_seconds
    db.execute(
        steps.update()
        .where((steps.c.run_id == claim.run_id) & (steps.c.name == claim.step))
        .values(
            state="waiting" if retry else "failed",
            active_seconds=active,
            finished_at=timestamp,
            error_code=code,
        )
    )
    if retry:
        delay = (
            retry_after
            if retry_after is not None
            else (
                settings.retry_base_seconds
                if claim.attempt == 1
                else settings.retry_second_seconds
            )
        )
        db.execute(
            jobs.update()
            .where(jobs.c.id == claim.job_id)
            .values(
                state="waiting",
                lease_token=None,
                lease_until=None,
                error_code=code,
                next_attempt_at=timestamp
                + timedelta(seconds=delay + random.uniform(0, 10)),
            )
        )
    else:
        terminal(
            db,
            {
                "id": claim.job_id,
                "run_id": claim.run_id,
                "application_id": claim.application_id,
            },
            timestamp,
            code,
        )
    return True


def fail(engine, settings, claim, code, *, retryable=False, retry_after=None):
    with engine.begin() as db:
        if not fenced(db, claim):
            return False
        step = (
            db.execute(
                select(steps).where(
                    (steps.c.run_id == claim.run_id) & (steps.c.name == claim.step)
                )
            )
            .mappings()
            .one()
        )
        result = fail_locked(
            db,
            settings,
            claim,
            step,
            now(db),
            code,
            retryable=retryable,
            retry_after=retry_after,
        )
    event("step_failed", claim, code=code, retryable=retryable)
    return result
