from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SupplierRiskAssessmentRecord(Base):
    __tablename__ = "b_supplier_risk_assessments"
    __table_args__ = (
        Index("ix_b_supplier_risk_assessments_supplier_updated", "supplier_id", "updated_at"),
        Index("ix_b_supplier_risk_assessments_org_risk", "org_id", "risk_level"),
        Index("ix_b_supplier_risk_assessments_score", "score"),
    )

    assessment_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    org_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(32), nullable=False)
    factors: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
