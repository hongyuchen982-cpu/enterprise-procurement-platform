from datetime import datetime
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ContractModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResponseMeta(ContractModel):
    request_id: UUID
    trace_id: UUID
    timestamp: datetime


class ApiResponse(ContractModel, Generic[T]):
    success: Literal[True] = True
    data: T
    meta: ResponseMeta


class ErrorDetail(ContractModel):
    field: str | None = None
    reason: str
    context: dict[str, Any] | None = None


class ErrorObject(ContractModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(ContractModel):
    success: Literal[False] = False
    error: ErrorObject
    meta: ResponseMeta


class PageRequest(ContractModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PageMeta(ContractModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PageResponse(ContractModel, Generic[T]):
    success: Literal[True] = True
    data: list[T]
    pagination: PageMeta
    meta: ResponseMeta


class ActorType(StrEnum):
    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class AuditSource(StrEnum):
    API = "API"
    WORKER = "WORKER"
    TOOL = "TOOL"
    INTEGRATION = "INTEGRATION"


class AuditMetadata(ContractModel):
    request_id: UUID
    trace_id: UUID
    actor_id: UUID | None
    actor_type: ActorType
    org_id: UUID
    source: AuditSource
    ip_address: str | None = None
    user_agent: str | None = None
    agent_task_id: UUID | None = None
    tool_call_id: UUID | None = None


class BusinessObjectRef(ContractModel):
    object_type: str
    object_id: UUID
    version: int | None = Field(default=None, ge=1)
