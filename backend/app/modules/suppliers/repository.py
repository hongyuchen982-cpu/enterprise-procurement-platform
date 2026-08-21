from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.supplier import (
    QualificationStatus,
    RiskLevel,
    SupplierRiskReview,
    SupplierSnapshot,
    SupplierStatus,
)
from app.core.database import session_scope
from app.modules.suppliers.models import SupplierRecord, SupplierRiskReviewRecord

_ORG_ID = UUID("22222222-2222-4222-8222-222222222222")


def _snapshot(
    supplier_id: str,
    legal_name: str,
    status: SupplierStatus,
    qualification_status: QualificationStatus,
    risk_level: RiskLevel,
    category_id: str,
    updated_at: datetime,
    *,
    is_frozen: bool = False,
    version: int = 1,
) -> SupplierSnapshot:
    return SupplierSnapshot(
        supplier_id=UUID(supplier_id),
        org_id=_ORG_ID,
        legal_name=legal_name,
        status=status,
        qualification_status=qualification_status,
        category_ids=[UUID(category_id)],
        risk_level=risk_level,
        is_frozen=is_frozen,
        version=version,
        updated_at=updated_at,
    )


_SUPPLIER_SNAPSHOTS = (
    _snapshot(
        "11111111-1111-4111-8111-111111111111",
        "Demo Precision Manufacturing Co., Ltd.",
        SupplierStatus.ACTIVE,
        QualificationStatus.QUALIFIED,
        RiskLevel.LOW,
        "33333333-3333-4333-8333-333333333333",
        datetime(2026, 8, 18, 8, 0, tzinfo=UTC),
        version=3,
    ),
    _snapshot(
        "11111111-1111-4111-8111-111111111112",
        "Northstar Industrial Components Ltd.",
        SupplierStatus.ACTIVE,
        QualificationStatus.REVIEWING,
        RiskLevel.MEDIUM,
        "33333333-3333-4333-8333-333333333334",
        datetime(2026, 8, 18, 6, 30, tzinfo=UTC),
        version=2,
    ),
    _snapshot(
        "11111111-1111-4111-8111-111111111113",
        "Shenzhen Apex Packaging Technology Co., Ltd.",
        SupplierStatus.PENDING,
        QualificationStatus.INCOMPLETE,
        RiskLevel.MEDIUM,
        "33333333-3333-4333-8333-333333333335",
        datetime(2026, 8, 17, 15, 45, tzinfo=UTC),
    ),
    _snapshot(
        "11111111-1111-4111-8111-111111111114",
        "Harbor Logistics Services Group",
        SupplierStatus.SUSPENDED,
        QualificationStatus.EXPIRED,
        RiskLevel.HIGH,
        "33333333-3333-4333-8333-333333333336",
        datetime(2026, 8, 16, 10, 20, tzinfo=UTC),
        is_frozen=True,
        version=5,
    ),
    _snapshot(
        "11111111-1111-4111-8111-111111111115",
        "Evergreen Office Supplies Co.",
        SupplierStatus.DRAFT,
        QualificationStatus.INCOMPLETE,
        RiskLevel.LOW,
        "33333333-3333-4333-8333-333333333337",
        datetime(2026, 8, 15, 13, 10, tzinfo=UTC),
    ),
)


def _seed_demo_suppliers(session: Session) -> None:
    seeded = False
    for snapshot in _SUPPLIER_SNAPSHOTS:
        if session.get(SupplierRecord, str(snapshot.supplier_id)) is not None:
            continue
        session.add(
            SupplierRecord(
                supplier_id=str(snapshot.supplier_id),
                org_id=str(snapshot.org_id),
                legal_name=snapshot.legal_name,
                status=snapshot.status,
                qualification_status=snapshot.qualification_status,
                category_ids=[str(category_id) for category_id in snapshot.category_ids],
                risk_level=snapshot.risk_level,
                is_frozen=snapshot.is_frozen,
                version=snapshot.version,
                updated_at=snapshot.updated_at,
            )
        )
        seeded = True
    if seeded:
        session.flush()


def _snapshot_from_record(record: SupplierRecord) -> SupplierSnapshot:
    return SupplierSnapshot(
        supplier_id=UUID(str(record.supplier_id)),
        org_id=UUID(str(record.org_id)),
        legal_name=record.legal_name,
        status=SupplierStatus(record.status),
        qualification_status=QualificationStatus(record.qualification_status),
        category_ids=[UUID(str(category_id)) for category_id in record.category_ids],
        risk_level=RiskLevel(record.risk_level),
        is_frozen=record.is_frozen,
        version=record.version,
        updated_at=record.updated_at,
    )


def _review_from_record(record: SupplierRiskReviewRecord) -> SupplierRiskReview:
    return SupplierRiskReview(
        review_id=UUID(str(record.review_id)),
        supplier_id=UUID(str(record.supplier_id)),
        conclusion=record.conclusion,
        note=record.note,
        reviewed_by=record.reviewed_by,
        created_at=record.created_at,
    )


def list_snapshots() -> list[SupplierSnapshot]:
    with session_scope() as session:
        _seed_demo_suppliers(session)
        records = session.scalars(
            select(SupplierRecord).order_by(SupplierRecord.updated_at.desc())
        ).all()
        return [_snapshot_from_record(record) for record in records]


def get_snapshot(supplier_id: UUID) -> SupplierSnapshot | None:
    with session_scope() as session:
        _seed_demo_suppliers(session)
        record = session.get(SupplierRecord, str(supplier_id))
        if record is None:
            return None
        return _snapshot_from_record(record)


def supplier_exists(supplier_id: UUID) -> bool:
    with session_scope() as session:
        _seed_demo_suppliers(session)
        return session.get(SupplierRecord, str(supplier_id)) is not None


def append_risk_review(review: SupplierRiskReview) -> SupplierRiskReview:
    with session_scope() as session:
        if session.get(SupplierRecord, str(review.supplier_id)) is None:
            return review
        latest_created_at = session.scalar(
            select(SupplierRiskReviewRecord.created_at)
            .where(SupplierRiskReviewRecord.supplier_id == str(review.supplier_id))
            .order_by(SupplierRiskReviewRecord.created_at.desc())
            .limit(1)
        )
        created_at = review.created_at
        if latest_created_at is not None:
            latest = (
                latest_created_at.replace(tzinfo=UTC)
                if latest_created_at.tzinfo is None
                else latest_created_at
            )
            if created_at.replace(microsecond=0) <= latest.replace(microsecond=0):
                created_at = latest + timedelta(seconds=1)
                review = review.model_copy(update={"created_at": created_at})
        session.add(
            SupplierRiskReviewRecord(
                review_id=str(review.review_id),
                supplier_id=str(review.supplier_id),
                conclusion=review.conclusion,
                note=review.note,
                reviewed_by=review.reviewed_by,
                created_at=created_at,
            )
        )
        return review


def list_risk_reviews(supplier_id: UUID) -> list[SupplierRiskReview] | None:
    with session_scope() as session:
        _seed_demo_suppliers(session)
        if session.get(SupplierRecord, str(supplier_id)) is None:
            return None
        records = session.scalars(
            select(SupplierRiskReviewRecord)
            .where(SupplierRiskReviewRecord.supplier_id == str(supplier_id))
            .order_by(SupplierRiskReviewRecord.created_at.asc())
        ).all()
        return [_review_from_record(record) for record in records]
