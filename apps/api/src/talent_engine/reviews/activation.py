from sqlalchemy import select
from talent_engine.campaigns.data import snapshots
from talent_engine.errors import AccessError
from talent_engine.evaluations.data import evaluations as bases

from .repository import events
from .service import bump, correct, record


def activate(db, row, owner_id, payload):
    target = (
        db.execute(
            select(bases).where(
                bases.c.id == payload.evaluation_id, bases.c.application_id == row["id"]
            )
        )
        .mappings()
        .first()
    )
    current = (
        db.execute(select(bases).where(bases.c.id == row["effective_evaluation_id"]))
        .mappings()
        .first()
    )
    if (
        not target
        or target["id"] == row["effective_evaluation_id"]
        or current
        and target["created_at"] <= current["created_at"]
    ):
        raise AccessError(
            422,
            "invalid_activation",
            "Select a newer completed evaluation of this application",
        )
    old_events = (
        db.execute(
            select(events)
            .where(
                events.c.application_id == row["id"],
                events.c.evaluation_id == row["effective_evaluation_id"],
                events.c.kind.in_(["assessment", "condition"]),
            )
            .order_by(events.c.created_at, events.c.id)
        )
        .mappings()
        .all()
    )
    latest = {(event["kind"], event["criterion_id"]): event for event in old_events}
    if (
        payload.mode == "use_new_base"
        and any(e["action"] == "set" for e in latest.values())
        and not payload.confirm_discard_corrections
    ):
        raise AccessError(
            422,
            "correction_confirmation_required",
            "Confirm that previous corrections leave the effective result",
        )
    if payload.mode == "reapply_selected":
        if (
            current is None
            or target["snapshot_id"] != current["snapshot_id"]
            or target["policy_version"] != current["policy_version"]
        ):
            raise AccessError(
                409, "incompatible_reapplication", "Snapshot and policy must match"
            )
        snapshot = (
            db.execute(select(snapshots).where(snapshots.c.id == target["snapshot_id"]))
            .mappings()
            .one()
        )
        if target["policy_version"] != snapshot["policy_snapshot"]["version"]:
            raise AccessError(
                409,
                "incompatible_reapplication",
                "Policy must match the immutable snapshot",
            )
        for item in payload.corrections:
            original = latest.get(
                (item.correction.target_kind, item.correction.criterion_id)
            )
            if (
                not original
                or original["id"] != item.origin_event_id
                or original["action"] != "set"
            ):
                raise AccessError(
                    422,
                    "invalid_reapplication",
                    "Select the latest active correction for each target",
                )
            correct(
                db,
                row["id"],
                owner_id,
                item.correction,
                row=row,
                target_evaluation_id=target["id"],
                origin_event_id=original["id"],
            )
    result = record(
        db,
        row,
        owner_id,
        kind="activation",
        action=payload.mode,
        reason=payload.reason,
        previous={
            "evaluation_id": str(row["effective_evaluation_id"]) if current else None
        },
        value={
            "evaluation_id": str(target["id"]),
            "mode": payload.mode,
            "origin_event_ids": [str(c.origin_event_id) for c in payload.corrections],
            "confirm_discard_corrections": payload.confirm_discard_corrections,
        },
    )
    bump(db, row, effective_evaluation_id=target["id"])
    return result["id"]
