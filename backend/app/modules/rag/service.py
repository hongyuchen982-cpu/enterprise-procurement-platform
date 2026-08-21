from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from app.contracts.rag import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentSnapshot,
    KnowledgeDocumentStatus,
    KnowledgeDocumentStatusUpdate,
    RagSearchMatch,
    RagSearchRequest,
    RagSearchResponse,
)
from app.persistence import rag_repository

_ORG_ID = UUID("22222222-2222-4222-8222-222222222222")
_OPERATOR_ID = UUID("44444444-4444-4444-8444-444444444444")
_SEED_DOCUMENTS: list[tuple[KnowledgeDocumentSnapshot, str]] = []

_ALLOWED_STATUS_TRANSITIONS: dict[
    KnowledgeDocumentStatus, set[KnowledgeDocumentStatus]
] = {
    KnowledgeDocumentStatus.UPLOADED: {
        KnowledgeDocumentStatus.INDEXING,
        KnowledgeDocumentStatus.ARCHIVED,
    },
    KnowledgeDocumentStatus.INDEXING: {
        KnowledgeDocumentStatus.INDEXED,
        KnowledgeDocumentStatus.FAILED,
    },
    KnowledgeDocumentStatus.INDEXED: {
        KnowledgeDocumentStatus.INDEXING,
        KnowledgeDocumentStatus.ARCHIVED,
    },
    KnowledgeDocumentStatus.FAILED: {
        KnowledgeDocumentStatus.INDEXING,
        KnowledgeDocumentStatus.ARCHIVED,
    },
    KnowledgeDocumentStatus.ARCHIVED: set(),
}


class InvalidKnowledgeDocumentStatusTransitionError(ValueError):
    def __init__(
        self,
        from_status: KnowledgeDocumentStatus,
        to_status: KnowledgeDocumentStatus,
    ) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Cannot change knowledge document status from {from_status} to {to_status}."
        )


def _chunk_count(content: str) -> int:
    return max(1, (len(content) + 499) // 500)


def _digest(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _snippet(content: str, query: str) -> str:
    normalized_content = content.lower()
    normalized_query = query.lower()
    index = normalized_content.find(normalized_query)
    if index < 0:
        return content[:180]
    start = max(0, index - 60)
    end = min(len(content), index + len(query) + 120)
    return content[start:end]


def _score(content: str, query: str) -> float:
    terms = {term for term in query.lower().split() if term}
    if not terms:
        return 0
    normalized_content = content.lower()
    matched = sum(1 for term in terms if term in normalized_content)
    return round(matched / len(terms), 2)


def _seed_document(
    document_id: str,
    title: str,
    owner_module: str,
    content: str,
    tags: list[str],
    updated_at: datetime,
) -> None:
    document_uuid = UUID(document_id)
    snapshot = KnowledgeDocumentSnapshot(
        document_id=document_uuid,
        org_id=_ORG_ID,
        title=title,
        owner_module=owner_module,
        source_type="TEXT",
        content_digest=_digest(content),
        status=KnowledgeDocumentStatus.INDEXED,
        chunk_count=_chunk_count(content),
        tags=tags,
        created_by=_OPERATOR_ID,
        indexed_at=updated_at,
        version=1,
        created_at=updated_at,
        updated_at=updated_at,
    )
    _SEED_DOCUMENTS.append((snapshot, content))


_seed_document(
    "77777777-7777-4777-8777-777777777771",
    "供应商风险复核规则",
    "risk",
    (
        "高风险供应商需要人工复核。若供应商资质过期、状态冻结或风险等级为 HIGH，"
        "Agent 必须进入人工确认。"
    ),
    ["supplier", "risk", "confirmation"],
    datetime(2026, 8, 18, 11, 20, tzinfo=UTC),
)
_seed_document(
    "77777777-7777-4777-8777-777777777772",
    "寻源项目推进规则",
    "sourcing",
    "寻源项目从 DRAFT 进入 ACTIVE 后才能进入 AWARDED。取消和关闭项目需要保留业务审计记录。",
    ["sourcing", "workflow"],
    datetime(2026, 8, 18, 11, 35, tzinfo=UTC),
)


def list_knowledge_documents(
    status: KnowledgeDocumentStatus | None = None,
) -> list[KnowledgeDocumentSnapshot]:
    return rag_repository.list_documents(_SEED_DOCUMENTS, status=status)


def get_knowledge_document(
    document_id: UUID,
) -> KnowledgeDocumentSnapshot | None:
    return rag_repository.get_document(document_id, _SEED_DOCUMENTS)


def create_knowledge_document(
    command: KnowledgeDocumentCreate,
) -> KnowledgeDocumentSnapshot:
    now = datetime.now(UTC)
    document_id = uuid4()
    snapshot = KnowledgeDocumentSnapshot(
        document_id=document_id,
        org_id=command.org_id,
        title=command.title,
        owner_module=command.owner_module,
        source_type=command.source_type,
        content_digest=_digest(command.content),
        status=KnowledgeDocumentStatus.UPLOADED,
        chunk_count=_chunk_count(command.content),
        tags=command.tags,
        created_by=command.created_by,
        version=1,
        created_at=now,
        updated_at=now,
    )
    return rag_repository.create_document(snapshot, command.content, _SEED_DOCUMENTS)


def update_knowledge_document_status(
    document_id: UUID,
    command: KnowledgeDocumentStatusUpdate,
) -> KnowledgeDocumentSnapshot | None:
    document = rag_repository.get_document(document_id, _SEED_DOCUMENTS)
    if document is None:
        return None
    if command.status == document.status:
        return document
    if command.status not in _ALLOWED_STATUS_TRANSITIONS[document.status]:
        raise InvalidKnowledgeDocumentStatusTransitionError(
            document.status,
            command.status,
        )

    now = datetime.now(UTC)
    updated_document = document.model_copy(
        update={
            "status": command.status,
            "indexed_at": (
                now
                if command.status == KnowledgeDocumentStatus.INDEXED
                else document.indexed_at
            ),
            "version": document.version + 1,
            "updated_at": now,
        }
    )
    return rag_repository.update_document(updated_document, _SEED_DOCUMENTS)


def search_knowledge(request: RagSearchRequest) -> RagSearchResponse:
    matches: list[RagSearchMatch] = []
    for document, content in rag_repository.list_indexed_documents_with_content(
        request.org_id,
        _SEED_DOCUMENTS,
    ):
        score = _score(content, request.query)
        if score <= 0:
            continue
        matches.append(
            RagSearchMatch(
                document_id=document.document_id,
                title=document.title,
                owner_module=document.owner_module,
                score=score,
                snippet=_snippet(content, request.query),
                status=document.status,
                updated_at=document.updated_at,
            )
        )

    matches.sort(key=lambda match: (match.score, match.updated_at), reverse=True)
    return RagSearchResponse(query=request.query, matches=matches[: request.top_k])
