"""Inventory-lite receipt ledger and formal business audit log.

Revision ID: 0012_inventory_audit
Revises: 0011_invoice_matching
Create Date: 2026-08-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_inventory_audit"
down_revision = "0011_invoice_matching"
branch_labels = None
depends_on = None

PERMISSION_CODES = ("inventory.read", "audit.read")


def upgrade() -> None:
    op.create_table(
        "inventory_balances",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.String(length=20), nullable=False),
        sa.Column("on_hand_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_received_quantity", sa.Numeric(18, 6), nullable=False),
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
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "on_hand_quantity >= 0",
            name=op.f("ck_inventory_balances_on_hand_quantity_non_negative"),
        ),
        sa.CheckConstraint(
            "total_received_quantity >= 0",
            name=op.f(
                "ck_inventory_balances_total_received_quantity_non_negative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["md_categories.id"],
            name=op.f("fk_inventory_balances_category_id_md_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["md_materials.id"],
            name=op.f("fk_inventory_balances_material_id_md_materials"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_inventory_balances_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["unit_code"],
            ["md_units.code"],
            name=op.f("fk_inventory_balances_unit_code_md_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_balances")),
        sa.UniqueConstraint(
            "organization_id",
            "material_id",
            name="uq_inventory_balances_org_material",
        ),
    )
    op.create_index(
        "ix_inventory_balances_category_id", "inventory_balances", ["category_id"]
    )
    op.create_index(
        "ix_inventory_balances_material_id", "inventory_balances", ["material_id"]
    )
    op.create_index(
        "ix_inventory_balances_organization_id",
        "inventory_balances",
        ["organization_id"],
    )
    op.create_index(
        "ix_inventory_balances_unit_code", "inventory_balances", ["unit_code"]
    )

    op.create_table(
        "inventory_movements",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.String(length=20), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 6), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("source_line_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "balance_after >= 0",
            name=op.f("ck_inventory_movements_balance_after_non_negative"),
        ),
        sa.CheckConstraint(
            "movement_type IN ('RECEIPT')",
            name=op.f("ck_inventory_movements_movement_type"),
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_inventory_movements_quantity_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["md_categories.id"],
            name=op.f("fk_inventory_movements_category_id_md_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["md_materials.id"],
            name=op.f("fk_inventory_movements_material_id_md_materials"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_inventory_movements_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["unit_code"],
            ["md_units.code"],
            name=op.f("fk_inventory_movements_unit_code_md_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_movements")),
        sa.UniqueConstraint(
            "source_type",
            "source_line_id",
            name="uq_inventory_movements_source_line",
        ),
    )
    op.create_index(
        "ix_inventory_movements_category_id", "inventory_movements", ["category_id"]
    )
    op.create_index(
        "ix_inventory_movements_material_id", "inventory_movements", ["material_id"]
    )
    op.create_index(
        "ix_inventory_movements_occurred_at", "inventory_movements", ["occurred_at"]
    )
    op.create_index(
        "ix_inventory_movements_organization_id",
        "inventory_movements",
        ["organization_id"],
    )
    op.create_index(
        "ix_inventory_movements_source_id", "inventory_movements", ["source_id"]
    )
    op.create_index(
        "ix_inventory_movements_source_line_id",
        "inventory_movements",
        ["source_line_id"],
    )
    op.create_index(
        "ix_inventory_movements_unit_code", "inventory_movements", ["unit_code"]
    )

    op.create_table(
        "business_audit_log",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("object_type", sa.String(length=80), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("object_version", sa.Integer(), nullable=True),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("before_data", sa.JSON(), nullable=True),
        sa.Column("after_data", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "actor_type IN ('USER', 'AGENT', 'SYSTEM')",
            name=op.f("ck_business_audit_log_actor_type"),
        ),
        sa.CheckConstraint(
            "source IN ('API', 'WORKER', 'TOOL', 'INTEGRATION')",
            name=op.f("ck_business_audit_log_source"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["iam_users.id"],
            name=op.f("fk_business_audit_log_actor_id_iam_users"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id"],
            ["iam_memberships.id"],
            name=op.f(
                "fk_business_audit_log_actor_membership_id_iam_memberships"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_business_audit_log_organization_id_iam_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_audit_log")),
    )
    op.create_index(
        "ix_business_audit_log_action", "business_audit_log", ["action"]
    )
    op.create_index(
        "ix_business_audit_log_actor_id", "business_audit_log", ["actor_id"]
    )
    op.create_index(
        "ix_business_audit_log_actor_membership_id",
        "business_audit_log",
        ["actor_membership_id"],
    )
    op.create_index(
        "ix_business_audit_log_object_id", "business_audit_log", ["object_id"]
    )
    op.create_index(
        "ix_business_audit_log_object_type", "business_audit_log", ["object_type"]
    )
    op.create_index(
        "ix_business_audit_log_occurred_at", "business_audit_log", ["occurred_at"]
    )
    op.create_index(
        "ix_business_audit_log_organization_id",
        "business_audit_log",
        ["organization_id"],
    )

    permission_table = sa.table(
        "iam_permissions",
        sa.column("code", sa.String(length=160)),
        sa.column("name", sa.String(length=200)),
    )
    op.bulk_insert(
        permission_table,
        [
            {"code": "inventory.read", "name": "Read inventory balances and movements"},
            {"code": "audit.read", "name": "Read formal business audit log"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM iam_role_permissions WHERE permission_code IN "
            "('inventory.read', 'audit.read')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM iam_permissions WHERE code IN "
            "('inventory.read', 'audit.read')"
        )
    )
    op.drop_table("business_audit_log")
    op.drop_table("inventory_movements")
    op.drop_table("inventory_balances")
