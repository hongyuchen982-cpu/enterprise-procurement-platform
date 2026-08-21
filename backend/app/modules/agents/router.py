from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.contracts.agent import (
    AgentTask,
    AgentTaskCreate,
    AgentTaskEvent,
    AgentTaskStatus,
    AgentTaskStatusUpdate,
    ConfirmationRequest,
    ConfirmationRequestDecision,
    ConfirmationStatus,
)
from app.contracts.common import ApiResponse, ResponseMeta
from app.modules.agents.service import (
    InvalidAgentTaskStatusTransitionError,
    InvalidConfirmationDecisionError,
    create_agent_task,
    decide_confirmation_request,
    get_agent_task,
    get_confirmation_request,
    list_agent_task_events,
    list_agent_tasks,
    list_confirmation_requests,
    update_agent_task_status,
)

router = APIRouter(prefix="/agent/tasks", tags=["member-b:agents"])
confirmations_router = APIRouter(
    prefix="/agent/confirmations", tags=["member-b:agent-confirmations"]
)


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.post("", response_model=ApiResponse[AgentTask], status_code=status.HTTP_202_ACCEPTED)
async def submit_agent_task(command: AgentTaskCreate, request: Request) -> ApiResponse[AgentTask]:
    task = create_agent_task(command, trace_id=request.state.trace_id)
    return ApiResponse(data=task, meta=_response_meta(request))


@router.get("", response_model=ApiResponse[list[AgentTask]])
async def list_tasks(
    request: Request,
    subject_type: str | None = None,
    subject_id: UUID | None = None,
    task_status: AgentTaskStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiResponse[list[AgentTask]]:
    return ApiResponse(
        data=list_agent_tasks(
            subject_type=subject_type,
            subject_id=subject_id,
            task_status=task_status,
            limit=limit,
        ),
        meta=_response_meta(request),
    )


@router.get("/{task_id}", response_model=ApiResponse[AgentTask])
async def read_agent_task(task_id: UUID, request: Request) -> ApiResponse[AgentTask]:
    task = get_agent_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found")
    return ApiResponse(data=task, meta=_response_meta(request))


@router.get("/{task_id}/events", response_model=ApiResponse[list[AgentTaskEvent]])
async def read_agent_task_events(
    task_id: UUID, request: Request
) -> ApiResponse[list[AgentTaskEvent]]:
    events = list_agent_task_events(task_id)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found")
    return ApiResponse(data=events, meta=_response_meta(request))


@router.patch("/{task_id}/status", response_model=ApiResponse[AgentTask])
async def update_task_status(
    task_id: UUID, command: AgentTaskStatusUpdate, request: Request
) -> ApiResponse[AgentTask]:
    try:
        task = update_agent_task_status(task_id, command)
    except InvalidAgentTaskStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found")
    return ApiResponse(data=task, meta=_response_meta(request))


@confirmations_router.get("", response_model=ApiResponse[list[ConfirmationRequest]])
async def list_confirmations(
    request: Request,
    confirmation_status: ConfirmationStatus | None = None,
    task_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiResponse[list[ConfirmationRequest]]:
    return ApiResponse(
        data=list_confirmation_requests(
            confirmation_status=confirmation_status,
            task_id=task_id,
            limit=limit,
        ),
        meta=_response_meta(request),
    )


@confirmations_router.get("/{confirmation_id}", response_model=ApiResponse[ConfirmationRequest])
async def read_confirmation(
    confirmation_id: UUID, request: Request
) -> ApiResponse[ConfirmationRequest]:
    confirmation = get_confirmation_request(confirmation_id)
    if confirmation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Confirmation request not found"
        )
    return ApiResponse(data=confirmation, meta=_response_meta(request))


@confirmations_router.patch("/{confirmation_id}", response_model=ApiResponse[ConfirmationRequest])
async def decide_confirmation(
    confirmation_id: UUID, command: ConfirmationRequestDecision, request: Request
) -> ApiResponse[ConfirmationRequest]:
    try:
        confirmation = decide_confirmation_request(confirmation_id, command)
    except InvalidConfirmationDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidAgentTaskStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if confirmation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Confirmation request not found"
        )
    return ApiResponse(data=confirmation, meta=_response_meta(request))
