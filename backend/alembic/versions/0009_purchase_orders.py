"""Purchase-order draft, issue, and cancellation lifecycle.

Revision ID: 0009_purchase_orders
Revises: 0008_approval_workflow
Create Date: 2026-08-20
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_purchase_orders"
down_revision = "0008_approval_workflow"
branch_labels = None
depends_on = None

PERMISSION_CODES = (
    "order.read",
    "order.create",
    "order.update",
    "order.issue",
    "order.cancel",
)


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("order_no", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_request_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("sourcing_award_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="DRAFT", nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("required_date", sa.Date(), nullable=True),
        sa.Column("promised_date", sa.Date(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ISSUED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CLOSED', 'CANCELLED')",
            name=op.f("ck_purchase_orders_status"),
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name=op.f("ck_purchase_orders_total_amount_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_purchase_orders_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["procurement_request_id"],
            ["procurement_requests.id"],
            name=op.f("fk_purchase_orders_procurement_request_id_procurement_requests"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_orders")),
        sa.UniqueConstraint("order_no", name=op.f("uq_purchase_orders_order_no")),
        sa.UniqueConstraint(
            "sourcing_award_id", name=op.f("uq_purchase_orders_sourcing_award_id")
        ),
    )
    op.create_index(
        "ix_purchase_orders_organization_id", "purchase_orders", ["organization_id"]
    )
    op.create_index(
        "ix_purchase_orders_procurement_request_id",
        "purchase_orders",
        ["procurement_request_id"],
    )
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index(
        "ix_purchase_orders_sourcing_award_id", "purchase_orders", ["sourcing_award_id"]
    )

    op.create_table(
        "purchase_order_lines",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("request_line_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("specification", sa.String(length=1000), nullable=True),
        sa.Column("unit_code", sa.String(length=20), nullable=False),
        sa.Column("ordered_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("received_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("invoiced_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(9, 6), nullable=False),
        sa.Column("line_amount", sa.Numeric(18, 2), nullable=False),
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
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "invoiced_quantity >= 0",
            name=op.f("ck_purchase_order_lines_invoiced_quantity_non_negative"),
        ),
        sa.CheckConstraint(
            "line_amount >= 0",
            name=op.f("ck_purchase_order_lines_line_amount_non_negative"),
        ),
        sa.CheckConstraint(
            "line_no > 0", name=op.f("ck_purchase_order_lines_line_no_positive")
        ),
        sa.CheckConstraint(
            "ordered_quantity > 0",
            name=op.f("ck_purchase_order_lines_ordered_quantity_positive"),
        ),
        sa.CheckConstraint(
            "received_quantity >= 0",
            name=op.f("ck_purchase_order_lines_received_quantity_non_negative"),
        ),
        sa.CheckConstraint(
            "received_quantity <= ordered_quantity",
            name=op.f("ck_purchase_order_lines_received_not_over_ordered"),
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 1",
            name=op.f("ck_purchase_order_lines_tax_rate_range"),
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name=op.f("ck_purchase_order_lines_unit_price_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["md_categories.id"],
            name=op.f("fk_purchase_order_lines_category_id_md_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["md_materials.id"],
            name=op.f("fk_purchase_order_lines_material_id_md_materials"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["purchase_orders.id"],
            name=op.f("fk_purchase_order_lines_order_id_purchase_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_line_id"],
            ["procurement_request_lines.id"],
            name=op.f(
                "fk_purchase_order_lines_request_line_id_procurement_request_lines"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["unit_code"],
            ["md_units.code"],
            name=op.f("fk_purchase_order_lines_unit_code_md_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_order_lines")),
        sa.UniqueConstraint(
            "order_id", "line_no", name="uq_purchase_order_lines_order_line_no"
        ),
        sa.UniqueConstraint(
            "order_id",
            "request_line_id",
            name="uq_purchase_order_lines_order_request_line",
        ),
    )
    op.create_index(
        "ix_purchase_order_lines_category_id", "purchase_order_lines", ["category_id"]
    )
    op.create_index(
        "ix_purchase_order_lines_material_id", "purchase_order_lines", ["material_id"]
    )
    op.create_index("ix_purchase_order_lines_order_id", "purchase_order_lines", ["order_id"])
    op.create_index(
        "ix_purchase_order_lines_request_line_id",
        "purchase_order_lines",
        ["request_line_id"],
    )
    op.create_index(
        "ix_purchase_order_lines_unit_code", "purchase_order_lines", ["unit_code"]
    )

    permission_table = sa.table(
        "iam_permissions",
        sa.column("code", sa.String(length=160)),
        sa.column("name", sa.String(length=200)),
    )
    op.bulk_insert(
        permission_table,
        [
            {"code": "order.read", "name": "Read purchase orders"},
            {"code": "order.create", "name": "Create purchase orders"},
            {"code": "order.update", "name": "Update purchase order drafts"},
            {"code": "order.issue", "name": "Issue purchase orders"},
            {"code": "order.cancel", "name": "Cancel purchase orders"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM iam_role_permissions WHERE permission_code IN "
            "('order.read', 'order.create', 'order.update', 'order.issue', 'order.cancel')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM iam_permissions WHERE code IN "
            "('order.read', 'order.create', 'order.update', 'order.issue', 'order.cancel')"
        )
    )
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
