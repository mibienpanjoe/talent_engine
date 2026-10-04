"""Private upload capabilities and ready document references."""

import sqlalchemy as sa
from alembic import op

revision = "0006_uploads"
down_revision = "0005_applications"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=False
        ),
        sa.Column(
            "snapshot_id", sa.Uuid(), sa.ForeignKey("snapshots.id"), nullable=False
        ),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("reviewers.id")),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id", sa.Uuid(), sa.ForeignKey("upload_sessions.id"), nullable=False
        ),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), sa.ForeignKey("applications.id")),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("media_type", sa.String(50), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(100), unique=True, nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_uploads_expiry", "uploads", ["expires_at"])
    op.create_index("ix_uploads_application", "uploads", ["application_id"])


def downgrade():
    op.drop_table("uploads")
    op.drop_table("upload_sessions")
