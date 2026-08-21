from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.contracts.agent import (
    AgentTask,
    AgentTaskEvent,
    AgentTaskStatus,
    ConfirmationRequest,
    ConfirmationStatus,
    RiskLevel,
)
from app.contracts.common import BusinessObjectRef
from app.core.database import session_scope
from app.persistence.agent_models import (
    AgentConfirmationRecord,
    AgentTaskEventRecord,
    AgentTaskRecord,
)


def _refs_to_json(refs: list[BusinessObjectRef]) -> list[dict[str, object]]:
    return [ref.model_dump(mode="json") for ref in refs]


def _refs_from_json(refs: list[dict[str, object]]) -> list[BusinessObjectRef]:
    return [BusinessObjectRef(**ref) for ref in refs]


def _next_persisted_second(value: datetime, previous: datetime | None) -> datetime:
    if previous is None:
        return value
    persisted_value = value.replace(microsecond=0, tzinfo=None)
    persisted_previous = previous.replace(microsecond=0, tzinfo=None)
    if persisted_value <= persisted_previous:
        next_value = persisted_previous + timedelta(seconds=1)
        if value.tzinfo is not None:
            return next_value.replace(tzinfo=value.tzinfo)
        return next_value
    return value


def _task_from_record(record: AgentTaskRecord) -> AgentTask:
    return AgentTask(
        task_id=UUID(str(record.task_id)),
        agent_type=record.agent_type,
        org_id=UUID(str(record.org_id)),
        requested_by=UUID(str(record.requested_by)),
        goal=record.goal,
        subject_refs=_refs_from_json(record.subject_refs),
        status=AgentTaskStatus(record.status),
        trace_id=UUID(str(record.trace_id)),
        created_at=record.created_at,
        updated_at=record.updated_at,
        error_code=record.error_code,
    )


