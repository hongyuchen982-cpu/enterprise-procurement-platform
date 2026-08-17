from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.contracts.common import ActorType, ContractModel


class EventEnvelope(ContractModel):
    event_id: UUID
    event_type: str
    event_version: int = Field(ge=1)
    occurred_at: datetime
    producer: str
    org_id: UUID
    actor_id: UUID | None
    actor_type: ActorType
    trace_id: UUID
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    entity_type: str
    entity_id: UUID
    entity_version: int = Field(ge=1)
    payload: dict[str, Any]
