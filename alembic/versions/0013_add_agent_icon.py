"""Add persisted agent display icon.

Revision ID: 0013
Revises: 0012
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0013"
down_revision: str | None = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Persist the configured display icon for each agent."""
    with op.batch_alter_table("agents") as batch:
        batch.add_column(
            sa.Column(
                "icon",
                sa.String(length=8),
                nullable=False,
                server_default="",
            )
        )


def downgrade() -> None:
    """Remove persisted agent display icons."""
    with op.batch_alter_table("agents") as batch:
        batch.drop_column("icon")