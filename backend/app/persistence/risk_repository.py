from datetime import UTC, timedelta
from uuid import UUID

from sqlalchemy import select

from app.contracts.risk import RiskFactor, SupplierRiskAction, SupplierRiskAssessment
from app.contracts.supplier import RiskLevel
from app.core.database import session_scope
from app.modules.risk.models import SupplierRiskAssessmentRecord


def _assessment_from_record(
    record: SupplierRiskAssessmentRecord,
) -> SupplierRiskAssessment:
    return SupplierRiskAssessment(
        assessment_id=UUID(str(record.assessment_id)),
        supplier_id=UUID(str(record.supplier_id)),
        org_id=UUID(str(record.org_id)),
        supplier_name=record.supplier_name,
        score=record.score,
        risk_level=RiskLevel(record.risk_level),
        recommended_action=SupplierRiskAction(record.recommended_action),
        factors=[RiskFactor(**factor) for factor in record.factors],
        summary=record.summary,
        assessed_by=record.assessed_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _record_from_assessment(
    assessment: SupplierRiskAssessment,
) -> SupplierRiskAssessmentRecord:
    return SupplierRiskAssessmentRecord(
        assessment_id=str(assessment.assessment_id),
        supplier_id=str(assessment.supplier_id),
        org_id=str(assessment.org_id),
        supplier_name=assessment.supplier_name,
        score=assessment.score,
        risk_level=assessment.risk_level,
        recommended_action=assessment.recommended_action,
        factors=[factor.model_dump() for factor in assessment.factors],
        summary=assessment.summary,
        assessed_by=assessment.assessed_by,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )


def get_latest_assessment(
    supplier_id: UUID,
) -> SupplierRiskAssessment | None:
    with session_scope() as session:
        record = session.scalar(
            select(SupplierRiskAssessmentRecord)
            .where(SupplierRiskAssessmentRecord.supplier_id == str(supplier_id))
            .order_by(SupplierRiskAssessmentRecord.updated_at.desc())
            .limit(1)
        )
        if record is None:
            return None
        return _assessment_from_record(record)


def list_latest_assessments() -> list[SupplierRiskAssessment]:
    with session_scope() as session:
        records = session.scalars(
            select(SupplierRiskAssessmentRecord).order_by(
                SupplierRiskAssessmentRecord.updated_at.desc()
            )
        ).all()
        latest_by_supplier: dict[str, SupplierRiskAssessmentRecord] = {}
        for record in records:
            latest_by_supplier.setdefault(str(record.supplier_id), record)
        return [
            _assessment_from_record(record)
            for record in latest_by_supplier.values()
        ]


def append_assessment(
    assessment: SupplierRiskAssessment,
) -> SupplierRiskAssessment:
    with session_scope() as session:
        latest_updated_at = session.scalar(
            select(SupplierRiskAssessmentRecord.updated_at)
            .where(SupplierRiskAssessmentRecord.supplier_id == str(assessment.supplier_id))
            .order_by(SupplierRiskAssessmentRecord.updated_at.desc())
            .limit(1)
        )
        if latest_updated_at is not None:
            latest = (
                latest_updated_at.replace(tzinfo=UTC)
                if latest_updated_at.tzinfo is None
                else latest_updated_at
            )
            if assessment.updated_at.replace(microsecond=0) <= latest.replace(microsecond=0):
                updated_at = latest + timedelta(seconds=1)
                assessment = assessment.model_copy(
                    update={
                        "created_at": updated_at,
                        "updated_at": updated_at,
                    }
                )
        session.add(_record_from_assessment(assessment))
        return assessment
