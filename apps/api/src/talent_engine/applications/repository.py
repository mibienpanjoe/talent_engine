from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Table,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from talent_engine.database import metadata

applications = Table(
    "applications",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("campaign_id", Uuid, ForeignKey("campaigns.id"), nullable=False),
    Column("snapshot_id", Uuid, nullable=False),
    Column("mode", String(10), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("contact", JSONB, nullable=False),
    Column("answers", JSONB, nullable=False),
    Column("decision", String(30), nullable=False),
    Column("review_revision", BigInteger, nullable=False),
    Column("processing_generation", BigInteger, nullable=False),
    Column("processing_state", String(30), nullable=False),
    Column("effective_evaluation_id", Uuid),
    Column("deleted_at", DateTime(timezone=True)),
    UniqueConstraint("id", "campaign_id", "snapshot_id"),
    ForeignKeyConstraint(
        ["campaign_id", "snapshot_id"], ["snapshots.campaign_id", "snapshots.id"]
    ),
)
Index("ix_applications_campaign_id_id", applications.c.campaign_id, applications.c.id)
analysis_runs = Table(
    "analysis_runs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("application_id", Uuid, ForeignKey("applications.id"), nullable=False),
    Column("snapshot_id", Uuid, ForeignKey("snapshots.id"), nullable=False),
    Column("reason", String(30), nullable=False),
    Column("state", String(30), nullable=False),
    Column("manifest", JSONB),
    Column("error_code", String(100)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
)
jobs = Table(
    "jobs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("run_id", Uuid, ForeignKey("analysis_runs.id"), unique=True, nullable=False),
    Column("application_id", Uuid, ForeignKey("applications.id"), nullable=False),
    Column("state", String(30), nullable=False),
    Column("lease_generation", BigInteger, nullable=False),
    Column("lease_token", Uuid),
    Column("lease_until", DateTime(timezone=True)),
    Column("worker_id", String(100)),
    Column("next_attempt_at", DateTime(timezone=True)),
    Column("error_code", String(100)),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
Index("ix_jobs_state_lease", jobs.c.state, jobs.c.lease_until)
receipts = Table(
    "receipts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("campaign_id", Uuid, ForeignKey("campaigns.id"), nullable=False),
    Column("mode", String(10), nullable=False),
    Column("key_digest", String(64), nullable=False),
    Column("canonical_version", String(30), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("receipt_ref", String(100), unique=True, nullable=False),
    Column("application_id", Uuid, ForeignKey("applications.id")),
    Column("upload_manifest", JSONB),
    Column("deleted_at", DateTime(timezone=True)),
    UniqueConstraint("campaign_id", "mode", "key_digest"),
)
Index("ix_receipts_expires", receipts.c.expires_at)
