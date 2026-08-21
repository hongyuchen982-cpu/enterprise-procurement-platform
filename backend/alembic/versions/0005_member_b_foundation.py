"""Member B supplier, sourcing, and agent persistence foundation.

Revision ID: 0005_member_b_foundation
Revises: 0004_organization_master_data
Create Date: 2026-08-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_member_b_foundation"
down_revision = "0004_organization_master_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "b_suppliers",
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("qualification_status", sa.String(length=32), nullable=False),
        sa.Column("category_ids", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("is_frozen", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("supplier_id", name=op.f("pk_b_suppliers")),
    )
    op.create_index("ix_b_suppliers_org_risk", "b_suppliers", ["org_id", "risk_level"])
    op.create_index("ix_b_suppliers_org_status", "b_suppliers", ["org_id", "status"])

    op.create_table(
        "b_agent_tasks",
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("agent_type", sa.String(length=80), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("subject_refs", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("task_id", name=op.f("pk_b_agent_tasks")),
    )
    op.create_index("ix_b_agent_tasks_org_status", "b_agent_tasks", ["org_id", "status"])
    op.create_index("ix_b_agent_tasks_status_updated", "b_agent_tasks", ["status", "updated_at"])
    op.create_index("ix_b_agent_tasks_trace", "b_agent_tasks", ["trace_id"])

    op.create_table(
        "b_sourcing_projects",
        sa.Column("sourcing_project_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("procurement_request_id", sa.String(length=36), nullable=False),
        sa.Column("procurement_request_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_supplier_ids", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("sourcing_project_id", name=op.f("pk_b_sourcing_projects")),
    )
    op.create_index(
        "ix_b_sourcing_projects_org_status", "b_sourcing_projects", ["org_id", "status"]
    )
    op.create_index(
        "ix_b_sourcing_projects_status_updated",
        "b_sourcing_projects",
        ["status", "updated_at"],
    )
    op.create_index(
        "ix_b_sourcing_projects_procurement_request",
        "b_sourcing_projects",
        ["procurement_request_id", "procurement_request_version"],
    )

    op.create_table(
        "b_supplier_risk_reviews",
        sa.Column("review_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("conclusion", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["b_suppliers.supplier_id"],
            name=op.f("fk_b_supplier_risk_reviews_supplier_id_b_suppliers"),
        ),
        sa.PrimaryKeyConstraint("review_id", name=op.f("pk_b_supplier_risk_reviews")),
    )
    op.create_index(
        "ix_b_supplier_risk_reviews_supplier_created",
        "b_supplier_risk_reviews",
        ["supplier_id", "created_at"],
    )

    op.create_table(
        "b_agent_task_events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["b_agent_tasks.task_id"],
            name=op.f("fk_b_agent_task_events_task_id_b_agent_tasks"),
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_b_agent_task_events")),
    )
    op.create_index(
        "ix_b_agent_task_events_task_created",
        "b_agent_task_events",
        ["task_id", "created_at"],
    )
    op.create_index(
        "ix_b_agent_task_events_type_created",
        "b_agent_task_events",
        ["event_type", "created_at"],
    )

    op.create_table(
        "b_agent_confirmations",
        sa.Column("confirmation_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("tool_call_id", sa.String(length=36), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("proposed_action", sa.Text(), nullable=False),
        sa.Column("target_refs", sa.JSON(), nullable=False),
        sa.Column("target_versions", sa.JSON(), nullable=False),
        sa.Column("input_digest", sa.String(length=128), nullable=False),
        sa.Column("required_permission", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", sa.String(length=36), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["b_agent_tasks.task_id"],
            name=op.f("fk_b_agent_confirmations_task_id_b_agent_tasks"),
        ),
        sa.PrimaryKeyConstraint("confirmation_id", name=op.f("pk_b_agent_confirmations")),
    )
    op.create_index(
        "ix_b_agent_confirmations_status_expires",
        "b_agent_confirmations",
        ["status", "expires_at"],
    )
    op.create_index(
        "ix_b_agent_confirmations_task_status",
        "b_agent_confirmations",
        ["task_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("b_agent_confirmations")
    op.drop_table("b_agent_task_events")
    op.drop_table("b_supplier_risk_reviews")
    op.drop_table("b_sourcing_projects")
    op.drop_table("b_agent_tasks")
    op.drop_table("b_suppliers")
