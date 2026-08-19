from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionedMixin,
)


class MasterRecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class Category(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "md_categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("md_categories.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20), default=MasterRecordStatus.ACTIVE, server_default=MasterRecordStatus.ACTIVE
    )

    @validates("code")
    def normalize_code(self, _key: str, value: str) -> str:
        return _normalize_code(value, 64)


class Unit(TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "md_units"
    __table_args__ = (
        CheckConstraint("decimal_places BETWEEN 0 AND 6", name="decimal_places_range"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),
    )

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    decimal_places: Mapped[int] = mapped_column(Integer, default=2, server_default="2")
    status: Mapped[str] = mapped_column(
        String(20), default=MasterRecordStatus.ACTIVE, server_default=MasterRecordStatus.ACTIVE
    )

    @validates("code")
    def normalize_code(self, _key: str, value: str) -> str:
        return _normalize_code(value, 20)


class Material(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "md_materials"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[UUID] = mapped_column(ForeignKey("md_categories.id"), index=True)
    unit_code: Mapped[str] = mapped_column(ForeignKey("md_units.code"), index=True)
    specification: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=MasterRecordStatus.ACTIVE, server_default=MasterRecordStatus.ACTIVE
    )

    @validates("code")
    def normalize_code(self, _key: str, value: str) -> str:
        return _normalize_code(value, 64)


def _normalize_code(value: str, maximum_length: int) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("code cannot be empty")
    if len(normalized) > maximum_length:
        raise ValueError(f"code cannot exceed {maximum_length} characters")
    return normalized
