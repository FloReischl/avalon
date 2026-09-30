"""Generalize conversation messages and replace workflow placeholders.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: str | None = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Port text history and discard the short-lived workflow placeholder data."""
    op.drop_table("workflow_executions")

    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("kind", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("invocation_id", sa.String(length=36), nullable=True))
    op.execute("UPDATE messages SET kind = 'text'")

    op.create_table(
        "text_messages",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.execute(
        "INSERT INTO text_messages (message_id, role, content) "
        "SELECT id, role, content FROM messages"
    )
    with op.batch_alter_table("messages") as batch:
        batch.alter_column("kind", existing_type=sa.String(length=16), nullable=False)
        batch.drop_column("role")
        batch.drop_column("content")
        batch.create_unique_constraint(
            "uq_messages_chat_id_invocation_id", ["chat_id", "invocation_id"]
        )

    op.create_table(
        "progress_messages",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("messages", sa.Text(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("progress_message_id", sa.Integer(), nullable=False),
        sa.Column("workflow_key", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("runtime_token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint(
            "state IN ('running', 'pending', 'completed', 'failed', 'aborted')",
            name="ck_workflow_executions_state",
        ),
        sa.ForeignKeyConstraint(
            ["progress_message_id"], ["progress_messages.message_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("progress_message_id"),
    )


def downgrade() -> None:
    """Restore the old text-only shape; workflow runtime data is intentionally lost."""
    op.drop_table("workflow_executions")
    op.drop_table("progress_messages")
    with op.batch_alter_table("messages") as batch:
        batch.drop_constraint("uq_messages_chat_id_invocation_id", type_="unique")
        batch.add_column(sa.Column("role", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("content", sa.Text(), nullable=True))
    op.execute(
        "UPDATE messages SET role = (SELECT role FROM text_messages "
        "WHERE text_messages.message_id = messages.id), "
        "content = (SELECT content FROM text_messages "
        "WHERE text_messages.message_id = messages.id)"
    )
    op.drop_table("text_messages")
    with op.batch_alter_table("messages") as batch:
        batch.alter_column("role", existing_type=sa.String(length=16), nullable=False)
        batch.alter_column("content", existing_type=sa.Text(), nullable=False)
        batch.drop_column("invocation_id")
        batch.drop_column("kind")
    # 0008's downgrade owns removal of this legacy table.
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("progress_content", sa.Text(), nullable=True),
        sa.Column("runtime_token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
