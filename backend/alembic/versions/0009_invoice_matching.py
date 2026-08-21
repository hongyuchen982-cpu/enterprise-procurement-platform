"""Supplier invoices and three-way matching.

Revision ID: 0009_invoice_matching
Revises: 0008_goods_receiving
Create Date: 2026-08-20
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_invoice_matching"
down_revision = "0008_goods_receiving"
branch_labels = None
depends_on = None

PERMISSION_CODES = (
    "invoice.read",
    "invoice.create",
    "invoice.update",
    "invoice.submit",
    "invoice.approve",
    "invoice.cancel",
)


def upgrade() -> None:
    op.create_table(
        "supplier_invoices",
        sa.Column("invoice_no", sa.String(length=80), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_membership_id", sa.Uuid(), nullable=True),
        sa.Column("approval_comment", sa.String(length=1000), nullable=True),
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
            "status IN ('DRAFT', 'MATCHED', 'EXCEPTION', 'APPROVED', 'CANCELLED')",
            name=op.f("ck_supplier_invoices_status"),
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name=op.f("ck_supplier_invoices_total_amount_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_membership_id"],
            ["iam_memberships.id"],
            name=op.f(
                "fk_supplier_invoices_approved_by_membership_id_iam_memberships"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["purchase_orders.id"],
            name=op.f("fk_supplier_invoices_order_id_purchase_orders"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_supplier_invoices_organization_id_iam_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_invoices")),
        sa.UniqueConstraint(
            "organization_id",
            "supplier_id",
            "invoice_no",
            name="uq_supplier_invoices_org_supplier_number",
        ),
    )
    op.create_index(
        "ix_supplier_invoices_approved_by_membership_id",
        "supplier_invoices",
        ["approved_by_membership_id"],
    )
    op.create_index(
        "ix_supplier_invoices_order_id", "supplier_invoices", ["order_id"]
    )
    op.create_index(
        "ix_supplier_invoices_organization_id",
        "supplier_invoices",
        ["organization_id"],
    )
    op.create_index(
        "ix_supplier_invoices_supplier_id", "supplier_invoices", ["supplier_id"]
    )

    op.create_table(
        "supplier_invoice_lines",
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("order_line_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("invoiced_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(9, 6), nullable=False),
        sa.Column("line_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("quantity_matched", sa.Boolean(), nullable=True),
        sa.Column("price_matched", sa.Boolean(), nullable=True),
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
            "invoiced_quantity > 0",
            name=op.f("ck_supplier_invoice_lines_invoiced_quantity_positive"),
        ),
        sa.CheckConstraint(
            "line_amount >= 0",
            name=op.f("ck_supplier_invoice_lines_line_amount_non_negative"),
        ),
        sa.CheckConstraint(
            "line_no > 0", name=op.f("ck_supplier_invoice_lines_line_no_positive")
        ),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 1",
            name=op.f("ck_supplier_invoice_lines_tax_rate_range"),
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name=op.f("ck_supplier_invoice_lines_unit_price_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["supplier_invoices.id"],
            name=op.f("fk_supplier_invoice_lines_invoice_id_supplier_invoices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_line_id"],
            ["purchase_order_lines.id"],
            name=op.f("fk_supplier_invoice_lines_order_line_id_purchase_order_lines"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_invoice_lines")),
        sa.UniqueConstraint(
            "invoice_id",
            "line_no",
            name="uq_supplier_invoice_lines_invoice_line_no",
        ),
        sa.UniqueConstraint(
            "invoice_id",
            "order_line_id",
            name="uq_supplier_invoice_lines_invoice_order_line",
        ),
    )
    op.create_index(
        "ix_supplier_invoice_lines_invoice_id",
        "supplier_invoice_lines",
        ["invoice_id"],
    )
    op.create_index(
        "ix_supplier_invoice_lines_order_line_id",
        "supplier_invoice_lines",
        ["order_line_id"],
    )

    permission_table = sa.table(
        "iam_permissions",
        sa.column("code", sa.String(length=160)),
        sa.column("name", sa.String(length=200)),
    )
    op.bulk_insert(
        permission_table,
        [
            {"code": "invoice.read", "name": "Read supplier invoices"},
            {"code": "invoice.create", "name": "Create supplier invoice drafts"},
            {"code": "invoice.update", "name": "Update supplier invoice drafts"},
            {"code": "invoice.submit", "name": "Submit invoices for matching"},
            {"code": "invoice.approve", "name": "Approve matched or exception invoices"},
            {"code": "invoice.cancel", "name": "Cancel unapproved invoices"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM iam_role_permissions WHERE permission_code IN "
            "('invoice.read', 'invoice.create', 'invoice.update', 'invoice.submit', "
            "'invoice.approve', 'invoice.cancel')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM iam_permissions WHERE code IN "
            "('invoice.read', 'invoice.create', 'invoice.update', 'invoice.submit', "
            "'invoice.approve', 'invoice.cancel')"
        )
    )
    op.drop_table("supplier_invoice_lines")
    op.drop_table("supplier_invoices")
