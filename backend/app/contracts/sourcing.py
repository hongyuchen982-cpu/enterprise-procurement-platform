from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class SourcingStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    AWARDED = "AWARDED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class AwardStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class SourcingProjectSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    sourcing_project_id: UUID
    org_id: UUID
    procurement_request_id: UUID
    procurement_request_version: int = Field(ge=1)
    title: str
    category_id: UUID
    candidate_supplier_ids: list[UUID]
    created_by: UUID
    status: SourcingStatus
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class SourcingProjectCreate(ContractModel):
    org_id: UUID
    procurement_request_id: UUID
    procurement_request_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    category_id: UUID
    candidate_supplier_ids: list[UUID] = Field(default_factory=list, max_length=20)
    created_by: UUID


class SourcingProjectStatusUpdate(ContractModel):
    status: SourcingStatus


class AwardSnapshot(ContractModel):
    schema_version: Literal["1"] = "1"
    award_id: UUID
    sourcing_project_id: UUID
    procurement_request_id: UUID
    org_id: UUID
    supplier_id: UUID
    status: AwardStatus
    currency: str = Field(min_length=3, max_length=3)
    total_amount: Decimal = Field(ge=0)
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    version: int = Field(ge=1)
    updated_at: datetime
