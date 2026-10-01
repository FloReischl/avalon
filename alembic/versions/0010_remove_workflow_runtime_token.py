"""Remove the workflow-specific runtime bearer token.

Revision ID: 0010
Revises: 0009
"""

from alembic import op


revision: str = "0010"
down_revision: str | None = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_executions") as batch:
        batch.drop_column("runtime_token_hash")


def downgrade() -> None:
    import sqlalchemy as sa

    with op.batch_alter_table("workflow_executions") as batch:
        batch.add_column(sa.Column("runtime_token_hash", sa.String(length=64), nullable=True))
