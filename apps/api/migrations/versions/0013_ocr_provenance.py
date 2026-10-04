"""Persist per-page OCR origin and explicit failures alongside original bytes."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013_ocr_provenance"
down_revision = "0012_review_revision"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "source_versions",
        sa.Column("extraction_metadata", JSONB(), nullable=False, server_default="{}"),
    )


def downgrade():
    op.drop_column("source_versions", "extraction_metadata")
