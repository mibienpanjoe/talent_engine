from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from talent_engine.access import build_access_guards, reviewers
from talent_engine.applications.cursor import decode, encode
from talent_engine.applications.data import analysis_runs
from talent_engine.applications.service import owned_application
from talent_engine.errors import Error
from talent_engine.evaluations.data import evaluations as bases
from talent_engine.evaluations.schemas import Evaluation

from .actions import action, check_header
from .activation import activate
from .analysis import request_analysis
from .data import evaluations
from .repository import events
from .schemas import (
    ActivationInput,
    AnalysisInput,
    AnalysisReceipt,
    CorrectionInput,
    DecisionInput,
    EvaluationVersion,
    ReviewEvent,
)
from .service import correct, decide


def build_review_router(engine, settings):
    _, read_guard, write_guard = build_access_guards(engine, settings)
    router = APIRouter(
        prefix="/api/v1/applications",
        tags=["reviews"],
        responses={code: {"model": Error} for code in (401, 403, 404, 409, 422, 428)},
    )

    def returned_event(db, ident):
        return (
            db.execute(
                select(events, reviewers.c.login.label("author_login"))
                .join(reviewers, reviewers.c.id == events.c.author_id)
                .where(events.c.id == ident)
            )
            .mappings()
            .one()
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
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            ident, _ = action(
                db,
                settings,
                application_id,
                session["reviewer_id"],
                "corrections",
                payload,
                idempotency_key,
                if_match,
                lambda row: correct(
                    db, application_id, session["reviewer_id"], payload, row=row
                )["id"],
            )
            result = returned_event(db, ident)
        response.headers["Cache-Control"] = "no-store"
        response.headers["ETag"] = f'"{result["review_revision"] + 1}"'
        return result

    @router.patch(
        "/{application_id}/decision",
        response_model=ReviewEvent,
        operation_id="set_decision",
    )
    def decision(
        application_id: UUID,
        payload: DecisionInput,
        response: Response,
        if_match: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            owned_application(db, application_id, session["reviewer_id"])
            check_header(payload, if_match)
            result = decide(db, application_id, session["reviewer_id"], payload)
            result = returned_event(db, result["id"])
        response.headers["Cache-Control"] = "no-store"
        response.headers["ETag"] = f'"{result["review_revision"] + 1}"'
        return result

    @router.post(
        "/{application_id}/analyses",
        response_model=AnalysisReceipt,
        status_code=202,
        operation_id="request_analysis",
    )
    def analysis(
        application_id: UUID,
        payload: AnalysisInput,
        response: Response,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            ident, _ = action(
                db,
                settings,
                application_id,
                session["reviewer_id"],
                "analyses",
                payload,
                idempotency_key,
                if_match,
                lambda row: request_analysis(db, row, payload),
                permanent=True,
            )
            row = (
                db.execute(select(analysis_runs).where(analysis_runs.c.id == ident))
                .mappings()
                .one()
            )
        response.headers["Cache-Control"] = "no-store"
        response.headers["ETag"] = f'"{payload.review_revision + 1}"'
        return AnalysisReceipt(
            **{k: row[k] for k in ("id", "application_id", "reason", "created_at")}
        )

    @router.post(
        "/{application_id}/activations",
        response_model=ReviewEvent,
        operation_id="activate_evaluation",
    )
    def activation(
        application_id: UUID,
        payload: ActivationInput,
        response: Response,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            ident, _ = action(
                db,
                settings,
                application_id,
                session["reviewer_id"],
                "activations",
                payload,
                idempotency_key,
                if_match,
                lambda row: activate(db, row, session["reviewer_id"], payload),
            )
            result = returned_event(db, ident)
        response.headers["Cache-Control"] = "no-store"
        response.headers["ETag"] = f'"{result["review_revision"] + 1}"'
        return result

    @router.get(
        "/{application_id}/review-history",
        response_model=list[ReviewEvent],
        operation_id="review_history",
    )
    def history(
        application_id: UUID,
        response: Response,
        limit: int = Query(100, ge=1, le=100),
        cursor: str | None = Query(None, max_length=500),
        active_only: bool = False,
        session=Depends(read_guard),
    ):
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as db:
            row = owned_application(db, application_id, session["reviewer_id"])
            binding = {
                "id": application_id,
                "list_revision": str(row["review_revision"])
                + ":"
                + str(row["processing_revision"]),
            }
            scope = ["review_history", active_only]
            offset = (
                decode(settings, session["reviewer_id"], binding, cursor, scope=scope)
                if cursor
                else 0
            )
            query = (
                select(events, reviewers.c.login.label("author_login"))
                .join(reviewers, reviewers.c.id == events.c.author_id)
                .where(events.c.application_id == application_id)
            )
            if active_only:
                query = (
                    query.where(
                        events.c.evaluation_id == row["effective_evaluation_id"],
                        events.c.kind.in_(["assessment", "condition"]),
                    )
                    .distinct(events.c.kind, events.c.criterion_id)
                    .order_by(
                        events.c.kind,
                        events.c.criterion_id,
                        events.c.created_at.desc(),
                        events.c.id.desc(),
                    )
                )
                result = [
                    item
                    for item in db.execute(query).mappings()
                    if item["action"] == "set"
                ]
            else:
                records = (
                    db.execute(
                        query.order_by(events.c.created_at, events.c.id)
                        .offset(offset)
                        .limit(limit + 1)
                    )
                    .mappings()
                    .all()
                )
                result = records[:limit]
                if len(records) > limit:
                    response.headers["X-Next-Cursor"] = encode(
                        settings,
                        session["reviewer_id"],
                        binding,
                        offset + limit,
                        scope=scope,
                    )
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.get(
        "/{application_id}/evaluation-versions",
        response_model=list[EvaluationVersion],
        operation_id="evaluation_versions",
    )
    def versions(
        application_id: UUID,
        response: Response,
        limit: int = Query(25, ge=1, le=100),
        cursor: str | None = Query(None, max_length=500),
        session=Depends(read_guard),
    ):
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as db:
            row = owned_application(db, application_id, session["reviewer_id"])
            binding = {
                "id": application_id,
                "list_revision": str(row["review_revision"])
                + ":"
                + str(row["processing_revision"]),
            }
            scope = ["evaluation_versions"]
            offset = (
                decode(settings, session["reviewer_id"], binding, cursor, scope=scope)
                if cursor
                else 0
            )
            original = (
                db.execute(
                    select(bases)
                    .where(bases.c.application_id == application_id)
                    .order_by(bases.c.created_at.desc(), bases.c.id.desc())
                    .offset(offset)
                    .limit(limit + 1)
                )
                .mappings()
                .all()
            )
            if len(original) > limit:
                response.headers["X-Next-Cursor"] = encode(
                    settings,
                    session["reviewer_id"],
                    binding,
                    offset + limit,
                    scope=scope,
                )
            original = original[:limit]
            projected = {
                r["id"]: r
                for r in db.execute(
                    select(evaluations).where(
                        evaluations.c.application_id == application_id,
                        evaluations.c.id.in_([r["id"] for r in original]),
                    )
                ).mappings()
            }
            result = [
                EvaluationVersion(
                    base=Evaluation(**{k: r[k] for k in Evaluation.model_fields}),
                    corrected=Evaluation(
                        **{k: projected[r["id"]][k] for k in Evaluation.model_fields}
                    )
                    if r["assessments"] != projected[r["id"]]["assessments"]
                    or r["conditions"] != projected[r["id"]]["conditions"]
                    else None,
                )
                for r in original
            ]
        response.headers["Cache-Control"] = "no-store"
        return result

    return router
