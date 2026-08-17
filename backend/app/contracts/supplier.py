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
