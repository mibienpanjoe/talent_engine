import hashlib
import hmac
import secrets
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from talent_engine.campaigns.data import campaigns, owned, snapshots
from talent_engine.campaigns.lifecycle import active_snapshot, now
from talent_engine.errors import AccessError

from .repository import analysis_runs, applications, jobs, receipts
from .schemas import Receipt
from .validation import canonical_payload, validate_answers


def receive(db, settings, campaign, payload, key, mode="real"):
    if not key or len(key) < 22 or len(key) > 200:
        raise AccessError(
            422, "invalid_idempotency_key", "Use a random Idempotency-Key"
        )
    digest = hmac.new(
        settings.csrf_secret.get_secret_value().encode(),
        ("submission-v1:" + key).encode(),
        hashlib.sha256,
    ).hexdigest()
    from talent_engine.documents.service import attach_files as attach_documents
    from talent_engine.documents.service import validate_uploads

    # The caller has acquired the campaign row before this second receipt lookup.
    previous = (
        db.execute(
            select(receipts).where(
                (receipts.c.campaign_id == campaign["id"])
                & (receipts.c.mode == mode)
                & (receipts.c.key_digest == digest)
            )
        )
        .mappings()
        .first()
    )
    if previous and previous["expires_at"] > now(db):
        if previous["deleted_at"]:
            raise AccessError(410, "submission_deleted", "This submission was deleted")
        if any(a.kind == "file" and a.value for a in payload.answers):
            original_app = (
                db.execute(
                    select(applications).where(
                        applications.c.id == previous["application_id"]
                    )
                )
                .mappings()
                .one()
            )
            original_snapshot = (
                db.execute(
                    select(snapshots).where(
                        snapshots.c.id == original_app["snapshot_id"]
                    )
                )
                .mappings()
                .one()
            )
            replay_manifest, _ = validate_uploads(
                db,
                settings,
                campaign,
                original_snapshot,
                payload,
                replay_original=previous["upload_manifest"],
            )
        else:
            replay_manifest = {}
        fingerprint = canonical_payload(payload, replay_manifest)
        if fingerprint != previous["payload_hash"]:
            raise AccessError(
                409,
                "idempotency_conflict",
                "Key already used with different application data",
            )
        return Receipt(
            receipt_ref=previous["receipt_ref"], received_at=previous["received_at"]
        ), False
    if previous:
        db.execute(receipts.delete().where(receipts.c.id == previous["id"]))
    if mode == "real":
        snapshot = active_snapshot(db, campaign)
        if payload.snapshot_id != snapshot["id"]:
            raise AccessError(
                409, "snapshot_conflict", "The form changed; reload before submitting"
            )
        if campaign["state"] != "published":
            raise AccessError(
                409, "campaign_closed", "Campaign no longer accepts applications"
            )
    else:
        snapshot = (
            db.execute(
                select(snapshots).where(
                    (snapshots.c.id == payload.snapshot_id)
                    & (snapshots.c.campaign_id == campaign["id"])
                    & (snapshots.c.mode == "test")
                )
            )
            .mappings()
            .first()
        )
        if not snapshot:
            raise AccessError(404, "not_found", "Test snapshot unavailable")
    decision_time = now(db)
    from talent_engine.campaigns.schemas import DraftConfiguration

    config = DraftConfiguration.model_validate(snapshot["configuration"])
    if mode == "real" and config.deadline and decision_time >= config.deadline:
        raise AccessError(409, "campaign_closed", "Campaign deadline passed")
    if (
        campaign["revision"] >= 9007199254740991
        or campaign["list_revision"] >= 9007199254740991
    ):
        raise AccessError(409, "revision_exhausted", "Campaign exhausted")
    validate_answers(payload, snapshot["configuration"])
    app_id = uuid4()
    db.execute(
        applications.insert().values(
            id=app_id,
            campaign_id=campaign["id"],
            snapshot_id=snapshot["id"],
            mode=mode,
            received_at=decision_time,
            contact=payload.contact.model_dump(mode="json"),
            answers=[a.model_dump(mode="json") for a in payload.answers],
            decision="to_review",
            review_revision=1,
            processing_generation=1,
            processing_state="queued",
        )
    )
    manifest = attach_documents(db, settings, campaign, snapshot, payload, app_id)
    fingerprint = canonical_payload(payload, manifest)
    run = uuid4()
    db.execute(
        analysis_runs.insert().values(
            id=run,
            application_id=app_id,
            snapshot_id=snapshot["id"],
            reason="initial",
            state="queued",
            created_at=decision_time,
        )
    )
    db.execute(
        jobs.insert().values(
            id=uuid4(),
            run_id=run,
            application_id=app_id,
            state="queued",
            lease_generation=0,
            created_at=decision_time,
        )
    )
    ref = secrets.token_urlsafe(24)
    db.execute(
        receipts.insert().values(
            id=uuid4(),
            campaign_id=campaign["id"],
            mode=mode,
            key_digest=digest,
            canonical_version="submission-v1",
            payload_hash=fingerprint,
            received_at=decision_time,
            expires_at=decision_time + timedelta(days=90),
            receipt_ref=ref,
            application_id=app_id,
            upload_manifest=manifest,
        )
    )
    if mode == "real":
        db.execute(
            campaigns.update()
            .where(campaigns.c.id == campaign["id"])
            .values(
                configuration_locked_at=campaign["configuration_locked_at"]
                or decision_time,
                revision=campaign["revision"] + 1,
                list_revision=campaign["list_revision"] + 1,
            )
        )
    return Receipt(receipt_ref=ref, received_at=decision_time), True


def owned_application(db, application_id, owner_id):
    row = (
        db.execute(
            select(applications).where(
                (applications.c.id == application_id)
                & (applications.c.deleted_at.is_(None))
                & (applications.c.received_at > now(db) - timedelta(days=90))
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise AccessError(404, "not_found", "Application unavailable")
    owned(db, row["campaign_id"], owner_id)
    return row
