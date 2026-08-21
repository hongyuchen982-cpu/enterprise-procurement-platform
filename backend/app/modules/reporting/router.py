from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.reporting import OperationsReport, WorkbenchActionItem
from app.modules.reporting.service import get_operations_report, get_workbench_action_items

router = APIRouter(prefix="/reporting", tags=["member-b:reporting"])


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("/operations", response_model=ApiResponse[OperationsReport])
async def operations_report(request: Request) -> ApiResponse[OperationsReport]:
    return ApiResponse(data=get_operations_report(), meta=_response_meta(request))


@router.get("/action-items", response_model=ApiResponse[list[WorkbenchActionItem]])
async def action_items(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[WorkbenchActionItem]]:
    return ApiResponse(data=get_workbench_action_items(limit=limit), meta=_response_meta(request))
