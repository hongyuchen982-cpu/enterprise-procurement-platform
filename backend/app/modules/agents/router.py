from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.contracts.agent import AgentTask, AgentTaskCreate
from app.contracts.common import ApiResponse, ResponseMeta
from app.modules.agents.service import create_agent_task, get_agent_task

router = APIRouter(prefix="/agent/tasks", tags=["member-b:agents"])


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


@router.get("/{task_id}", response_model=ApiResponse[AgentTask])
async def read_agent_task(task_id: UUID, request: Request) -> ApiResponse[AgentTask]:
    task = get_agent_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found")
    return ApiResponse(data=task, meta=_response_meta(request))
