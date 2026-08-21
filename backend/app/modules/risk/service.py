from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.contracts.risk import (
    RiskFactor,
    SupplierRiskAction,
    SupplierRiskAssessment,
    SupplierRiskAssessmentRefresh,
)
from app.contracts.supplier import (
    QualificationStatus,
    RiskLevel,
    SupplierSnapshot,
    SupplierStatus,
)
from app.modules.suppliers.facade import (
    get_supplier_snapshot,
    list_supplier_summaries,
)
from app.persistence import risk_repository

_BASE_SCORE_BY_RISK: dict[RiskLevel, int] = {
    RiskLevel.LOW: 20,
    RiskLevel.MEDIUM: 45,
    RiskLevel.HIGH: 70,
    RiskLevel.CRITICAL: 88,
}


def _factor(code: str, label: str, impact_score: int) -> RiskFactor:
    return RiskFactor(code=code, label=label, impact_score=impact_score)


def _risk_level(score: int) -> RiskLevel:
    if score >= 85:
        return RiskLevel.CRITICAL
    if score >= 65:
        return RiskLevel.HIGH
    if score >= 40:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _recommended_action(score: int, snapshot: SupplierSnapshot) -> SupplierRiskAction:
    if snapshot.is_frozen or score >= 85:
        return SupplierRiskAction.FREEZE
    if score >= 65:
        return SupplierRiskAction.ESCALATE
    if score >= 40:
        return SupplierRiskAction.MONITOR
    return SupplierRiskAction.APPROVE


def _factors(snapshot: SupplierSnapshot) -> list[RiskFactor]:
    factors = [
        _factor(
            "SUPPLIER_BASE_RISK",
            f"Supplier declared risk level is {snapshot.risk_level}.",
            _BASE_SCORE_BY_RISK[snapshot.risk_level],
        )
    ]
    if snapshot.is_frozen:
        factors.append(_factor("SUPPLIER_FROZEN", "Supplier is currently frozen.", 15))
    if snapshot.status in {SupplierStatus.SUSPENDED, SupplierStatus.BLOCKED}:
        factors.append(
            _factor("SUPPLIER_STATUS_RESTRICTED", f"Supplier status is {snapshot.status}.", 20)
        )
    elif snapshot.status in {SupplierStatus.DRAFT, SupplierStatus.PENDING}:
        factors.append(
            _factor("SUPPLIER_STATUS_NOT_ACTIVE", f"Supplier status is {snapshot.status}.", 8)
        )

    if snapshot.qualification_status in {
        QualificationStatus.EXPIRED,
        QualificationStatus.REJECTED,
    }:
        factors.append(
            _factor(
                "QUALIFICATION_BLOCKED",
                f"Qualification status is {snapshot.qualification_status}.",
                20,
            )
        )
    elif snapshot.qualification_status == QualificationStatus.INCOMPLETE:
        factors.append(
            _factor("QUALIFICATION_INCOMPLETE", "Qualification evidence is incomplete.", 10)
        )
    elif snapshot.qualification_status == QualificationStatus.REVIEWING:
        factors.append(
            _factor("QUALIFICATION_REVIEWING", "Qualification evidence is under review.", 5)
        )

    return factors


def _build_assessment(
    snapshot: SupplierSnapshot,
    assessed_by: str,
) -> SupplierRiskAssessment:
    now = datetime.now(UTC)
    factors = _factors(snapshot)
    score = min(100, sum(factor.impact_score for factor in factors))
    risk_level = _risk_level(score)
    action = _recommended_action(score, snapshot)
    return SupplierRiskAssessment(
        assessment_id=uuid4(),
        supplier_id=snapshot.supplier_id,
        org_id=snapshot.org_id,
        supplier_name=snapshot.legal_name,
        score=score,
        risk_level=risk_level,
        recommended_action=action,
        factors=factors,
        summary=(
            f"Risk score {score}; recommended action is {action}. "
            f"{len(factors)} explainable factors were evaluated."
        ),
        assessed_by=assessed_by,
        created_at=now,
        updated_at=now,
    )


def refresh_supplier_risk_assessment(
    supplier_id: UUID,
    command: SupplierRiskAssessmentRefresh,
) -> SupplierRiskAssessment | None:
    snapshot = get_supplier_snapshot(supplier_id)
    if snapshot is None:
        return None
    assessment = _build_assessment(snapshot, command.assessed_by)
    return risk_repository.append_assessment(assessment)


def get_supplier_risk_assessment(
    supplier_id: UUID,
) -> SupplierRiskAssessment | None:
    assessment = risk_repository.get_latest_assessment(supplier_id)
    if assessment is not None:
        return assessment
    return refresh_supplier_risk_assessment(
        supplier_id,
        SupplierRiskAssessmentRefresh(),
    )


def list_supplier_risk_assessments(
    supplier_id: UUID | None = None,
) -> list[SupplierRiskAssessment]:
    if supplier_id is not None:
        assessment = get_supplier_risk_assessment(supplier_id)
        return [assessment] if assessment is not None else []

    for summary in list_supplier_summaries():
        if risk_repository.get_latest_assessment(summary.supplier_id) is None:
            get_supplier_risk_assessment(summary.supplier_id)

    return sorted(
        risk_repository.list_latest_assessments(),
        key=lambda assessment: (assessment.score, assessment.updated_at),
        reverse=True,
    )
