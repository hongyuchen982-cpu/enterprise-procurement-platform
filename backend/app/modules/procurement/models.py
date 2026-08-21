from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionedMixin,
)


class ProcurementRequestRecordStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_APPROVAL = "IN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProcurementRequest(
    UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base
):
    __tablename__ = "procurement_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'IN_APPROVAL', 'APPROVED', 'REJECTED')",
            name="status",
        ),
        CheckConstraint("estimated_total >= 0", name="estimated_total_non_negative"),
    )

    request_no: Mapped[str] = mapped_column(String(40), unique=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    requester_id: Mapped[UUID] = mapped_column(ForeignKey("iam_users.id"), index=True)
    requester_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("iam_memberships.id"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ProcurementRequestRecordStatus.DRAFT,
        server_default=ProcurementRequestRecordStatus.DRAFT,
    )
    currency: Mapped[str] = mapped_column(String(3))
    purpose: Mapped[str] = mapped_column(String(1000))
    required_date: Mapped[date] = mapped_column(Date)
    estimated_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lines: Mapped[list["ProcurementRequestLine"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ProcurementRequestLine.line_no",
    )


class ProcurementRequestLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "procurement_request_lines"
    __table_args__ = (
        UniqueConstraint("request_id", "line_no"),
        CheckConstraint("line_no > 0", name="line_no_positive"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "estimated_unit_price IS NULL OR estimated_unit_price >= 0",
            name="estimated_unit_price_non_negative",
        ),
        CheckConstraint("estimated_amount >= 0", name="estimated_amount_non_negative"),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int] = mapped_column(Integer)
    material_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("md_materials.id"), nullable=True, index=True
    )
    category_id: Mapped[UUID] = mapped_column(ForeignKey("md_categories.id"), index=True)
    description: Mapped[str] = mapped_column(String(500))
    specification: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit_code: Mapped[str] = mapped_column(ForeignKey("md_units.code"), index=True)
    estimated_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    request: Mapped[ProcurementRequest] = relationship(back_populates="lines")
