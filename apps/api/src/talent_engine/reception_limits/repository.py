from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table, Uuid
from talent_engine.database import metadata

public_limits = Table(
    "public_limits",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("requests", Integer, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)
Index("ix_public_limits_expiry", public_limits.c.expires_at)
transfers = Table(
    "upload_transfers",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("session_id", Uuid, ForeignKey("upload_sessions.id"), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)
Index("ix_upload_transfers_session", transfers.c.session_id)
