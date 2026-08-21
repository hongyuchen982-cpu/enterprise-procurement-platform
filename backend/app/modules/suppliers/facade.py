from uuid import UUID

from app.contracts.supplier import (
    RiskLevel,
    SupplierRiskReview,
    SupplierRiskReviewCreate,
    SupplierSnapshot,
    SupplierStatus,
    SupplierSummary,
)
from app.modules.suppliers.service import (
    create_supplier_risk_review as service_create_supplier_risk_review,
)
from app.modules.suppliers.service import (
    get_latest_supplier_risk_review as service_get_latest_supplier_risk_review,
)
from app.modules.suppliers.service import (
    get_supplier_snapshot as service_get_supplier_snapshot,
)
from app.modules.suppliers.service import (
    list_supplier_risk_reviews as service_list_supplier_risk_reviews,
)
from app.modules.suppliers.service import (
    list_supplier_summaries as service_list_supplier_summaries,
)


def list_supplier_summaries(
    keyword: str | None = None,
    risk_level: RiskLevel | None = None,
    status: SupplierStatus | None = None,
    high_risk_only: bool = False,
) -> list[SupplierSummary]:
    return service_list_supplier_summaries(
        keyword=keyword,
        risk_level=risk_level,
        status=status,
        high_risk_only=high_risk_only,
    )


def get_supplier_snapshot(supplier_id: UUID) -> SupplierSnapshot | None:
    return service_get_supplier_snapshot(supplier_id)


def create_supplier_risk_review(
    supplier_id: UUID, command: SupplierRiskReviewCreate
) -> SupplierRiskReview | None:
    return service_create_supplier_risk_review(supplier_id, command)


def get_latest_supplier_risk_review(supplier_id: UUID) -> SupplierRiskReview | None:
    return service_get_latest_supplier_risk_review(supplier_id)


def list_supplier_risk_reviews(supplier_id: UUID) -> list[SupplierRiskReview] | None:
    return service_list_supplier_risk_reviews(supplier_id)
