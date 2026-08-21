from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionedMixin


class InventoryMovementRecordType(StrEnum):
    RECEIPT = "RECEIPT"


class InventoryBalance(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "material_id",
            name="uq_inventory_balances_org_material",
        ),
        CheckConstraint("on_hand_quantity >= 0", name="on_hand_quantity_non_negative"),
        CheckConstraint(
            "total_received_quantity >= 0",
            name="total_received_quantity_non_negative",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    material_id: Mapped[UUID] = mapped_column(ForeignKey("md_materials.id"), index=True)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("md_categories.id"), index=True)
    unit_code: Mapped[str] = mapped_column(ForeignKey("md_units.code"), index=True)
    on_hand_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    total_received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))


class InventoryMovement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_line_id",
            name="uq_inventory_movements_source_line",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("balance_after >= 0", name="balance_after_non_negative"),
        CheckConstraint("movement_type IN ('RECEIPT')", name="movement_type"),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    material_id: Mapped[UUID] = mapped_column(ForeignKey("md_materials.id"), index=True)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("md_categories.id"), index=True)
    unit_code: Mapped[str] = mapped_column(ForeignKey("md_units.code"), index=True)
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[UUID] = mapped_column(index=True)
    source_line_id: Mapped[UUID] = mapped_column(index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
