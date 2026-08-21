from uuid import UUID

from app.contracts.risk import SupplierRiskAssessment
from app.modules.risk.service import (
    get_supplier_risk_assessment as service_get_supplier_risk_assessment,
)
from app.modules.risk.service import (
    list_supplier_risk_assessments as service_list_supplier_risk_assessments,
)


def get_supplier_risk_assessment(
    supplier_id: UUID,
) -> SupplierRiskAssessment | None:
    return service_get_supplier_risk_assessment(supplier_id)


def list_supplier_risk_assessments(
    supplier_id: UUID | None = None,
) -> list[SupplierRiskAssessment]:
    return service_list_supplier_risk_assessments(supplier_id=supplier_id)
