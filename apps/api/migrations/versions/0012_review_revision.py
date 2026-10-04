"""Invalidate review pagination when technical state changes."""

import sqlalchemy as sa
from alembic import op

revision = "0012_review_revision"
down_revision = "0011_evaluations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "applications",
        sa.Column(
            "processing_revision", sa.BigInteger(), nullable=False, server_default="1"
        ),
    )


def downgrade():
    op.drop_column("applications", "processing_revision")
