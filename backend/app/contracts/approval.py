from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.contracts.common import ContractModel
from app.contracts.procurement import ProcurementRequestSnapshot


class ApprovalRecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ApprovalInstanceStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalNodeStatus(StrEnum):
    WAITING = "WAITING"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class ApprovalDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ApprovalActionType(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    TRANSFER = "TRANSFER"


class ApprovalTemplateStepInput(ContractModel):
    name: str = Field(min_length=1, max_length=200)
    approver_membership_id: UUID

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("step name cannot be blank")
        return normalized


class ApprovalTemplateCreate(ContractModel):
    organization_id: UUID
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    steps: list[ApprovalTemplateStepInput] = Field(min_length=1, max_length=20)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("template name cannot be blank")
        return normalized


class ApprovalTemplateStepSnapshot(ContractModel):
    step_id: UUID
    step_no: int = Field(ge=1)
    name: str
    approver_membership_id: UUID


class ApprovalTemplateSnapshot(ContractModel):
    template_id: UUID
    organization_id: UUID
    code: str
    name: str
    status: ApprovalRecordStatus
    steps: list[ApprovalTemplateStepSnapshot]
    version: int = Field(ge=1)


class ApprovalStart(ContractModel):
    request_id: UUID
    template_id: UUID
    expected_request_version: int = Field(ge=1)


class ApprovalDecisionInput(ContractModel):
    decision: ApprovalDecision
    expected_version: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ApprovalTransferInput(ContractModel):
    target_membership_id: UUID
    expected_version: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ApprovalCancelInput(ContractModel):
    expected_version: int = Field(ge=1)


class ApprovalNodeSnapshot(ContractModel):
    node_id: UUID
    step_no: int = Field(ge=1)
    name: str
    approver_membership_id: UUID
    status: ApprovalNodeStatus
    decision_comment: str | None = None
    decided_by_membership_id: UUID | None = None
    decided_at: datetime | None = None


class ApprovalActionSnapshot(ContractModel):
    action_id: UUID
    node_id: UUID
    action: ApprovalActionType
    actor_membership_id: UUID
    target_membership_id: UUID | None = None
    comment: str | None = None
    created_at: datetime


class ApprovalInstanceSnapshot(ContractModel):
    instance_id: UUID
    organization_id: UUID
    request_id: UUID
    template_id: UUID
    status: ApprovalInstanceStatus
    current_step_no: int = Field(ge=1)
    request_version: int = Field(ge=1)
    request_snapshot: ProcurementRequestSnapshot
    nodes: list[ApprovalNodeSnapshot]
    actions: list[ApprovalActionSnapshot] = Field(default_factory=list)
    version: int = Field(ge=1)


class ApprovalDeleteResult(ContractModel):
    deleted: Literal[True] = True
