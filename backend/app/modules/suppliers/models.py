from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SupplierRecord(Base):
    __tablename__ = "b_suppliers"
    __table_args__ = (
        Index("ix_b_suppliers_org_risk", "org_id", "risk_level"),
        Index("ix_b_suppliers_org_status", "org_id", "status"),
    )

    supplier_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    qualification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    category_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplierRiskReviewRecord(Base):
    __tablename__ = "b_supplier_risk_reviews"
    __table_args__ = (
        Index("ix_b_supplier_risk_reviews_supplier_created", "supplier_id", "created_at"),
    )

    review_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("b_suppliers.supplier_id"), nullable=False
    )
    conclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
