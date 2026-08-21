from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.audit import AuditEntryInput, AuditEntrySnapshot
from app.contracts.common import ActorType, AuditSource
from app.core.database import utc_now
from app.modules.audit.models import AuditEntry
from app.modules.audit.repository import AuditRepository


class AuditFacade:
    def __init__(self, session: Session) -> None:
        self.repository = AuditRepository(session)

    def stage(self, payload: AuditEntryInput) -> None:
        self.repository.add(
            AuditEntry(
                organization_id=payload.organization_id,
                action=payload.action,
                object_type=payload.object_type,
                object_id=payload.object_id,
                object_version=payload.object_version,
                actor_membership_id=payload.actor_membership_id,
                actor_id=payload.actor_id,
                actor_type=payload.actor_type,
                source=payload.source,
                before_data=payload.before,
                after_data=payload.after,
                occurred_at=utc_now(),
            )
        )

    def list(
        self,
        organization_id: UUID,
        object_type: str | None = None,
        object_id: UUID | None = None,
        action: str | None = None,
    ) -> tuple[AuditEntrySnapshot, ...]:
        return tuple(
            AuditEntrySnapshot(
                audit_id=value.id,
                organization_id=value.organization_id,
                action=value.action,
                object_type=value.object_type,
                object_id=value.object_id,
                object_version=value.object_version,
                actor_membership_id=value.actor_membership_id,
                actor_id=value.actor_id,
                actor_type=ActorType(value.actor_type),
                source=AuditSource(value.source),
                before=value.before_data,
                after=value.after_data,
                occurred_at=value.occurred_at,
            )
            for value in self.repository.entries(
                organization_id,
                object_type,
                object_id,
                action,
            )
        )
