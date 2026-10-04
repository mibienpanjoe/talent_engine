"""Durable purge records, minimized receipt tombstones and in-flight files."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0017_durable_cleanup"
down_revision = "0016_application_actions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cleanup_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("application_id", sa.Uuid(), unique=True, nullable=False),
        sa.Column(
            "campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=False
        ),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("incident", sa.Boolean(), nullable=False),
        sa.Column("storage_keys", JSONB(), nullable=False),
        sa.Column("session_ids", JSONB(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_cleanup_due", "cleanup_requests", ["state", "next_attempt_at"])
    for name in ("canonical_version", "received_at", "receipt_ref"):
        op.alter_column("receipts", name, nullable=True)
    op.add_column("upload_transfers", sa.Column("storage_key", sa.String(100)))


def downgrade():
    op.drop_column("upload_transfers", "storage_key")
    # Deleted tombstones cannot become full receipt records again.
    op.execute("DELETE FROM receipts WHERE deleted_at IS NOT NULL")
    for name in ("canonical_version", "received_at", "receipt_ref"):
        op.alter_column("receipts", name, nullable=False)
    op.drop_index("ix_cleanup_due", table_name="cleanup_requests")
    op.drop_table("cleanup_requests")
