from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.orders.models import PurchaseOrder, PurchaseOrderRecordStatus


class PurchaseOrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def order(self, order_id: UUID) -> PurchaseOrder | None:
        return self.session.scalar(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.lines))
            .where(PurchaseOrder.id == order_id, PurchaseOrder.deleted_at.is_(None))
        )

    def order_for_update(self, order_id: UUID) -> PurchaseOrder | None:
        return self.session.scalar(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.lines))
            .where(PurchaseOrder.id == order_id, PurchaseOrder.deleted_at.is_(None))
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def order_by_no(self, order_no: str) -> PurchaseOrder | None:
        return self.session.scalar(
            select(PurchaseOrder).where(
                PurchaseOrder.order_no == order_no,
                PurchaseOrder.deleted_at.is_(None),
            )
        )

    def order_for_award(self, award_id: UUID) -> PurchaseOrder | None:
        return self.session.scalar(
            select(PurchaseOrder).where(
                PurchaseOrder.sourcing_award_id == award_id,
                PurchaseOrder.deleted_at.is_(None),
            )
        )

    def orders_for_request(self, request_id: UUID) -> tuple[PurchaseOrder, ...]:
        return tuple(
            self.session.scalars(
                select(PurchaseOrder)
                .options(selectinload(PurchaseOrder.lines))
                .where(
                    PurchaseOrder.procurement_request_id == request_id,
                    PurchaseOrder.deleted_at.is_(None),
                    PurchaseOrder.status != PurchaseOrderRecordStatus.CANCELLED,
                )
            )
        )

    def orders(self, organization_id: UUID) -> tuple[PurchaseOrder, ...]:
        return tuple(
            self.session.scalars(
                select(PurchaseOrder)
                .options(selectinload(PurchaseOrder.lines))
                .where(
                    PurchaseOrder.organization_id == organization_id,
                    PurchaseOrder.deleted_at.is_(None),
                )
                .order_by(PurchaseOrder.created_at.desc())
            )
        )

    def add(self, order: PurchaseOrder) -> None:
        self.session.add(order)

    def delete(self, order: PurchaseOrder) -> None:
        order.soft_delete()

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
