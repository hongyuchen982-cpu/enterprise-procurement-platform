from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class ReceiptRecordStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InspectionRecordStatus(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "goods_receipts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'COMPLETED', 'CANCELLED')",
            name="status",
        ),
    )

    receipt_no: Mapped[str] = mapped_column(String(40), unique=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    receiver_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("iam_memberships.id"), index=True
    )
    receiver_id: Mapped[UUID] = mapped_column(ForeignKey("iam_users.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=ReceiptRecordStatus.DRAFT,
        server_default=ReceiptRecordStatus.DRAFT,
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lines: Mapped[list["ReceiptLine"]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptLine.line_no",
    )


class ReceiptLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "goods_receipt_lines"
    __table_args__ = (
        UniqueConstraint("receipt_id", "line_no", name="uq_goods_receipt_lines_receipt_line_no"),
        UniqueConstraint(
            "receipt_id",
            "order_line_id",
            name="uq_goods_receipt_lines_receipt_order_line",
        ),
        CheckConstraint("line_no > 0", name="line_no_positive"),
        CheckConstraint("received_quantity > 0", name="received_quantity_positive"),
        CheckConstraint("accepted_quantity >= 0", name="accepted_quantity_non_negative"),
        CheckConstraint("rejected_quantity >= 0", name="rejected_quantity_non_negative"),
        CheckConstraint(
            "received_quantity = accepted_quantity + rejected_quantity",
            name="quantity_balance",
        ),
        CheckConstraint(
            "inspection_status IN ('NOT_REQUIRED', 'PENDING', 'PASSED', 'FAILED')",
            name="inspection_status",
        ),
    )

    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("goods_receipts.id", ondelete="CASCADE"), index=True
    )
    order_line_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_order_lines.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    accepted_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    rejected_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    inspection_status: Mapped[str] = mapped_column(String(20))
    receipt: Mapped[Receipt] = relationship(back_populates="lines")
