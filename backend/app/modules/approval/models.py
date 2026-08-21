from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
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


class ApprovalTemplateRecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ApprovalInstanceRecordStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalNodeRecordStatus(StrEnum):
    WAITING = "WAITING"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class ApprovalTemplate(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, SoftDeleteMixin, Base):
    __tablename__ = "approval_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="status"),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20),
        default=ApprovalTemplateRecordStatus.ACTIVE,
        server_default=ApprovalTemplateRecordStatus.ACTIVE,
    )
    steps: Mapped[list["ApprovalTemplateStep"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ApprovalTemplateStep.step_no",
    )


class ApprovalTemplateStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_template_steps"
    __table_args__ = (
        UniqueConstraint("template_id", "step_no"),
        CheckConstraint("step_no > 0", name="step_no_positive"),
    )

    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("approval_templates.id", ondelete="CASCADE"), index=True
    )
    step_no: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    approver_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("iam_memberships.id"), index=True
    )
    template: Mapped[ApprovalTemplate] = relationship(back_populates="steps")


class ApprovalInstance(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "approval_instances"
    __table_args__ = (
        UniqueConstraint("request_id"),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="status",
        ),
        CheckConstraint("current_step_no > 0", name="current_step_no_positive"),
        CheckConstraint("request_version > 0", name="request_version_positive"),
    )

    organization_id: Mapped[UUID] = mapped_column(ForeignKey("iam_organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("procurement_requests.id"), index=True)
    template_id: Mapped[UUID] = mapped_column(ForeignKey("approval_templates.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=ApprovalInstanceRecordStatus.PENDING,
        server_default=ApprovalInstanceRecordStatus.PENDING,
    )
    current_step_no: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    request_version: Mapped[int] = mapped_column(Integer)
    request_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    nodes: Mapped[list["ApprovalNode"]] = relationship(
        back_populates="instance",
        cascade="all, delete-orphan",
        order_by="ApprovalNode.step_no",
    )
    actions: Mapped[list["ApprovalAction"]] = relationship(
        back_populates="instance",
        cascade="all, delete-orphan",
        order_by="ApprovalAction.created_at",
    )


class ApprovalNode(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "approval_nodes"
    __table_args__ = (
        UniqueConstraint("instance_id", "step_no"),
        CheckConstraint("step_no > 0", name="step_no_positive"),
        CheckConstraint(
            "status IN ('WAITING', 'PENDING', 'APPROVED', 'REJECTED', 'SKIPPED')",
            name="status",
        ),
    )

    instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("approval_instances.id", ondelete="CASCADE"), index=True
    )
    step_no: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    approver_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("iam_memberships.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    decision_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    decided_by_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("iam_memberships.id"), nullable=True, index=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    instance: Mapped[ApprovalInstance] = relationship(back_populates="nodes")


class ApprovalAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_actions"
    __table_args__ = (
        CheckConstraint("action IN ('APPROVE', 'REJECT', 'TRANSFER')", name="action"),
    )

    instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("approval_instances.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[UUID] = mapped_column(
        ForeignKey("approval_nodes.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(20))
    actor_membership_id: Mapped[UUID] = mapped_column(ForeignKey("iam_memberships.id"), index=True)
    target_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("iam_memberships.id"), nullable=True, index=True
    )
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    instance: Mapped[ApprovalInstance] = relationship(back_populates="actions")
