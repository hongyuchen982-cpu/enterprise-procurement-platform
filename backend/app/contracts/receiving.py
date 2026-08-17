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
    status: ReceiptStatus
    received_at: datetime | None = None
    lines: list[ReceiptLineSnapshot]
    version: int = Field(ge=1)
    updated_at: datetime
