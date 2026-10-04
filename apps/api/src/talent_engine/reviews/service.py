import hashlib
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from talent_engine.applications.data import applications
from talent_engine.applications.service import owned_application
from talent_engine.campaigns.data import campaigns, owned, snapshots
from talent_engine.campaigns.lifecycle import now
from talent_engine.errors import AccessError
from talent_engine.evaluations.data import evaluations as bases
from talent_engine.evaluations.engine import calculate
from talent_engine.evaluations.schemas import Assessment, ConditionResult
from talent_engine.sources.data import excerpts, run_evidence, sources

from .data import evaluations
from .repository import events, projections


def locked(db, application_id, owner_id, expectation):
    row = owned_application(db, application_id, owner_id)
    owned(db, row["campaign_id"], owner_id, lock=True)
    row = (
        db.execute(
            select(applications)
            .where(applications.c.id == application_id)
            .with_for_update()
        )
        .mappings()
        .one()
    )
    if row["deleted_at"]:
        raise AccessError(404, "not_found", "Application unavailable")
    if (
        row["review_revision"] != expectation.review_revision
        or row["effective_evaluation_id"] != expectation.effective_evaluation_id
    ):
        raise AccessError(
            409,
            "review_revision_conflict",
            "Reload the recorded review before changing it",
        )
    return row


def bump(db, row, **values):
    db.execute(
        applications.update()
        .where(applications.c.id == row["id"])
        .values(review_revision=row["review_revision"] + 1, **values)
    )
    db.execute(
        campaigns.update()
        .where(campaigns.c.id == row["campaign_id"])
        .values(list_revision=campaigns.c.list_revision + 1)
    )


def record(
    db,
    row,
    owner_id,
    *,
    kind,
    action,
    reason,
    previous,
    value,
    criterion_id=None,
    evaluation_id=None,
    origin_event_id=None,
):
    result = dict(
        id=uuid4(),
        application_id=row["id"],
        evaluation_id=evaluation_id,
        author_id=owner_id,
        created_at=now(db),
        review_revision=row["review_revision"],
        kind=kind,
        criterion_id=criterion_id,
        action=action,
        reason=reason,
        previous=previous,
        value=value,
        origin_event_id=origin_event_id,
    )
    db.execute(events.insert().values(**result))
    return result


def evidence(db, row, base, payload, criterion):
    ids = list(payload.evidence_ids)
    available = (
        db.execute(
            select(excerpts, sources.c.kind, sources.c.question_ids)
            .join(sources, sources.c.id == excerpts.c.source_version_id)
            .where(excerpts.c.id.in_(ids), excerpts.c.application_id == row["id"])
        )
        .mappings()
        .all()
    )
    run_ids = set(
        db.scalars(
            select(run_evidence.c.excerpt_id).where(
                run_evidence.c.run_id == base["run_id"]
            )
        )
    )
    if len(available) != len(ids):
        raise AccessError(
            422, "invalid_review_evidence", "Evidence must belong to this application"
        )
    for item in available:
        if item["nature"] != "human_verification" and (
            item["id"] not in run_ids
            or not set(item["question_ids"]) & set(criterion["source_question_ids"])
        ):
            raise AccessError(
                422,
                "invalid_review_evidence",
                "Evidence must justify the target in this analysis",
            )
    if payload.human_note:
        source_id, excerpt_id = uuid4(), uuid4()
        digest = hashlib.sha256(payload.human_note.encode()).hexdigest()
        db.execute(
            sources.insert().values(
                id=source_id,
                application_id=row["id"],
                source_key="human:" + str(source_id),
                kind="human_note",
                content_hash=digest,
                text_hash=digest,
                question_ids=[],
                upload_id=None,
                extractor_version="human-verification-v1",
                state="available",
                error_code=None,
                ocr_pages=[],
                pages=[],
                extraction_metadata={},
                created_at=now(db),
            )
        )
        db.execute(
            excerpts.insert().values(
                id=excerpt_id,
                application_id=row["id"],
                source_version_id=source_id,
                text=payload.human_note,
                locator=dict(kind="human", start=0, end=len(payload.human_note)),
                nature="human_verification",
                excerpt_hash=digest,
            )
        )
        ids.append(excerpt_id)
    if payload.zero_evidence_quote:
        texts = [item["text"] for item in available] + (
            [payload.human_note] if payload.human_note else []
        )
        if not any(payload.zero_evidence_quote in text for text in texts):
            raise AccessError(
                422,
                "invalid_review_evidence",
                "Zero observation must occur in cited evidence",
            )
    return [str(item) for item in ids]


