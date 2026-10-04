"""Durable, idempotent purge: physical files precede irreversible SQL removal."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from talent_engine.analyses.data import steps
from talent_engine.analyses.queue import event
from talent_engine.applications.data import analysis_runs, applications, jobs, receipts
from talent_engine.campaigns.data import campaigns
from talent_engine.campaigns.lifecycle import now
from talent_engine.documents.data import upload_sessions, uploads
from talent_engine.documents.service import storage_path
from talent_engine.evaluations.data import embedding_cache, evaluations
from talent_engine.reception_limits.data import transfers
from talent_engine.reviews.data import application_actions, events, projections
from talent_engine.sources.data import excerpts, run_evidence, run_sources, sources

from .repository import cleanup_requests


def retry(db, record, code):
    failures = record["failures"] + 1
    delay = 30 if failures == 1 else 120 if failures == 2 else 3600
    db.execute(
        cleanup_requests.update()
        .where(
            cleanup_requests.c.id == record["id"],
            cleanup_requests.c.state != "completed",
        )
        .values(
            state="waiting",
            attempts=record["attempts"] + 1,
            failures=failures,
            incident=failures >= 3,
            error_code=code,
            next_attempt_at=now(db) + timedelta(seconds=delay),
        )
    )
    event(
        "cleanup_retry",
        request_id=str(record["id"]),
        attempt=record["attempts"] + 1,
        code=code,
        incident=failures >= 3,
    )


def remove_rows(db, record):
    ident = record["application_id"]
    run_ids = select(analysis_runs.c.id).where(analysis_runs.c.application_id == ident)
    tables = (
        events,
        projections,
        application_actions,
        embedding_cache,
        run_evidence,
        run_sources,
        excerpts,
        sources,
        evaluations,
    )
    for table in tables:
        db.execute(table.delete().where(table.c.application_id == ident))
    db.execute(steps.delete().where(steps.c.run_id.in_(run_ids)))
    for table in (jobs, analysis_runs):
        db.execute(table.delete().where(table.c.application_id == ident))
    # Include unattached files; preserve files belonging to another application.
    db.execute(
        uploads.delete().where(
            (uploads.c.application_id == ident)
            | (
                uploads.c.application_id.is_(None)
                & uploads.c.storage_key.in_(record["storage_keys"])
            )
        )
    )
    session_ids = [UUID(item) for item in record["session_ids"]]
    db.execute(transfers.delete().where(transfers.c.session_id.in_(session_ids)))
    db.execute(
        upload_sessions.delete().where(
            upload_sessions.c.id.in_(session_ids),
            ~upload_sessions.c.id.in_(select(uploads.c.session_id)),
        )
    )
    db.execute(
        applications.delete().where(
            applications.c.id == ident, applications.c.deleted_at.is_not(None)
        )
    )
    for table in (*tables, jobs, analysis_runs, uploads, receipts):
        if (
            db.scalar(
                select(table.c.application_id)
                .where(table.c.application_id == ident)
                .limit(1)
            )
            is not None
        ):
            raise ValueError("cleanup_verification_failed")
    if (
        db.scalar(select(applications.c.id).where(applications.c.id == ident))
        is not None
    ):
        raise ValueError("cleanup_verification_failed")


def purge_once(engine, settings):
    with engine.connect() as db:
        candidate = (
            db.execute(
                select(cleanup_requests)
                .where(
                    cleanup_requests.c.state != "completed",
                    or_(
                        cleanup_requests.c.next_attempt_at.is_(None),
                        cleanup_requests.c.next_attempt_at <= now(db),
                    ),
                )
                .order_by(cleanup_requests.c.created_at, cleanup_requests.c.id)
                .limit(1)
            )
            .mappings()
            .first()
        )
    if not candidate:
        return False
    try:
        with engine.begin() as db:
            # Campaign -> application -> cleanup; competing purgers skip locks.
            if (
                db.scalar(
                    select(campaigns.c.id)
                    .where(campaigns.c.id == candidate["campaign_id"])
                    .with_for_update(skip_locked=True)
                )
                is None
            ):
                return False
            app = (
                db.execute(
                    select(applications)
                    .where(applications.c.id == candidate["application_id"])
                    .with_for_update(skip_locked=True)
                )
                .mappings()
                .first()
            )
            if not app or not app["deleted_at"]:
                return False
            record = (
                db.execute(
                    select(cleanup_requests)
                    .where(
                        cleanup_requests.c.id == candidate["id"],
                        cleanup_requests.c.state != "completed",
                    )
                    .with_for_update(skip_locked=True)
                )
                .mappings()
                .first()
            )
            if (
                not record
                or record["next_attempt_at"]
                and record["next_attempt_at"] > now(db)
            ):
                return False
            try:
                for key in record["storage_keys"]:
                    storage_path(settings, key).unlink(missing_ok=True)
                if any(
                    storage_path(settings, key).exists()
                    for key in record["storage_keys"]
                ):
                    raise OSError("cleanup_storage_verification_failed")
            except OSError:
                retry(db, record, "cleanup_storage_unavailable")
                return True
            remove_rows(db, record)
            db.execute(
                cleanup_requests.update()
                .where(cleanup_requests.c.id == record["id"])
                .values(
                    state="completed",
                    attempts=record["attempts"] + 1,
                    failures=0,
                    incident=False,
                    storage_keys=[],
                    session_ids=[],
                    next_attempt_at=None,
                    error_code=None,
                    completed_at=now(db),
                )
            )
        event("cleanup_completed", request_id=str(candidate["id"]))
        return True
    except (SQLAlchemyError, ValueError):
        # An aborted SQL transaction cannot record its own retry. Retry in a fresh one.
        with engine.begin() as db:
            db.execute(
                select(campaigns.c.id)
                .where(campaigns.c.id == candidate["campaign_id"])
                .with_for_update()
            ).first()
            db.execute(
                select(applications.c.id)
                .where(applications.c.id == candidate["application_id"])
                .with_for_update()
            ).first()
            record = (
                db.execute(
                    select(cleanup_requests)
                    .where(
                        cleanup_requests.c.id == candidate["id"],
                        cleanup_requests.c.state != "completed",
                    )
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if record:
                retry(db, record, "cleanup_database_unavailable")
        return True
