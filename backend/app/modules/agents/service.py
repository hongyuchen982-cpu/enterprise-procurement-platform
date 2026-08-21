from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.contracts.agent import (
    AgentTask,
    AgentTaskCreate,
    AgentTaskEvent,
    AgentTaskStatus,
    AgentTaskStatusUpdate,
    ConfirmationRequest,
    ConfirmationRequestDecision,
    ConfirmationStatus,
    RiskLevel,
)
from app.persistence import agent_repository

_ALLOWED_STATUS_TRANSITIONS: dict[AgentTaskStatus, set[AgentTaskStatus]] = {
    AgentTaskStatus.QUEUED: {AgentTaskStatus.RUNNING, AgentTaskStatus.CANCELLED},
    AgentTaskStatus.RUNNING: {
        AgentTaskStatus.WAITING_CONFIRMATION,
        AgentTaskStatus.COMPLETED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.HANDOFF,
    },
    AgentTaskStatus.WAITING_CONFIRMATION: {
        AgentTaskStatus.RUNNING,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.HANDOFF,
    },
    AgentTaskStatus.COMPLETED: set(),
    AgentTaskStatus.FAILED: set(),
    AgentTaskStatus.CANCELLED: set(),
    AgentTaskStatus.HANDOFF: set(),
}


class InvalidAgentTaskStatusTransitionError(ValueError):
    def __init__(self, from_status: AgentTaskStatus, to_status: AgentTaskStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot change agent task status from {from_status} to {to_status}.")


class InvalidConfirmationDecisionError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def _append_task_event(
    task_id: UUID,
    event_type: str,
    to_status: AgentTaskStatus,
    message: str,
    from_status: AgentTaskStatus | None = None,
) -> AgentTaskEvent:
    event = AgentTaskEvent(
        event_id=uuid4(),
        task_id=task_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        message=message,
        created_at=datetime.now(UTC),
    )
    return agent_repository.append_task_event(event)


def _create_confirmation_request(task: AgentTask) -> ConfirmationRequest:
    target_versions = {
        ref.object_id: ref.version
        for ref in task.subject_refs
        if ref.version is not None
    }
    confirmation = ConfirmationRequest(
        confirmation_id=uuid4(),
        task_id=task.task_id,
        tool_call_id=uuid4(),
        risk_level=RiskLevel.L2,
        proposed_action="Continue agent task after human confirmation.",
        target_refs=task.subject_refs,
        target_versions=target_versions,
        input_digest=str(task.trace_id),
        required_permission="agent.confirm_high_risk_action",
        status=ConfirmationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    return agent_repository.create_confirmation(confirmation)


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
    event = AgentTaskEvent(
        event_id=uuid4(),
        task_id=task.task_id,
        event_type="TASK_CREATED",
        to_status=task.status,
        message="Agent task accepted and queued.",
        created_at=now,
    )
    return agent_repository.create_task(task, event)


def get_agent_task(task_id: UUID) -> AgentTask | None:
    return agent_repository.get_task(task_id)


def update_agent_task_status(
    task_id: UUID, command: AgentTaskStatusUpdate
) -> AgentTask | None:
    task = get_agent_task(task_id)
    if task is None:
        return None
    if command.status == task.status:
        return task
    if command.status not in _ALLOWED_STATUS_TRANSITIONS[task.status]:
        raise InvalidAgentTaskStatusTransitionError(task.status, command.status)

    updated_task = task.model_copy(
        update={
            "status": command.status,
            "error_code": command.error_code,
            "updated_at": datetime.now(UTC),
        }
    )
    agent_repository.update_task(updated_task)
    if command.status == AgentTaskStatus.WAITING_CONFIRMATION:
        _create_confirmation_request(updated_task)
    _append_task_event(
        task_id=task_id,
        event_type="STATUS_CHANGED",
        from_status=task.status,
        to_status=command.status,
        message=f"Task status changed from {task.status} to {command.status}.",
    )
    return updated_task


def list_agent_task_events(task_id: UUID) -> list[AgentTaskEvent] | None:
    return agent_repository.list_task_events(task_id)


def list_confirmation_requests(
    confirmation_status: ConfirmationStatus | None = None,
    task_id: UUID | None = None,
    limit: int | None = None,
) -> list[ConfirmationRequest]:
    return agent_repository.list_confirmations(
        confirmation_status=confirmation_status,
        task_id=task_id,
        limit=limit,
    )


def get_confirmation_request(confirmation_id: UUID) -> ConfirmationRequest | None:
    return agent_repository.get_confirmation(confirmation_id)


def decide_confirmation_request(
    confirmation_id: UUID, command: ConfirmationRequestDecision
) -> ConfirmationRequest | None:
    confirmation = get_confirmation_request(confirmation_id)
    if confirmation is None:
        return None
    if confirmation.status != ConfirmationStatus.PENDING:
        raise InvalidConfirmationDecisionError("Confirmation request is not pending.")
    if command.status not in {ConfirmationStatus.CONFIRMED, ConfirmationStatus.REJECTED}:
        raise InvalidConfirmationDecisionError(
            "Confirmation request can only be confirmed or rejected."
        )

    now = datetime.now(UTC)
    updated_confirmation = confirmation.model_copy(
        update={
            "status": command.status,
            "confirmed_by": command.confirmed_by,
            "confirmed_at": now,
            "rejection_reason": command.rejection_reason,
        }
    )
    agent_repository.update_confirmation(updated_confirmation)

    if command.status == ConfirmationStatus.CONFIRMED:
        update_agent_task_status(
            confirmation.task_id,
            AgentTaskStatusUpdate(status=AgentTaskStatus.RUNNING),
        )
        _append_task_event(
            task_id=confirmation.task_id,
            event_type="CONFIRMATION_CONFIRMED",
            from_status=AgentTaskStatus.WAITING_CONFIRMATION,
            to_status=AgentTaskStatus.RUNNING,
            message="Human confirmation approved the pending action.",
        )
    else:
        update_agent_task_status(
            confirmation.task_id,
            AgentTaskStatusUpdate(status=AgentTaskStatus.HANDOFF),
        )
        _append_task_event(
            task_id=confirmation.task_id,
            event_type="CONFIRMATION_REJECTED",
            from_status=AgentTaskStatus.WAITING_CONFIRMATION,
            to_status=AgentTaskStatus.HANDOFF,
            message=command.rejection_reason or "Human confirmation rejected the pending action.",
        )

    return updated_confirmation


def list_agent_tasks(
    subject_type: str | None = None,
    subject_id: UUID | None = None,
    task_status: AgentTaskStatus | None = None,
    limit: int | None = None,
) -> list[AgentTask]:
    return agent_repository.list_tasks(
        subject_type=subject_type,
        subject_id=subject_id,
        task_status=task_status,
        limit=limit,
    )
