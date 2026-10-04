"""Scoped action references; permanent analysis request identities."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016_application_actions"
down_revision = "0015_human_review"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "application_actions",
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id"),
            primary_key=True,
        ),
        sa.Column("route", sa.String(30), primary_key=True),
        sa.Column("key_digest", sa.String(64), primary_key=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("request", JSONB()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_review_history", "review_events", ["application_id", "created_at", "id"]
    )


def downgrade():
    op.drop_index("ix_review_history", table_name="review_events")
    op.drop_table("application_actions")
