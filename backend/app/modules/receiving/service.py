from collections.abc import Callable
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.contracts.audit import AuditEntryInput
from app.contracts.common import ActorType, AuditSource
from app.contracts.inventory import InventoryReceiptAllocation
from app.contracts.order import (
    PurchaseOrderReceiptAllocation,
    PurchaseOrderSnapshot,
    PurchaseOrderStatus,
)
from app.contracts.receiving import (
    InspectionStatus,
    ReceiptCreate,
    ReceiptLineInput,
    ReceiptLineSnapshot,
    ReceiptSnapshot,
    ReceiptStatus,
    ReceiptUpdate,
)
from app.core.database import utc_now
from app.modules.audit.facade import AuditFacade
from app.modules.identity.facade import IdentityFacade
from app.modules.inventory.facade import InventoryFacade
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.receiving.models import Receipt, ReceiptLine, ReceiptRecordStatus
from app.modules.receiving.repository import ReceiptRepository


class ReceiptNotFoundError(LookupError):
    pass


class ReceiptConflictError(ValueError):
    pass


class ReceiptStateError(ValueError):
    pass


class InvalidReceiptReferenceError(ValueError):
    pass


class ReceiptService:
    def __init__(
        self,
        repository: ReceiptRepository,
        orders: PurchaseOrderFacade,
        identity: IdentityFacade,
        today: Callable[[], date] = date.today,
        inventory: InventoryFacade | None = None,
        audit: AuditFacade | None = None,
    ) -> None:
        self.repository = repository
        self.orders = orders
        self.identity = identity
        self.today = today
        self.inventory = inventory
        self.audit = audit

    def create(
        self,
        payload: ReceiptCreate,
        receiver_membership_id: UUID,
        receiver_id: UUID,
    ) -> ReceiptSnapshot:
        order = self._receivable_order(payload.order_id)
        self._validate_receiver(
            receiver_membership_id,
            receiver_id,
            order.org_id,
        )
        receipt = Receipt(
            receipt_no=self._new_receipt_no(),
            organization_id=order.org_id,
            order_id=order.order_id,
            receiver_membership_id=receiver_membership_id,
            receiver_id=receiver_id,
            lines=self._build_lines(order, payload.lines),
        )
        self.repository.add(receipt)
        self._commit("receipt number already exists")
        return self.snapshot(receipt)

    def get(self, receipt_id: UUID) -> ReceiptSnapshot:
        return self.snapshot(self._receipt(receipt_id))

    def list_receipts(self, organization_id: UUID) -> tuple[ReceiptSnapshot, ...]:
        return tuple(self.snapshot(value) for value in self.repository.receipts(organization_id))

    def update(self, receipt_id: UUID, payload: ReceiptUpdate) -> ReceiptSnapshot:
        receipt = self._receipt(receipt_id)
        self._require_version(receipt, payload.expected_version)
        self._require_draft(receipt)
        order = self._receivable_order(receipt.order_id)
        lines = self._build_lines(order, payload.lines)
        self.repository.replace_lines(receipt, lines)
        receipt.updated_at = utc_now()
        self._commit("receipt was updated concurrently")
        return self.snapshot(receipt)

    def delete(self, receipt_id: UUID, expected_version: int) -> None:
        receipt = self._receipt(receipt_id)
        self._require_version(receipt, expected_version)
        self._require_draft(receipt)
        self.repository.delete(receipt)
        self._commit("receipt was updated concurrently")

    def complete(self, receipt_id: UUID, expected_version: int) -> ReceiptSnapshot:
        receipt = self._receipt(receipt_id)
        self._require_version(receipt, expected_version)
        self._require_draft(receipt)
        if any(line.inspection_status == InspectionStatus.PENDING for line in receipt.lines):
            raise ReceiptStateError("all receipt inspections must be complete")
        order = self._receivable_order(receipt.order_id)
        order_lines = {line.line_id: line for line in order.lines}
        receipt.status = ReceiptRecordStatus.COMPLETED
        receipt.received_at = utc_now()
        try:
            if self.inventory is not None:
                self.inventory.stage_receipt(
                    [
                        InventoryReceiptAllocation(
                            receipt_id=receipt.id,
                            receipt_line_id=line.id,
                            organization_id=receipt.organization_id,
                            material_id=order_lines[line.order_line_id].material_id,
                            category_id=order_lines[line.order_line_id].category_id,
                            unit=order_lines[line.order_line_id].unit,
                            quantity=line.accepted_quantity,
                        )
                        for line in receipt.lines
                        if line.accepted_quantity > 0
                        and order_lines[line.order_line_id].material_id is not None
                    ]
                )
            if self.audit is not None:
                self.audit.stage(
                    AuditEntryInput(
                        organization_id=receipt.organization_id,
                        action="RECEIPT_COMPLETED",
                        object_type="GOODS_RECEIPT",
                        object_id=receipt.id,
                        object_version=receipt.version + 1,
                        actor_membership_id=receipt.receiver_membership_id,
                        actor_id=receipt.receiver_id,
                        actor_type=ActorType.USER,
                        source=AuditSource.API,
                        before={"status": ReceiptRecordStatus.DRAFT},
                        after={
                            "status": ReceiptRecordStatus.COMPLETED,
                            "order_id": str(receipt.order_id),
                        },
                    )
                )
            self.orders.record_receipt(
                receipt.order_id,
                [
                    PurchaseOrderReceiptAllocation(
                        order_line_id=line.order_line_id,
                        accepted_quantity=line.accepted_quantity,
                    )
                    for line in receipt.lines
                ],
            )
        except (LookupError, ValueError) as exc:
            self.repository.rollback()
            raise ReceiptConflictError(str(exc)) from exc
        return self.snapshot(receipt)

    def cancel(self, receipt_id: UUID, expected_version: int) -> ReceiptSnapshot:
        receipt = self._receipt(receipt_id)
        self._require_version(receipt, expected_version)
        self._require_draft(receipt)
        receipt.status = ReceiptRecordStatus.CANCELLED
        self._commit("receipt was updated concurrently")
        return self.snapshot(receipt)

    def _receivable_order(self, order_id: UUID) -> PurchaseOrderSnapshot:
        try:
            order = self.orders.get(order_id)
        except LookupError as exc:
            raise InvalidReceiptReferenceError("purchase order not found") from exc
        if order.status not in (
            PurchaseOrderStatus.ISSUED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        ):
            raise ReceiptStateError(
                "only issued or partially received orders can create receipt drafts"
            )
        return order

    def _build_lines(
        self,
        order: PurchaseOrderSnapshot,
        payloads: list[ReceiptLineInput],
    ) -> list[ReceiptLine]:
        order_lines = {line.line_id: line for line in order.lines}
        seen: set[UUID] = set()
        lines: list[ReceiptLine] = []
        for line_no, payload in enumerate(payloads, start=1):
            if payload.order_line_id in seen:
                raise InvalidReceiptReferenceError("an order line may appear only once per receipt")
            seen.add(payload.order_line_id)
            order_line = order_lines.get(payload.order_line_id)
            if order_line is None:
                raise InvalidReceiptReferenceError(
                    f"receipt line {line_no} does not belong to the purchase order"
                )
            received = payload.accepted_quantity + payload.rejected_quantity
            if received <= 0:
                raise InvalidReceiptReferenceError(
                    f"receipt line {line_no} quantity must be positive"
                )
            remaining = order_line.ordered_quantity - order_line.received_quantity
            if payload.accepted_quantity > remaining:
                raise ReceiptConflictError(
                    f"receipt line {line_no} accepted quantity exceeds remaining {remaining}"
                )
            if (
                payload.inspection_status is InspectionStatus.FAILED
                and payload.accepted_quantity > 0
            ):
                raise InvalidReceiptReferenceError(
                    f"failed receipt line {line_no} cannot have accepted quantity"
                )
            if (
                payload.inspection_status is InspectionStatus.PASSED
                and payload.accepted_quantity <= 0
            ):
                raise InvalidReceiptReferenceError(
                    f"passed receipt line {line_no} must have accepted quantity"
                )
            lines.append(
                ReceiptLine(
                    line_no=line_no,
                    order_line_id=payload.order_line_id,
                    received_quantity=received,
                    accepted_quantity=payload.accepted_quantity,
                    rejected_quantity=payload.rejected_quantity,
                    inspection_status=payload.inspection_status,
                )
            )
        return lines

    def _validate_receiver(
        self,
        membership_id: UUID,
        receiver_id: UUID,
        organization_id: UUID,
    ) -> None:
        try:
            membership = self.identity.membership(membership_id)
        except LookupError as exc:
            raise InvalidReceiptReferenceError("active receiver membership not found") from exc
        if membership.user_id != receiver_id or membership.organization_id != organization_id:
            raise InvalidReceiptReferenceError(
                "receiver membership must belong to the user and order organization"
            )

    def _receipt(self, receipt_id: UUID) -> Receipt:
        receipt = self.repository.receipt(receipt_id)
        if receipt is None:
            raise ReceiptNotFoundError(str(receipt_id))
        return receipt

    @staticmethod
    def _require_draft(receipt: Receipt) -> None:
        if receipt.status != ReceiptRecordStatus.DRAFT:
            raise ReceiptStateError("only draft receipts can be changed")

    @staticmethod
    def _require_version(receipt: Receipt, expected_version: int) -> None:
        if receipt.version != expected_version:
            raise ReceiptConflictError(
                f"version mismatch: expected {expected_version}, current {receipt.version}"
            )

    def _new_receipt_no(self) -> str:
        return f"GR-{self.today():%Y%m%d}-{uuid4().hex[:12].upper()}"

    def _commit(self, message: str) -> None:
        try:
            self.repository.commit()
        except (IntegrityError, StaleDataError) as exc:
            self.repository.rollback()
            raise ReceiptConflictError(message) from exc

    @staticmethod
    def snapshot(receipt: Receipt) -> ReceiptSnapshot:
        return ReceiptSnapshot(
            receipt_id=receipt.id,
            receipt_no=receipt.receipt_no,
            org_id=receipt.organization_id,
            order_id=receipt.order_id,
            receiver_membership_id=receipt.receiver_membership_id,
            receiver_id=receipt.receiver_id,
            status=ReceiptStatus(receipt.status),
            received_at=receipt.received_at,
            lines=[
                ReceiptLineSnapshot(
                    line_id=line.id,
                    order_line_id=line.order_line_id,
                    received_quantity=line.received_quantity,
                    accepted_quantity=line.accepted_quantity,
                    rejected_quantity=line.rejected_quantity,
                    inspection_status=InspectionStatus(line.inspection_status),
                )
                for line in receipt.lines
            ],
            version=receipt.version,
            updated_at=receipt.updated_at,
        )
