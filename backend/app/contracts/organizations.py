from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class OrganizationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class OrganizationCreate(ContractModel):
    parent_id: UUID
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)


class OrganizationSnapshot(ContractModel):
    organization_id: UUID
    parent_id: UUID | None = None
    code: str
    name: str
    status: OrganizationStatus
    version: int = Field(ge=1)


class OrganizationTreeNode(OrganizationSnapshot):
    children: tuple["OrganizationTreeNode", ...] = ()


class MembershipCreate(ContractModel):
    user_id: UUID
    organization_id: UUID
    department_id: UUID | None = None


class MembershipSnapshot(ContractModel):
    membership_id: UUID
    user_id: UUID
    organization_id: UUID
    department_id: UUID | None = None
    status: OrganizationStatus
    version: int = Field(ge=1)
