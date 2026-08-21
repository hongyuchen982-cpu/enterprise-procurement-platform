from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.rag import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentSnapshot,
    KnowledgeDocumentStatus,
    KnowledgeDocumentStatusUpdate,
    RagSearchRequest,
    RagSearchResponse,
)
from app.modules.rag.service import (
    InvalidKnowledgeDocumentStatusTransitionError,
    create_knowledge_document,
    get_knowledge_document,
    list_knowledge_documents,
    search_knowledge,
    update_knowledge_document_status,
)

router = APIRouter(prefix="/rag", tags=["member-b:rag"])


def _response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("/documents", response_model=ApiResponse[list[KnowledgeDocumentSnapshot]])
async def list_documents(
    request: Request,
    document_status: KnowledgeDocumentStatus | None = None,
) -> ApiResponse[list[KnowledgeDocumentSnapshot]]:
    return ApiResponse(
        data=list_knowledge_documents(status=document_status),
        meta=_response_meta(request),
    )


@router.post(
    "/documents",
    response_model=ApiResponse[KnowledgeDocumentSnapshot],
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    command: KnowledgeDocumentCreate,
    request: Request,
) -> ApiResponse[KnowledgeDocumentSnapshot]:
    return ApiResponse(
        data=create_knowledge_document(command),
        meta=_response_meta(request),
    )


@router.get("/documents/{document_id}", response_model=ApiResponse[KnowledgeDocumentSnapshot])
async def read_document(
    document_id: UUID,
    request: Request,
) -> ApiResponse[KnowledgeDocumentSnapshot]:
    document = get_knowledge_document(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge document not found",
        )
    return ApiResponse(data=document, meta=_response_meta(request))


@router.patch(
    "/documents/{document_id}/status",
    response_model=ApiResponse[KnowledgeDocumentSnapshot],
)
async def update_document_status(
    document_id: UUID,
    command: KnowledgeDocumentStatusUpdate,
    request: Request,
) -> ApiResponse[KnowledgeDocumentSnapshot]:
    try:
        document = update_knowledge_document_status(document_id, command)
    except InvalidKnowledgeDocumentStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge document not found",
        )
    return ApiResponse(data=document, meta=_response_meta(request))


@router.post("/search", response_model=ApiResponse[RagSearchResponse])
async def search(
    command: RagSearchRequest,
    request: Request,
) -> ApiResponse[RagSearchResponse]:
    return ApiResponse(data=search_knowledge(command), meta=_response_meta(request))
