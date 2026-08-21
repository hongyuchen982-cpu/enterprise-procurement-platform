from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.rag import KnowledgeDocumentSnapshot, KnowledgeDocumentStatus
from app.core.database import session_scope
from app.persistence.rag_models import KnowledgeDocumentRecord


def _snapshot_from_record(record: KnowledgeDocumentRecord) -> KnowledgeDocumentSnapshot:
    return KnowledgeDocumentSnapshot(
        document_id=UUID(str(record.document_id)),
        org_id=UUID(str(record.org_id)),
        title=record.title,
        owner_module=record.owner_module,
        source_type=record.source_type,
        content_digest=record.content_digest,
        status=KnowledgeDocumentStatus(record.status),
        chunk_count=record.chunk_count,
        tags=record.tags,
        created_by=UUID(str(record.created_by)),
        indexed_at=record.indexed_at,
        version=record.version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _record_from_snapshot(
    snapshot: KnowledgeDocumentSnapshot,
    content: str,
) -> KnowledgeDocumentRecord:
    return KnowledgeDocumentRecord(
        document_id=str(snapshot.document_id),
        org_id=str(snapshot.org_id),
        title=snapshot.title,
        owner_module=snapshot.owner_module,
        source_type=snapshot.source_type,
        content_digest=snapshot.content_digest,
        content=content,
        status=snapshot.status,
        chunk_count=snapshot.chunk_count,
        tags=snapshot.tags,
        created_by=str(snapshot.created_by),
        indexed_at=snapshot.indexed_at,
        version=snapshot.version,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
    )


def seed_documents_if_missing(
    seeds: list[tuple[KnowledgeDocumentSnapshot, str]],
    session: Session,
) -> None:
    seeded = False
    for snapshot, content in seeds:
        if session.get(KnowledgeDocumentRecord, str(snapshot.document_id)) is not None:
            continue
        session.add(_record_from_snapshot(snapshot, content))
        seeded = True
    if seeded:
        session.flush()


def list_documents(
    seeds: list[tuple[KnowledgeDocumentSnapshot, str]],
    status: KnowledgeDocumentStatus | None = None,
) -> list[KnowledgeDocumentSnapshot]:
    with session_scope() as session:
        seed_documents_if_missing(seeds, session)
        statement = select(KnowledgeDocumentRecord)
        if status is not None:
            statement = statement.where(KnowledgeDocumentRecord.status == status)
        records = session.scalars(
            statement.order_by(KnowledgeDocumentRecord.updated_at.desc())
        ).all()
        return [_snapshot_from_record(record) for record in records]


def get_document(
    document_id: UUID,
    seeds: list[tuple[KnowledgeDocumentSnapshot, str]],
) -> KnowledgeDocumentSnapshot | None:
    with session_scope() as session:
        seed_documents_if_missing(seeds, session)
        record = session.get(KnowledgeDocumentRecord, str(document_id))
        if record is None:
            return None
        return _snapshot_from_record(record)


def create_document(
    snapshot: KnowledgeDocumentSnapshot,
    content: str,
    seeds: list[tuple[KnowledgeDocumentSnapshot, str]],
) -> KnowledgeDocumentSnapshot:
    with session_scope() as session:
        seed_documents_if_missing(seeds, session)
        session.add(_record_from_snapshot(snapshot, content))
        return snapshot


def update_document(
    snapshot: KnowledgeDocumentSnapshot,
    seeds: list[tuple[KnowledgeDocumentSnapshot, str]],
) -> KnowledgeDocumentSnapshot | None:
    with session_scope() as session:
        seed_documents_if_missing(seeds, session)
        record = session.get(KnowledgeDocumentRecord, str(snapshot.document_id))
        if record is None:
            return None
        record.status = snapshot.status
        record.indexed_at = snapshot.indexed_at
        record.version = snapshot.version
        record.updated_at = snapshot.updated_at
        return snapshot


def list_indexed_documents_with_content(
    org_id: UUID,
    seeds: list[tuple[KnowledgeDocumentSnapshot, str]],
) -> list[tuple[KnowledgeDocumentSnapshot, str]]:
    with session_scope() as session:
        seed_documents_if_missing(seeds, session)
        records = session.scalars(
            select(KnowledgeDocumentRecord)
            .where(KnowledgeDocumentRecord.org_id == str(org_id))
            .where(KnowledgeDocumentRecord.status == KnowledgeDocumentStatus.INDEXED)
            .order_by(KnowledgeDocumentRecord.updated_at.desc())
        ).all()
        return [(_snapshot_from_record(record), record.content) for record in records]
