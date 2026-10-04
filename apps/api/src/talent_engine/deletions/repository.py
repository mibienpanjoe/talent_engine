from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from talent_engine.database import metadata

cleanup_requests = Table(
    "cleanup_requests",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("application_id", Uuid, unique=True, nullable=False),
    Column("campaign_id", Uuid, ForeignKey("campaigns.id"), nullable=False),
    Column("state", String(20), nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("failures", Integer, nullable=False),
    Column("incident", Boolean, nullable=False),
    Column("storage_keys", JSONB, nullable=False),
    Column("session_ids", JSONB, nullable=False),
    Column("next_attempt_at", DateTime(timezone=True)),
    Column("error_code", String(50)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
)
Index("ix_cleanup_due", cleanup_requests.c.state, cleanup_requests.c.next_attempt_at)
