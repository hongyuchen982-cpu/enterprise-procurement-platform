"""Organization permissions and procurement master data.

Revision ID: 0004_organization_master_data
Revises: 0003_authentication
Create Date: 2026-08-19
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_organization_master_data"
down_revision = "0003_authentication"
branch_labels = None
depends_on = None

PERMISSION_CODES = (
    "organization.read",
    "organization.manage",
    "master_data.read",
    "master_data.manage",
)


def upgrade() -> None:
    op.create_table(
        "md_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
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
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_md_categories_status")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_md_categories_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["md_categories.id"],
            name=op.f("fk_md_categories_parent_id_md_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_md_categories")),
        sa.UniqueConstraint(
            "organization_id", "code", name=op.f("uq_md_categories_organization_id")
        ),
    )
    op.create_index("ix_md_categories_organization_id", "md_categories", ["organization_id"])
    op.create_index("ix_md_categories_parent_id", "md_categories", ["parent_id"])

    op.create_table(
        "md_units",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("decimal_places", sa.Integer(), server_default="2", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
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
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "decimal_places BETWEEN 0 AND 6", name=op.f("ck_md_units_decimal_places_range")
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_md_units_status")),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_md_units")),
    )

    op.create_table(
        "md_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.String(length=20), nullable=False),
        sa.Column("specification", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
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
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_md_materials_status")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_md_materials_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["md_categories.id"],
            name=op.f("fk_md_materials_category_id_md_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["unit_code"],
            ["md_units.code"],
            name=op.f("fk_md_materials_unit_code_md_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_md_materials")),
        sa.UniqueConstraint(
            "organization_id", "code", name=op.f("uq_md_materials_organization_id")
        ),
    )
    op.create_index("ix_md_materials_category_id", "md_materials", ["category_id"])
    op.create_index("ix_md_materials_organization_id", "md_materials", ["organization_id"])
    op.create_index("ix_md_materials_unit_code", "md_materials", ["unit_code"])

    permission_table = sa.table(
        "iam_permissions",
        sa.column("code", sa.String(length=160)),
        sa.column("name", sa.String(length=200)),
    )
    op.bulk_insert(
        permission_table,
        [
            {"code": "organization.read", "name": "Read organization hierarchy"},
            {"code": "organization.manage", "name": "Manage organizations and memberships"},
            {"code": "master_data.read", "name": "Read procurement master data"},
            {"code": "master_data.manage", "name": "Manage procurement master data"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM iam_role_permissions WHERE permission_code IN "
            "('organization.read', 'organization.manage', 'master_data.read', 'master_data.manage')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM iam_permissions WHERE code IN "
            "('organization.read', 'organization.manage', 'master_data.read', 'master_data.manage')"
        )
    )
    op.drop_table("md_materials")
    op.drop_table("md_categories")
    op.drop_table("md_units")
