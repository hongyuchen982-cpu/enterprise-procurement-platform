from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.procurement.models import ProcurementRequest, ProcurementRequestLine


class ProcurementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def request(self, request_id: UUID) -> ProcurementRequest | None:
        return self.session.scalar(
            select(ProcurementRequest)
            .options(selectinload(ProcurementRequest.lines))
            .where(
                ProcurementRequest.id == request_id,
                ProcurementRequest.deleted_at.is_(None),
            )
        )

    def request_for_update(self, request_id: UUID) -> ProcurementRequest | None:
        return self.session.scalar(
            select(ProcurementRequest)
            .options(selectinload(ProcurementRequest.lines))
            .where(
                ProcurementRequest.id == request_id,
                ProcurementRequest.deleted_at.is_(None),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def requests(self, organization_id: UUID) -> tuple[ProcurementRequest, ...]:
        statement = (
            select(ProcurementRequest)
            .options(selectinload(ProcurementRequest.lines))
            .where(
                ProcurementRequest.organization_id == organization_id,
                ProcurementRequest.deleted_at.is_(None),
            )
            .order_by(ProcurementRequest.created_at.desc(), ProcurementRequest.request_no.desc())
        )
        return tuple(self.session.scalars(statement))

    def add(self, request: ProcurementRequest) -> None:
        self.session.add(request)

    def delete(self, request: ProcurementRequest) -> None:
        request.soft_delete()

    def replace_lines(
        self, request: ProcurementRequest, lines: list[ProcurementRequestLine]
    ) -> None:
        request.lines.clear()
        self.session.flush()
        request.lines.extend(lines)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
