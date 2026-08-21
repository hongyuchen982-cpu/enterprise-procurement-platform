from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.contracts.common import ContractModel


class ProcurementRequestStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_APPROVAL = "IN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ProcurementRequestLineInput(ContractModel):
    material_id: UUID | None = None
    category_id: UUID
    description: str = Field(min_length=1, max_length=500)
    specification: str | None = Field(default=None, max_length=1000)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit: str = Field(min_length=1, max_length=20)
    estimated_unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=2
    )

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("unit cannot be blank")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("description cannot be blank")
        return normalized


class ProcurementRequestCreate(ContractModel):
    org_id: UUID
    department_id: UUID
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    required_date: date
    purpose: str = Field(min_length=1, max_length=1000)
    lines: list[ProcurementRequestLineInput] = Field(min_length=1, max_length=200)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("purpose")
    @classmethod
    def normalize_purpose(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("purpose cannot be blank")
        return normalized


class ProcurementRequestUpdate(ContractModel):
    expected_version: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    required_date: date
    purpose: str = Field(min_length=1, max_length=1000)
    lines: list[ProcurementRequestLineInput] = Field(min_length=1, max_length=200)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("purpose")
    @classmethod
    def normalize_purpose(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("purpose cannot be blank")
        return normalized


class ProcurementRequestTransition(ContractModel):
    expected_version: int = Field(ge=1)


class ProcurementRequestDeleteResult(ContractModel):
    deleted: Literal[True] = True


class ProcurementRequestLineSnapshot(ContractModel):
    line_id: UUID
    line_no: int = Field(default=1, ge=1)
    material_id: UUID | None = None
    category_id: UUID
    description: str
    specification: str | None = None
    quantity: Decimal = Field(gt=0)
    unit: str
    estimated_unit_price: Decimal | None = Field(default=None, ge=0)
    estimated_amount: Decimal = Field(default=Decimal("0.00"), ge=0)


class ProcurementRequestSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    request_no: str
    org_id: UUID
    department_id: UUID
    requester_id: UUID
    status: ProcurementRequestStatus
    currency: str = Field(min_length=3, max_length=3)
    purpose: str = ""
    estimated_total: Decimal = Field(ge=0)
    required_date: date
    lines: list[ProcurementRequestLineSnapshot]
    version: int = Field(ge=1)
    submitted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime
