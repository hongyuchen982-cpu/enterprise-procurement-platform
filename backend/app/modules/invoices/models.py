from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
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


class InvoiceRecordStatus(StrEnum):
    DRAFT = "DRAFT"
    MATCHED = "MATCHED"
    EXCEPTION = "EXCEPTION"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "supplier_invoices"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "supplier_id",
            "invoice_no",
            name="uq_supplier_invoices_org_supplier_number",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'MATCHED', 'EXCEPTION', 'APPROVED', 'CANCELLED')",
            name="status",
        ),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
    )

    invoice_no: Mapped[str] = mapped_column(String(80))
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    supplier_id: Mapped[UUID] = mapped_column(index=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(
        String(20),
        default=InvoiceRecordStatus.DRAFT,
        server_default=InvoiceRecordStatus.DRAFT,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("iam_memberships.id"), nullable=True, index=True
    )
    approval_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.line_no",
    )


class InvoiceLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_invoice_lines"
    __table_args__ = (
        UniqueConstraint("invoice_id", "line_no", name="uq_supplier_invoice_lines_invoice_line_no"),
        UniqueConstraint(
            "invoice_id",
            "order_line_id",
            name="uq_supplier_invoice_lines_invoice_order_line",
        ),
        CheckConstraint("line_no > 0", name="line_no_positive"),
        CheckConstraint("invoiced_quantity > 0", name="invoiced_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 1", name="tax_rate_range"),
        CheckConstraint("line_amount >= 0", name="line_amount_non_negative"),
    )

    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplier_invoices.id", ondelete="CASCADE"), index=True
    )
    order_line_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_order_lines.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    invoiced_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    line_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    quantity_matched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    price_matched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    invoice: Mapped[Invoice] = relationship(back_populates="lines")
