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


class PurchaseOrderRecordStatus(StrEnum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PurchaseOrder(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'ISSUED', 'PARTIALLY_RECEIVED', "
            "'RECEIVED', 'CLOSED', 'CANCELLED')",
            name="status",
        ),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
        UniqueConstraint("sourcing_award_id"),
    )

    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    procurement_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.id"), index=True
    )
    supplier_id: Mapped[UUID] = mapped_column(index=True)
    sourcing_award_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(24),
        default=PurchaseOrderRecordStatus.DRAFT,
        server_default=PurchaseOrderRecordStatus.DRAFT,
    )
    currency: Mapped[str] = mapped_column(String(3))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    required_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    promised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderLine.line_no",
    )


class PurchaseOrderLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "line_no", name="uq_purchase_order_lines_order_line_no"),
        UniqueConstraint(
            "order_id",
            "request_line_id",
            name="uq_purchase_order_lines_order_request_line",
        ),
        CheckConstraint("line_no > 0", name="line_no_positive"),
        CheckConstraint("ordered_quantity > 0", name="ordered_quantity_positive"),
        CheckConstraint("received_quantity >= 0", name="received_quantity_non_negative"),
        CheckConstraint("received_quantity <= ordered_quantity", name="received_not_over_ordered"),
        CheckConstraint("invoiced_quantity >= 0", name="invoiced_quantity_non_negative"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 1", name="tax_rate_range"),
        CheckConstraint("line_amount >= 0", name="line_amount_non_negative"),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    request_line_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_request_lines.id"), index=True
    )
    line_no: Mapped[int] = mapped_column(Integer)
    material_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("md_materials.id"), nullable=True, index=True
    )
    category_id: Mapped[UUID] = mapped_column(ForeignKey("md_categories.id"), index=True)
    description: Mapped[str] = mapped_column(String(500))
    specification: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    unit_code: Mapped[str] = mapped_column(ForeignKey("md_units.code"), index=True)
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    invoiced_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    line_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
