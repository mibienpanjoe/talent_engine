from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy import func, or_, select
from talent_engine.access import build_access_guards
from talent_engine.applications.data import applications
from talent_engine.campaigns.data import owned
from talent_engine.errors import AccessError, Error
from talent_engine.reviews.actions import check_header
from talent_engine.reviews.schemas import ReviewExpectation

from .repository import cleanup_requests
from .schemas import Cleanup
from .service import mark


def visible():
    return or_(
        cleanup_requests.c.completed_at.is_(None),
        cleanup_requests.c.completed_at > func.now() - timedelta(days=7),
    )


def build_deletion_router(engine, settings):
    _, read_guard, write_guard = build_access_guards(engine, settings)
    router = APIRouter(
        prefix="/api/v1",
        tags=["deletions"],
        responses={code: {"model": Error} for code in (401, 403, 404, 409, 422, 428)},
    )

    @router.delete(
        "/applications/{application_id}",
        response_model=Cleanup,
        status_code=202,
        responses={200: {"model": Cleanup}},
        operation_id="delete_application",
    )
    def delete(
        application_id: UUID,
        response: Response,
        payload: ReviewExpectation | None = None,
        if_match: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            campaign_id = db.scalar(
                select(applications.c.campaign_id)
                .where(applications.c.id == application_id)
                .union_all(
                    select(cleanup_requests.c.campaign_id).where(
                        cleanup_requests.c.application_id == application_id, visible()
                    )
                )
                .limit(1)
            )
            if campaign_id is None:
                raise AccessError(404, "not_found", "Application unavailable")
            owned(db, campaign_id, session["reviewer_id"], lock=True)
            existing = (
                db.execute(
                    select(cleanup_requests).where(
                        cleanup_requests.c.application_id == application_id, visible()
                    )
                )
                .mappings()
                .first()
            )
            if existing:
                result = existing
            else:
                row = (
                    db.execute(
                        select(applications)
                        .where(applications.c.id == application_id)
                        .with_for_update()
                    )
                    .mappings()
                    .first()
                )
                if not row or row["deleted_at"]:
                    raise AccessError(404, "not_found", "Application unavailable")
                expectation = payload or ReviewExpectation(
                    review_revision=row["review_revision"],
                    effective_evaluation_id=row["effective_evaluation_id"],
                )
                check_header(expectation, if_match)
                if (
                    expectation.review_revision != row["review_revision"]
                    or expectation.effective_evaluation_id
                    != row["effective_evaluation_id"]
                ):
                    raise AccessError(
                        409,
                        "review_revision_conflict",
                        "Reload before deleting this application",
                    )
                result = mark(db, row)
        response.status_code = 200 if result["state"] == "completed" else 202
        response.headers["Cache-Control"] = "no-store"
        return Cleanup(**{k: result[k] for k in Cleanup.model_fields})

    @router.get(
        "/cleanup-requests/{request_id}",
        response_model=Cleanup,
        operation_id="read_cleanup",
    )
    def read(request_id: UUID, response: Response, session=Depends(read_guard)):
        with engine.connect() as db:
            row = (
                db.execute(
                    select(cleanup_requests).where(
                        cleanup_requests.c.id == request_id, visible()
                    )
                )
                .mappings()
                .first()
            )
            if not row:
                raise AccessError(404, "not_found", "Cleanup unavailable")
            owned(db, row["campaign_id"], session["reviewer_id"])
        response.headers["Cache-Control"] = "no-store"
        return Cleanup(**{k: row[k] for k in Cleanup.model_fields})

    @router.get(
        "/campaigns/{campaign_id}/cleanup-requests",
        response_model=list[Cleanup],
        operation_id="list_cleanup",
    )
    def listing(campaign_id: UUID, response: Response, session=Depends(read_guard)):
        with engine.connect() as db:
            owned(db, campaign_id, session["reviewer_id"])
            records = (
                db.execute(
                    select(cleanup_requests)
                    .where(cleanup_requests.c.campaign_id == campaign_id, visible())
                    .order_by(cleanup_requests.c.created_at.desc())
                    .limit(100)
                )
                .mappings()
                .all()
            )
        response.headers["Cache-Control"] = "no-store"
        return [Cleanup(**{k: row[k] for k in Cleanup.model_fields}) for row in records]

    return router
