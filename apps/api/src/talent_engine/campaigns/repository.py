import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Uuid,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from talent_engine.access import metadata
from talent_engine.errors import AccessError

from .schemas import Campaign

campaigns = Table(
    "campaigns",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("owner_id", Uuid, ForeignKey("reviewers.id"), nullable=False),
    Column("state", String(20), nullable=False),
    Column("revision", BigInteger, nullable=False),
    Column("list_revision", BigInteger, nullable=False),
    Column("draft_configuration", JSONB, nullable=False),
    Column("active_snapshot_id", Uuid),
    Column("configuration_locked_at", DateTime(timezone=True)),
    Column("closed_at", DateTime(timezone=True)),
    Column("public_token", String(64), unique=True, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("state IN ('draft','published','closed')"),
    CheckConstraint("revision BETWEEN 1 AND 9007199254740991"),
)
Index("ix_campaigns_owner_id_id", campaigns.c.owner_id, campaigns.c.id)
mutation_receipts = Table(
    "mutation_receipts",
    metadata,
    Column("key_digest", String(64), primary_key=True),
    Column("payload_hash", String(64), nullable=False),
    Column("result", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)


def campaign_result(row):
    return Campaign(
        id=row["id"],
        state=row["state"],
        revision=row["revision"],
        configuration=row["draft_configuration"],
        active_snapshot_id=row["active_snapshot_id"],
        configuration_locked_at=row["configuration_locked_at"],
        has_unpublished_changes=False,
        created_at=row["created_at"],
        public_url=None,
    )


def owned(db, campaign_id, owner_id, *, lock=False):
    query = select(campaigns).where(
        (campaigns.c.id == campaign_id) & (campaigns.c.owner_id == owner_id)
    )
    if lock:
        query = query.with_for_update()
    row = db.execute(query).mappings().first()
    if not row:
        raise AccessError(404, "not_found", "Campaign unavailable")
    return row


def check_revision(row, header):
    if header is None:
        raise AccessError(428, "precondition_required", "If-Match required")
    if header != f'"{row["revision"]}"':
        raise AccessError(
            409, "revision_conflict", "Campaign changed; reload before saving"
        )
    if row["revision"] >= 9007199254740991:
        raise AccessError(409, "revision_exhausted", "Duplicate campaign")


def idempotent(db, settings, owner_id, route, key, payload, action):
    if not key or len(key) < 22 or len(key) > 200:
        raise AccessError(
            422,
            "invalid_idempotency_key",
            "Idempotency-Key must contain at least 128 random bits",
        )
    scope = json.dumps([str(owner_id), route, key], separators=(",", ":"))
    digest = hmac.new(
        settings.csrf_secret.get_secret_value().encode(), scope.encode(), hashlib.sha256
    ).hexdigest()
    fingerprint = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": int(digest[:16], 16) - (1 << 63)},
    )
    now = datetime.now(timezone.utc)
    previous = (
        db.execute(
            select(mutation_receipts).where(mutation_receipts.c.key_digest == digest)
        )
        .mappings()
        .first()
    )
    if previous and previous["expires_at"] > now:
        if previous["payload_hash"] != fingerprint:
            raise AccessError(
                409, "idempotency_conflict", "Key already used with different data"
            )
        return Campaign.model_validate(previous["result"])
    if previous:
        db.execute(
            mutation_receipts.delete().where(mutation_receipts.c.key_digest == digest)
        )
    result = action()
    db.execute(
        mutation_receipts.insert().values(
            key_digest=digest,
            payload_hash=fingerprint,
            result=result.model_dump(mode="json"),
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
    )
    return result


def insert_campaign(db, owner_id, configuration):
    import secrets

    row = (
        db.execute(
            campaigns.insert()
            .values(
                id=uuid4(),
                owner_id=owner_id,
                state="draft",
                revision=1,
                list_revision=1,
                draft_configuration=configuration,
                public_token=secrets.token_urlsafe(32),
                created_at=datetime.now(timezone.utc),
            )
            .returning(campaigns)
        )
        .mappings()
        .one()
    )
    return campaign_result(row)
