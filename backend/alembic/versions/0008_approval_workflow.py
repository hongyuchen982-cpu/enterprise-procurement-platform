"""Approval templates, instances, nodes, and request transitions.

Revision ID: 0008_approval_workflow
Revises: 0007_procurement_requests
Create Date: 2026-08-20
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_approval_workflow"
down_revision = "0007_procurement_requests"
branch_labels = None
depends_on = None

PERMISSION_CODES = (
    "approval.template.manage",
    "approval.instance.start",
    "approval.instance.read",
    "approval.task.decide",
)


def upgrade() -> None:
    with op.batch_alter_table("procurement_requests") as batch_op:
        batch_op.drop_constraint(op.f("ck_procurement_requests_status"), type_="check")
        batch_op.create_check_constraint(
            "status",
            "status IN ('DRAFT', 'SUBMITTED', 'IN_APPROVAL', 'APPROVED', 'REJECTED')",
        )

    op.create_table(
        "approval_templates",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
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
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'DISABLED')", name=op.f("ck_approval_templates_status")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_approval_templates_organization_id_iam_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_templates")),
        sa.UniqueConstraint(
            "organization_id", "code", name=op.f("uq_approval_templates_organization_id")
        ),
    )
    op.create_index(
        "ix_approval_templates_organization_id", "approval_templates", ["organization_id"]
    )

    op.create_table(
        "approval_template_steps",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("approver_membership_id", sa.Uuid(), nullable=False),
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
            "step_no > 0",
            name=op.f("ck_approval_template_steps_step_no_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["approver_membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_approval_template_steps_approver_membership_id_iam_memberships"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["approval_templates.id"],
            name=op.f("fk_approval_template_steps_template_id_approval_templates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_template_steps")),
        sa.UniqueConstraint(
            "template_id", "step_no", name=op.f("uq_approval_template_steps_template_id")
        ),
    )
    op.create_index(
        "ix_approval_template_steps_approver_membership_id",
        "approval_template_steps",
        ["approver_membership_id"],
    )
    op.create_index(
        "ix_approval_template_steps_template_id", "approval_template_steps", ["template_id"]
    )

    op.create_table(
        "approval_instances",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("current_step_no", sa.Integer(), server_default="1", nullable=False),
        sa.Column("request_version", sa.Integer(), nullable=False),
        sa.Column("request_snapshot", sa.JSON(), nullable=False),
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
            "current_step_no > 0",
            name=op.f("ck_approval_instances_current_step_no_positive"),
        ),
        sa.CheckConstraint(
            "request_version > 0",
            name=op.f("ck_approval_instances_request_version_positive"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name=op.f("ck_approval_instances_status"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["iam_organizations.id"],
            name=op.f("fk_approval_instances_organization_id_iam_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["procurement_requests.id"],
            name=op.f("fk_approval_instances_request_id_procurement_requests"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["approval_templates.id"],
            name=op.f("fk_approval_instances_template_id_approval_templates"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_instances")),
        sa.UniqueConstraint("request_id", name=op.f("uq_approval_instances_request_id")),
    )
    op.create_index(
        "ix_approval_instances_organization_id", "approval_instances", ["organization_id"]
    )
    op.create_index("ix_approval_instances_request_id", "approval_instances", ["request_id"])
    op.create_index("ix_approval_instances_template_id", "approval_instances", ["template_id"])

    op.create_table(
        "approval_nodes",
        sa.Column("instance_id", sa.Uuid(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("approver_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("decision_comment", sa.String(length=1000), nullable=True),
        sa.Column("decided_by_membership_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('WAITING', 'PENDING', 'APPROVED', 'REJECTED', 'SKIPPED')",
            name=op.f("ck_approval_nodes_status"),
        ),
        sa.CheckConstraint("step_no > 0", name=op.f("ck_approval_nodes_step_no_positive")),
        sa.ForeignKeyConstraint(
            ["approver_membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_approval_nodes_approver_membership_id_iam_memberships"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_approval_nodes_decided_by_membership_id_iam_memberships"),
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["approval_instances.id"],
            name=op.f("fk_approval_nodes_instance_id_approval_instances"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_nodes")),
        sa.UniqueConstraint("instance_id", "step_no", name=op.f("uq_approval_nodes_instance_id")),
    )
    op.create_index(
        "ix_approval_nodes_approver_membership_id",
        "approval_nodes",
        ["approver_membership_id"],
    )
    op.create_index(
        "ix_approval_nodes_decided_by_membership_id",
        "approval_nodes",
        ["decided_by_membership_id"],
    )
    op.create_index("ix_approval_nodes_instance_id", "approval_nodes", ["instance_id"])

    op.create_table(
        "approval_actions",
        sa.Column("instance_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("target_membership_id", sa.Uuid(), nullable=True),
        sa.Column("comment", sa.String(length=1000), nullable=True),
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
            "action IN ('APPROVE', 'REJECT', 'TRANSFER')",
            name=op.f("ck_approval_actions_action"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_approval_actions_actor_membership_id_iam_memberships"),
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["approval_instances.id"],
            name=op.f("fk_approval_actions_instance_id_approval_instances"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["approval_nodes.id"],
            name=op.f("fk_approval_actions_node_id_approval_nodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_membership_id"],
            ["iam_memberships.id"],
            name=op.f("fk_approval_actions_target_membership_id_iam_memberships"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_actions")),
    )
    op.create_index(
        "ix_approval_actions_actor_membership_id",
        "approval_actions",
        ["actor_membership_id"],
    )
    op.create_index("ix_approval_actions_instance_id", "approval_actions", ["instance_id"])
    op.create_index("ix_approval_actions_node_id", "approval_actions", ["node_id"])
    op.create_index(
        "ix_approval_actions_target_membership_id",
        "approval_actions",
        ["target_membership_id"],
    )

    permission_table = sa.table(
        "iam_permissions",
        sa.column("code", sa.String(length=160)),
        sa.column("name", sa.String(length=200)),
    )
    op.bulk_insert(
        permission_table,
        [
            {"code": "approval.template.manage", "name": "Manage approval templates"},
            {"code": "approval.instance.start", "name": "Start approval instances"},
            {"code": "approval.instance.read", "name": "Read approval instances"},
            {"code": "approval.task.decide", "name": "Decide assigned approval tasks"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM iam_role_permissions WHERE permission_code IN "
            "('approval.template.manage', 'approval.instance.start', "
            "'approval.instance.read', 'approval.task.decide')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM iam_permissions WHERE code IN "
            "('approval.template.manage', 'approval.instance.start', "
            "'approval.instance.read', 'approval.task.decide')"
        )
    )
    op.drop_table("approval_actions")
    op.drop_table("approval_nodes")
    op.drop_table("approval_instances")
    op.drop_table("approval_template_steps")
    op.drop_table("approval_templates")
    op.execute(
        sa.text(
            "UPDATE procurement_requests SET status = 'SUBMITTED' "
            "WHERE status IN ('IN_APPROVAL', 'APPROVED', 'REJECTED')"
        )
    )
    with op.batch_alter_table("procurement_requests") as batch_op:
        batch_op.drop_constraint(op.f("ck_procurement_requests_status"), type_="check")
        batch_op.create_check_constraint("status", "status IN ('DRAFT', 'SUBMITTED')")
