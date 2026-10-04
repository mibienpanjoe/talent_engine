from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import func, select
from talent_engine.access import build_access_guards
from talent_engine.campaigns.data import owned, snapshots
from talent_engine.campaigns.lifecycle import public_campaign, snapshot_result
from talent_engine.errors import AccessError, Error
from talent_engine.evaluations.data import evaluations
from talent_engine.evaluations.engine import views
from talent_engine.evaluations.schemas import Evaluation

from .cursor import decode, encode
from .repository import analysis_runs, applications, jobs
from .schemas import (
    ApplicationDetail,
    ApplicationPage,
    ApplicationSummary,
    Receipt,
    SubmissionInput,
)
from .service import owned_application, receive


def summary(row, evaluation=None):
    return ApplicationSummary(
        **{
            k: row[k]
            for k in (
                "id",
                "campaign_id",
                "snapshot_id",
                "mode",
                "contact",
                "received_at",
                "processing_state",
                "decision",
                "review_revision",
                "effective_evaluation_id",
            )
        },
        calculation=evaluation.calculation if evaluation else None,
        eligibility=evaluation.eligibility if evaluation else None,
        views=views(
            evaluation.calculation.model_dump(mode="json") if evaluation else None,
            evaluation.eligibility if evaluation else None,
        ),
    )


def build_application_router(engine, settings):
    _, read_guard, write_guard = build_access_guards(engine, settings)
    router = APIRouter(
        prefix="/api/v1",
        tags=["applications"],
        responses={
            400: {"model": Error},
            401: {"model": Error},
            403: {"model": Error},
            404: {"model": Error},
            409: {"model": Error},
            410: {"model": Error},
            413: {"model": Error},
            422: {"model": Error},
            429: {"model": Error},
        },
    )

    @router.post(
        "/public/campaigns/{public_token}/applications",
        response_model=Receipt,
        status_code=201,
        responses={200: {"model": Receipt}},
        operation_id="submit_application",
    )
    def submit(
        public_token: str,
        payload: SubmissionInput,
        response: Response,
        idempotency_key: str | None = Header(None),
    ):
        if len(public_token) > 64:
            raise AccessError(404, "not_found", "Campaign unavailable")
        with engine.begin() as db:
            campaign = public_campaign(db, public_token, lock=True)
            result, created = receive(db, settings, campaign, payload, idempotency_key)
        response.status_code = 201 if created else 200
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.post(
        "/campaigns/{campaign_id}/test-applications",
        response_model=Receipt,
        status_code=201,
        responses={200: {"model": Receipt}},
        operation_id="submit_test_application",
    )
    def test_submit(
        campaign_id: UUID,
        payload: SubmissionInput,
        response: Response,
        idempotency_key: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            campaign = owned(db, campaign_id, session["reviewer_id"], lock=True)
            result, created = receive(
                db, settings, campaign, payload, idempotency_key, "test"
            )
        response.status_code = 201 if created else 200
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.get(
        "/campaigns/{campaign_id}/applications",
        response_model=ApplicationPage,
        operation_id="list_applications",
    )
    def listing(
        campaign_id: UUID,
        response: Response,
        limit: int = Query(25, ge=1, le=100),
        cursor: str | None = Query(None, max_length=400),
        session=Depends(read_guard),
    ):
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as db:
            campaign = owned(db, campaign_id, session["reviewer_id"])
            base = select(applications).where(
                (applications.c.campaign_id == campaign_id)
                & (applications.c.mode == "real")
                & (applications.c.deleted_at.is_(None))
            )
            total = db.scalar(select(func.count()).select_from(base.subquery()))
            if cursor:
                base = base.where(
                    applications.c.id
                    > decode(settings, session["reviewer_id"], campaign, cursor)
                )
            rows = (
                db.execute(base.order_by(applications.c.id).limit(limit + 1))
                .mappings()
                .all()
            )
        response.headers["Cache-Control"] = "no-store"
        return ApplicationPage(
            items=[summary(r) for r in rows[:limit]],
            next_cursor=encode(
                settings, session["reviewer_id"], campaign, rows[limit - 1]["id"]
            )
            if len(rows) > limit
            else None,
            list_revision=str(campaign["list_revision"]),
            counts={
                "all": total,
                "ready": 0,
                "needs_review": total,
                "condition_unmet": 0,
            },
        )

    @router.get(
        "/applications/{application_id}",
        response_model=ApplicationDetail,
        operation_id="read_application",
    )
    def read(application_id: UUID, response: Response, session=Depends(read_guard)):
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as db:
            row = owned_application(db, application_id, session["reviewer_id"])
            snapshot = (
                db.execute(
                    select(snapshots).where(snapshots.c.id == row["snapshot_id"])
                )
                .mappings()
                .one()
            )
            from talent_engine.analyses.data import steps
            from talent_engine.analyses.schemas import AnalysisProgress, StepProgress
            from talent_engine.documents.data import uploads
            from talent_engine.documents.schemas import Upload

            histories = (
                db.execute(
                    select(analysis_runs, jobs.c.next_attempt_at)
                    .join(jobs, jobs.c.run_id == analysis_runs.c.id)
                    .where(analysis_runs.c.application_id == application_id)
                    .order_by(analysis_runs.c.created_at.desc())
                    .limit(20)
                )
                .mappings()
                .all()
            )
            step_rows = (
                db.execute(
                    select(steps)
                    .where(steps.c.run_id.in_([r["id"] for r in histories]))
                    .order_by(steps.c.position)
                )
                .mappings()
                .all()
            )
            progress = [
                AnalysisProgress(
                    **{
                        k: r[k]
                        for k in (
                            "id",
                            "reason",
                            "state",
                            "error_code",
                            "next_attempt_at",
                        )
                    },
                    steps=[
                        StepProgress(**{k: step[k] for k in StepProgress.model_fields})
                        for step in step_rows
                        if step["run_id"] == r["id"]
                    ],
                )
                for r in histories
            ]
            effective = None
            if row["effective_evaluation_id"]:
                base = (
                    db.execute(
                        select(evaluations).where(
                            (evaluations.c.id == row["effective_evaluation_id"])
                            & (evaluations.c.application_id == application_id)
                        )
                    )
                    .mappings()
                    .one()
                )
                effective = Evaluation(**{k: base[k] for k in Evaluation.model_fields})
            documents = [
                Upload(**{k: r[k] for k in Upload.model_fields})
                for r in db.execute(
                    select(uploads).where(uploads.c.application_id == application_id)
                ).mappings()
            ]
        response.headers["Cache-Control"] = "no-store"
        response.headers["ETag"] = f'"{row["review_revision"]}"'
        return ApplicationDetail(
            application=summary(row, effective),
            effective_evaluation=effective,
            answers=row["answers"],
            snapshot=snapshot_result(snapshot),
            uploads=documents,
            analyses=progress,
        )

    return router
