"""Add name to agents table.

Revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0011"
down_revision: str | None = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("name", sa.String(length=200), nullable=True),
    )
    op.execute("UPDATE agents SET name = key")
    with op.batch_alter_table("agents") as batch:
        batch.alter_column("name", existing_type=sa.String(length=200), nullable=False)


def downgrade() -> None:
    op.drop_column("agents", "name")
