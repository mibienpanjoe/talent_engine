"""Atomically persist submissions, receipts and initial analysis tasks."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_applications"
down_revision = "0004_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=False
        ),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contact", JSONB, nullable=False),
        sa.Column("answers", JSONB, nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("review_revision", sa.BigInteger(), nullable=False),
        sa.Column("processing_generation", sa.BigInteger(), nullable=False),
        sa.Column("processing_state", sa.String(30), nullable=False),
        sa.Column("effective_evaluation_id", sa.Uuid()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("id", "campaign_id", "snapshot_id"),
        sa.ForeignKeyConstraint(
            ["campaign_id", "snapshot_id"], ["snapshots.campaign_id", "snapshots.id"]
        ),
    )
    op.create_index(
        "ix_applications_campaign_id_id", "applications", ["campaign_id", "id"]
    )
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id", sa.Uuid(), sa.ForeignKey("snapshots.id"), nullable=False
        ),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("manifest", JSONB),
        sa.Column("error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("analysis_runs.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("lease_generation", sa.BigInteger(), nullable=False),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("worker_id", sa.String(100)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_state_lease", "jobs", ["state", "lease_until"])
    op.create_table(
        "receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=False
        ),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("key_digest", sa.String(64), nullable=False),
        sa.Column("canonical_version", sa.String(30), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_ref", sa.String(100), unique=True, nullable=False),
        sa.Column("application_id", sa.Uuid(), sa.ForeignKey("applications.id")),
        sa.Column("upload_manifest", JSONB),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("campaign_id", "mode", "key_digest"),
    )
    op.create_index("ix_receipts_expires", "receipts", ["expires_at"])


def downgrade():
    for table in ["receipts", "jobs", "analysis_runs", "applications"]:
        op.drop_table(table)