def _task_record_from_task(task: AgentTask) -> AgentTaskRecord:
    return AgentTaskRecord(
        task_id=str(task.task_id),
        agent_type=task.agent_type,
        org_id=str(task.org_id),
        requested_by=str(task.requested_by),
        goal=task.goal,
        subject_refs=_refs_to_json(task.subject_refs),
        status=task.status.value,
        trace_id=str(task.trace_id),
        error_code=task.error_code,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _event_from_record(record: AgentTaskEventRecord) -> AgentTaskEvent:
    return AgentTaskEvent(
        event_id=UUID(str(record.event_id)),
        task_id=UUID(str(record.task_id)),
        event_type=record.event_type,
        from_status=AgentTaskStatus(record.from_status) if record.from_status else None,
        to_status=AgentTaskStatus(record.to_status),
        message=record.message,
        created_at=record.created_at,
    )


def _event_record_from_event(event: AgentTaskEvent) -> AgentTaskEventRecord:
    return AgentTaskEventRecord(
        event_id=str(event.event_id),
        task_id=str(event.task_id),
        event_type=event.event_type,
        from_status=event.from_status.value if event.from_status else None,
        to_status=event.to_status.value,
        message=event.message,
        created_at=event.created_at,
    )


def _confirmation_from_record(record: AgentConfirmationRecord) -> ConfirmationRequest:
    return ConfirmationRequest(
        confirmation_id=UUID(str(record.confirmation_id)),
        task_id=UUID(str(record.task_id)),
        tool_call_id=UUID(str(record.tool_call_id)),
        risk_level=RiskLevel(record.risk_level),
        proposed_action=record.proposed_action,
        target_refs=_refs_from_json(record.target_refs),
        target_versions={
            UUID(str(object_id)): version for object_id, version in record.target_versions.items()
        },
        input_digest=record.input_digest,
        required_permission=record.required_permission,
        status=ConfirmationStatus(record.status),
        expires_at=record.expires_at,
        confirmed_by=UUID(str(record.confirmed_by)) if record.confirmed_by else None,
        confirmed_at=record.confirmed_at,
        rejection_reason=record.rejection_reason,
    )


def _confirmation_record_from_confirmation(
    confirmation: ConfirmationRequest,
) -> AgentConfirmationRecord:
    return AgentConfirmationRecord(
        confirmation_id=str(confirmation.confirmation_id),
        task_id=str(confirmation.task_id),
        tool_call_id=str(confirmation.tool_call_id),
        risk_level=confirmation.risk_level.value,
        proposed_action=confirmation.proposed_action,
        target_refs=_refs_to_json(confirmation.target_refs),
        target_versions={
            str(object_id): version for object_id, version in confirmation.target_versions.items()
        },
        input_digest=confirmation.input_digest,
        required_permission=confirmation.required_permission,
        status=confirmation.status.value,
        expires_at=confirmation.expires_at,
        confirmed_by=str(confirmation.confirmed_by) if confirmation.confirmed_by else None,
        confirmed_at=confirmation.confirmed_at,
        rejection_reason=confirmation.rejection_reason,
    )


def create_task(task: AgentTask, event: AgentTaskEvent) -> AgentTask:
    with session_scope() as session:
        latest_created_at = session.scalar(
            select(AgentTaskRecord.created_at).order_by(AgentTaskRecord.created_at.desc()).limit(1)
        )
        created_at = _next_persisted_second(task.created_at, latest_created_at)
        persisted_task = task.model_copy(
            update={"created_at": created_at, "updated_at": created_at}
        )
        persisted_event = event.model_copy(update={"created_at": created_at})
        session.add(_task_record_from_task(persisted_task))
        session.flush()
        session.add(_event_record_from_event(persisted_event))
        return persisted_task


def get_task(task_id: UUID) -> AgentTask | None:
    with session_scope() as session:
        record = session.get(AgentTaskRecord, str(task_id))
        if record is None:
            return None
        return _task_from_record(record)


def update_task(task: AgentTask) -> AgentTask | None:
    with session_scope() as session:
        record = session.get(AgentTaskRecord, str(task.task_id))
        if record is None:
            return None
        record.status = task.status.value
        record.error_code = task.error_code
        record.updated_at = task.updated_at
        return task


def append_task_event(event: AgentTaskEvent) -> AgentTaskEvent:
    with session_scope() as session:
        latest_created_at = session.scalar(
            select(AgentTaskEventRecord.created_at)
            .where(AgentTaskEventRecord.task_id == str(event.task_id))
            .order_by(AgentTaskEventRecord.created_at.desc())
            .limit(1)
        )
        created_at = _next_persisted_second(event.created_at, latest_created_at)
        persisted_event = event.model_copy(update={"created_at": created_at})
        session.add(_event_record_from_event(persisted_event))
        return persisted_event


def list_task_events(task_id: UUID) -> list[AgentTaskEvent] | None:
    with session_scope() as session:
        if session.get(AgentTaskRecord, str(task_id)) is None:
            return None
        records = session.scalars(
            select(AgentTaskEventRecord)
            .where(AgentTaskEventRecord.task_id == str(task_id))
            .order_by(AgentTaskEventRecord.created_at.desc())
        ).all()
        return [_event_from_record(record) for record in records]


def list_tasks(
    subject_type: str | None = None,
    subject_id: UUID | None = None,
    task_status: AgentTaskStatus | None = None,
    limit: int | None = None,
) -> list[AgentTask]:
    with session_scope() as session:
        statement = select(AgentTaskRecord)
        if task_status is not None:
            statement = statement.where(AgentTaskRecord.status == task_status.value)
        records = session.scalars(statement.order_by(AgentTaskRecord.created_at.desc())).all()
        tasks = [_task_from_record(record) for record in records]

    if subject_type is not None:
        tasks = [
            task
            for task in tasks
            if any(ref.object_type == subject_type for ref in task.subject_refs)
        ]

    if subject_id is not None:
        tasks = [
            task for task in tasks if any(ref.object_id == subject_id for ref in task.subject_refs)
        ]

    if limit is not None:
        return tasks[:limit]

    return tasks


def create_confirmation(confirmation: ConfirmationRequest) -> ConfirmationRequest:
    with session_scope() as session:
        session.add(_confirmation_record_from_confirmation(confirmation))
        return confirmation


def get_confirmation(confirmation_id: UUID) -> ConfirmationRequest | None:
    with session_scope() as session:
        record = session.get(AgentConfirmationRecord, str(confirmation_id))
        if record is None:
            return None
        return _confirmation_from_record(record)


def update_confirmation(confirmation: ConfirmationRequest) -> ConfirmationRequest | None:
    with session_scope() as session:
        record = session.get(AgentConfirmationRecord, str(confirmation.confirmation_id))
        if record is None:
            return None
        record.status = confirmation.status.value
        record.confirmed_by = str(confirmation.confirmed_by) if confirmation.confirmed_by else None
        record.confirmed_at = confirmation.confirmed_at
        record.rejection_reason = confirmation.rejection_reason
        return confirmation


def list_confirmations(
    confirmation_status: ConfirmationStatus | None = None,
    task_id: UUID | None = None,
    limit: int | None = None,
) -> list[ConfirmationRequest]:
    with session_scope() as session:
        statement = select(AgentConfirmationRecord)
        if confirmation_status is not None:
            statement = statement.where(AgentConfirmationRecord.status == confirmation_status.value)
        if task_id is not None:
            statement = statement.where(AgentConfirmationRecord.task_id == str(task_id))
        records = session.scalars(
            statement.order_by(AgentConfirmationRecord.expires_at.asc())
        ).all()
        confirmations = [_confirmation_from_record(record) for record in records]
        if limit is not None:
            return confirmations[:limit]
        return confirmations
