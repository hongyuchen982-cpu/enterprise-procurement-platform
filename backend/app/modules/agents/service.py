from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.contracts.agent import AgentTask, AgentTaskCreate, AgentTaskStatus

_TASKS: dict[UUID, AgentTask] = {}


def create_agent_task(command: AgentTaskCreate, trace_id: UUID) -> AgentTask:
    now = datetime.now(UTC)
    task = AgentTask(
        task_id=uuid4(),
        agent_type=command.agent_type,
        org_id=command.org_id,
        requested_by=command.requested_by,
        goal=command.goal,
        subject_refs=command.subject_refs,
        status=AgentTaskStatus.QUEUED,
        trace_id=trace_id,
        created_at=now,
        updated_at=now,
    )
    _TASKS[task.task_id] = task
    return task


def get_agent_task(task_id: UUID) -> AgentTask | None:
    return _TASKS.get(task_id)
