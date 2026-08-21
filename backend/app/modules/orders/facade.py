from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.order import (
    PurchaseOrderCreate,
    PurchaseOrderInvoiceAllocation,
    PurchaseOrderReceiptAllocation,
    PurchaseOrderSnapshot,
    PurchaseOrderUpdate,
)
from app.modules.orders.repository import PurchaseOrderRepository
from app.modules.orders.service import PurchaseOrderService
from app.modules.procurement.facade import ProcurementFacade


class PurchaseOrderFacade:
    def __init__(self, session: Session) -> None:
        self.service = PurchaseOrderService(
            PurchaseOrderRepository(session), ProcurementFacade(session)
        )

    def create(self, payload: PurchaseOrderCreate) -> PurchaseOrderSnapshot:
        return self.service.create(payload)

    def get(self, order_id: UUID) -> PurchaseOrderSnapshot:
        return self.service.get(order_id)

    def list(self, organization_id: UUID) -> tuple[PurchaseOrderSnapshot, ...]:
        return self.service.list_orders(organization_id)

    def update(self, order_id: UUID, payload: PurchaseOrderUpdate) -> PurchaseOrderSnapshot:
        return self.service.update(order_id, payload)

    def delete(self, order_id: UUID, expected_version: int) -> None:
        self.service.delete(order_id, expected_version)

    def issue(self, order_id: UUID, expected_version: int) -> PurchaseOrderSnapshot:
        return self.service.issue(order_id, expected_version)

    def cancel(self, order_id: UUID, expected_version: int) -> PurchaseOrderSnapshot:
        return self.service.cancel(order_id, expected_version)

    def record_receipt(
        self,
        order_id: UUID,
        allocations: list[PurchaseOrderReceiptAllocation],
    ) -> PurchaseOrderSnapshot:
        return self.service.record_receipt(order_id, allocations)

    def record_invoice(
        self,
        order_id: UUID,
        allocations: list[PurchaseOrderInvoiceAllocation],
        allow_variance: bool,
    ) -> PurchaseOrderSnapshot:
        return self.service.record_invoice(order_id, allocations, allow_variance)
