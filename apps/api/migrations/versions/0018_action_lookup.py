"""Index persisted reanalysis receipts without rewriting applied migrations."""

from alembic import op

revision = "0018_action_lookup"
down_revision = "0017_durable_cleanup"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_application_actions_result", "application_actions", ["result_id", "route"]
    )


def downgrade():
    op.drop_index("ix_application_actions_result", table_name="application_actions")
