from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel
from app.contracts.risk import SupplierRiskAction
from app.contracts.supplier import RiskLevel


class ActionItemPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReportMetric(ContractModel):
    key: str
    label: str
    value: int
    description: str


class SupplierRiskHotspot(ContractModel):
    supplier_id: UUID
    supplier_name: str
    score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    recommended_action: SupplierRiskAction


class ReportNextAction(ContractModel):
    key: str
    label: str
    description: str
    target_module: str


class PlatformCapability(ContractModel):
    key: str
    label: str
    description: str
    status: str
    owner_module: str
    endpoint: str


class OperationsReport(ContractModel):
    generated_at: datetime
    metrics: list[ReportMetric]
    platform_capabilities: list[PlatformCapability]
    top_risk_suppliers: list[SupplierRiskHotspot]
    next_actions: list[ReportNextAction]


class WorkbenchActionItem(ContractModel):
    item_id: str
    item_type: str
    title: str
    description: str
    priority: ActionItemPriority
    target_module: str
    target_id: str
    status_label: str
    created_at: datetime
    due_at: datetime | None = None
