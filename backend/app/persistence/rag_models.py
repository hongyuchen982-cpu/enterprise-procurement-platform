from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeDocumentRecord(Base):
    __tablename__ = "b_knowledge_documents"
    __table_args__ = (
        Index("ix_b_knowledge_documents_org_status", "org_id", "status"),
        Index("ix_b_knowledge_documents_owner_status", "owner_module", "status"),
        Index("ix_b_knowledge_documents_updated", "updated_at"),
    )

    document_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_module: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[UUID] = mapped_column(String(36), nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
