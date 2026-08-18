from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database import (
    Base,
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionedMixin,
)


class RecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "iam_organizations"
    __table_args__ = (CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),)

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("iam_organizations.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20), default=RecordStatus.ACTIVE, server_default=RecordStatus.ACTIVE
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "iam_users"
    __table_args__ = (CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),)

    login_name: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=RecordStatus.ACTIVE, server_default=RecordStatus.ACTIVE
    )

    @validates("login_name")
    def normalize_login_name(self, _key: str, value: str) -> str:
        normalized = value.strip().casefold()
        if not normalized:
            raise ValueError("login name cannot be empty")
        if len(normalized) > 100:
            raise ValueError("login name cannot exceed 100 characters")
        return normalized


class Membership(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "iam_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("iam_users.id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("iam_organizations.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=RecordStatus.ACTIVE, server_default=RecordStatus.ACTIVE
    )


class Role(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "iam_roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20), default=RecordStatus.ACTIVE, server_default=RecordStatus.ACTIVE
    )


class Permission(TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "iam_permissions"

    code: Mapped[str] = mapped_column(String(160), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


class RolePermission(CreatedAtMixin, Base):
    __tablename__ = "iam_role_permissions"

    role_id: Mapped[UUID] = mapped_column(ForeignKey("iam_roles.id"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("iam_permissions.code"), primary_key=True
    )


class MembershipRole(CreatedAtMixin, Base):
    __tablename__ = "iam_membership_roles"

    membership_id: Mapped[UUID] = mapped_column(ForeignKey("iam_memberships.id"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("iam_roles.id"), primary_key=True)


class RoleScopeGrant(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "iam_role_scope_grants"
    __table_args__ = (
        UniqueConstraint("role_id", "scope_type", "scope_ref"),
        CheckConstraint(
            "scope_type IN ('ALL', 'ORGANIZATION', 'ORGANIZATION_TREE', "
            "'DEPARTMENT', 'SELF', 'CATEGORY', 'SUPPLIER')",
            name="scope_type",
        ),
        CheckConstraint(
            "scope_type NOT IN ('CATEGORY', 'SUPPLIER') OR scope_ref IS NOT NULL",
            name="specific_scope_ref",
        ),
    )

    role_id: Mapped[UUID] = mapped_column(ForeignKey("iam_roles.id"), index=True)
    scope_type: Mapped[str] = mapped_column(String(40))
    scope_ref: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
