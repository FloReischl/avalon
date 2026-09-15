"""Add persisted context-compression state and message sequences.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels = None
depends_on = None


_EMPTY_CONTEXT = '{"summaries":[],"stars":[]}'


def upgrade() -> None:
    """Add compression state and backfill stable per-chat message sequences."""
    op.add_column(
        "chats",
        sa.Column(
            "compressed_context",
            sa.Text(),
            nullable=False,
            server_default=_EMPTY_CONTEXT,
        ),
    )
    op.add_column(
        "chats",
        sa.Column(
            "compressed_through_seq",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "chats",
        sa.Column(
            "compression_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "chats",
        sa.Column("compression_error_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "chats",
        sa.Column(
            "next_message_seq",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column("messages", sa.Column("seq", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE messages
        SET seq = (
            SELECT COUNT(*)
            FROM messages AS prior
            WHERE prior.chat_id = messages.chat_id
              AND (
                  prior.created_at < messages.created_at
                  OR (
                      prior.created_at = messages.created_at
                      AND prior.id <= messages.id
                  )
              )
        )
        """
    )
    op.execute(
        """
        UPDATE chats
        SET next_message_seq = COALESCE(
            (SELECT MAX(seq) + 1 FROM messages WHERE messages.chat_id = chats.id),
            1
        )
        """
    )

    with op.batch_alter_table("messages") as batch:
        batch.alter_column("seq", existing_type=sa.Integer(), nullable=False)
        batch.create_index("ix_messages_chat_id_seq", ["chat_id", "seq"], unique=True)


def downgrade() -> None:
    """Remove context-compression state and stable message sequences."""
    with op.batch_alter_table("messages") as batch:
        batch.drop_index("ix_messages_chat_id_seq")
        batch.drop_column("seq")

    op.drop_column("chats", "next_message_seq")
    op.drop_column("chats", "compression_error_code")
    op.drop_column("chats", "compression_version")
    op.drop_column("chats", "compressed_through_seq")
    op.drop_column("chats", "compressed_context")
