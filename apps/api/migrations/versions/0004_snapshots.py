"""Immutable campaign publication and test snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_snapshots"
down_revision = "0003_campaigns"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=False
        ),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("configuration", JSONB, nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("policy_snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("reviewers.id"), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("campaign_id", "id"),
        sa.UniqueConstraint("campaign_id", "mode", "version"),
    )
    op.create_foreign_key(
        "fk_campaign_active_snapshot",
        "campaigns",
        "snapshots",
        ["id", "active_snapshot_id"],
        ["campaign_id", "id"],
    )


def downgrade():
    op.drop_constraint("fk_campaign_active_snapshot", "campaigns", type_="foreignkey")
    op.drop_table("snapshots")
