"""Scoped action receipts; retries are recognized before new review preconditions."""

import hashlib
import hmac
import json
from datetime import timedelta

from sqlalchemy import select
from talent_engine.applications.data import applications
from talent_engine.applications.service import owned_application
from talent_engine.campaigns.data import owned
from talent_engine.campaigns.lifecycle import now
from talent_engine.errors import AccessError

from .repository import application_actions


def lock_application(db, application_id, owner_id):
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
    return row


def check_header(payload, if_match):
    if if_match is None:
        raise AccessError(428, "precondition_required", "If-Match required")
    if if_match != f'"{payload.review_revision}"':
        raise AccessError(
            409, "review_revision_conflict", "Header and review expectation disagree"
        )


def action(
    db,
    settings,
    application_id,
    owner_id,
    route,
    payload,
    key,
    if_match,
    callback,
    *,
    permanent=False,
):
    row = lock_application(db, application_id, owner_id)
    if not key or not 22 <= len(key) <= 200:
        raise AccessError(
            422,
            "invalid_idempotency_key",
            "Idempotency-Key must contain at least 128 random bits",
        )
    scope = json.dumps(
        [str(owner_id), str(application_id), route, key], separators=(",", ":")
    )
    digest = hmac.new(
        settings.csrf_secret.get_secret_value().encode(), scope.encode(), hashlib.sha256
    ).hexdigest()
    fingerprint = hashlib.sha256(
        json.dumps(
            {"body": payload.model_dump(mode="json"), "if_match": if_match},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    match = (
        (application_actions.c.application_id == application_id)
        & (application_actions.c.route == route)
        & (application_actions.c.key_digest == digest)
    )
    cached = db.execute(select(application_actions).where(match)).mappings().first()
    if cached and cached["expires_at"] is not None and cached["expires_at"] <= now(db):
        db.execute(application_actions.delete().where(match))
        cached = None
    if cached:
        if cached["payload_hash"] != fingerprint:
            raise AccessError(
                409,
                "idempotency_conflict",
                "This key already identifies a different action",
            )
        return cached["result_id"], False
    check_header(payload, if_match)
    if (
        row["review_revision"] != payload.review_revision
        or row["effective_evaluation_id"] != payload.effective_evaluation_id
    ):
        raise AccessError(409, "review_revision_conflict", "Reload the recorded review")
    result = callback(row)
    db.execute(
        application_actions.insert().values(
            application_id=application_id,
            route=route,
            key_digest=digest,
            payload_hash=fingerprint,
            result_id=result,
            request=payload.model_dump(mode="json") if permanent else None,
            expires_at=None if permanent else now(db) + timedelta(hours=24),
        )
    )
    return result, True
