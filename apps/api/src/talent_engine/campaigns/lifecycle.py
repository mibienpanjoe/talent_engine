from copy import deepcopy
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Response
from pydantic import Field
from sqlalchemy import (
    func,
    select,
)
from talent_engine.access import build_access_guards
from talent_engine.errors import AccessError, Error

from .policy import compile_policy
from .repository import (
    campaign_result,
    campaigns,
    check_revision,
    idempotent,
    insert_campaign,
    owned,
    snapshots,
)
from .schemas import Campaign, DraftConfiguration, Model, Question


class EmptyInput(Model):
    pass


class DuplicationInput(Model):
    source: Literal["draft", "published"]


class PublishedSnapshot(Model):
    id: UUID
    campaign_id: UUID
    mode: Literal["real", "test"]
    version: int
    configuration: DraftConfiguration
    policy_version: str
    created_at: datetime


class FormLimits(Model):
    max_files: int = 5
    max_file_bytes: int = 10485760
    max_total_bytes: int = 31457280
    max_links: int = 5
    accepted_media_types: list[str] = Field(
        default_factory=lambda: ["application/pdf", "image/png", "image/jpeg"]
    )


class PublicForm(Model):
    snapshot_id: UUID
    state: Literal["open", "closed"]
    title: str
    description: str
    type: Literal["training", "recruitment"]
    domain: str
    target_level: str
    deadline: datetime | None
    questions: list[Question]
    limits: FormLimits = Field(default_factory=FormLimits)
    processing_notice: str = (
        "Vos réponses sont enregistrées pour la revue de cette "
        "campagne. Leur analyse peut prendre du temps ; la décision "
        "appartient au responsable. Ne transmettez que les "
        "informations nécessaires."
    )


class TestForm(PublicForm):
    campaign_id: UUID


class Rational(Model):
    numerator: str
    denominator: str


class PolicyCriterion(Model):
    criterion_id: UUID
    family: str
    weight: Rational | None
    rubric_version: str | None
    levels: list[str]
    required_skill_threshold: int | None


class PolicyExplanation(Model):
    snapshot_id: UUID
    policy_version: str
    notice: str
    criteria: list[PolicyCriterion]


def now(db):
    return db.scalar(select(func.clock_timestamp()))


def snapshot_result(row):
    return PublishedSnapshot(**{k: row[k] for k in PublishedSnapshot.model_fields})


def active_snapshot(db, campaign):
    if not campaign["active_snapshot_id"]:
        raise AccessError(409, "not_published", "Publish a campaign first")
    return (
        db.execute(
            select(snapshots).where(
                (snapshots.c.id == campaign["active_snapshot_id"])
                & (snapshots.c.campaign_id == campaign["id"])
            )
        )
        .mappings()
        .one()
    )


def public_campaign(db, token, *, lock=False):
    query = select(campaigns).where(
        (campaigns.c.public_token == token)
        & (campaigns.c.active_snapshot_id.is_not(None))
    )
    if lock:
        query = query.with_for_update()
    row = db.execute(query).mappings().first()
    if not row:
        raise AccessError(404, "not_found", "Campaign unavailable")
    return row


def form_result(db, campaign, snapshot):
    config = DraftConfiguration.model_validate(snapshot["configuration"])
    state = (
        "closed"
        if campaign["state"] == "closed"
        or (config.deadline and now(db) >= config.deadline)
        else "open"
    )
    return PublicForm(
        snapshot_id=snapshot["id"],
        state=state,
        title=config.title,
        description=config.description,
        type=config.type,
        domain=config.domain,
        target_level=config.target_level,
        deadline=config.deadline,
        questions=sorted(config.questions, key=lambda q: q.position),
    )


