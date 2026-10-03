"""Persist campaign drafts and scoped mutation receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_campaigns"
down_revision = "0002_access"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("reviewers.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("list_revision", sa.BigInteger(), nullable=False),
        sa.Column("draft_configuration", JSONB, nullable=False),
        sa.Column("active_snapshot_id", sa.Uuid()),
        sa.Column("configuration_locked_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("public_token", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('draft','published','closed')"),
        sa.CheckConstraint("revision BETWEEN 1 AND 9007199254740991"),
    )
    op.create_index("ix_campaigns_owner_id_id", "campaigns", ["owner_id", "id"])
    op.create_table(
        "mutation_receipts",
        sa.Column("key_digest", sa.String(64), primary_key=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("mutation_receipts")
    op.drop_table("campaigns")
