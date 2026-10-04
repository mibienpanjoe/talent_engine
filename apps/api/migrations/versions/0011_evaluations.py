"""Immutable evaluation bases and application-scoped effective pointer."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0011_evaluations"
down_revision = "0010_sources"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_applications_id_snapshot", "applications", ["id", "snapshot_id"]
    )
    op.create_unique_constraint(
        "uq_runs_id_application_snapshot",
        "analysis_runs",
        ["id", "application_id", "snapshot_id"],
    )
    op.create_foreign_key(
        "fk_run_application_snapshot",
        "analysis_runs",
        "applications",
        ["application_id", "snapshot_id"],
        ["id", "snapshot_id"],
    )
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), unique=True, nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("assessments", JSONB(), nullable=False),
        sa.Column("conditions", JSONB(), nullable=False),
        sa.Column("eligibility", sa.String(30), nullable=False),
        sa.Column("calculation", JSONB(), nullable=False),
        sa.Column("provenance", JSONB(), nullable=False),
        sa.Column("score_numerator", sa.Numeric(100, 0)),
        sa.Column("score_denominator", sa.Numeric(100, 0)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "application_id"),
        sa.ForeignKeyConstraint(
            ["run_id", "application_id", "snapshot_id"],
            [
                "analysis_runs.id",
                "analysis_runs.application_id",
                "analysis_runs.snapshot_id",
            ],
        ),
    )
    op.create_foreign_key(
        "fk_application_effective_evaluation",
        "applications",
        "evaluations",
        ["id", "effective_evaluation_id"],
        ["application_id", "id"],
    )


def downgrade():
    op.drop_constraint(
        "fk_application_effective_evaluation", "applications", type_="foreignkey"
    )
    op.drop_table("evaluations")
    op.drop_constraint(
        "fk_run_application_snapshot", "analysis_runs", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_runs_id_application_snapshot", "analysis_runs", type_="unique"
    )
    op.drop_constraint("uq_applications_id_snapshot", "applications", type_="unique")
