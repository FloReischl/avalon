"""Record whether automatic chat title generation was attempted.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the persistent automatic-title attempt marker."""
    op.add_column(
        "chats",
        sa.Column(
            "auto_title_attempted",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove the automatic-title attempt marker."""
    op.drop_column("chats", "auto_title_attempted")