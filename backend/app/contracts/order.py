from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class PurchaseOrderLineSnapshot(ContractModel):
    line_id: UUID
    material_id: UUID | None = None
    description: str
    ordered_quantity: Decimal = Field(gt=0)
    received_quantity: Decimal = Field(ge=0)
    invoiced_quantity: Decimal = Field(ge=0)
    unit_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0)


class PurchaseOrderSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    order_id: UUID
    order_no: str
    org_id: UUID
    supplier_id: UUID
    sourcing_award_id: UUID | None = None
    status: str
    currency: str = Field(min_length=3, max_length=3)
    total_amount: Decimal = Field(ge=0)
    required_date: date | None = None
    promised_date: date | None = None
    lines: list[PurchaseOrderLineSnapshot]
    version: int = Field(ge=1)
    updated_at: datetime
