"""Versioned private sources, excerpts and fenced analysis manifests."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010_sources"
down_revision = "0009_title_corrections"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_runs_id_application", "analysis_runs", ["id", "application_id"]
    )
    op.create_table(
        "source_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("question_ids", JSONB(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id")),
        sa.Column("extractor_version", sa.String(100), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("ocr_pages", JSONB(), nullable=False),
        sa.Column("pages", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "application_id"),
    )
    op.create_table(
        "evidence_excerpts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("locator", JSONB(), nullable=False),
        sa.Column("nature", sa.String(30), nullable=False),
        sa.Column("excerpt_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("id", "application_id"),
        sa.ForeignKeyConstraint(
            ["source_version_id", "application_id"],
            ["source_versions.id", "source_versions.application_id"],
        ),
    )
    for name, column, target in [
        ("run_sources", "source_version_id", "source_versions"),
        ("run_evidence", "excerpt_id", "evidence_excerpts"),
    ]:
        op.create_table(
            name,
            sa.Column("run_id", sa.Uuid(), primary_key=True),
            sa.Column(column, sa.Uuid(), primary_key=True),
            sa.Column("application_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(
                ["run_id", "application_id"],
                ["analysis_runs.id", "analysis_runs.application_id"],
            ),
            sa.ForeignKeyConstraint(
                [column, "application_id"], [target + ".id", target + ".application_id"]
            ),
        )


def downgrade():
    for table in (
        "run_evidence",
        "run_sources",
        "evidence_excerpts",
        "source_versions",
    ):
        op.drop_table(table)
    op.drop_constraint("uq_runs_id_application", "analysis_runs", type_="unique")
