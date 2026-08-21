from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class PurchaseOrderStatus(StrEnum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PurchaseOrderLineInput(ContractModel):
    request_line_id: UUID
    ordered_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1, decimal_places=6)


class PurchaseOrderCreate(ContractModel):
    procurement_request_id: UUID
    supplier_id: UUID
    sourcing_award_id: UUID | None = None
    promised_date: date | None = None
    lines: list[PurchaseOrderLineInput] = Field(min_length=1, max_length=200)


class PurchaseOrderUpdate(ContractModel):
    promised_date: date | None = None
    lines: list[PurchaseOrderLineInput] = Field(min_length=1, max_length=200)
    expected_version: int = Field(ge=1)


class PurchaseOrderTransition(ContractModel):
    expected_version: int = Field(ge=1)


class PurchaseOrderReceiptAllocation(ContractModel):
    order_line_id: UUID
    accepted_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)


class PurchaseOrderInvoiceAllocation(ContractModel):
    order_line_id: UUID
    invoiced_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class PurchaseOrderDeleteResult(ContractModel):
    deleted: Literal[True] = True


class PurchaseOrderLineSnapshot(ContractModel):
    line_id: UUID
    line_no: int = Field(ge=1)
    request_line_id: UUID
    material_id: UUID | None = None
    category_id: UUID
    description: str
    specification: str | None = None
    unit: str
    ordered_quantity: Decimal = Field(gt=0)
    received_quantity: Decimal = Field(ge=0)
    invoiced_quantity: Decimal = Field(ge=0)
    unit_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0, le=1)
    line_amount: Decimal = Field(ge=0)


class PurchaseOrderSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    order_id: UUID
    order_no: str
    org_id: UUID
    procurement_request_id: UUID
    supplier_id: UUID
    sourcing_award_id: UUID | None = None
    status: PurchaseOrderStatus
    currency: str = Field(min_length=3, max_length=3)
    total_amount: Decimal = Field(ge=0)
    required_date: date | None = None
    promised_date: date | None = None
    issued_at: datetime | None = None
    cancelled_at: datetime | None = None
    lines: list[PurchaseOrderLineSnapshot]
    version: int = Field(ge=1)
    updated_at: datetime