def project(db, base, policy, assessments, condition_rows):
    calculation = calculate(policy, assessments)
    required = [item["status"] for item in condition_rows if item["required"]]
    eligibility = (
        "condition_unmet"
        if "unmet" in required
        else "needs_review"
        if "unknown" in required
        else "eligible"
        if required
        else "not_applicable"
    )
    score = calculation["score_exact"]
    values = dict(
        evaluation_id=base["id"],
        application_id=base["application_id"],
        assessments=assessments,
        conditions=condition_rows,
        eligibility=eligibility,
        calculation=calculation,
        score_numerator=score["numerator"] if score else None,
        score_denominator=score["denominator"] if score else None,
    )
    db.execute(
        insert(projections)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[projections.c.evaluation_id],
            set_={k: v for k, v in values.items() if k != "evaluation_id"},
        )
    )


def correct(
    db,
    application_id,
    owner_id,
    payload,
    *,
    row=None,
    target_evaluation_id=None,
    origin_event_id=None,
):
    row = row or locked(db, application_id, owner_id, payload)
    evaluation_id = target_evaluation_id or row["effective_evaluation_id"]
    if evaluation_id is None:
        raise AccessError(
            422, "evaluation_required", "An evaluation is required before correction"
        )
    base = (
        db.execute(
            select(bases).where(
                bases.c.id == evaluation_id, bases.c.application_id == application_id
            )
        )
        .mappings()
        .one()
    )
    current = (
        db.execute(select(evaluations).where(evaluations.c.id == evaluation_id))
        .mappings()
        .one()
    )
    snapshot = (
        db.execute(select(snapshots).where(snapshots.c.id == base["snapshot_id"]))
        .mappings()
        .one()
    )
    policy = snapshot["policy_snapshot"]
    field = "assessments" if payload.target_kind == "assessment" else "conditions"
    rows = deepcopy(current[field])
    index = next(
        (
            i
            for i, item in enumerate(rows)
            if item["criterion_id"] == str(payload.criterion_id)
        ),
        None,
    )
    if index is None:
        raise AccessError(
            422, "invalid_review_target", "Target absent from this evaluation"
        )
    previous = rows[index]
    if payload.action == "restore_base":
        value = next(
            item
            for item in base[field]
            if item["criterion_id"] == str(payload.criterion_id)
        )
    else:
        criterion = next(
            item
            for item in snapshot["configuration"]["requirements"]
            if item["id"] == str(payload.criterion_id)
        )
        ids = evidence(db, row, base, payload, criterion)
        value = {
            **previous,
            "status": payload.status,
            "rationale": payload.reason,
            "evidence_ids": ids,
        }
        if field == "assessments":
            value.update(
                level=payload.level,
                zero_evidence_quote=payload.zero_evidence_quote,
                uncertainties=[],
            )
            value = Assessment.model_validate(value).model_dump(mode="json")
        else:
            value = ConditionResult.model_validate(value).model_dump(mode="json")
    rows[index] = value
    project(
        db,
        base,
        policy,
        rows if field == "assessments" else current["assessments"],
        rows if field == "conditions" else current["conditions"],
    )
    event = record(
        db,
        row,
        owner_id,
        kind=payload.target_kind,
        action=payload.action,
        reason=payload.reason,
        previous=previous,
        value=value,
        criterion_id=payload.criterion_id,
        evaluation_id=evaluation_id,
        origin_event_id=origin_event_id,
    )
    if target_evaluation_id is None:
        bump(db, row)
    return event
