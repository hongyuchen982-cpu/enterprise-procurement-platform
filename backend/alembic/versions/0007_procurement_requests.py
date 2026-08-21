"""Procurement request drafts and submission workflow.

Revision ID: 0007_procurement_requests
Revises: 0006_b_rag_risk_foundation
Create Date: 2026-08-20
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_procurement_requests"
down_revision = "0006_b_rag_risk_foundation"
branch_labels = None
depends_on = None

PERMISSION_CODES = (
    "procurement.request.read",
    "procurement.request.create",
    "procurement.request.update",
    "procurement.request.submit",
)


def upgrade() -> None:
    op.create_table(
        "procurement_requests",
        sa.Column("request_no", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("requester_id", sa.Uuid(), nullable=False),
        sa.Column("requester_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("purpose", sa.String(length=1000), nullable=False),
        sa.Column("required_date", sa.Date(), nullable=False),
        sa.Column("estimated_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
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
            "estimated_total >= 0",
            name=op.f("ck_procurement_requests_estimated_total_non_negative"),
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED')", name=op.f("ck_procurement_requests_status")
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["iam_organizations.id"],
            name=op.f("fk_procurement_requests_department_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_procurement_requests_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"],
            ["iam_users.id"],
            name=op.f("fk_procurement_requests_requester_id_iam_users"),
        ),
        sa.ForeignKeyConstraint(
            ["requester_membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_procurement_requests_requester_membership_id_iam_memberships"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_procurement_requests")),
        sa.UniqueConstraint("request_no", name=op.f("uq_procurement_requests_request_no")),
    )
    op.create_index(
        "ix_procurement_requests_department_id", "procurement_requests", ["department_id"]
    )
    op.create_index(
        "ix_procurement_requests_organization_id", "procurement_requests", ["organization_id"]
    )
    op.create_index(
        "ix_procurement_requests_requester_id", "procurement_requests", ["requester_id"]
    )
    op.create_index(
        "ix_procurement_requests_requester_membership_id",
        "procurement_requests",
        ["requester_membership_id"],
    )

    op.create_table(
        "procurement_request_lines",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("specification", sa.String(length=1000), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_code", sa.String(length=20), nullable=False),
        sa.Column("estimated_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("estimated_amount", sa.Numeric(18, 2), nullable=False),
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
            "estimated_amount >= 0",
            name=op.f("ck_procurement_request_lines_estimated_amount_non_negative"),
        ),
        sa.CheckConstraint(
            "estimated_unit_price IS NULL OR estimated_unit_price >= 0",
            name=op.f("ck_procurement_request_lines_estimated_unit_price_non_negative"),
        ),
        sa.CheckConstraint(
            "line_no > 0", name=op.f("ck_procurement_request_lines_line_no_positive")
        ),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_procurement_request_lines_quantity_positive")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["md_categories.id"],
            name=op.f("fk_procurement_request_lines_category_id_md_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["md_materials.id"],
            name=op.f("fk_procurement_request_lines_material_id_md_materials"),
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["procurement_requests.id"],
            name=op.f("fk_procurement_request_lines_request_id_procurement_requests"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_code"],
            ["md_units.code"],
            name=op.f("fk_procurement_request_lines_unit_code_md_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_procurement_request_lines")),
        sa.UniqueConstraint(
            "request_id", "line_no", name=op.f("uq_procurement_request_lines_request_id")
        ),
    )
    op.create_index(
        "ix_procurement_request_lines_category_id", "procurement_request_lines", ["category_id"]
    )
    op.create_index(
        "ix_procurement_request_lines_material_id", "procurement_request_lines", ["material_id"]
    )
    op.create_index(
        "ix_procurement_request_lines_request_id", "procurement_request_lines", ["request_id"]
    )
    op.create_index(
        "ix_procurement_request_lines_unit_code", "procurement_request_lines", ["unit_code"]
    )

    permission_table = sa.table(
        "iam_permissions",
        sa.column("code", sa.String(length=160)),
        sa.column("name", sa.String(length=200)),
    )
    op.bulk_insert(
        permission_table,
        [
            {"code": "procurement.request.read", "name": "Read procurement requests"},
            {"code": "procurement.request.create", "name": "Create procurement requests"},
            {"code": "procurement.request.update", "name": "Update procurement requests"},
            {"code": "procurement.request.submit", "name": "Submit procurement requests"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM iam_role_permissions WHERE permission_code IN "
            "('procurement.request.read', 'procurement.request.create', "
            "'procurement.request.update', 'procurement.request.submit')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM iam_permissions WHERE code IN "
            "('procurement.request.read', 'procurement.request.create', "
            "'procurement.request.update', 'procurement.request.submit')"
        )
    )
    op.drop_table("procurement_request_lines")
    op.drop_table("procurement_requests")
