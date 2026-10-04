from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from talent_engine.access import build_access_guards
from talent_engine.applications.service import owned_application
from talent_engine.errors import Error

from .repository import events
from .schemas import CorrectionInput, ReviewEvent
from .service import correct


def build_review_router(engine, settings):
    _, read_guard, write_guard = build_access_guards(engine, settings)
    router = APIRouter(
        prefix="/api/v1/applications",
        tags=["reviews"],
        responses={code: {"model": Error} for code in (401, 403, 404, 409, 422)},
    )

    @router.post(
        "/{application_id}/corrections",
        response_model=ReviewEvent,
        status_code=201,
        operation_id="correct_assessment",
    )
    def correction(
        application_id: UUID,
        payload: CorrectionInput,
        response: Response,
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            result = correct(db, application_id, session["reviewer_id"], payload)
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.get(
        "/{application_id}/review-history",
        response_model=list[ReviewEvent],
        operation_id="review_history",
    )
    def history(application_id: UUID, response: Response, session=Depends(read_guard)):
        with engine.connect() as db:
            owned_application(db, application_id, session["reviewer_id"])
            result = (
                db.execute(
                    select(events)
                    .where(events.c.application_id == application_id)
                    .order_by(events.c.created_at, events.c.id)
                )
                .mappings()
                .all()
            )
        response.headers["Cache-Control"] = "no-store"
        return result

    return router
