from collections import defaultdict
from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.contracts.order import (
    PurchaseOrderCreate,
    PurchaseOrderInvoiceAllocation,
    PurchaseOrderLineInput,
    PurchaseOrderLineSnapshot,
    PurchaseOrderReceiptAllocation,
    PurchaseOrderSnapshot,
    PurchaseOrderStatus,
    PurchaseOrderUpdate,
)
from app.contracts.procurement import ProcurementRequestSnapshot, ProcurementRequestStatus
from app.contracts.supplier import QualificationStatus, SupplierSnapshot, SupplierStatus
from app.core.database import utc_now
from app.modules.orders.models import PurchaseOrder, PurchaseOrderLine, PurchaseOrderRecordStatus
from app.modules.orders.repository import PurchaseOrderRepository
from app.modules.procurement.facade import ProcurementFacade
from app.modules.suppliers.facade import get_supplier_snapshot

MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("9999999999999999.99")


class PurchaseOrderNotFoundError(LookupError):
    pass


class PurchaseOrderConflictError(ValueError):
    pass


class PurchaseOrderStateError(ValueError):
    pass


class InvalidPurchaseOrderReferenceError(ValueError):
    pass


class PurchaseOrderService:
    def __init__(
        self,
        repository: PurchaseOrderRepository,
        procurement: ProcurementFacade,
        supplier_lookup: Callable[[UUID], SupplierSnapshot | None] = get_supplier_snapshot,
        today: Callable[[], date] = date.today,
    ) -> None:
        self.repository = repository
        self.procurement = procurement
        self.supplier_lookup = supplier_lookup
        self.today = today

    def create(self, payload: PurchaseOrderCreate) -> PurchaseOrderSnapshot:
        request = self._approved_request(payload.procurement_request_id)
        supplier = self._supplier(payload.supplier_id, request.org_id)
        if payload.sourcing_award_id is not None and self.repository.order_for_award(
            payload.sourcing_award_id
        ):
            raise PurchaseOrderConflictError("sourcing award already has a purchase order")
        self._validate_promised_date(payload.promised_date)
        lines = self._build_lines(request, supplier, payload.lines)
        order = PurchaseOrder(
            order_no=self._new_order_no(),
            organization_id=request.org_id,
            procurement_request_id=request.request_id,
            supplier_id=payload.supplier_id,
            sourcing_award_id=payload.sourcing_award_id,
            currency=request.currency,
            total_amount=self._total(lines),
            required_date=request.required_date,
            promised_date=payload.promised_date,
            lines=lines,
        )
        self.repository.add(order)
        self._commit("purchase order number or sourcing award already exists")
        return self.snapshot(order)

    def get(self, order_id: UUID) -> PurchaseOrderSnapshot:
        return self.snapshot(self._order(order_id))

    def list_orders(self, organization_id: UUID) -> tuple[PurchaseOrderSnapshot, ...]:
        return tuple(self.snapshot(order) for order in self.repository.orders(organization_id))

    def update(self, order_id: UUID, payload: PurchaseOrderUpdate) -> PurchaseOrderSnapshot:
        order = self._order(order_id)
        self._require_version(order, payload.expected_version)
        self._require_draft(order)
        request = self._approved_request(order.procurement_request_id)
        supplier = self._supplier(order.supplier_id, order.organization_id)
        self._validate_promised_date(payload.promised_date)
        lines = self._build_lines(request, supplier, payload.lines, excluding_order_id=order.id)
        order.promised_date = payload.promised_date
        order.lines.clear()
        self.repository.flush()
        order.lines = lines
        order.total_amount = self._total(lines)
        # Child-only edits must still advance the aggregate's optimistic-lock version.
        order.updated_at = utc_now()
        self._commit("purchase order was updated concurrently")
        return self.snapshot(order)

    def delete(self, order_id: UUID, expected_version: int) -> None:
        order = self._order(order_id)
        self._require_version(order, expected_version)
        self._require_draft(order)
        self.repository.delete(order)
        self._commit("purchase order was updated concurrently")

    def issue(self, order_id: UUID, expected_version: int) -> PurchaseOrderSnapshot:
        order = self._order(order_id)
        self._require_version(order, expected_version)
        self._require_draft(order)
        self._supplier(order.supplier_id, order.organization_id)
        if not order.lines:
            raise PurchaseOrderStateError("purchase order has no lines")
        order.status = PurchaseOrderRecordStatus.ISSUED
        order.issued_at = utc_now()
        self._commit("purchase order was updated concurrently")
        return self.snapshot(order)

    def cancel(self, order_id: UUID, expected_version: int) -> PurchaseOrderSnapshot:
        order = self._order(order_id)
        self._require_version(order, expected_version)
        if order.status not in (
            PurchaseOrderRecordStatus.DRAFT,
            PurchaseOrderRecordStatus.ISSUED,
        ):
            raise PurchaseOrderStateError("only draft or issued orders can be cancelled")
        if any(line.received_quantity > 0 or line.invoiced_quantity > 0 for line in order.lines):
            raise PurchaseOrderStateError("fulfilled purchase orders cannot be cancelled")
        order.status = PurchaseOrderRecordStatus.CANCELLED
        order.cancelled_at = utc_now()
        self._commit("purchase order was updated concurrently")
        return self.snapshot(order)

    def record_receipt(
        self,
        order_id: UUID,
        allocations: list[PurchaseOrderReceiptAllocation],
    ) -> PurchaseOrderSnapshot:
        order = self.repository.order_for_update(order_id)
        if order is None:
            raise PurchaseOrderNotFoundError(str(order_id))
        if order.status not in (
            PurchaseOrderRecordStatus.ISSUED,
            PurchaseOrderRecordStatus.PARTIALLY_RECEIVED,
        ):
            raise PurchaseOrderStateError(
                "only issued or partially received orders can receive goods"
            )
        lines = {line.id: line for line in order.lines}
        seen: set[UUID] = set()
        changed = False
        for allocation in allocations:
            if allocation.order_line_id in seen:
                raise InvalidPurchaseOrderReferenceError(
                    "an order line may appear only once per receipt"
                )
            seen.add(allocation.order_line_id)
            line = lines.get(allocation.order_line_id)
            if line is None:
                raise InvalidPurchaseOrderReferenceError(
                    "receipt line does not belong to the purchase order"
                )
            received = line.received_quantity + allocation.accepted_quantity
            if received > line.ordered_quantity:
                raise PurchaseOrderConflictError(
                    f"accepted quantity exceeds remaining order quantity for line {line.line_no}"
                )
            if allocation.accepted_quantity > 0:
                line.received_quantity = received
                changed = True
        if all(line.received_quantity == line.ordered_quantity for line in order.lines):
            order.status = (
                PurchaseOrderRecordStatus.CLOSED
                if all(line.invoiced_quantity >= line.ordered_quantity for line in order.lines)
                else PurchaseOrderRecordStatus.RECEIVED
            )
            changed = True
        elif any(line.received_quantity > 0 for line in order.lines):
            order.status = PurchaseOrderRecordStatus.PARTIALLY_RECEIVED
            changed = True
        if changed:
            order.updated_at = utc_now()
        self._commit("purchase order receipt was updated concurrently")
        return self.snapshot(order)

    def record_invoice(
        self,
        order_id: UUID,
        allocations: list[PurchaseOrderInvoiceAllocation],
        allow_variance: bool,
    ) -> PurchaseOrderSnapshot:
        order = self.repository.order_for_update(order_id)
        if order is None:
            raise PurchaseOrderNotFoundError(str(order_id))
        if order.status not in (
            PurchaseOrderRecordStatus.ISSUED,
            PurchaseOrderRecordStatus.PARTIALLY_RECEIVED,
            PurchaseOrderRecordStatus.RECEIVED,
        ):
            raise PurchaseOrderStateError("purchase order cannot accept invoices")
        lines = {line.id: line for line in order.lines}
        seen: set[UUID] = set()
        for allocation in allocations:
            if allocation.order_line_id in seen:
                raise InvalidPurchaseOrderReferenceError(
                    "an order line may appear only once per invoice"
                )
            seen.add(allocation.order_line_id)
            line = lines.get(allocation.order_line_id)
            if line is None:
                raise InvalidPurchaseOrderReferenceError(
                    "invoice line does not belong to the purchase order"
                )
            invoiced = line.invoiced_quantity + allocation.invoiced_quantity
            if not allow_variance and invoiced > line.received_quantity:
                raise PurchaseOrderConflictError(
                    f"invoice quantity exceeds accepted quantity for line {line.line_no}"
                )
            line.invoiced_quantity = invoiced
        if all(
            line.received_quantity == line.ordered_quantity
            and line.invoiced_quantity >= line.ordered_quantity
            for line in order.lines
        ):
            order.status = PurchaseOrderRecordStatus.CLOSED
        order.updated_at = utc_now()
        self._commit("purchase order invoice was updated concurrently")
        return self.snapshot(order)

    def _approved_request(self, request_id: UUID) -> ProcurementRequestSnapshot:
        try:
            # The provider-owned lock serializes split-order allocation for one request.
            request = self.procurement.get_for_update(request_id)
        except LookupError as exc:
            raise InvalidPurchaseOrderReferenceError("procurement request not found") from exc
        if request.status is not ProcurementRequestStatus.APPROVED:
            raise PurchaseOrderStateError(
                "only approved procurement requests can create purchase orders"
            )
        return request

    def _supplier(self, supplier_id: UUID, organization_id: UUID) -> SupplierSnapshot:
        supplier = self.supplier_lookup(supplier_id)
        if supplier is None:
            raise InvalidPurchaseOrderReferenceError("supplier not found")
        if supplier.org_id != organization_id:
            raise InvalidPurchaseOrderReferenceError(
                "supplier and purchase order must belong to the same organization"
            )
        if (
            supplier.status is not SupplierStatus.ACTIVE
            or supplier.qualification_status is not QualificationStatus.QUALIFIED
            or supplier.is_frozen
        ):
            raise InvalidPurchaseOrderReferenceError(
                "supplier must be active, qualified, and not frozen"
            )
        return supplier

    def _build_lines(
        self,
        request: ProcurementRequestSnapshot,
        supplier: SupplierSnapshot,
        payloads: list[PurchaseOrderLineInput],
        excluding_order_id: UUID | None = None,
    ) -> list[PurchaseOrderLine]:
        request_lines = {line.line_id: line for line in request.lines}
        seen: set[UUID] = set()
        allocated: defaultdict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        for existing in self.repository.orders_for_request(request.request_id):
            if existing.id == excluding_order_id:
                continue
            for line in existing.lines:
                allocated[line.request_line_id] += line.ordered_quantity
        supplier_categories = set(supplier.category_ids)
        lines: list[PurchaseOrderLine] = []
        for line_no, payload in enumerate(payloads, start=1):
            if payload.request_line_id in seen:
                raise InvalidPurchaseOrderReferenceError(
                    "a procurement request line may appear only once per order"
                )
            seen.add(payload.request_line_id)
            source = request_lines.get(payload.request_line_id)
            if source is None:
                raise InvalidPurchaseOrderReferenceError(
                    f"order line {line_no} does not belong to the procurement request"
                )
            if source.category_id not in supplier_categories:
                raise InvalidPurchaseOrderReferenceError(
                    f"supplier is not qualified for order line {line_no} category"
                )
            remaining = source.quantity - allocated[payload.request_line_id]
            if payload.ordered_quantity > remaining:
                raise PurchaseOrderConflictError(
                    f"order line {line_no} exceeds remaining approved quantity {remaining}"
                )
            amount = (
                payload.ordered_quantity * payload.unit_price * (Decimal("1") + payload.tax_rate)
            ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            if amount > MAX_MONEY:
                raise InvalidPurchaseOrderReferenceError(
                    f"order line {line_no} amount exceeds the supported money range"
                )
            lines.append(
                PurchaseOrderLine(
                    line_no=line_no,
                    request_line_id=source.line_id,
                    material_id=source.material_id,
                    category_id=source.category_id,
                    description=source.description,
                    specification=source.specification,
                    unit_code=source.unit,
                    ordered_quantity=payload.ordered_quantity,
                    received_quantity=Decimal("0"),
                    invoiced_quantity=Decimal("0"),
                    unit_price=payload.unit_price,
                    tax_rate=payload.tax_rate,
                    line_amount=amount,
                )
            )
        return lines

    def _order(self, order_id: UUID) -> PurchaseOrder:
        order = self.repository.order(order_id)
        if order is None:
            raise PurchaseOrderNotFoundError(str(order_id))
        return order

    def _validate_promised_date(self, promised_date: date | None) -> None:
        if promised_date is not None and promised_date < self.today():
            raise InvalidPurchaseOrderReferenceError("promised date cannot be in the past")

    @staticmethod
    def _require_draft(order: PurchaseOrder) -> None:
        if order.status != PurchaseOrderRecordStatus.DRAFT:
            raise PurchaseOrderStateError("only draft purchase orders can be changed")

    @staticmethod
    def _require_version(order: PurchaseOrder, expected_version: int) -> None:
        if order.version != expected_version:
            raise PurchaseOrderConflictError(
                f"version mismatch: expected {expected_version}, current {order.version}"
            )

    @staticmethod
    def _total(lines: list[PurchaseOrderLine]) -> Decimal:
        total = sum((line.line_amount for line in lines), Decimal("0")).quantize(MONEY_QUANTUM)
        if total > MAX_MONEY:
            raise InvalidPurchaseOrderReferenceError(
                "purchase order total exceeds the supported money range"
            )
        return total

    def _new_order_no(self) -> str:
        return f"PO-{self.today():%Y%m%d}-{uuid4().hex[:12].upper()}"

    def _commit(self, message: str) -> None:
        try:
            self.repository.commit()
        except (IntegrityError, StaleDataError) as exc:
            self.repository.rollback()
            raise PurchaseOrderConflictError(message) from exc

    @staticmethod
    def snapshot(order: PurchaseOrder) -> PurchaseOrderSnapshot:
        return PurchaseOrderSnapshot(
            order_id=order.id,
            order_no=order.order_no,
            org_id=order.organization_id,
            procurement_request_id=order.procurement_request_id,
            supplier_id=order.supplier_id,
            sourcing_award_id=order.sourcing_award_id,
            status=PurchaseOrderStatus(order.status),
            currency=order.currency,
            total_amount=order.total_amount,
            required_date=order.required_date,
            promised_date=order.promised_date,
            issued_at=order.issued_at,
            cancelled_at=order.cancelled_at,
            lines=[
                PurchaseOrderLineSnapshot(
                    line_id=line.id,
                    line_no=line.line_no,
                    request_line_id=line.request_line_id,
                    material_id=line.material_id,
                    category_id=line.category_id,
                    description=line.description,
                    specification=line.specification,
                    unit=line.unit_code,
                    ordered_quantity=line.ordered_quantity,
                    received_quantity=line.received_quantity,
                    invoiced_quantity=line.invoiced_quantity,
                    unit_price=line.unit_price,
                    tax_rate=line.tax_rate,
                    line_amount=line.line_amount,
                )
                for line in order.lines
            ],
            version=order.version,
            updated_at=order.updated_at,
        )
