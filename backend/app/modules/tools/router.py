from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.contracts.agent import ToolDefinition
from app.contracts.common import ApiResponse, ResponseMeta
from app.modules.tools.registry import list_tool_definitions

router = APIRouter(prefix="/tools", tags=["member-b:tools"])


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("", response_model=ApiResponse[list[ToolDefinition]])
async def list_tools(request: Request) -> ApiResponse[list[ToolDefinition]]:
    return ApiResponse(data=list_tool_definitions(), meta=_response_meta(request))
