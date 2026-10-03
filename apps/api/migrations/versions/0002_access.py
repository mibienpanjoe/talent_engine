"""Persist reviewer access, server sessions and atomic login limits."""

import sqlalchemy as sa
from alembic import op

revision = "0002_access"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reviewers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("login", sa.String(200), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "reviewer_id", sa.Uuid(), sa.ForeignKey("reviewers.id"), nullable=False
        ),
        sa.Column("token_digest", sa.String(64), unique=True, nullable=False),
        sa.Column("csrf_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "login_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_limits_expires_at", "login_limits", ["expires_at"])


def downgrade():
    op.drop_table("login_limits")
    op.drop_table("sessions")
    op.drop_table("reviewers")
