"""Application scoped embedding cache, immutable input and model identity."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014_embedding_cache"
down_revision = "0013_ocr_provenance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "embedding_cache",
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("identity", sa.String(64), primary_key=True),
        sa.Column("input_hash", sa.String(64), primary_key=True),
        sa.Column("vector", JSONB(), nullable=False),
    )


def downgrade():
    op.drop_table("embedding_cache")
