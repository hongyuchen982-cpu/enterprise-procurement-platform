from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class KnowledgeDocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    INDEXING = "INDEXING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class KnowledgeDocumentSnapshot(ContractModel):
    document_id: UUID
    org_id: UUID
    title: str
    owner_module: str
    source_type: str
    content_digest: str
    status: KnowledgeDocumentStatus
    chunk_count: int = Field(ge=0)
    tags: list[str]
    created_by: UUID
    indexed_at: datetime | None = None
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentCreate(ContractModel):
    org_id: UUID
    title: str = Field(min_length=1, max_length=200)
    owner_module: str = Field(min_length=1, max_length=80)
    source_type: str = Field(default="TEXT", min_length=1, max_length=40)
    content: str = Field(min_length=1, max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    created_by: UUID


class KnowledgeDocumentStatusUpdate(ContractModel):
    status: KnowledgeDocumentStatus


class RagSearchRequest(ContractModel):
    org_id: UUID
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSearchMatch(ContractModel):
    document_id: UUID
    title: str
    owner_module: str
    score: float = Field(ge=0, le=1)
    snippet: str
    status: KnowledgeDocumentStatus
    updated_at: datetime


class RagSearchResponse(ContractModel):
    query: str
    matches: list[RagSearchMatch]
