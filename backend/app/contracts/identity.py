from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from app.contracts.common import ContractModel


class DataScopeType(StrEnum):
    ALL = "ALL"
    ORGANIZATION = "ORGANIZATION"
    ORGANIZATION_TREE = "ORGANIZATION_TREE"
    DEPARTMENT = "DEPARTMENT"
    SELF = "SELF"
    CATEGORY = "CATEGORY"
    SUPPLIER = "SUPPLIER"


class DataScopeGrantSnapshot(ContractModel):
    scope_type: DataScopeType
    scope_ref: UUID | None = None


class EffectiveAccessSnapshot(ContractModel):
    membership_id: UUID
    user_id: UUID
    organization_id: UUID
    department_id: UUID | None = None
    permission_codes: frozenset[str]
    data_scopes: tuple[DataScopeGrantSnapshot, ...]


class AccessTarget(ContractModel):
    organization_id: UUID | None = None
    department_id: UUID | None = None
    owner_user_id: UUID | None = None
    category_id: UUID | None = None
    supplier_id: UUID | None = None


class AccessEvaluationRequest(ContractModel):
    membership_id: UUID
    permission_code: str = Field(min_length=1, max_length=160)
    target: AccessTarget

    @model_validator(mode="after")
    def target_must_identify_data(self) -> "AccessEvaluationRequest":
        if not any(self.target.model_dump().values()):
            raise ValueError("target must contain at least one data dimension")
        return self


class AccessEvaluationResult(ContractModel):
    allowed: bool
    reason: str
