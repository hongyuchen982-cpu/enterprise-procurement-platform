from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class ProcurementRequestLineSnapshot(ContractModel):
    line_id: UUID
    material_id: UUID | None = None
    category_id: UUID
    description: str
    specification: str | None = None
    quantity: Decimal = Field(gt=0)
    unit: str
    estimated_unit_price: Decimal | None = Field(default=None, ge=0)


class ProcurementRequestSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    request_no: str
    org_id: UUID
    department_id: UUID
    requester_id: UUID
    status: str
    currency: str = Field(min_length=3, max_length=3)
    estimated_total: Decimal = Field(ge=0)
    required_date: date
    lines: list[ProcurementRequestLineSnapshot]
    version: int = Field(ge=1)
    updated_at: datetime
