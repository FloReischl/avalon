"""Add principals, permissions, grants, and chat authorization identity.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create authorization storage and backfill old chats."""
    op.create_table(
        "principals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("chat_assignable", sa.Boolean(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("principal_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        sa.UniqueConstraint("principal_id"),
    )
    op.create_table(
        "permission_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("context", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("context", "key"),
    )
    op.create_table(
        "principal_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("principal_id", sa.Integer(), nullable=False),
        sa.Column("permission_catalog_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("validity_type", sa.String(length=16), nullable=False),
        sa.Column("default_expiry", sa.Integer(), nullable=False),
        sa.CheckConstraint("validity_type IN ('permanent', 'duration', 'range')", name="ck_principal_permissions_validity_type"),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_catalog_id"], ["permission_catalog.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("principal_id", "permission_catalog_id"),
    )
    op.create_table(
        "permission_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("principal_permission_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime(), nullable=False),
        sa.Column("range", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["principal_permission_id"], ["principal_permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO principals (key, chat_assignable) VALUES ('chat-default', 1)")
    op.add_column("chats", sa.Column("principal_id", sa.Integer(), nullable=True))
    op.add_column("chats", sa.Column("agent_id", sa.Integer(), nullable=True))
    op.execute("UPDATE chats SET principal_id = (SELECT id FROM principals WHERE key = 'chat-default')")
    with op.batch_alter_table("chats") as batch:
        batch.create_foreign_key("fk_chats_principal_id", "principals", ["principal_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_chats_agent_id", "agents", ["agent_id"], ["id"], ondelete="RESTRICT")
        batch.create_check_constraint(
            "ck_chats_exactly_one_authorization_identity",
            "(principal_id IS NOT NULL AND agent_id IS NULL) OR (principal_id IS NULL AND agent_id IS NOT NULL)",
        )


def downgrade() -> None:
    """Remove authorization storage."""
    with op.batch_alter_table("chats") as batch:
        batch.drop_constraint("ck_chats_exactly_one_authorization_identity", type_="check")
        batch.drop_constraint("fk_chats_agent_id", type_="foreignkey")
        batch.drop_constraint("fk_chats_principal_id", type_="foreignkey")
        batch.drop_column("agent_id")
        batch.drop_column("principal_id")
    op.drop_table("permission_grants")
    op.drop_table("principal_permissions")
    op.drop_table("permission_catalog")
    op.drop_table("agents")
    op.drop_table("principals")
