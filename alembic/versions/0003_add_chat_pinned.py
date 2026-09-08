"""Add persistent pinned state to chats.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the persistent pinned state."""
    op.add_column(
        "chats",
        sa.Column(
            "pinned",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove the persistent pinned state."""
    op.drop_column("chats", "pinned")
