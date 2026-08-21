"""Goods receipt drafts, inspection, and purchase-order fulfillment.

Revision ID: 0010_goods_receiving
Revises: 0009_purchase_orders
Create Date: 2026-08-20
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_goods_receiving"
down_revision = "0009_purchase_orders"
branch_labels = None
depends_on = None

PERMISSION_CODES = (
    "receipt.read",
    "receipt.create",
    "receipt.update",
    "receipt.complete",
    "receipt.cancel",
)


def upgrade() -> None:
    op.create_table(
        "goods_receipts",
        sa.Column("receipt_no", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("receiver_membership_id", sa.Uuid(), nullable=False),
        sa.Column("receiver_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('DRAFT', 'COMPLETED', 'CANCELLED')",
            name=op.f("ck_goods_receipts_status"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["purchase_orders.id"],
            name=op.f("fk_goods_receipts_order_id_purchase_orders"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_goods_receipts_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["receiver_id"],
            ["iam_users.id"],
            name=op.f("fk_goods_receipts_receiver_id_iam_users"),
        ),
        sa.ForeignKeyConstraint(
            ["receiver_membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_goods_receipts_receiver_membership_id_iam_memberships"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goods_receipts")),
        sa.UniqueConstraint("receipt_no", name=op.f("uq_goods_receipts_receipt_no")),
    )
    op.create_index(
        "ix_goods_receipts_order_id", "goods_receipts", ["order_id"]
    )
    op.create_index(
        "ix_goods_receipts_organization_id", "goods_receipts", ["organization_id"]
    )
    op.create_index(
        "ix_goods_receipts_receiver_id", "goods_receipts", ["receiver_id"]
    )
    op.create_index(
        "ix_goods_receipts_receiver_membership_id",
        "goods_receipts",
        ["receiver_membership_id"],
    )

    op.create_table(
        "goods_receipt_lines",
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("order_line_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("received_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("accepted_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("rejected_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("inspection_status", sa.String(length=20), nullable=False),
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
            "accepted_quantity >= 0",
            name=op.f("ck_goods_receipt_lines_accepted_quantity_non_negative"),
        ),
        sa.CheckConstraint(
            "inspection_status IN ('NOT_REQUIRED', 'PENDING', 'PASSED', 'FAILED')",
            name=op.f("ck_goods_receipt_lines_inspection_status"),
        ),
        sa.CheckConstraint(
            "line_no > 0", name=op.f("ck_goods_receipt_lines_line_no_positive")
        ),
        sa.CheckConstraint(
            "received_quantity = accepted_quantity + rejected_quantity",
            name=op.f("ck_goods_receipt_lines_quantity_balance"),
        ),
        sa.CheckConstraint(
            "received_quantity > 0",
            name=op.f("ck_goods_receipt_lines_received_quantity_positive"),
        ),
        sa.CheckConstraint(
            "rejected_quantity >= 0",
            name=op.f("ck_goods_receipt_lines_rejected_quantity_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["order_line_id"],
            ["purchase_order_lines.id"],
            name=op.f("fk_goods_receipt_lines_order_line_id_purchase_order_lines"),
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["goods_receipts.id"],
            name=op.f("fk_goods_receipt_lines_receipt_id_goods_receipts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goods_receipt_lines")),
        sa.UniqueConstraint(
            "receipt_id", "line_no", name="uq_goods_receipt_lines_receipt_line_no"
        ),
        sa.UniqueConstraint(
            "receipt_id",
            "order_line_id",
            name="uq_goods_receipt_lines_receipt_order_line",
        ),
    )
    op.create_index(
        "ix_goods_receipt_lines_order_line_id",
        "goods_receipt_lines",
        ["order_line_id"],
    )
    op.create_index(
        "ix_goods_receipt_lines_receipt_id", "goods_receipt_lines", ["receipt_id"]
    )

    permission_table = sa.table(
        "iam_permissions",
        sa.column("code", sa.String(length=160)),
        sa.column("name", sa.String(length=200)),
    )
    op.bulk_insert(
        permission_table,
        [
            {"code": "receipt.read", "name": "Read goods receipts"},
            {"code": "receipt.create", "name": "Create goods receipt drafts"},
            {"code": "receipt.update", "name": "Update goods receipt drafts"},
            {"code": "receipt.complete", "name": "Complete goods receipts"},
            {"code": "receipt.cancel", "name": "Cancel goods receipt drafts"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM iam_role_permissions WHERE permission_code IN "
            "('receipt.read', 'receipt.create', 'receipt.update', "
            "'receipt.complete', 'receipt.cancel')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM iam_permissions WHERE code IN "
            "('receipt.read', 'receipt.create', 'receipt.update', "
            "'receipt.complete', 'receipt.cancel')"
        )
    )
    op.drop_table("goods_receipt_lines")
    op.drop_table("goods_receipts")
