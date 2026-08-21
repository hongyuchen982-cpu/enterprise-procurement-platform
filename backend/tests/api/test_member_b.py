from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.database import session_scope
from app.main import app
from app.modules.risk.models import SupplierRiskAssessmentRecord
from app.modules.sourcing.models import SourcingProjectRecord
from app.modules.suppliers.models import SupplierRiskReviewRecord
from app.persistence.agent_models import (
    AgentConfirmationRecord,
    AgentTaskEventRecord,
    AgentTaskRecord,
)
from app.persistence.rag_models import KnowledgeDocumentRecord


def _delete_agent_tasks(*task_ids: str) -> None:
    if not task_ids:
        return
    with session_scope() as session:
        session.execute(
            delete(AgentConfirmationRecord).where(AgentConfirmationRecord.task_id.in_(task_ids))
        )
        session.execute(
            delete(AgentTaskEventRecord).where(AgentTaskEventRecord.task_id.in_(task_ids))
        )
        session.execute(delete(AgentTaskRecord).where(AgentTaskRecord.task_id.in_(task_ids)))


def test_supplier_snapshot_api() -> None:
    supplier_id = "11111111-1111-4111-8111-111111111111"

    with TestClient(app) as client:
        response = client.get(f"/suppliers/{supplier_id}/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["supplier_id"] == supplier_id
    assert payload["data"]["status"] == "ACTIVE"


def test_supplier_list_can_filter_by_keyword_and_risk() -> None:
    with TestClient(app) as client:
        keyword_response = client.get("/suppliers", params={"keyword": "apex"})
        risk_response = client.get("/suppliers", params={"risk_level": "HIGH"})
        active_response = client.get("/suppliers", params={"status": "ACTIVE"})
        high_risk_response = client.get("/suppliers", params={"high_risk_only": "true"})

    assert keyword_response.status_code == 200
    keyword_payload = keyword_response.json()
    assert [item["legal_name"] for item in keyword_payload["data"]] == [
        "Shenzhen Apex Packaging Technology Co., Ltd."
    ]

    assert risk_response.status_code == 200
    risk_payload = risk_response.json()
    assert [item["risk_level"] for item in risk_payload["data"]] == ["HIGH"]
    assert [item["legal_name"] for item in risk_payload["data"]] == [
        "Harbor Logistics Services Group"
    ]

    assert active_response.status_code == 200
    assert all(item["status"] == "ACTIVE" for item in active_response.json()["data"])

    assert high_risk_response.status_code == 200
    assert {item["risk_level"] for item in high_risk_response.json()["data"]} <= {
        "HIGH",
        "CRITICAL",
    }


def test_supplier_risk_review_can_be_created_and_read_latest() -> None:
    supplier_id = "11111111-1111-4111-8111-111111111114"
    command = {
        "conclusion": "ESCALATE",
        "note": "High logistics disruption risk requires procurement manager review.",
        "reviewed_by": "Member B Demo Operator",
    }

    with TestClient(app) as client:
        created = client.post(f"/suppliers/{supplier_id}/risk-reviews", json=command)
        latest = client.get(f"/suppliers/{supplier_id}/risk-reviews/latest")

    assert created.status_code == 201
    created_payload = created.json()
    UUID(created_payload["data"]["review_id"])
    assert created_payload["data"]["supplier_id"] == supplier_id
    assert created_payload["data"]["conclusion"] == command["conclusion"]
    with session_scope() as session:
        persisted_review = session.scalar(
            select(SupplierRiskReviewRecord).where(
                SupplierRiskReviewRecord.review_id == created_payload["data"]["review_id"]
            )
        )
    assert persisted_review is not None
    assert persisted_review.note == command["note"]

    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["data"]["review_id"] == created_payload["data"]["review_id"]
    assert latest_payload["data"]["note"] == command["note"]


def test_supplier_risk_review_list_returns_newest_first() -> None:
    supplier_id = "11111111-1111-4111-8111-111111111113"
    first_command = {
        "conclusion": "MONITOR",
        "note": "Initial review asks for updated packaging qualification evidence.",
        "reviewed_by": "Member B Demo Operator",
    }
    second_command = {
        "conclusion": "ESCALATE",
        "note": "Escalated because qualification evidence is still incomplete.",
        "reviewed_by": "Member B Demo Operator",
    }

    with TestClient(app) as client:
        first = client.post(f"/suppliers/{supplier_id}/risk-reviews", json=first_command)
        second = client.post(f"/suppliers/{supplier_id}/risk-reviews", json=second_command)
        listed = client.get(f"/suppliers/{supplier_id}/risk-reviews")

    assert first.status_code == 201
    assert second.status_code == 201
    assert listed.status_code == 200

    first_id = first.json()["data"]["review_id"]
    second_id = second.json()["data"]["review_id"]
    review_ids = [item["review_id"] for item in listed.json()["data"]]
    assert review_ids[:2] == [second_id, first_id]


def test_create_and_read_agent_task() -> None:
    command = {
        "agent_type": "sourcing_assistant",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Find qualified suppliers for the approved request.",
        "subject_refs": [],
    }

    with TestClient(app) as client:
        created = client.post("/agent/tasks", json=command)
        assert created.status_code == 202
        task_id = created.json()["data"]["task_id"]
        UUID(task_id)

        fetched = client.get(f"/agent/tasks/{task_id}")

    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["data"]["status"] == "QUEUED"
    assert payload["data"]["goal"] == command["goal"]
    with session_scope() as session:
        persisted_task = session.get(AgentTaskRecord, task_id)
        persisted_events = session.scalars(
            select(AgentTaskEventRecord).where(AgentTaskEventRecord.task_id == task_id)
        ).all()
    assert persisted_task is not None
    assert persisted_task.goal == command["goal"]
    assert [event.event_type for event in persisted_events] == ["TASK_CREATED"]
    _delete_agent_tasks(task_id)


def test_agent_tasks_can_filter_by_subject_ref() -> None:
    supplier_id = "11111111-1111-4111-8111-111111111111"
    other_supplier_id = "11111111-1111-4111-8111-111111111112"
    first_command = {
        "agent_type": "sourcing_assistant",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Create a sourcing plan for the selected supplier.",
        "subject_refs": [{"object_type": "supplier", "object_id": supplier_id, "version": 1}],
    }
    second_command = {
        "agent_type": "supplier_risk_analyzer",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Analyze supplier risk for the selected supplier.",
        "subject_refs": [{"object_type": "supplier", "object_id": supplier_id, "version": 1}],
    }
    unrelated_command = {
        "agent_type": "sourcing_assistant",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Create a sourcing plan for another supplier.",
        "subject_refs": [{"object_type": "supplier", "object_id": other_supplier_id, "version": 1}],
    }

    with TestClient(app) as client:
        first = client.post("/agent/tasks", json=first_command)
        second = client.post("/agent/tasks", json=second_command)
        unrelated = client.post("/agent/tasks", json=unrelated_command)
        listed = client.get(
            "/agent/tasks",
            params={"subject_type": "supplier", "subject_id": supplier_id},
        )
        limited = client.get(
            "/agent/tasks",
            params={
                "subject_type": "supplier",
                "subject_id": supplier_id,
                "limit": 1,
            },
        )
        invalid_limit = client.get("/agent/tasks", params={"limit": 0})

    assert first.status_code == 202
    assert second.status_code == 202
    assert unrelated.status_code == 202
    assert listed.status_code == 200
    assert limited.status_code == 200
    assert invalid_limit.status_code == 422

    first_id = first.json()["data"]["task_id"]
    second_id = second.json()["data"]["task_id"]
    task_ids = [item["task_id"] for item in listed.json()["data"]]
    assert task_ids[:2] == [second_id, first_id]
    assert [item["task_id"] for item in limited.json()["data"]] == [second_id]
    assert unrelated.json()["data"]["task_id"] not in task_ids
    _delete_agent_tasks(first_id, second_id, unrelated.json()["data"]["task_id"])


def test_agent_tasks_can_filter_by_status() -> None:
    command = {
        "agent_type": "sourcing_assistant",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Create a queued task for status filtering.",
        "subject_refs": [],
    }

    with TestClient(app) as client:
        created = client.post("/agent/tasks", json=command)
        queued = client.get("/agent/tasks", params={"task_status": "QUEUED"})
        running = client.get("/agent/tasks", params={"task_status": "RUNNING"})

    assert created.status_code == 202
    assert queued.status_code == 200
    assert running.status_code == 200

    created_id = created.json()["data"]["task_id"]
    queued_ids = [item["task_id"] for item in queued.json()["data"]]
    running_ids = [item["task_id"] for item in running.json()["data"]]
    assert created_id in queued_ids
    assert created_id not in running_ids
    _delete_agent_tasks(created_id)


def test_agent_task_status_can_be_updated() -> None:
    command = {
        "agent_type": "supplier_risk_analyzer",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Analyze supplier risk and update task status.",
        "subject_refs": [],
    }

    with TestClient(app) as client:
        created = client.post("/agent/tasks", json=command)
        task_id = created.json()["data"]["task_id"]
        running = client.patch(f"/agent/tasks/{task_id}/status", json={"status": "RUNNING"})
        failed = client.patch(
            f"/agent/tasks/{task_id}/status",
            json={"status": "FAILED", "error_code": "DEMO_TOOL_TIMEOUT"},
        )
        missing = client.patch(
            "/agent/tasks/00000000-0000-4000-8000-000000000000/status",
            json={"status": "RUNNING"},
        )

    assert created.status_code == 202
    assert running.status_code == 200
    assert running.json()["data"]["status"] == "RUNNING"
    assert running.json()["data"]["error_code"] is None

    assert failed.status_code == 200
    assert failed.json()["data"]["status"] == "FAILED"
    assert failed.json()["data"]["error_code"] == "DEMO_TOOL_TIMEOUT"

    assert missing.status_code == 404
    _delete_agent_tasks(task_id)


def test_agent_task_rejects_invalid_status_transition() -> None:
    command = {
        "agent_type": "sourcing_assistant",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Reject invalid task status transitions.",
        "subject_refs": [],
    }

    with TestClient(app) as client:
        created = client.post("/agent/tasks", json=command)
        task_id = created.json()["data"]["task_id"]
        running = client.patch(f"/agent/tasks/{task_id}/status", json={"status": "RUNNING"})
        completed = client.patch(f"/agent/tasks/{task_id}/status", json={"status": "COMPLETED"})
        invalid = client.patch(f"/agent/tasks/{task_id}/status", json={"status": "RUNNING"})
        fetched = client.get(f"/agent/tasks/{task_id}")

    assert created.status_code == 202
    assert running.status_code == 200
    assert completed.status_code == 200
    assert invalid.status_code == 409
    assert fetched.status_code == 200
    assert fetched.json()["data"]["status"] == "COMPLETED"
    _delete_agent_tasks(task_id)


def test_agent_task_events_track_creation_and_status_changes() -> None:
    command = {
        "agent_type": "supplier_risk_analyzer",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Track task execution events.",
        "subject_refs": [],
    }

    with TestClient(app) as client:
        created = client.post("/agent/tasks", json=command)
        task_id = created.json()["data"]["task_id"]
        client.patch(f"/agent/tasks/{task_id}/status", json={"status": "RUNNING"})
        client.patch(f"/agent/tasks/{task_id}/status", json={"status": "COMPLETED"})
        events = client.get(f"/agent/tasks/{task_id}/events")
        missing = client.get("/agent/tasks/00000000-0000-4000-8000-000000000000/events")

    assert created.status_code == 202
    assert events.status_code == 200
    event_payload = events.json()["data"]
    assert [event["event_type"] for event in event_payload] == [
        "STATUS_CHANGED",
        "STATUS_CHANGED",
        "TASK_CREATED",
    ]
    assert [event["to_status"] for event in event_payload] == [
        "COMPLETED",
        "RUNNING",
        "QUEUED",
    ]
    assert event_payload[0]["from_status"] == "RUNNING"
    assert event_payload[-1]["from_status"] is None
    assert missing.status_code == 404
    _delete_agent_tasks(task_id)


def test_waiting_confirmation_creates_confirmation_request() -> None:
    supplier_id = "11111111-1111-4111-8111-111111111111"
    command = {
        "agent_type": "supplier_risk_analyzer",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Require human confirmation for a high-risk tool action.",
        "subject_refs": [{"object_type": "supplier", "object_id": supplier_id, "version": 3}],
    }

    with TestClient(app) as client:
        created = client.post("/agent/tasks", json=command)
        task_id = created.json()["data"]["task_id"]
        client.patch(f"/agent/tasks/{task_id}/status", json={"status": "RUNNING"})
        waiting = client.patch(
            f"/agent/tasks/{task_id}/status",
            json={"status": "WAITING_CONFIRMATION"},
        )
        pending = client.get("/agent/confirmations", params={"confirmation_status": "PENDING"})
        task_confirmations = client.get("/agent/confirmations", params={"task_id": task_id})
        limited_confirmations = client.get(
            "/agent/confirmations", params={"task_id": task_id, "limit": 1}
        )
        invalid_limit = client.get("/agent/confirmations", params={"limit": 0})
        confirmation = next(item for item in pending.json()["data"] if item["task_id"] == task_id)
        fetched = client.get(f"/agent/confirmations/{confirmation['confirmation_id']}")

    assert created.status_code == 202
    assert waiting.status_code == 200
    assert pending.status_code == 200
    assert confirmation["task_id"] == task_id
    assert confirmation["status"] == "PENDING"
    assert confirmation["risk_level"] == "L2"
    assert confirmation["required_permission"] == "agent.confirm_high_risk_action"
    assert confirmation["target_refs"][0]["object_id"] == supplier_id
    assert task_confirmations.status_code == 200
    assert [item["task_id"] for item in task_confirmations.json()["data"]] == [task_id]
    assert limited_confirmations.status_code == 200
    assert [item["task_id"] for item in limited_confirmations.json()["data"]] == [task_id]
    assert invalid_limit.status_code == 422
    assert fetched.status_code == 200
    assert fetched.json()["data"]["confirmation_id"] == confirmation["confirmation_id"]
    with session_scope() as session:
        persisted_confirmation = session.get(
            AgentConfirmationRecord,
            confirmation["confirmation_id"],
        )
    assert persisted_confirmation is not None
    assert persisted_confirmation.task_id == task_id
    _delete_agent_tasks(task_id)


def test_confirmation_request_can_be_confirmed_or_rejected() -> None:
    confirm_command = {
        "agent_type": "supplier_risk_analyzer",
        "org_id": "22222222-2222-4222-8222-222222222222",
        "requested_by": "44444444-4444-4444-8444-444444444444",
        "goal": "Confirm a pending high-risk action.",
        "subject_refs": [],
    }
    reject_command = {
        **confirm_command,
        "goal": "Reject a pending high-risk action.",
    }

    with TestClient(app) as client:
        confirm_task = client.post("/agent/tasks", json=confirm_command)
        confirm_task_id = confirm_task.json()["data"]["task_id"]
        client.patch(f"/agent/tasks/{confirm_task_id}/status", json={"status": "RUNNING"})
        client.patch(
            f"/agent/tasks/{confirm_task_id}/status",
            json={"status": "WAITING_CONFIRMATION"},
        )
        confirmations = client.get(
            "/agent/confirmations", params={"confirmation_status": "PENDING"}
        )
        confirm_request = next(
            item for item in confirmations.json()["data"] if item["task_id"] == confirm_task_id
        )
        confirmed = client.patch(
            f"/agent/confirmations/{confirm_request['confirmation_id']}",
            json={
                "status": "CONFIRMED",
                "confirmed_by": "44444444-4444-4444-8444-444444444444",
            },
        )
        confirmed_task = client.get(f"/agent/tasks/{confirm_task_id}")
        confirmed_events = client.get(f"/agent/tasks/{confirm_task_id}/events")
        repeated = client.patch(
            f"/agent/confirmations/{confirm_request['confirmation_id']}",
            json={"status": "CONFIRMED"},
        )

        reject_task = client.post("/agent/tasks", json=reject_command)
        reject_task_id = reject_task.json()["data"]["task_id"]
        client.patch(f"/agent/tasks/{reject_task_id}/status", json={"status": "RUNNING"})
        client.patch(
            f"/agent/tasks/{reject_task_id}/status",
            json={"status": "WAITING_CONFIRMATION"},
        )
        confirmations = client.get(
            "/agent/confirmations", params={"confirmation_status": "PENDING"}
        )
        reject_request = next(
            item for item in confirmations.json()["data"] if item["task_id"] == reject_task_id
        )
        rejected = client.patch(
            f"/agent/confirmations/{reject_request['confirmation_id']}",
            json={
                "status": "REJECTED",
                "confirmed_by": "44444444-4444-4444-8444-444444444444",
                "rejection_reason": "Risk is not acceptable for demo approval.",
            },
        )
        rejected_task = client.get(f"/agent/tasks/{reject_task_id}")
        rejected_events = client.get(f"/agent/tasks/{reject_task_id}/events")

    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["status"] == "CONFIRMED"
    assert confirmed_task.json()["data"]["status"] == "RUNNING"
    assert confirmed_events.status_code == 200
    assert confirmed_events.json()["data"][0]["event_type"] == "CONFIRMATION_CONFIRMED"
    assert repeated.status_code == 409

    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "REJECTED"
    assert rejected_task.json()["data"]["status"] == "HANDOFF"
    assert rejected_events.status_code == 200
    assert rejected_events.json()["data"][0]["event_type"] == "CONFIRMATION_REJECTED"
    assert (
        rejected_events.json()["data"][0]["message"] == "Risk is not acceptable for demo approval."
    )
    _delete_agent_tasks(confirm_task_id, reject_task_id)


def test_sourcing_projects_can_be_listed_created_and_advanced() -> None:
    supplier_id = "11111111-1111-4111-8111-111111111111"
    command = {
        "org_id": "22222222-2222-4222-8222-222222222222",
        "procurement_request_id": "66666666-6666-4666-8666-666666666669",
        "procurement_request_version": 1,
        "title": "Create a demo sourcing project from Member B workspace.",
        "category_id": "33333333-3333-4333-8333-333333333333",
        "candidate_supplier_ids": [supplier_id],
        "created_by": "44444444-4444-4444-8444-444444444444",
    }

    with TestClient(app) as client:
        listed = client.get("/sourcing/projects")
        active = client.get("/sourcing/projects", params={"sourcing_status": "ACTIVE"})
        created = client.post("/sourcing/projects", json=command)
        project_id = created.json()["data"]["sourcing_project_id"]
        fetched = client.get(f"/sourcing/projects/{project_id}")
        activated = client.patch(
            f"/sourcing/projects/{project_id}/status",
            json={"status": "ACTIVE"},
        )
        awarded = client.patch(
            f"/sourcing/projects/{project_id}/status",
            json={"status": "AWARDED"},
        )

    assert listed.status_code == 200
    assert any(
        item["title"] == "Precision machining supplier shortlist" for item in listed.json()["data"]
    )
    assert active.status_code == 200
    assert all(item["status"] == "ACTIVE" for item in active.json()["data"])

    assert created.status_code == 201
    UUID(project_id)
    assert created.json()["data"]["status"] == "DRAFT"
    assert created.json()["data"]["candidate_supplier_ids"] == [supplier_id]
    with session_scope() as session:
        persisted_project = session.get(SourcingProjectRecord, project_id)
    assert persisted_project is not None
    assert persisted_project.title == command["title"]
    assert persisted_project.candidate_supplier_ids == [supplier_id]

    assert fetched.status_code == 200
    assert fetched.json()["data"]["title"] == command["title"]

    assert activated.status_code == 200
    assert activated.json()["data"]["status"] == "ACTIVE"
    assert activated.json()["data"]["version"] == 2

    assert awarded.status_code == 200
    assert awarded.json()["data"]["status"] == "AWARDED"
    with session_scope() as session:
        session.execute(
            delete(SourcingProjectRecord).where(
                SourcingProjectRecord.sourcing_project_id == project_id
            )
        )


def test_sourcing_project_rejects_unknown_supplier_and_invalid_transition() -> None:
    command = {
        "org_id": "22222222-2222-4222-8222-222222222222",
        "procurement_request_id": "66666666-6666-4666-8666-666666666670",
        "procurement_request_version": 1,
        "title": "Reject invalid sourcing inputs.",
        "category_id": "33333333-3333-4333-8333-333333333333",
        "candidate_supplier_ids": ["00000000-0000-4000-8000-000000000000"],
        "created_by": "44444444-4444-4444-8444-444444444444",
    }
    valid_command = {
        **command,
        "candidate_supplier_ids": [],
    }

    with TestClient(app) as client:
        unknown_supplier = client.post("/sourcing/projects", json=command)
        created = client.post("/sourcing/projects", json=valid_command)
        project_id = created.json()["data"]["sourcing_project_id"]
        invalid_transition = client.patch(
            f"/sourcing/projects/{project_id}/status",
            json={"status": "AWARDED"},
        )
        missing = client.get("/sourcing/projects/00000000-0000-4000-8000-000000000000")

    assert unknown_supplier.status_code == 409
    assert created.status_code == 201
    assert invalid_transition.status_code == 409
    assert missing.status_code == 404
    with session_scope() as session:
        session.execute(
            delete(SourcingProjectRecord).where(
                SourcingProjectRecord.sourcing_project_id == project_id
            )
        )


def test_rag_documents_can_be_listed_created_indexed_and_searched() -> None:
    command = {
        "org_id": "22222222-2222-4222-8222-222222222222",
        "title": "Demo supplier onboarding policy",
        "owner_module": "suppliers",
        "source_type": "TEXT",
        "content": (
            "Supplier onboarding requires qualification review and risk confirmation "
            "before sourcing."
        ),
        "tags": ["supplier", "onboarding"],
        "created_by": "44444444-4444-4444-8444-444444444444",
    }

    with TestClient(app) as client:
        listed = client.get("/rag/documents")
        indexed = client.get("/rag/documents", params={"document_status": "INDEXED"})
        created = client.post("/rag/documents", json=command)
        document_id = created.json()["data"]["document_id"]
        indexing = client.patch(
            f"/rag/documents/{document_id}/status",
            json={"status": "INDEXING"},
        )
        indexed_created = client.patch(
            f"/rag/documents/{document_id}/status",
            json={"status": "INDEXED"},
        )
        fetched = client.get(f"/rag/documents/{document_id}")
        searched = client.post(
            "/rag/search",
            json={
                "org_id": command["org_id"],
                "query": "qualification risk",
                "top_k": 5,
            },
        )

    assert listed.status_code == 200
    assert indexed.status_code == 200
    assert all(item["status"] == "INDEXED" for item in indexed.json()["data"])

    assert created.status_code == 201
    UUID(document_id)
    assert created.json()["data"]["status"] == "UPLOADED"
    assert created.json()["data"]["chunk_count"] == 1
    assert created.json()["data"]["content_digest"]
    with session_scope() as session:
        persisted_document = session.get(KnowledgeDocumentRecord, document_id)
    assert persisted_document is not None
    assert persisted_document.content == command["content"]
    assert persisted_document.content_digest == created.json()["data"]["content_digest"]

    assert indexing.status_code == 200
    assert indexing.json()["data"]["status"] == "INDEXING"
    assert indexed_created.status_code == 200
    assert indexed_created.json()["data"]["status"] == "INDEXED"
    assert indexed_created.json()["data"]["indexed_at"] is not None

    assert fetched.status_code == 200
    assert fetched.json()["data"]["title"] == command["title"]

    assert searched.status_code == 200
    matches = searched.json()["data"]["matches"]
    assert matches[0]["document_id"] == document_id
    assert matches[0]["score"] > 0
    assert "qualification" in matches[0]["snippet"].lower()
    with session_scope() as session:
        session.execute(
            delete(KnowledgeDocumentRecord).where(
                KnowledgeDocumentRecord.document_id == document_id
            )
        )


def test_rag_documents_reject_invalid_status_transition() -> None:
    command = {
        "org_id": "22222222-2222-4222-8222-222222222222",
        "title": "Invalid RAG transition policy",
        "owner_module": "rag",
        "content": "This document stays uploaded until the indexer starts.",
        "created_by": "44444444-4444-4444-8444-444444444444",
    }

    with TestClient(app) as client:
        created = client.post("/rag/documents", json=command)
        document_id = created.json()["data"]["document_id"]
        invalid = client.patch(
            f"/rag/documents/{document_id}/status",
            json={"status": "INDEXED"},
        )
        missing = client.get("/rag/documents/00000000-0000-4000-8000-000000000000")
        no_hits = client.post(
            "/rag/search",
            json={
                "org_id": command["org_id"],
                "query": "nonexistent phrase",
            },
        )

    assert created.status_code == 201
    assert invalid.status_code == 409
    assert missing.status_code == 404
    assert no_hits.status_code == 200
    assert no_hits.json()["data"]["matches"] == []
    with session_scope() as session:
        session.execute(
            delete(KnowledgeDocumentRecord).where(
                KnowledgeDocumentRecord.document_id == document_id
            )
        )


def test_supplier_risk_assessments_can_be_listed_read_and_refreshed() -> None:
    high_risk_supplier_id = "11111111-1111-4111-8111-111111111114"

    with TestClient(app) as client:
        listed = client.get("/risk/supplier-assessments")
        filtered = client.get(
            "/risk/supplier-assessments",
            params={"supplier_id": high_risk_supplier_id},
        )
        fetched = client.get(f"/risk/supplier-assessments/{high_risk_supplier_id}")
        refreshed = client.post(
            f"/risk/supplier-assessments/{high_risk_supplier_id}/refresh",
            json={"assessed_by": "Member B Risk Analyst"},
        )

    assert listed.status_code == 200
    listed_payload = listed.json()["data"]
    assert len(listed_payload) >= 5
    assert listed_payload[0]["score"] >= listed_payload[-1]["score"]

    assert filtered.status_code == 200
    assert [item["supplier_id"] for item in filtered.json()["data"]] == [high_risk_supplier_id]

    assert fetched.status_code == 200
    fetched_payload = fetched.json()["data"]
    assert fetched_payload["supplier_id"] == high_risk_supplier_id
    assert fetched_payload["score"] >= 85
    assert fetched_payload["risk_level"] == "CRITICAL"
    assert fetched_payload["recommended_action"] == "FREEZE"
    assert any(factor["code"] == "SUPPLIER_FROZEN" for factor in fetched_payload["factors"])

    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()["data"]
    assert refreshed_payload["assessed_by"] == "Member B Risk Analyst"
    with session_scope() as session:
        persisted_assessment = session.get(
            SupplierRiskAssessmentRecord,
            refreshed_payload["assessment_id"],
        )
    assert persisted_assessment is not None
    assert persisted_assessment.supplier_id == high_risk_supplier_id
    assert persisted_assessment.assessed_by == "Member B Risk Analyst"
    with session_scope() as session:
        session.execute(
            delete(SupplierRiskAssessmentRecord).where(
                SupplierRiskAssessmentRecord.assessment_id == refreshed_payload["assessment_id"]
            )
        )


def test_supplier_risk_assessment_returns_404_for_missing_supplier() -> None:
    missing_supplier_id = "00000000-0000-4000-8000-000000000000"

    with TestClient(app) as client:
        fetched = client.get(f"/risk/supplier-assessments/{missing_supplier_id}")
        refreshed = client.post(
            f"/risk/supplier-assessments/{missing_supplier_id}/refresh",
            json={"assessed_by": "Member B Risk Analyst"},
        )

    assert fetched.status_code == 404
    assert refreshed.status_code == 404


def test_operations_report_aggregates_member_b_workbench_metrics() -> None:
    with TestClient(app) as client:
        response = client.get("/reporting/operations")

    assert response.status_code == 200
    payload = response.json()["data"]
    metric_values = {item["key"]: item["value"] for item in payload["metrics"]}

    assert metric_values["suppliers.total"] >= 5
    assert metric_values["suppliers.high_risk"] >= 1
    assert metric_values["rag.indexed_documents"] >= 2
    assert metric_values["tools.enabled"] == 2
    assert payload["top_risk_suppliers"][0]["score"] >= payload["top_risk_suppliers"][-1]["score"]
    assert payload["next_actions"]
    assert payload["next_actions"][0]["key"] == "review-high-risk-suppliers"
    assert payload["next_actions"][0]["target_module"] == "suppliers"
    capability_keys = {item["key"] for item in payload["platform_capabilities"]}
    assert {"identity-access", "organization-tree", "master-data"} <= capability_keys
    assert payload["generated_at"]


def test_action_items_surface_member_b_work_queue() -> None:
    with TestClient(app) as client:
        response = client.get("/reporting/action-items")
        limited = client.get("/reporting/action-items", params={"limit": 1})
        invalid_limit = client.get("/reporting/action-items", params={"limit": 0})

    assert response.status_code == 200
    payload = response.json()["data"]

    assert payload
    assert payload[0]["priority"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    assert {"item_id", "item_type", "target_module", "target_id"} <= set(payload[0])
    assert any(item["target_module"] == "suppliers" for item in payload)
    assert limited.status_code == 200
    assert len(limited.json()["data"]) == 1
    assert invalid_limit.status_code == 422


def test_tool_registry_exposes_b_owned_tools() -> None:
    with TestClient(app) as client:
        response = client.get("/tools")

    assert response.status_code == 200
    tool_names = {item["name"] for item in response.json()["data"]}
    assert "supplier.get_snapshot" in tool_names
    assert "sourcing.create_project" in tool_names
