from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class MasterDataStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class CategoryCreate(ContractModel):
    organization_id: UUID
    parent_id: UUID | None = None
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)


class CategorySnapshot(ContractModel):
    category_id: UUID
    organization_id: UUID
    parent_id: UUID | None = None
    code: str
    name: str
    status: MasterDataStatus
    version: int = Field(ge=1)


class UnitCreate(ContractModel):
    code: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=100)
    decimal_places: int = Field(default=2, ge=0, le=6)


class UnitSnapshot(ContractModel):
    code: str
    name: str
    decimal_places: int = Field(ge=0, le=6)
    status: MasterDataStatus
    version: int = Field(ge=1)


class MaterialCreate(ContractModel):
    organization_id: UUID
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    category_id: UUID
    unit_code: str = Field(min_length=1, max_length=20)
    specification: str | None = Field(default=None, max_length=500)


class MaterialSnapshot(ContractModel):
    material_id: UUID
    organization_id: UUID
    code: str
    name: str
    category_id: UUID
    unit_code: str
    specification: str | None = None
    status: MasterDataStatus
    version: int = Field(ge=1)
