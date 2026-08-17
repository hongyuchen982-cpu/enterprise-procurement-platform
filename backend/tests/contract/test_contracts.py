from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.procurement import (
    ProcurementRequestLineSnapshot,
    ProcurementRequestSnapshot,
)


def test_api_response_serializes_contract_data() -> None:
    now = datetime.now(UTC)
    response = ApiResponse(
        data={"status": "ok"},
        meta=ResponseMeta(request_id=uuid4(), trace_id=uuid4(), timestamp=now),
    )

    assert response.model_dump(mode="json")["success"] is True


def test_snapshot_is_orm_independent_and_frozen() -> None:
    snapshot = ProcurementRequestSnapshot(
        request_id=uuid4(),
        request_no="PR-0001",
        org_id=uuid4(),
        department_id=uuid4(),
        requester_id=uuid4(),
        status="APPROVED",
        currency="CNY",
        estimated_total=Decimal("100.00"),
        required_date=date.today(),
        lines=[
            ProcurementRequestLineSnapshot(
                line_id=uuid4(),
                category_id=uuid4(),
                description="Contract-only example",
                quantity=Decimal("1"),
                unit="EA",
            )
        ],
        version=1,
        updated_at=datetime.now(UTC),
    )

    with pytest.raises(ValidationError):
        snapshot.status = "DRAFT"
