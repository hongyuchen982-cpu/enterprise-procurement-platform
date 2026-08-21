from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.receiving import ReceiptCreate, ReceiptSnapshot, ReceiptUpdate
from app.modules.audit.facade import AuditFacade
from app.modules.identity.facade import IdentityFacade
from app.modules.inventory.facade import InventoryFacade
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.receiving.repository import ReceiptRepository
from app.modules.receiving.service import ReceiptService


class ReceiptFacade:
    def __init__(self, session: Session) -> None:
        self.service = ReceiptService(
            ReceiptRepository(session),
            PurchaseOrderFacade(session),
            IdentityFacade(session),
            inventory=InventoryFacade(session),
            audit=AuditFacade(session),
        )

    def create(
        self,
        payload: ReceiptCreate,
        receiver_membership_id: UUID,
        receiver_id: UUID,
    ) -> ReceiptSnapshot:
        return self.service.create(payload, receiver_membership_id, receiver_id)

    def get(self, receipt_id: UUID) -> ReceiptSnapshot:
        return self.service.get(receipt_id)

    def list(self, organization_id: UUID) -> tuple[ReceiptSnapshot, ...]:
        return self.service.list_receipts(organization_id)

    def update(self, receipt_id: UUID, payload: ReceiptUpdate) -> ReceiptSnapshot:
        return self.service.update(receipt_id, payload)

    def delete(self, receipt_id: UUID, expected_version: int) -> None:
        self.service.delete(receipt_id, expected_version)

    def complete(self, receipt_id: UUID, expected_version: int) -> ReceiptSnapshot:
        return self.service.complete(receipt_id, expected_version)

    def cancel(self, receipt_id: UUID, expected_version: int) -> ReceiptSnapshot:
        return self.service.cancel(receipt_id, expected_version)
