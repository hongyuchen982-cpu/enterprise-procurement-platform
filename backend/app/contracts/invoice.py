from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.contracts.common import ContractModel


class InvoiceStatus(StrEnum):
    DRAFT = "DRAFT"
    MATCHED = "MATCHED"
    EXCEPTION = "EXCEPTION"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class InvoiceLineInput(ContractModel):
    order_line_id: UUID
    invoiced_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1, decimal_places=6)


class InvoiceCreate(ContractModel):
    order_id: UUID
    supplier_id: UUID
    invoice_no: str = Field(min_length=1, max_length=80)
    invoice_date: date
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    lines: list[InvoiceLineInput] = Field(min_length=1, max_length=200)

    @field_validator("invoice_no")
    @classmethod
    def normalize_invoice_no(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("invoice number cannot be blank")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class InvoiceUpdate(ContractModel):
    invoice_date: date
    lines: list[InvoiceLineInput] = Field(min_length=1, max_length=200)
    expected_version: int = Field(ge=1)


class InvoiceTransition(ContractModel):
    expected_version: int = Field(ge=1)


class InvoiceApproval(ContractModel):
    expected_version: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class InvoiceDeleteResult(ContractModel):
    deleted: Literal[True] = True


class InvoiceLineSnapshot(ContractModel):
    line_id: UUID
    line_no: int = Field(ge=1)
    order_line_id: UUID
    invoiced_quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0, le=1)
    line_amount: Decimal = Field(ge=0)
    quantity_matched: bool | None = None
    price_matched: bool | None = None


class InvoiceSnapshot(ContractModel):
    invoice_id: UUID
    invoice_no: str
    org_id: UUID
    order_id: UUID
    supplier_id: UUID
    invoice_date: date
    currency: str
    status: InvoiceStatus
    total_amount: Decimal = Field(ge=0)
    lines: list[InvoiceLineSnapshot]
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by_membership_id: UUID | None = None
    approval_comment: str | None = None
    version: int = Field(ge=1)
    updated_at: datetime
