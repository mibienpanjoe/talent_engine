"""Editorial display title with immutable submitted snapshots and audit."""

import sqlalchemy as sa
from alembic import op

revision = "0009_title_corrections"
down_revision = "0008_reception_limits"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("campaigns", sa.Column("display_title", sa.String(200)))
    op.create_table(
        "campaign_title_changes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=False
        ),
        sa.Column("previous_title", sa.String(200), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "author_id", sa.Uuid(), sa.ForeignKey("reviewers.id"), nullable=False
        ),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_title_changes_campaign", "campaign_title_changes", ["campaign_id"]
    )


def downgrade():
    op.drop_table("campaign_title_changes")
    op.drop_column("campaigns", "display_title")
