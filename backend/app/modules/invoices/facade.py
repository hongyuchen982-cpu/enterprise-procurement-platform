from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.invoice import (
    InvoiceApproval,
    InvoiceCreate,
    InvoiceSnapshot,
    InvoiceUpdate,
)
from app.modules.audit.facade import AuditFacade
from app.modules.identity.facade import IdentityFacade
from app.modules.invoices.repository import InvoiceRepository
from app.modules.invoices.service import InvoiceService
from app.modules.orders.facade import PurchaseOrderFacade


class InvoiceFacade:
    def __init__(self, session: Session) -> None:
        self.service = InvoiceService(
            InvoiceRepository(session),
            PurchaseOrderFacade(session),
            IdentityFacade(session),
            audit=AuditFacade(session),
        )

    def create(self, payload: InvoiceCreate) -> InvoiceSnapshot:
        return self.service.create(payload)

    def get(self, invoice_id: UUID) -> InvoiceSnapshot:
        return self.service.get(invoice_id)

    def list(self, organization_id: UUID) -> tuple[InvoiceSnapshot, ...]:
        return self.service.list_invoices(organization_id)

    def update(self, invoice_id: UUID, payload: InvoiceUpdate) -> InvoiceSnapshot:
        return self.service.update(invoice_id, payload)

    def delete(self, invoice_id: UUID, expected_version: int) -> None:
        self.service.delete(invoice_id, expected_version)

    def submit(self, invoice_id: UUID, expected_version: int) -> InvoiceSnapshot:
        return self.service.submit(invoice_id, expected_version)

    def approve(
        self,
        invoice_id: UUID,
        approver_membership_id: UUID,
        payload: InvoiceApproval,
    ) -> InvoiceSnapshot:
        return self.service.approve(invoice_id, approver_membership_id, payload)

    def cancel(self, invoice_id: UUID, expected_version: int) -> InvoiceSnapshot:
        return self.service.cancel(invoice_id, expected_version)
