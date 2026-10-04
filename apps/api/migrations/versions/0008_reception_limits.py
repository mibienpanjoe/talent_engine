"""Public quotas shared across API instances and expiring upload slots."""

import sqlalchemy as sa
from alembic import op

revision = "0008_reception_limits"
down_revision = "0007_worker"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "public_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("requests", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_public_limits_expiry", "public_limits", ["expires_at"])
    op.create_table(
        "upload_transfers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id", sa.Uuid(), sa.ForeignKey("upload_sessions.id"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_upload_transfers_session", "upload_transfers", ["session_id"])


def downgrade():
    op.drop_table("upload_transfers")
    op.drop_table("public_limits")
