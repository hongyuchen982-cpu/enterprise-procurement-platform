from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.contracts.audit import AuditEntryInput
from app.contracts.common import ActorType, AuditSource
from app.contracts.invoice import (
    InvoiceApproval,
    InvoiceCreate,
    InvoiceLineInput,
    InvoiceLineSnapshot,
    InvoiceSnapshot,
    InvoiceStatus,
    InvoiceUpdate,
)
from app.contracts.order import (
    PurchaseOrderInvoiceAllocation,
    PurchaseOrderSnapshot,
    PurchaseOrderStatus,
)
from app.core.database import utc_now
from app.modules.audit.facade import AuditFacade
from app.modules.identity.facade import IdentityFacade
from app.modules.invoices.models import Invoice, InvoiceLine, InvoiceRecordStatus
from app.modules.invoices.repository import InvoiceRepository
from app.modules.orders.facade import PurchaseOrderFacade

MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("9999999999999999.99")
PRICE_TOLERANCE = Decimal("0.01")


class InvoiceNotFoundError(LookupError):
    pass


class InvoiceConflictError(ValueError):
    pass


class InvoiceStateError(ValueError):
    pass


class InvalidInvoiceReferenceError(ValueError):
    pass


class InvoiceService:
    def __init__(
        self,
        repository: InvoiceRepository,
        orders: PurchaseOrderFacade,
        identity: IdentityFacade,
        today: Callable[[], date] = date.today,
        audit: AuditFacade | None = None,
    ) -> None:
        self.repository = repository
        self.orders = orders
        self.identity = identity
        self.today = today
        self.audit = audit

    def create(self, payload: InvoiceCreate) -> InvoiceSnapshot:
        order = self._invoiceable_order(payload.order_id)
        if payload.supplier_id != order.supplier_id:
            raise InvalidInvoiceReferenceError("invoice supplier must match the purchase order")
        if payload.currency != order.currency:
            raise InvalidInvoiceReferenceError("invoice currency must match the purchase order")
        self._validate_invoice_date(payload.invoice_date)
        lines = self._build_lines(order, payload.lines)
        invoice = Invoice(
            invoice_no=payload.invoice_no,
            organization_id=order.org_id,
            order_id=order.order_id,
            supplier_id=payload.supplier_id,
            invoice_date=payload.invoice_date,
            currency=payload.currency,
            total_amount=self._total(lines),
            lines=lines,
        )
        self.repository.add(invoice)
        self._commit("supplier invoice number already exists")
        return self.snapshot(invoice)

    def get(self, invoice_id: UUID) -> InvoiceSnapshot:
        return self.snapshot(self._invoice(invoice_id))

    def list_invoices(self, organization_id: UUID) -> tuple[InvoiceSnapshot, ...]:
        return tuple(self.snapshot(value) for value in self.repository.invoices(organization_id))

    def update(self, invoice_id: UUID, payload: InvoiceUpdate) -> InvoiceSnapshot:
        invoice = self._invoice(invoice_id)
        self._require_version(invoice, payload.expected_version)
        self._require_draft(invoice)
        order = self._invoiceable_order(invoice.order_id)
        self._validate_invoice_date(payload.invoice_date)
        lines = self._build_lines(order, payload.lines)
        invoice.invoice_date = payload.invoice_date
        self.repository.replace_lines(invoice, lines)
        invoice.total_amount = self._total(lines)
        invoice.updated_at = utc_now()
        self._commit("invoice was updated concurrently")
        return self.snapshot(invoice)

    def delete(self, invoice_id: UUID, expected_version: int) -> None:
        invoice = self._invoice(invoice_id)
        self._require_version(invoice, expected_version)
        self._require_draft(invoice)
        self.repository.delete(invoice)
        self._commit("invoice was updated concurrently")

    def submit(self, invoice_id: UUID, expected_version: int) -> InvoiceSnapshot:
        invoice = self._invoice(invoice_id)
        self._require_version(invoice, expected_version)
        self._require_draft(invoice)
        order = self._invoiceable_order(invoice.order_id)
        order_lines = {line.line_id: line for line in order.lines}
        matched = True
        for line in invoice.lines:
            order_line = order_lines.get(line.order_line_id)
            if order_line is None:
                raise InvalidInvoiceReferenceError(
                    "invoice line does not belong to the purchase order"
                )
            line.quantity_matched = (
                order_line.invoiced_quantity + line.invoiced_quantity
                <= order_line.received_quantity
            )
            line.price_matched = (
                abs(line.unit_price - order_line.unit_price) <= PRICE_TOLERANCE
                and line.tax_rate == order_line.tax_rate
            )
            matched = matched and line.quantity_matched and line.price_matched
        invoice.status = InvoiceRecordStatus.MATCHED if matched else InvoiceRecordStatus.EXCEPTION
        invoice.submitted_at = utc_now()
        self._commit("invoice was updated concurrently")
        return self.snapshot(invoice)

    def approve(
        self,
        invoice_id: UUID,
        approver_membership_id: UUID,
        payload: InvoiceApproval,
    ) -> InvoiceSnapshot:
        invoice = self._invoice(invoice_id)
        self._require_version(invoice, payload.expected_version)
        if invoice.status not in (
            InvoiceRecordStatus.MATCHED,
            InvoiceRecordStatus.EXCEPTION,
        ):
            raise InvoiceStateError("only matched or exception invoices can be approved")
        if invoice.status == InvoiceRecordStatus.EXCEPTION and payload.comment is None:
            raise InvoiceStateError("exception approval comment is required")
        try:
            membership = self.identity.membership(approver_membership_id)
        except LookupError as exc:
            raise InvalidInvoiceReferenceError("active approver membership not found") from exc
        if membership.organization_id != invoice.organization_id:
            raise InvalidInvoiceReferenceError(
                "approver membership must belong to the invoice organization"
            )
        has_variance = invoice.status == InvoiceRecordStatus.EXCEPTION
        previous_status = invoice.status
        invoice.status = InvoiceRecordStatus.APPROVED
        invoice.approved_at = utc_now()
        invoice.approved_by_membership_id = approver_membership_id
        invoice.approval_comment = payload.comment
        try:
            if self.audit is not None:
                self.audit.stage(
                    AuditEntryInput(
                        organization_id=invoice.organization_id,
                        action="INVOICE_APPROVED",
                        object_type="SUPPLIER_INVOICE",
                        object_id=invoice.id,
                        object_version=invoice.version + 1,
                        actor_membership_id=approver_membership_id,
                        actor_id=membership.user_id,
                        actor_type=ActorType.USER,
                        source=AuditSource.API,
                        before={"status": previous_status},
                        after={
                            "status": InvoiceRecordStatus.APPROVED,
                            "exception": has_variance,
                            "comment": payload.comment,
                        },
                    )
                )
            self.orders.record_invoice(
                invoice.order_id,
                [
                    PurchaseOrderInvoiceAllocation(
                        order_line_id=line.order_line_id,
                        invoiced_quantity=line.invoiced_quantity,
                    )
                    for line in invoice.lines
                ],
                allow_variance=has_variance,
            )
        except (LookupError, ValueError) as exc:
            self.repository.rollback()
            raise InvoiceConflictError(str(exc)) from exc
        return self.snapshot(invoice)

    def cancel(self, invoice_id: UUID, expected_version: int) -> InvoiceSnapshot:
        invoice = self._invoice(invoice_id)
        self._require_version(invoice, expected_version)
        if invoice.status not in (
            InvoiceRecordStatus.DRAFT,
            InvoiceRecordStatus.MATCHED,
            InvoiceRecordStatus.EXCEPTION,
        ):
            raise InvoiceStateError("approved or cancelled invoices cannot be cancelled")
        invoice.status = InvoiceRecordStatus.CANCELLED
        self._commit("invoice was updated concurrently")
        return self.snapshot(invoice)

    def _invoiceable_order(self, order_id: UUID) -> PurchaseOrderSnapshot:
        try:
            order = self.orders.get(order_id)
        except LookupError as exc:
            raise InvalidInvoiceReferenceError("purchase order not found") from exc
        if order.status not in (
            PurchaseOrderStatus.ISSUED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
            PurchaseOrderStatus.RECEIVED,
        ):
            raise InvoiceStateError("purchase order cannot accept invoices")
        return order

    def _build_lines(
        self,
        order: PurchaseOrderSnapshot,
        payloads: list[InvoiceLineInput],
    ) -> list[InvoiceLine]:
        order_lines = {line.line_id: line for line in order.lines}
        seen: set[UUID] = set()
        lines: list[InvoiceLine] = []
        for line_no, payload in enumerate(payloads, start=1):
            if payload.order_line_id in seen:
                raise InvalidInvoiceReferenceError("an order line may appear only once per invoice")
            seen.add(payload.order_line_id)
            if payload.order_line_id not in order_lines:
                raise InvalidInvoiceReferenceError(
                    f"invoice line {line_no} does not belong to the purchase order"
                )
            amount = (
                payload.invoiced_quantity * payload.unit_price * (Decimal("1") + payload.tax_rate)
            ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            if amount > MAX_MONEY:
                raise InvalidInvoiceReferenceError(
                    f"invoice line {line_no} amount exceeds the supported money range"
                )
            lines.append(
                InvoiceLine(
                    line_no=line_no,
                    order_line_id=payload.order_line_id,
                    invoiced_quantity=payload.invoiced_quantity,
                    unit_price=payload.unit_price,
                    tax_rate=payload.tax_rate,
                    line_amount=amount,
                )
            )
        return lines

    def _validate_invoice_date(self, invoice_date: date) -> None:
        if invoice_date > self.today():
            raise InvalidInvoiceReferenceError("invoice date cannot be in the future")

    def _invoice(self, invoice_id: UUID) -> Invoice:
        invoice = self.repository.invoice(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))
        return invoice

    @staticmethod
    def _require_draft(invoice: Invoice) -> None:
        if invoice.status != InvoiceRecordStatus.DRAFT:
            raise InvoiceStateError("only draft invoices can be changed")

    @staticmethod
    def _require_version(invoice: Invoice, expected_version: int) -> None:
        if invoice.version != expected_version:
            raise InvoiceConflictError(
                f"version mismatch: expected {expected_version}, current {invoice.version}"
            )

    @staticmethod
    def _total(lines: list[InvoiceLine]) -> Decimal:
        total = sum((line.line_amount for line in lines), Decimal("0")).quantize(MONEY_QUANTUM)
        if total > MAX_MONEY:
            raise InvalidInvoiceReferenceError("invoice total exceeds the supported money range")
        return total

    def _commit(self, message: str) -> None:
        try:
            self.repository.commit()
        except (IntegrityError, StaleDataError) as exc:
            self.repository.rollback()
            raise InvoiceConflictError(message) from exc

    @staticmethod
    def snapshot(invoice: Invoice) -> InvoiceSnapshot:
        return InvoiceSnapshot(
            invoice_id=invoice.id,
            invoice_no=invoice.invoice_no,
            org_id=invoice.organization_id,
            order_id=invoice.order_id,
            supplier_id=invoice.supplier_id,
            invoice_date=invoice.invoice_date,
            currency=invoice.currency,
            status=InvoiceStatus(invoice.status),
            total_amount=invoice.total_amount,
            lines=[
                InvoiceLineSnapshot(
                    line_id=line.id,
                    line_no=line.line_no,
                    order_line_id=line.order_line_id,
                    invoiced_quantity=line.invoiced_quantity,
                    unit_price=line.unit_price,
                    tax_rate=line.tax_rate,
                    line_amount=line.line_amount,
                    quantity_matched=line.quantity_matched,
                    price_matched=line.price_matched,
                )
                for line in invoice.lines
            ],
            submitted_at=invoice.submitted_at,
            approved_at=invoice.approved_at,
            approved_by_membership_id=invoice.approved_by_membership_id,
            approval_comment=invoice.approval_comment,
            version=invoice.version,
            updated_at=invoice.updated_at,
        )
