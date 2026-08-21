from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.invoices.models import Invoice, InvoiceLine


class InvoiceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def invoice(self, invoice_id: UUID) -> Invoice | None:
        return self.session.scalar(
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
        )

    def invoices(self, organization_id: UUID) -> tuple[Invoice, ...]:
        return tuple(
            self.session.scalars(
                select(Invoice)
                .options(selectinload(Invoice.lines))
                .where(
                    Invoice.organization_id == organization_id,
                    Invoice.deleted_at.is_(None),
                )
                .order_by(Invoice.created_at.desc())
            )
        )

    def add(self, invoice: Invoice) -> None:
        self.session.add(invoice)

    def replace_lines(self, invoice: Invoice, lines: list[InvoiceLine]) -> None:
        invoice.lines.clear()
        self.session.flush()
        invoice.lines.extend(lines)

    def delete(self, invoice: Invoice) -> None:
        invoice.soft_delete()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
