from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.contracts.supplier import (
    RiskLevel,
    SupplierRiskReview,
    SupplierRiskReviewCreate,
    SupplierSnapshot,
    SupplierStatus,
    SupplierSummary,
)
from app.modules.suppliers import repository


def list_supplier_summaries(
    keyword: str | None = None,
    risk_level: RiskLevel | None = None,
    status: SupplierStatus | None = None,
    high_risk_only: bool = False,
) -> list[SupplierSummary]:
    normalized_keyword = keyword.strip().lower() if keyword else None
    snapshots = repository.list_snapshots()
    if normalized_keyword:
        snapshots = [
            snapshot for snapshot in snapshots if normalized_keyword in snapshot.legal_name.lower()
        ]
    if risk_level is not None:
        snapshots = [snapshot for snapshot in snapshots if snapshot.risk_level == risk_level]
    if status is not None:
        snapshots = [snapshot for snapshot in snapshots if snapshot.status == status]
    if high_risk_only:
        snapshots = [
            snapshot
            for snapshot in snapshots
            if snapshot.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        ]

    return [
        SupplierSummary(
            supplier_id=snapshot.supplier_id,
            legal_name=snapshot.legal_name,
            status=snapshot.status,
            qualification_status=snapshot.qualification_status,
            risk_level=snapshot.risk_level,
            is_frozen=snapshot.is_frozen,
            updated_at=snapshot.updated_at,
        )
        for snapshot in snapshots
    ]


def get_supplier_snapshot(supplier_id: UUID) -> SupplierSnapshot | None:
    return repository.get_snapshot(supplier_id)


def create_supplier_risk_review(
    supplier_id: UUID, command: SupplierRiskReviewCreate
) -> SupplierRiskReview | None:
    if not repository.supplier_exists(supplier_id):
        return None

    review = SupplierRiskReview(
        review_id=uuid4(),
        supplier_id=supplier_id,
        conclusion=command.conclusion,
        note=command.note,
        reviewed_by=command.reviewed_by,
        created_at=datetime.now(UTC),
    )
    return repository.append_risk_review(review)


def get_latest_supplier_risk_review(supplier_id: UUID) -> SupplierRiskReview | None:
    reviews = list_supplier_risk_reviews(supplier_id)
    if reviews is None:
        return None
    return reviews[0] if reviews else None


def list_supplier_risk_reviews(supplier_id: UUID) -> list[SupplierRiskReview] | None:
    reviews = repository.list_risk_reviews(supplier_id)
    if reviews is None:
        return None
    return list(reversed(reviews))
