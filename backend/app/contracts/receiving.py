from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class InspectionStatus(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class ReceiptStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReceiptLineInput(ContractModel):
    order_line_id: UUID
    accepted_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    rejected_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    inspection_status: InspectionStatus


class ReceiptCreate(ContractModel):
    order_id: UUID
    lines: list[ReceiptLineInput] = Field(min_length=1, max_length=200)


class ReceiptUpdate(ContractModel):
    lines: list[ReceiptLineInput] = Field(min_length=1, max_length=200)
    expected_version: int = Field(ge=1)


class ReceiptTransition(ContractModel):
    expected_version: int = Field(ge=1)


class ReceiptDeleteResult(ContractModel):
    deleted: Literal[True] = True


class ReceiptLineSnapshot(ContractModel):
    line_id: UUID
    order_line_id: UUID
    received_quantity: Decimal = Field(ge=0)
    accepted_quantity: Decimal = Field(ge=0)
    rejected_quantity: Decimal = Field(ge=0)
    inspection_status: InspectionStatus


class ReceiptSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    receipt_id: UUID
    receipt_no: str
    org_id: UUID
    order_id: UUID
    receiver_membership_id: UUID
    receiver_id: UUID
    status: ReceiptStatus
    received_at: datetime | None = None
    lines: list[ReceiptLineSnapshot]
    version: int = Field(ge=1)
    updated_at: datetime
