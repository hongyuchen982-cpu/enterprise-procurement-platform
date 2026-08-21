from uuid import UUID

from app.contracts.agent import (
    AgentTask,
    AgentTaskStatus,
    ConfirmationRequest,
    ConfirmationStatus,
)
from app.modules.agents.service import (
    list_agent_tasks as service_list_agent_tasks,
)
from app.modules.agents.service import (
    list_confirmation_requests as service_list_confirmation_requests,
)


def list_agent_tasks(
    subject_type: str | None = None,
    subject_id: UUID | None = None,
    task_status: AgentTaskStatus | None = None,
    limit: int | None = None,
) -> list[AgentTask]:
    return service_list_agent_tasks(
        subject_type=subject_type,
        subject_id=subject_id,
        task_status=task_status,
        limit=limit,
    )


def list_confirmation_requests(
    confirmation_status: ConfirmationStatus | None = None,
    task_id: UUID | None = None,
    limit: int | None = None,
) -> list[ConfirmationRequest]:
    return service_list_confirmation_requests(
        confirmation_status=confirmation_status,
        task_id=task_id,
        limit=limit,
    )
