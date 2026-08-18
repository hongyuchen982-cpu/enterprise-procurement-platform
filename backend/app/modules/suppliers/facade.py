from datetime import UTC, datetime
from uuid import UUID

from app.contracts.supplier import (
    QualificationStatus,
    RiskLevel,
    SupplierSnapshot,
    SupplierStatus,
    SupplierSummary,
)

_SUPPLIER_ID = UUID("11111111-1111-4111-8111-111111111111")
_ORG_ID = UUID("22222222-2222-4222-8222-222222222222")
_CATEGORY_ID = UUID("33333333-3333-4333-8333-333333333333")

_SNAPSHOTS: dict[UUID, SupplierSnapshot] = {
    _SUPPLIER_ID: SupplierSnapshot(
        supplier_id=_SUPPLIER_ID,
        org_id=_ORG_ID,
        legal_name="Demo Precision Manufacturing Co., Ltd.",
        status=SupplierStatus.ACTIVE,
        qualification_status=QualificationStatus.QUALIFIED,
        category_ids=[_CATEGORY_ID],
        risk_level=RiskLevel.LOW,
        is_frozen=False,
        version=1,
        updated_at=datetime(2026, 8, 18, tzinfo=UTC),
    )
}


def list_supplier_summaries() -> list[SupplierSummary]:
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
        for snapshot in _SNAPSHOTS.values()
    ]


def get_supplier_snapshot(supplier_id: UUID) -> SupplierSnapshot | None:
    return _SNAPSHOTS.get(supplier_id)
