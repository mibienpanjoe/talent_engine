from datetime import timedelta

from sqlalchemy import select
from talent_engine.applications.data import applications, receipts
from talent_engine.campaigns.data import campaigns
from talent_engine.campaigns.lifecycle import now
from talent_engine.reviews.data import application_actions

from .repository import cleanup_requests
from .service import mark


def collect_retention(engine):
    count = 0
    with engine.connect() as db:
        candidates = (
            db.execute(
                select(applications.c.id, applications.c.campaign_id)
                .where(
                    applications.c.deleted_at.is_(None),
                    applications.c.received_at <= now(db) - timedelta(days=90),
                )
                .order_by(applications.c.received_at)
                .limit(100)
            )
            .mappings()
            .all()
        )
    for candidate in candidates:
        with engine.begin() as db:
            if (
                db.scalar(
                    select(campaigns.c.id)
                    .where(campaigns.c.id == candidate["campaign_id"])
                    .with_for_update(skip_locked=True)
                )
                is None
            ):
                continue
            row = (
                db.execute(
                    select(applications)
                    .where(
                        applications.c.id == candidate["id"],
                        applications.c.deleted_at.is_(None),
                    )
                    .with_for_update(skip_locked=True)
                )
                .mappings()
                .first()
            )
            if row and row["received_at"] <= now(db) - timedelta(days=90):
                mark(db, row)
                count += 1
    with engine.begin() as db:
        db.execute(
            application_actions.delete().where(
                application_actions.c.expires_at <= now(db)
            )
        )
        db.execute(receipts.delete().where(receipts.c.expires_at <= now(db)))
        db.execute(
            cleanup_requests.delete().where(
                cleanup_requests.c.state == "completed",
                cleanup_requests.c.completed_at <= now(db) - timedelta(days=7),
            )
        )
    return count
