from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


def test_supplier_snapshot_api() -> None:
    supplier_id = "11111111-1111-4111-8111-111111111111"

    with TestClient(app) as client:
        response = client.get(f"/suppliers/{supplier_id}/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["supplier_id"] == supplier_id
    assert payload["data"]["status"] == "ACTIVE"


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


def test_tool_registry_exposes_b_owned_tools() -> None:
    with TestClient(app) as client:
        response = client.get("/tools")

    assert response.status_code == 200
    tool_names = {item["name"] for item in response.json()["data"]}
    assert "supplier.get_snapshot" in tool_names
    assert "sourcing.create_project" in tool_names
