from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.sourcing import (
    SourcingProjectCreate,
    SourcingProjectSnapshot,
    SourcingProjectStatusUpdate,
    SourcingStatus,
)
from app.modules.sourcing.service import (
    InvalidSourcingStatusTransitionError,
    UnknownCandidateSupplierError,
    create_sourcing_project,
    get_sourcing_project,
    list_sourcing_projects,
    update_sourcing_project_status,
)

router = APIRouter(prefix="/sourcing/projects", tags=["member-b:sourcing"])


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("", response_model=ApiResponse[list[SourcingProjectSnapshot]])
async def list_projects(
    request: Request,
    sourcing_status: SourcingStatus | None = None,
) -> ApiResponse[list[SourcingProjectSnapshot]]:
    return ApiResponse(
        data=list_sourcing_projects(status=sourcing_status),
        meta=_response_meta(request),
    )


@router.post(
    "",
    response_model=ApiResponse[SourcingProjectSnapshot],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    command: SourcingProjectCreate,
    request: Request,
) -> ApiResponse[SourcingProjectSnapshot]:
    try:
        project = create_sourcing_project(command)
    except UnknownCandidateSupplierError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ApiResponse(data=project, meta=_response_meta(request))


@router.get("/{project_id}", response_model=ApiResponse[SourcingProjectSnapshot])
async def read_project(
    project_id: UUID,
    request: Request,
) -> ApiResponse[SourcingProjectSnapshot]:
    project = get_sourcing_project(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sourcing project not found",
        )
    return ApiResponse(data=project, meta=_response_meta(request))


@router.patch("/{project_id}/status", response_model=ApiResponse[SourcingProjectSnapshot])
async def update_project_status(
    project_id: UUID,
    command: SourcingProjectStatusUpdate,
    request: Request,
) -> ApiResponse[SourcingProjectSnapshot]:
    try:
        project = update_sourcing_project_status(project_id, command)
    except InvalidSourcingStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sourcing project not found",
        )
    return ApiResponse(data=project, meta=_response_meta(request))
