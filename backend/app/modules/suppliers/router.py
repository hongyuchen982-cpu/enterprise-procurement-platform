from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.supplier import (
    RiskLevel,
    SupplierRiskReview,
    SupplierRiskReviewCreate,
    SupplierSnapshot,
    SupplierStatus,
    SupplierSummary,
)
from app.modules.suppliers.facade import (
    create_supplier_risk_review,
    get_latest_supplier_risk_review,
    get_supplier_snapshot,
    list_supplier_risk_reviews,
    list_supplier_summaries,
)

router = APIRouter(prefix="/suppliers", tags=["member-b:suppliers"])


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("", response_model=ApiResponse[list[SupplierSummary]])
async def list_suppliers(
    request: Request,
    keyword: str | None = Query(default=None, min_length=1, max_length=120),
    risk_level: RiskLevel | None = None,
    status: SupplierStatus | None = None,
    high_risk_only: bool = False,
) -> ApiResponse[list[SupplierSummary]]:
    return ApiResponse(
        data=list_supplier_summaries(
            keyword=keyword,
            risk_level=risk_level,
            status=status,
            high_risk_only=high_risk_only,
        ),
        meta=_response_meta(request),
    )


@router.get("/{supplier_id}/snapshot", response_model=ApiResponse[SupplierSnapshot])
async def supplier_snapshot(supplier_id: UUID, request: Request) -> ApiResponse[SupplierSnapshot]:
    snapshot = get_supplier_snapshot(supplier_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier snapshot not found",
        )
    return ApiResponse(data=snapshot, meta=_response_meta(request))


@router.post(
    "/{supplier_id}/risk-reviews",
    response_model=ApiResponse[SupplierRiskReview],
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_review(
    supplier_id: UUID,
    command: SupplierRiskReviewCreate,
    request: Request,
) -> ApiResponse[SupplierRiskReview]:
    review = create_supplier_risk_review(supplier_id, command)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier snapshot not found",
        )
    return ApiResponse(data=review, meta=_response_meta(request))


@router.get(
    "/{supplier_id}/risk-reviews",
    response_model=ApiResponse[list[SupplierRiskReview]],
)
async def list_risk_reviews(
    supplier_id: UUID, request: Request
) -> ApiResponse[list[SupplierRiskReview]]:
    reviews = list_supplier_risk_reviews(supplier_id)
    if reviews is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier snapshot not found",
        )
    return ApiResponse(data=reviews, meta=_response_meta(request))


@router.get(
    "/{supplier_id}/risk-reviews/latest",
    response_model=ApiResponse[SupplierRiskReview | None],
)
async def latest_risk_review(
    supplier_id: UUID, request: Request
) -> ApiResponse[SupplierRiskReview | None]:
    if get_supplier_snapshot(supplier_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier snapshot not found",
        )
    return ApiResponse(
        data=get_latest_supplier_risk_review(supplier_id),
        meta=_response_meta(request),
    )
