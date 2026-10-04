from uuid import uuid4

from sqlalchemy import or_, select
from talent_engine.applications.data import applications, jobs, receipts
from talent_engine.campaigns.lifecycle import now
from talent_engine.documents.data import upload_sessions, uploads
from talent_engine.reception_limits.data import transfers
from talent_engine.reviews.service import bump

from .repository import cleanup_requests


def mark(db, row):
    timestamp = now(db)
    session_ids = list(
        db.scalars(
            select(uploads.c.session_id)
            .where(uploads.c.application_id == row["id"])
            .distinct()
        )
    )
    if session_ids:
        db.execute(
            select(upload_sessions.c.id)
            .where(upload_sessions.c.id.in_(session_ids))
            .with_for_update()
        ).all()
        db.execute(
            upload_sessions.update()
            .where(upload_sessions.c.id.in_(session_ids))
            .values(expires_at=timestamp)
        )
    files = (
        db.execute(
            select(uploads.c.storage_key).where(
                or_(
                    uploads.c.application_id == row["id"],
                    uploads.c.session_id.in_(session_ids)
                    & uploads.c.application_id.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    inflight = list(
        db.scalars(
            select(transfers.c.storage_key).where(
                transfers.c.session_id.in_(session_ids),
                transfers.c.storage_key.is_not(None),
            )
        )
    )
    bump(
        db,
        row,
        deleted_at=timestamp,
        effective_evaluation_id=None,
        processing_generation=applications.c.processing_generation + 1,
        processing_revision=applications.c.processing_revision + 1,
    )
    db.execute(
        jobs.update()
        .where(
            jobs.c.application_id == row["id"],
            jobs.c.state.in_(["queued", "running", "waiting"]),
        )
        .values(
            state="cancelled",
            lease_generation=jobs.c.lease_generation + 1,
            lease_token=None,
            lease_until=None,
            next_attempt_at=None,
            worker_id=None,
        )
    )
    # Keep the original expiry, without responses or filenames.
    db.execute(
        receipts.update()
        .where(receipts.c.application_id == row["id"])
        .values(
            deleted_at=timestamp,
            application_id=None,
            received_at=None,
            receipt_ref=None,
            canonical_version=None,
            upload_manifest=None,
        )
    )
    record = dict(
        id=uuid4(),
        application_id=row["id"],
        campaign_id=row["campaign_id"],
        state="pending",
        attempts=0,
        failures=0,
        incident=False,
        storage_keys=sorted(set(files + inflight)),
        session_ids=[str(ident) for ident in session_ids],
        next_attempt_at=timestamp,
        error_code=None,
        created_at=timestamp,
        completed_at=None,
    )
    db.execute(cleanup_requests.insert().values(**record))
    return record
