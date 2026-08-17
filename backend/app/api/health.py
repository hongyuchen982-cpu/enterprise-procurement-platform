from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from app.contracts.common import ApiResponse, ResponseMeta
from app.core.health import ReadinessResult, check_readiness

router = APIRouter(prefix="/health", tags=["health"])


class LiveStatus(BaseModel):
    status: Literal["alive"] = "alive"


def response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("/live", response_model=ApiResponse[LiveStatus])
async def live(request: Request) -> ApiResponse[LiveStatus]:
    return ApiResponse(data=LiveStatus(), meta=response_meta(request))


@router.get("/ready", response_model=ApiResponse[ReadinessResult])
async def ready(request: Request, response: Response) -> ApiResponse[ReadinessResult]:
    readiness = await check_readiness()
    if readiness.status == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ApiResponse(data=readiness, meta=response_meta(request))
