from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel
from app.contracts.supplier import RiskLevel


class SupplierRiskAction(StrEnum):
    APPROVE = "APPROVE"
    MONITOR = "MONITOR"
    ESCALATE = "ESCALATE"
    FREEZE = "FREEZE"


class RiskFactor(ContractModel):
    code: str
    label: str
    impact_score: int


class SupplierRiskAssessment(ContractModel):
    assessment_id: UUID
    supplier_id: UUID
    org_id: UUID
    supplier_name: str
    score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    recommended_action: SupplierRiskAction
    factors: list[RiskFactor]
    summary: str
    assessed_by: str
    created_at: datetime
    updated_at: datetime


class SupplierRiskAssessmentRefresh(ContractModel):
    assessed_by: str = Field(default="Member B Risk Engine", min_length=1, max_length=80)
