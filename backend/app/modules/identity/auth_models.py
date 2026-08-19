from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionedMixin,
)


class UserCredential(TimestampMixin, VersionedMixin, Base):
    __tablename__ = "iam_user_credentials"
    __table_args__ = (CheckConstraint("failed_attempts >= 0", name="failed_attempts_nonnegative"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("iam_users.id"), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthSession(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "iam_auth_sessions"
    __table_args__ = (
        CheckConstraint("length(token_hash) = 64", name="token_hash_length"),
        CheckConstraint("expires_at > created_at", name="expires_after_creation"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("iam_users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
