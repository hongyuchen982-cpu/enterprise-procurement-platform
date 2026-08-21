from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UUIDPrimaryKeyMixin


class AuditEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "business_audit_log"
    __table_args__ = (
        CheckConstraint("actor_type IN ('USER', 'AGENT', 'SYSTEM')", name="actor_type"),
        CheckConstraint(
            "source IN ('API', 'WORKER', 'TOOL', 'INTEGRATION')",
            name="source",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    object_type: Mapped[str] = mapped_column(String(80), index=True)
    object_id: Mapped[UUID] = mapped_column(index=True)
    object_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("iam_memberships.id"), nullable=True, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("iam_users.id"), nullable=True, index=True
    )
    actor_type: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20))
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
