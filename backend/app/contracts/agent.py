from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.contracts.common import BusinessObjectRef, ContractModel, ErrorObject


class AgentTaskStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    HANDOFF = "HANDOFF"


class RiskLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ToolResultStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    HANDOFF = "HANDOFF"


class ConfirmationStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


class AgentTask(ContractModel):
    task_id: UUID
    agent_type: str
    org_id: UUID
    requested_by: UUID
    goal: str
    subject_refs: list[BusinessObjectRef]
    status: AgentTaskStatus
    trace_id: UUID
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None


class AgentTaskCreate(ContractModel):
    agent_type: str
    org_id: UUID
    requested_by: UUID
    goal: str = Field(min_length=1, max_length=2000)
    subject_refs: list[BusinessObjectRef] = Field(default_factory=list)


class AgentTaskStatusUpdate(ContractModel):
    status: AgentTaskStatus
    error_code: str | None = Field(default=None, max_length=80)


class ConfirmationRequestDecision(ContractModel):
    status: ConfirmationStatus
    confirmed_by: UUID | None = None
    rejection_reason: str | None = Field(default=None, max_length=500)


class AgentTaskEvent(ContractModel):
    event_id: UUID
    task_id: UUID
    event_type: str
    from_status: AgentTaskStatus | None = None
    to_status: AgentTaskStatus
    message: str
    created_at: datetime


class ToolDefinition(ContractModel):
    name: str
    version: str
    owner_module: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_permissions: list[str]
    risk_level: RiskLevel
    idempotency_required: bool
    timeout_seconds: int = Field(ge=1, le=300)
    enabled: bool = True


class ToolResult(ContractModel):
    tool_call_id: UUID
    tool_name: str
    tool_version: str
    status: ToolResultStatus
    data: dict[str, Any] | None = None
    error: ErrorObject | None = None
    business_object_refs: list[BusinessObjectRef]
    trace_id: UUID
    started_at: datetime
    completed_at: datetime | None = None


class ConfirmationRequest(ContractModel):
    confirmation_id: UUID
    task_id: UUID
    tool_call_id: UUID
    risk_level: RiskLevel
    proposed_action: str
    target_refs: list[BusinessObjectRef]
    target_versions: dict[UUID, int]
    input_digest: str
    required_permission: str
    status: ConfirmationStatus
    expires_at: datetime
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None
    rejection_reason: str | None = None
