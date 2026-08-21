from app.contracts.rag import KnowledgeDocumentSnapshot, KnowledgeDocumentStatus
from app.modules.rag.service import (
    list_knowledge_documents as service_list_knowledge_documents,
)


def list_knowledge_documents(
    status: KnowledgeDocumentStatus | None = None,
) -> list[KnowledgeDocumentSnapshot]:
    return service_list_knowledge_documents(status=status)
