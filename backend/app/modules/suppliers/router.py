from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.supplier import SupplierSnapshot, SupplierSummary
from app.modules.suppliers.facade import get_supplier_snapshot, list_supplier_summaries

router = APIRouter(prefix="/suppliers", tags=["member-b:suppliers"])


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("", response_model=ApiResponse[list[SupplierSummary]])
async def list_suppliers(request: Request) -> ApiResponse[list[SupplierSummary]]:
    return ApiResponse(data=list_supplier_summaries(), meta=_response_meta(request))


@router.get("/{supplier_id}/snapshot", response_model=ApiResponse[SupplierSnapshot])
async def supplier_snapshot(supplier_id: UUID, request: Request) -> ApiResponse[SupplierSnapshot]:
    snapshot = get_supplier_snapshot(supplier_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier snapshot not found",
        )
    return ApiResponse(data=snapshot, meta=_response_meta(request))
