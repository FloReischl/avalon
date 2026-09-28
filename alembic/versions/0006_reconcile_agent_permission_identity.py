"""Add active state and scope-aware principal permission identity.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: str | None = "0005"
branch_labels = None
depends_on = None


def _create_principal_permissions(
    table_name: str, scope_unique: bool, include_active: bool
) -> None:
    constraints: list[object] = [
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "validity_type IN ('permanent', 'duration', 'range')",
            name="ck_principal_permissions_validity_type",
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_catalog_id"], ["permission_catalog.id"], ondelete="CASCADE"
        ),
    ]
    unique_columns = ["principal_id", "permission_catalog_id"]
    if scope_unique:
        unique_columns.append("scope")
    constraints.append(sa.UniqueConstraint(*unique_columns))
    table_columns: list[object] = [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("principal_id", sa.Integer(), nullable=False),
        sa.Column("permission_catalog_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
    ]
    if include_active:
        table_columns.append(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1")
        )
    table_columns.extend(
        [
            sa.Column("validity_type", sa.String(length=16), nullable=False),
            sa.Column("default_expiry", sa.Integer(), nullable=False),
            *constraints,
        ]
    )
    op.create_table(table_name, *table_columns)


def upgrade() -> None:
    """Rebuild the SQLite table because its existing unique constraint changes."""
    _create_principal_permissions(
        "principal_permissions_new", scope_unique=True, include_active=True
    )
    op.execute(
        "INSERT INTO principal_permissions_new "
        "(id, principal_id, permission_catalog_id, scope, is_active, validity_type, default_expiry) "
        "SELECT id, principal_id, permission_catalog_id, scope, 1, validity_type, default_expiry "
        "FROM principal_permissions"
    )
    op.drop_table("principal_permissions")
    op.rename_table("principal_permissions_new", "principal_permissions")


def downgrade() -> None:
    """Restore the former one-scope-per-catalog constraint."""
    _create_principal_permissions(
        "principal_permissions_old", scope_unique=False, include_active=False
    )
    op.execute(
        "INSERT INTO principal_permissions_old "
        "(id, principal_id, permission_catalog_id, scope, validity_type, default_expiry) "
        "SELECT id, principal_id, permission_catalog_id, scope, validity_type, default_expiry "
        "FROM principal_permissions"
    )
    op.drop_table("principal_permissions")
    op.rename_table("principal_permissions_old", "principal_permissions")
