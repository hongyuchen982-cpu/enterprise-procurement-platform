from datetime import datetime
from typing import Any
from uuid import UUID

from app.contracts.common import ActorType, AuditSource, ContractModel


class AuditEntryInput(ContractModel):
    organization_id: UUID
    action: str
    object_type: str
    object_id: UUID
    object_version: int | None = None
    actor_membership_id: UUID | None = None
    actor_id: UUID | None = None
    actor_type: ActorType = ActorType.SYSTEM
    source: AuditSource = AuditSource.API
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class AuditEntrySnapshot(ContractModel):
    audit_id: UUID
    organization_id: UUID
    action: str
    object_type: str
    object_id: UUID
    object_version: int | None = None
    actor_membership_id: UUID | None = None
    actor_id: UUID | None = None
    actor_type: ActorType
    source: AuditSource
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    occurred_at: datetime
