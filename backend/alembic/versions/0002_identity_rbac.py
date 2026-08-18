"""Identity, organization, RBAC, and data-scope foundation.

Revision ID: 0002_identity_rbac
Revises: 0001_baseline
Create Date: 2026-08-18
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_identity_rbac"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iam_organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_iam_organizations_status")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["iam_organizations.id"],
            name=op.f("fk_iam_organizations_parent_id_iam_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_iam_organizations")),
        sa.UniqueConstraint("code", name=op.f("uq_iam_organizations_code")),
    )
    op.create_index("ix_iam_organizations_parent_id", "iam_organizations", ["parent_id"])
    op.create_table(
        "iam_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("login_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_iam_users_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_iam_users")),
        sa.UniqueConstraint("email", name=op.f("uq_iam_users_email")),
        sa.UniqueConstraint("login_name", name=op.f("uq_iam_users_login_name")),
    )
    op.create_table(
        "iam_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_iam_memberships_status")
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["iam_organizations.id"],
            name=op.f("fk_iam_memberships_department_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_iam_memberships_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["iam_users.id"], name=op.f("fk_iam_memberships_user_id_iam_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_iam_memberships")),
        sa.UniqueConstraint("user_id", "organization_id", name=op.f("uq_iam_memberships_user_id")),
    )
    op.create_index("ix_iam_memberships_department_id", "iam_memberships", ["department_id"])
    op.create_index("ix_iam_memberships_organization_id", "iam_memberships", ["organization_id"])
    op.create_index("ix_iam_memberships_user_id", "iam_memberships", ["user_id"])
    op.create_table(
        "iam_permissions",
        sa.Column("code", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_iam_permissions")),
    )
    op.create_table(
        "iam_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_iam_roles_status")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_iam_roles_organization_id_iam_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_iam_roles")),
        sa.UniqueConstraint("organization_id", "code", name=op.f("uq_iam_roles_organization_id")),
    )
    op.create_index("ix_iam_roles_organization_id", "iam_roles", ["organization_id"])
    op.create_table(
        "iam_membership_roles",
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_iam_membership_roles_membership_id_iam_memberships"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["iam_roles.id"], name=op.f("fk_iam_membership_roles_role_id_iam_roles")
        ),
        sa.PrimaryKeyConstraint("membership_id", "role_id", name=op.f("pk_iam_membership_roles")),
    )
    op.create_table(
        "iam_role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_code", sa.String(length=160), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["permission_code"],
            ["iam_permissions.code"],
            name=op.f("fk_iam_role_permissions_permission_code_iam_permissions"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["iam_roles.id"], name=op.f("fk_iam_role_permissions_role_id_iam_roles")
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_code", name=op.f("pk_iam_role_permissions")),
    )
    op.create_table(
        "iam_role_scope_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("scope_ref", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "scope_type NOT IN ('CATEGORY', 'SUPPLIER') OR scope_ref IS NOT NULL",
            name=op.f("ck_iam_role_scope_grants_specific_scope_ref"),
        ),
        sa.CheckConstraint(
            "scope_type IN ('ALL', 'ORGANIZATION', 'ORGANIZATION_TREE', "
            "'DEPARTMENT', 'SELF', 'CATEGORY', 'SUPPLIER')",
            name=op.f("ck_iam_role_scope_grants_scope_type"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["iam_roles.id"], name=op.f("fk_iam_role_scope_grants_role_id_iam_roles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_iam_role_scope_grants")),
        sa.UniqueConstraint(
            "role_id", "scope_type", "scope_ref", name=op.f("uq_iam_role_scope_grants_role_id")
        ),
    )
    op.create_index("ix_iam_role_scope_grants_role_id", "iam_role_scope_grants", ["role_id"])
    op.create_index("ix_iam_role_scope_grants_scope_ref", "iam_role_scope_grants", ["scope_ref"])


def downgrade() -> None:
    op.drop_table("iam_role_scope_grants")
    op.drop_table("iam_role_permissions")
    op.drop_table("iam_membership_roles")
    op.drop_table("iam_roles")
    op.drop_table("iam_permissions")
    op.drop_table("iam_memberships")
    op.drop_table("iam_users")
    op.drop_table("iam_organizations")
