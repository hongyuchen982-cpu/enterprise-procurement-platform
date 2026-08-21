"""Member B RAG and supplier risk persistence foundation.

Revision ID: 0006_b_rag_risk_foundation
Revises: 0005_member_b_foundation
Create Date: 2026-08-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_b_rag_risk_foundation"
down_revision = "0005_member_b_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "b_knowledge_documents",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("owner_module", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("content_digest", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("document_id", name=op.f("pk_b_knowledge_documents")),
    )
    op.create_index(
        "ix_b_knowledge_documents_org_status",
        "b_knowledge_documents",
        ["org_id", "status"],
    )
    op.create_index(
        "ix_b_knowledge_documents_owner_status",
        "b_knowledge_documents",
        ["owner_module", "status"],
    )
    op.create_index(
        "ix_b_knowledge_documents_updated",
        "b_knowledge_documents",
        ["updated_at"],
    )

    op.create_table(
        "b_supplier_risk_assessments",
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("recommended_action", sa.String(length=32), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("assessed_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("assessment_id", name=op.f("pk_b_supplier_risk_assessments")),
    )
    op.create_index(
        "ix_b_supplier_risk_assessments_supplier_updated",
        "b_supplier_risk_assessments",
        ["supplier_id", "updated_at"],
    )
    op.create_index(
        "ix_b_supplier_risk_assessments_org_risk",
        "b_supplier_risk_assessments",
        ["org_id", "risk_level"],
    )
    op.create_index(
        "ix_b_supplier_risk_assessments_score",
        "b_supplier_risk_assessments",
        ["score"],
    )


def downgrade() -> None:
    op.drop_table("b_supplier_risk_assessments")
    op.drop_table("b_knowledge_documents")
