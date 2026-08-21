from app.persistence.agent_models import (
    AgentConfirmationRecord,
    AgentTaskEventRecord,
    AgentTaskRecord,
)


def test_agent_orm_tables_have_expected_names_and_columns() -> None:
    task_columns = set(AgentTaskRecord.__table__.columns.keys())
    event_columns = set(AgentTaskEventRecord.__table__.columns.keys())
    confirmation_columns = set(AgentConfirmationRecord.__table__.columns.keys())

    assert AgentTaskRecord.__tablename__ == "b_agent_tasks"
    assert AgentTaskEventRecord.__tablename__ == "b_agent_task_events"
    assert AgentConfirmationRecord.__tablename__ == "b_agent_confirmations"
    assert {
        "task_id",
        "agent_type",
        "org_id",
        "requested_by",
        "goal",
        "subject_refs",
        "status",
        "trace_id",
        "error_code",
        "created_at",
        "updated_at",
    }.issubset(task_columns)
    assert {
        "event_id",
        "task_id",
        "event_type",
        "from_status",
        "to_status",
        "message",
        "created_at",
    }.issubset(event_columns)
    assert {
        "confirmation_id",
        "task_id",
        "tool_call_id",
        "risk_level",
        "proposed_action",
        "target_refs",
        "target_versions",
        "input_digest",
        "required_permission",
        "status",
        "expires_at",
        "confirmed_by",
        "confirmed_at",
        "rejection_reason",
    }.issubset(confirmation_columns)


def test_agent_orm_tables_keep_query_indexes() -> None:
    task_indexes = {index.name for index in AgentTaskRecord.__table__.indexes}
    event_indexes = {index.name for index in AgentTaskEventRecord.__table__.indexes}
    confirmation_indexes = {index.name for index in AgentConfirmationRecord.__table__.indexes}

    assert "ix_b_agent_tasks_org_status" in task_indexes
    assert "ix_b_agent_tasks_status_updated" in task_indexes
    assert "ix_b_agent_tasks_trace" in task_indexes
    assert "ix_b_agent_task_events_task_created" in event_indexes
    assert "ix_b_agent_task_events_type_created" in event_indexes
    assert "ix_b_agent_confirmations_status_expires" in confirmation_indexes
    assert "ix_b_agent_confirmations_task_status" in confirmation_indexes