def create_snapshot(db, campaign, config, owner, mode):
    draft = DraftConfiguration.model_validate(config)
    policy = compile_policy(draft)
    created = now(db)
    if mode == "real" and draft.deadline and draft.deadline <= created:
        raise AccessError(422, "deadline_passed", "Review campaign deadline")
    version = (
        db.scalar(
            select(func.max(snapshots.c.version)).where(
                (snapshots.c.campaign_id == campaign["id"]) & (snapshots.c.mode == mode)
            )
        )
        or 0
    ) + 1
    return (
        db.execute(
            snapshots.insert()
            .values(
                id=uuid4(),
                campaign_id=campaign["id"],
                mode=mode,
                version=version,
                configuration=config,
                policy_version=policy["version"],
                policy_snapshot=policy,
                created_at=created,
                created_by=owner,
                published_at=created if mode == "real" else None,
            )
            .returning(snapshots)
        )
        .mappings()
        .one()
    )


def build_lifecycle_router(engine, settings):
    _, read_guard, write_guard = build_access_guards(engine, settings)
    router = APIRouter(
        prefix="/api/v1",
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

    def headers(response, revision=None):
        response.headers["Cache-Control"] = "no-store"
        if revision:
            response.headers["ETag"] = f'"{revision}"'

    @router.post(
        "/campaigns/{campaign_id}/publications",
        response_model=PublishedSnapshot,
        status_code=201,
        operation_id="publish_campaign",
    )
    def publish(
        campaign_id: UUID,
        payload: EmptyInput,
        response: Response,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            # Replays are recognized before checking a revision advanced by the action.
            def action():
                campaign = owned(db, campaign_id, session["reviewer_id"], lock=True)
                check_revision(campaign, if_match)
                if campaign["state"] == "closed" or campaign["configuration_locked_at"]:
                    raise AccessError(
                        409,
                        "configuration_locked",
                        "Duplicate campaign to change its configuration",
                    )
                row = create_snapshot(
                    db,
                    campaign,
                    campaign["draft_configuration"],
                    session["reviewer_id"],
                    "real",
                )
                db.execute(
                    campaigns.update()
                    .where(campaigns.c.id == campaign_id)
                    .values(
                        state="published",
                        revision=campaign["revision"] + 1,
                        active_snapshot_id=row["id"],
                    )
                )
                return snapshot_result(row)

            result = idempotent(
                db,
                settings,
                session["reviewer_id"],
                f"publish:{campaign_id}",
                idempotency_key,
                {"body": payload.model_dump(mode="json"), "if_match": if_match},
                action,
                result_model=PublishedSnapshot,
            )
            owned(db, campaign_id, session["reviewer_id"])
            revision = int(if_match.strip('"')) + 1
        headers(response, revision)
        return result

    @router.post(
        "/campaigns/{campaign_id}/closures",
        response_model=Campaign,
        operation_id="close_campaign",
    )
    def close(
        campaign_id: UUID,
        payload: EmptyInput,
        response: Response,
        if_match: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            campaign = owned(db, campaign_id, session["reviewer_id"], lock=True)
            check_revision(campaign, if_match)
            if campaign["state"] != "published":
                raise AccessError(
                    409, "invalid_transition", "Only a published campaign can be closed"
                )
            (
                db.execute(
                    campaigns.update()
                    .where(campaigns.c.id == campaign_id)
                    .values(
                        state="closed",
                        revision=campaign["revision"] + 1,
                        closed_at=now(db),
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
        headers(response, result.revision)
        return result

    @router.post(
        "/campaigns/{campaign_id}/duplicates",
        response_model=Campaign,
        status_code=201,
        operation_id="duplicate_campaign",
    )
    def duplicate(
        campaign_id: UUID,
        payload: DuplicationInput,
        response: Response,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:

            def action():
                campaign = owned(db, campaign_id, session["reviewer_id"], lock=True)
                check_revision(campaign, if_match)
                config = deepcopy(
                    campaign["draft_configuration"]
                    if payload.source == "draft"
                    else active_snapshot(db, campaign)["configuration"]
                )
                ids = {q["id"]: str(uuid4()) for q in config["questions"]}
                options = {
                    o["id"]: str(uuid4())
                    for q in config["questions"]
                    for o in q.get("options", [])
                }
                for q in config["questions"]:
                    q["id"] = ids[q["id"]]
                    for o in q.get("options", []):
                        o["id"] = options[o["id"]]
                for r in config["requirements"]:
                    r["id"] = str(uuid4())
                    r["source_question_ids"] = [
                        ids[x] for x in r["source_question_ids"]
                    ]
                    if r.get("condition_rule"):
                        rule = r["condition_rule"]
                        rule["question_id"] = ids[rule["question_id"]]
                        if rule["kind"] == "available_slots":
                            rule["option_ids"] = [
                                options[x] for x in rule["option_ids"]
                            ]
                config["deadline"] = None
                return insert_campaign(db, session["reviewer_id"], config)

            result = idempotent(
                db,
                settings,
                session["reviewer_id"],
                f"duplicate:{campaign_id}",
                idempotency_key,
                {"body": payload.model_dump(mode="json"), "if_match": if_match},
                action,
            )
        headers(response, result.revision)
        return result

    @router.post(
        "/campaigns/{campaign_id}/test-snapshots",
        response_model=PublishedSnapshot,
        status_code=201,
        operation_id="create_test_snapshot",
    )
    def test_snapshot(
        campaign_id: UUID,
        payload: DuplicationInput,
        response: Response,
        if_match: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        session=Depends(write_guard),
    ):
        with engine.begin() as db:

            def action():
                campaign = owned(db, campaign_id, session["reviewer_id"], lock=True)
                check_revision(campaign, if_match)
                config = (
                    campaign["draft_configuration"]
                    if payload.source == "draft"
                    else active_snapshot(db, campaign)["configuration"]
                )
                return snapshot_result(
                    create_snapshot(
                        db, campaign, config, session["reviewer_id"], "test"
                    )
                )

            result = idempotent(
                db,
                settings,
                session["reviewer_id"],
                f"test_snapshot:{campaign_id}",
                idempotency_key,
                {"body": payload.model_dump(mode="json"), "if_match": if_match},
                action,
                result_model=PublishedSnapshot,
            )
        headers(response)
        return result

    @router.get(
        "/public/campaigns/{public_token}",
        response_model=PublicForm,
        operation_id="public_form",
    )
    def public_form(public_token: str, response: Response):
        if len(public_token) > 64:
            raise AccessError(404, "not_found", "Campaign unavailable")
        with engine.connect() as db:
            campaign = public_campaign(db, public_token)
            result = form_result(db, campaign, active_snapshot(db, campaign))
        headers(response)
        return result

    @router.get(
        "/test-snapshots/{snapshot_id}",
        response_model=TestForm,
        operation_id="test_form",
    )
    def test_form(snapshot_id: UUID, response: Response, session=Depends(read_guard)):
        with engine.connect() as db:
            row = (
                db.execute(
                    select(snapshots).where(
                        (snapshots.c.id == snapshot_id) & (snapshots.c.mode == "test")
                    )
                )
                .mappings()
                .first()
            )
            if not row:
                raise AccessError(404, "not_found", "Snapshot unavailable")
            campaign = owned(db, row["campaign_id"], session["reviewer_id"])
            result = form_result(db, campaign, row)
        headers(response)
        return TestForm(**result.model_dump(), campaign_id=campaign["id"])

    @router.get(
        "/snapshots/{snapshot_id}/policy",
        response_model=PolicyExplanation,
        operation_id="read_policy",
    )
    def policy(snapshot_id: UUID, response: Response, session=Depends(read_guard)):
        with engine.connect() as db:
            row = (
                db.execute(select(snapshots).where(snapshots.c.id == snapshot_id))
                .mappings()
                .first()
            )
            if not row:
                raise AccessError(404, "not_found", "Policy unavailable")
            owned(db, row["campaign_id"], session["reviewer_id"])
            criteria = [
                PolicyCriterion(**{key: c[key] for key in PolicyCriterion.model_fields})
                for c in row["policy_snapshot"]["criteria"]
            ]
        headers(response)
        return PolicyExplanation(
            snapshot_id=snapshot_id,
            policy_version=row["policy_version"],
            notice=(
                "Barèmes de démonstration fictifs, non calibrés sur des personnes "
                "réelles. Une information manquante reste inconnue ; "
                "aucune décision automatique."
            ),
            criteria=criteria,
        )

    return router
