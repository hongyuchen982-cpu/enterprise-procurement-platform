from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr

from app.contracts.common import ContractModel


class LoginRequest(ContractModel):
    login_name: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(max_length=128)


class ChangePasswordRequest(ContractModel):
    current_password: SecretStr = Field(max_length=128)
    new_password: SecretStr = Field(min_length=12, max_length=128)


class MembershipContext(ContractModel):
    membership_id: UUID
    organization_id: UUID
    department_id: UUID | None = None


class CurrentUser(ContractModel):
    user_id: UUID
    login_name: str
    display_name: str
    memberships: tuple[MembershipContext, ...]


class LoginResult(ContractModel):
    access_token: str = Field(repr=False)
    token_type: Literal["Bearer"] = "Bearer"
    expires_at: datetime
    user: CurrentUser


class LogoutResult(ContractModel):
    revoked: Literal[True] = True
