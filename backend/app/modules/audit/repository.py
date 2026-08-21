from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEntry


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entry: AuditEntry) -> None:
        self.session.add(entry)

    def entries(
        self,
        organization_id: UUID,
        object_type: str | None = None,
        object_id: UUID | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[AuditEntry, ...]:
        statement = select(AuditEntry).where(AuditEntry.organization_id == organization_id)
        if object_type is not None:
            statement = statement.where(AuditEntry.object_type == object_type)
        if object_id is not None:
            statement = statement.where(AuditEntry.object_id == object_id)
        if action is not None:
            statement = statement.where(AuditEntry.action == action)
        return tuple(
            self.session.scalars(
                statement.order_by(AuditEntry.occurred_at.desc(), AuditEntry.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
