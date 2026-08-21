from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.risk import (
    SupplierRiskAssessment,
    SupplierRiskAssessmentRefresh,
)
from app.modules.risk.service import (
    get_supplier_risk_assessment,
    list_supplier_risk_assessments,
    refresh_supplier_risk_assessment,
)

router = APIRouter(prefix="/risk", tags=["member-b:risk"])


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("/supplier-assessments", response_model=ApiResponse[list[SupplierRiskAssessment]])
async def list_assessments(
    request: Request,
    supplier_id: UUID | None = None,
) -> ApiResponse[list[SupplierRiskAssessment]]:
    return ApiResponse(
        data=list_supplier_risk_assessments(supplier_id=supplier_id),
        meta=_response_meta(request),
    )


@router.get(
    "/supplier-assessments/{supplier_id}",
    response_model=ApiResponse[SupplierRiskAssessment],
)
async def read_assessment(
    supplier_id: UUID,
    request: Request,
) -> ApiResponse[SupplierRiskAssessment]:
    assessment = get_supplier_risk_assessment(supplier_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier risk assessment not found",
        )
    return ApiResponse(data=assessment, meta=_response_meta(request))


@router.post(
    "/supplier-assessments/{supplier_id}/refresh",
    response_model=ApiResponse[SupplierRiskAssessment],
)
async def refresh_assessment(
    supplier_id: UUID,
    command: SupplierRiskAssessmentRefresh,
    request: Request,
) -> ApiResponse[SupplierRiskAssessment]:
    assessment = refresh_supplier_risk_assessment(supplier_id, command)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier risk assessment not found",
        )
    return ApiResponse(data=assessment, meta=_response_meta(request))
