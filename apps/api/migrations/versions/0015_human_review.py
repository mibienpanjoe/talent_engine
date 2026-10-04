"""Immutable review events and transactional effective projections."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0015_human_review"
down_revision = "0014_embedding_cache"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_projections",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        *[
            sa.Column(name, JSONB(), nullable=False)
            for name in ("assessments", "conditions", "calculation")
        ],
        sa.Column("eligibility", sa.String(30), nullable=False),
        sa.Column("score_numerator", sa.Numeric(100, 0)),
        sa.Column("score_denominator", sa.Numeric(100, 0)),
        sa.ForeignKeyConstraint(
            ["evaluation_id", "application_id"],
            ["evaluations.id", "evaluations.application_id"],
        ),
    )
    op.create_table(
        "review_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column("evaluation_id", sa.Uuid()),
        sa.Column(
            "author_id", sa.Uuid(), sa.ForeignKey("reviewers.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_revision", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("criterion_id", sa.Uuid()),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("previous", JSONB(), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.Column("origin_event_id", sa.Uuid(), sa.ForeignKey("review_events.id")),
        sa.ForeignKeyConstraint(
            ["evaluation_id", "application_id"],
            ["evaluations.id", "evaluations.application_id"],
        ),
    )


def downgrade():
    op.drop_table("review_events")
    op.drop_table("review_projections")
