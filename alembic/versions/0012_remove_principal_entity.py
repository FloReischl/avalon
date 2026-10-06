"""Replace Principal authorization identities with Agents.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0012"
down_revision: str | None = "0011"
branch_labels = None
depends_on = None


def _require_no_rows(sql: str, message: str) -> None:
    """Abort before destructive work when one migration invariant is broken."""
    row = op.get_bind().execute(sa.text(sql)).first()
    if row is not None:
        raise RuntimeError(f"{message}: {tuple(row)}")


def upgrade() -> None:
    """Migrate persisted authorization data to the agent-owned model."""
    _require_no_rows(
        "SELECT permission_grants.id, permission_grants.principal_permission_id "
        "FROM permission_grants LEFT JOIN principal_permissions "
        "ON principal_permissions.id = permission_grants.principal_permission_id "
        "WHERE principal_permissions.id IS NULL LIMIT 1",
        "A PermissionGrant references a missing PrincipalPermission",
    )
    op.execute(
        "INSERT INTO agents (id, key, principal_id, name) "
        "SELECT principals.id, 'default', principals.id, 'Default Agent' "
        "FROM principals WHERE principals.key = 'chat-default' "
        "AND NOT EXISTS (SELECT 1 FROM agents WHERE agents.id = principals.id)"
    )

    op.create_table(
        "permission_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("permission_catalog_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("validity_type", sa.String(length=16), nullable=False),
        sa.Column("default_expiry", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "validity_type IN ('permanent', 'duration', 'range')",
            name="ck_permission_sets_validity_type",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_catalog_id"], ["permission_catalog.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "permission_catalog_id", "scope"),
    )
    op.execute(
        "INSERT INTO permission_sets "
        "(id, agent_id, permission_catalog_id, scope, is_active, validity_type, default_expiry) "
        "SELECT id, principal_id, permission_catalog_id, scope, is_active, validity_type, default_expiry "
        "FROM principal_permissions"
    )

    op.create_table(
        "permission_grants_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("permission_set_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime(), nullable=False),
        sa.Column("range", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["permission_set_id"], ["permission_sets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO permission_grants_new "
        "(id, permission_set_id, valid_from, valid_to, range) "
        "SELECT id, principal_permission_id, valid_from, valid_to, range "
        "FROM permission_grants"
    )
    op.drop_table("permission_grants")
    op.rename_table("permission_grants_new", "permission_grants")

    with op.batch_alter_table("chats") as batch:
        batch.drop_constraint("ck_chats_exactly_one_authorization_identity", type_="check")
    op.execute("UPDATE chats SET agent_id = principal_id WHERE agent_id IS NULL")
    with op.batch_alter_table("chats") as batch:
        batch.drop_constraint("fk_chats_principal_id", type_="foreignkey")
        batch.drop_column("principal_id")
        batch.alter_column("agent_id", existing_type=sa.Integer(), nullable=False)
        batch.create_check_constraint("ck_chats_agent_id_required", "agent_id IS NOT NULL")

    with op.batch_alter_table("agents") as batch:
        batch.drop_column("principal_id")

    op.drop_table("principal_permissions")
    op.drop_table("principals")


def downgrade() -> None:
    """Principal removal is intentionally upgrade-only."""
    raise NotImplementedError("Migration 0012 is upgrade-only.")
