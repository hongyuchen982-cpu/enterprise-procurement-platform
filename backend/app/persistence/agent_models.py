from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentTaskRecord(Base):
    __tablename__ = "b_agent_tasks"
    __table_args__ = (
        Index("ix_b_agent_tasks_org_status", "org_id", "status"),
        Index("ix_b_agent_tasks_status_updated", "status", "updated_at"),
        Index("ix_b_agent_tasks_trace", "trace_id"),
    )

    task_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    agent_type: Mapped[str] = mapped_column(String(80), nullable=False)
    org_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(String(36), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    subject_refs: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    trace_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskEventRecord(Base):
    __tablename__ = "b_agent_task_events"
    __table_args__ = (
        Index("ix_b_agent_task_events_task_created", "task_id", "created_at"),
        Index("ix_b_agent_task_events_type_created", "event_type", "created_at"),
    )

    event_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("b_agent_tasks.task_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentConfirmationRecord(Base):
    __tablename__ = "b_agent_confirmations"
    __table_args__ = (
        Index("ix_b_agent_confirmations_status_expires", "status", "expires_at"),
        Index("ix_b_agent_confirmations_task_status", "task_id", "status"),
    )

    confirmation_id: Mapped[UUID] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("b_agent_tasks.task_id"), nullable=False
    )
    tool_call_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    target_refs: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    target_versions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    required_permission: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_by: Mapped[UUID | None] = mapped_column(String(36), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
