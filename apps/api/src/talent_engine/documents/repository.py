from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table, Uuid
from talent_engine.database import metadata

upload_sessions = Table(
    "upload_sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("campaign_id", Uuid, ForeignKey("campaigns.id"), nullable=False),
    Column("snapshot_id", Uuid, ForeignKey("snapshots.id"), nullable=False),
    Column("mode", String(10), nullable=False),
    Column("owner_id", Uuid, ForeignKey("reviewers.id")),
    Column("token_hash", String(64), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)
uploads = Table(
    "uploads",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("session_id", Uuid, ForeignKey("upload_sessions.id"), nullable=False),
    Column("question_id", Uuid, nullable=False),
    Column("application_id", Uuid, ForeignKey("applications.id")),
    Column("filename", String(200), nullable=False),
    Column("media_type", String(50), nullable=False),
    Column("bytes", Integer, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("storage_key", String(100), unique=True, nullable=False),
    Column("state", String(20), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)
Index("ix_uploads_expiry", uploads.c.expires_at)
Index("ix_uploads_application", uploads.c.application_id)
