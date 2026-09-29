"""Add immutable file attachments for messages.

Revision ID: 0007
Revises: 0006
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: str | None = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=300), nullable=False),
        sa.Column("original_file_name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_name"),
    )
    op.create_table(
        "message_attachments",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("attachment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "attachment_id"),
    )


def downgrade() -> None:
    op.drop_table("message_attachments")
    op.drop_table("attachments")
