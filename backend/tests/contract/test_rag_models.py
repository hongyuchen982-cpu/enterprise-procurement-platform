from app.persistence.rag_models import KnowledgeDocumentRecord


def test_rag_orm_table_has_expected_name_and_columns() -> None:
    columns = set(KnowledgeDocumentRecord.__table__.columns.keys())

    assert KnowledgeDocumentRecord.__tablename__ == "b_knowledge_documents"
    assert {
        "document_id",
        "org_id",
        "title",
        "owner_module",
        "source_type",
        "content_digest",
        "content",
        "status",
        "chunk_count",
        "tags",
        "created_by",
        "indexed_at",
        "version",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_rag_orm_table_keeps_query_indexes() -> None:
    indexes = {index.name for index in KnowledgeDocumentRecord.__table__.indexes}

    assert "ix_b_knowledge_documents_org_status" in indexes
    assert "ix_b_knowledge_documents_owner_status" in indexes
    assert "ix_b_knowledge_documents_updated" in indexes
