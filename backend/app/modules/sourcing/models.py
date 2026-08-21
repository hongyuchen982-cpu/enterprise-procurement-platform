from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SourcingProjectRecord(Base):
    __tablename__ = "b_sourcing_projects"
    __table_args__ = (
        Index("ix_b_sourcing_projects_org_status", "org_id", "status"),
        Index("ix_b_sourcing_projects_status_updated", "status", "updated_at"),
        Index(
            "ix_b_sourcing_projects_procurement_request",
            "procurement_request_id",
            "procurement_request_version",
        ),
    )

    sourcing_project_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    procurement_request_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    procurement_request_version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    candidate_supplier_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[UUID] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
