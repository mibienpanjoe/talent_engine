"""Persistent worker checkpoints, budgets and one active task per application."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_worker"
down_revision = "0006_uploads"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "jobs",
        sa.Column(
            "application_generation",
            sa.BigInteger(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_index(
        "uq_jobs_active_application",
        "jobs",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('queued', 'running', 'waiting')"),
    )
    op.create_table(
        "analysis_steps",
        sa.Column(
            "run_id", sa.Uuid(), sa.ForeignKey("analysis_runs.id"), primary_key=True
        ),
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("active_seconds", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("input_hash", sa.String(64)),
        sa.Column("output", JSONB),
        sa.Column("error_code", sa.String(100)),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_step_attempts"),
        sa.CheckConstraint("active_seconds >= 0", name="ck_step_active_seconds"),
    )


def downgrade():
    op.drop_table("analysis_steps")
    op.drop_index("uq_jobs_active_application", table_name="jobs")
    op.drop_column("jobs", "application_generation")
