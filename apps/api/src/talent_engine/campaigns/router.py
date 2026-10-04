from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from talent_engine.access import build_access_guards
from talent_engine.errors import Error

from .repository import (
    campaign_result,
    campaigns,
    check_revision,
    idempotent,
    insert_campaign,
    owned,
    snapshots,
    title_changes,
)
from .schemas import (
    Campaign,
    CampaignInput,
    CampaignPage,
    Preparation,
    TitleChange,
    TitleInput,
    preparation_issues,
)


def build_campaign_router(engine, settings):
    _, require_session, require_mutation = build_access_guards(engine, settings)
    router = APIRouter(
        prefix="/api/v1/campaigns",
        tags=["campaigns"],
        responses={
            401: {"model": Error},
            403: {"model": Error},
            404: {"model": Error},
            409: {"model": Error},
            422: {"model": Error},
            428: {"model": Error},
        },
    )

    def headers(response, result=None):
        response.headers["Cache-Control"] = "no-store"
        if result:
            response.headers["ETag"] = f'"{result.revision}"'

    @router.get("", response_model=CampaignPage, operation_id="list_campaigns")
    def listing(
        response: Response,
        limit: int = Query(25, ge=1, le=100),
        cursor: UUID | None = None,
        session=Depends(require_session),
    ):
        query = (
            select(campaigns, snapshots.c.configuration.label("active_configuration"))
            .outerjoin(snapshots, snapshots.c.id == campaigns.c.active_snapshot_id)
            .where(campaigns.c.owner_id == session["reviewer_id"])
        )
        if cursor:
            query = query.where(campaigns.c.id > cursor)
        with engine.connect() as db:
            rows = (
                db.execute(query.order_by(campaigns.c.id).limit(limit + 1))
                .mappings()
                .all()
            )
        headers(response)
        with engine.connect() as db:
            return CampaignPage(
                items=[
                    campaign_result(r, db=db, origin=settings.public_origin)
                    for r in rows[:limit]
                ],
                next_cursor=str(rows[limit - 1]["id"]) if len(rows) > limit else None,
            )

    @router.post(
        "", response_model=Campaign, status_code=201, operation_id="create_campaign"
    )
    def create(
        payload: CampaignInput,
        response: Response,
        idempotency_key: str | None = Header(None),
        session=Depends(require_mutation),
    ):
        with engine.begin() as db:
            result = idempotent(
                db,
                settings,
                session["reviewer_id"],
                "create_campaign",
                idempotency_key,
                payload.model_dump(mode="json"),
                lambda: insert_campaign(
                    db,
                    session["reviewer_id"],
                    payload.configuration.model_dump(mode="json"),
                ),
            )
        headers(response, result)
        return result

    @router.get("/{campaign_id}", response_model=Campaign, operation_id="read_campaign")
    def read(campaign_id: UUID, response: Response, session=Depends(require_session)):
        with engine.connect() as db:
            result = campaign_result(
                owned(db, campaign_id, session["reviewer_id"]),
                db=db,
                origin=settings.public_origin,
            )
        headers(response, result)
        return result

    @router.patch(
        "/{campaign_id}", response_model=Campaign, operation_id="update_campaign"
    )
    def patch(
        campaign_id: UUID,
        payload: CampaignInput | TitleInput,
        response: Response,
        if_match: str | None = Header(None),
        session=Depends(require_mutation),
    ):
        from talent_engine.errors import AccessError

        with engine.begin() as db:
            row = owned(db, campaign_id, session["reviewer_id"], lock=True)
            check_revision(row, if_match)
            if isinstance(payload, TitleInput):
                if row["state"] != "published" or not row["configuration_locked_at"]:
                    raise AccessError(
                        409,
                        "title_correction_unavailable",
                        "Edit the draft title before freezing",
                    )
                previous = row["display_title"] or row["active_configuration"]["title"]
                if previous != payload.title:
                    from .lifecycle import now

                    db.execute(
                        title_changes.insert().values(
                            id=uuid4(),
                            campaign_id=campaign_id,
                            previous_title=previous,
                            title=payload.title,
                            author_id=session["reviewer_id"],
                            changed_at=now(db),
                        )
                    )
                    db.execute(
                        campaigns.update()
                        .where(campaigns.c.id == campaign_id)
                        .values(
                            display_title=payload.title, revision=row["revision"] + 1
                        )
                    )
                result = campaign_result(
                    owned(db, campaign_id, session["reviewer_id"]),
                    origin=settings.public_origin,
                )
                headers(response, result)
                return result
            if row["state"] == "closed" or row["configuration_locked_at"]:
                raise AccessError(
                    409,
                    "configuration_locked",
                    "Duplicate this campaign to change its configuration",
                )
            row = (
                db.execute(
                    campaigns.update()
                    .where(campaigns.c.id == campaign_id)
                    .values(
                        draft_configuration=payload.configuration.model_dump(
                            mode="json"
                        ),
                        revision=row["revision"] + 1,
                    )
                    .returning(campaigns)
                )
                .mappings()
                .one()
            )
            result = campaign_result(
                owned(db, campaign_id, session["reviewer_id"]),
                origin=settings.public_origin,
            )
        headers(response, result)
        return result

    @router.get(
        "/{campaign_id}/title-history",
        response_model=list[TitleChange],
        operation_id="title_history",
    )
    def title_history(
        campaign_id: UUID, response: Response, session=Depends(require_session)
    ):
        with engine.connect() as db:
            owned(db, campaign_id, session["reviewer_id"])
            rows = (
                db.execute(
                    select(title_changes)
                    .where(title_changes.c.campaign_id == campaign_id)
                    .order_by(title_changes.c.changed_at.desc())
                    .limit(100)
                )
                .mappings()
                .all()
            )
        headers(response)
        return [
            TitleChange(**{k: row[k] for k in TitleChange.model_fields}) for row in rows
        ]

    @router.get(
        "/{campaign_id}/preparation",
        response_model=Preparation,
        operation_id="campaign_preparation",
    )
    def preparation(
        campaign_id: UUID, response: Response, session=Depends(require_session)
    ):
        with engine.connect() as db:
            result = campaign_result(
                owned(db, campaign_id, session["reviewer_id"]),
                db=db,
                origin=settings.public_origin,
            )
        headers(response)
        return Preparation(issues=preparation_issues(result.configuration))

    return router
