from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class SupplierStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"
    EXITED = "EXITED"


class QualificationStatus(StrEnum):
    INCOMPLETE = "INCOMPLETE"
    REVIEWING = "REVIEWING"
    QUALIFIED = "QUALIFIED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskReviewConclusion(StrEnum):
    ACCEPTABLE = "ACCEPTABLE"
    MONITOR = "MONITOR"
    ESCALATE = "ESCALATE"
    FREEZE_RECOMMENDED = "FREEZE_RECOMMENDED"


class SupplierSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    supplier_id: UUID
    org_id: UUID
    legal_name: str
    status: SupplierStatus
    qualification_status: QualificationStatus
    category_ids: list[UUID]
    risk_level: RiskLevel
    is_frozen: bool
    version: int = Field(ge=1)
    updated_at: datetime


class SupplierSummary(ContractModel):
    schema_version: Literal["1"] = "1"
    supplier_id: UUID
    legal_name: str
    status: SupplierStatus
    qualification_status: QualificationStatus
    risk_level: RiskLevel
    is_frozen: bool
    updated_at: datetime


class SupplierRiskReviewCreate(ContractModel):
    conclusion: RiskReviewConclusion
    note: str = Field(min_length=1, max_length=1000)
    reviewed_by: str = Field(min_length=1, max_length=80)


class SupplierRiskReview(ContractModel):
    review_id: UUID
    supplier_id: UUID
    conclusion: RiskReviewConclusion
    note: str
    reviewed_by: str
    created_at: datetime
