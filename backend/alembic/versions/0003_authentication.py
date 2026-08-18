"""Password credentials and opaque authentication sessions.

Revision ID: 0003_authentication
Revises: 0002_identity_rbac
Create Date: 2026-08-18
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_authentication"
down_revision = "0002_identity_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iam_user_credentials",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "failed_attempts >= 0",
            name=op.f("ck_iam_user_credentials_failed_attempts_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam_users.id"],
            name=op.f("fk_iam_user_credentials_user_id_iam_users"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_iam_user_credentials")),
    )
    op.create_table(
        "iam_auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
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
        sa.CheckConstraint(
            "expires_at > created_at",
            name=op.f("ck_iam_auth_sessions_expires_after_creation"),
        ),
        sa.CheckConstraint(
            "length(token_hash) = 64",
            name=op.f("ck_iam_auth_sessions_token_hash_length"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam_users.id"],
            name=op.f("fk_iam_auth_sessions_user_id_iam_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_iam_auth_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_iam_auth_sessions_token_hash")),
    )
    op.create_index(
        op.f("ix_iam_auth_sessions_expires_at"),
        "iam_auth_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_iam_auth_sessions_user_id"),
        "iam_auth_sessions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("iam_auth_sessions")
    op.drop_table("iam_user_credentials")
