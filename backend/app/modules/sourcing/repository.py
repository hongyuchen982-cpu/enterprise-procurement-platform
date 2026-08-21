from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.sourcing import SourcingProjectSnapshot, SourcingStatus
from app.core.database import session_scope
from app.modules.sourcing.models import SourcingProjectRecord

_ORG_ID = UUID("22222222-2222-4222-8222-222222222222")
_OPERATOR_ID = UUID("44444444-4444-4444-8444-444444444444")


def _project(
    sourcing_project_id: str,
    procurement_request_id: str,
    procurement_request_version: int,
    title: str,
    category_id: str,
    candidate_supplier_ids: list[str],
    status: SourcingStatus,
    created_at: datetime,
    updated_at: datetime,
    *,
    version: int = 1,
) -> SourcingProjectSnapshot:
    return SourcingProjectSnapshot(
        sourcing_project_id=UUID(sourcing_project_id),
        org_id=_ORG_ID,
        procurement_request_id=UUID(procurement_request_id),
        procurement_request_version=procurement_request_version,
        title=title,
        category_id=UUID(category_id),
        candidate_supplier_ids=[
            UUID(supplier_id) for supplier_id in candidate_supplier_ids
        ],
        created_by=_OPERATOR_ID,
        status=status,
        version=version,
        created_at=created_at,
        updated_at=updated_at,
    )


_SEED_PROJECTS = (
    _project(
        "55555555-5555-4555-8555-555555555551",
        "66666666-6666-4666-8666-666666666661",
        2,
        "Precision machining supplier shortlist",
        "33333333-3333-4333-8333-333333333333",
        [
            "11111111-1111-4111-8111-111111111111",
            "11111111-1111-4111-8111-111111111112",
        ],
        SourcingStatus.ACTIVE,
        datetime(2026, 8, 18, 9, 15, tzinfo=UTC),
        datetime(2026, 8, 18, 10, 30, tzinfo=UTC),
        version=2,
    ),
)


def _seed_projects(session: Session) -> None:
    seeded = False
    for project in _SEED_PROJECTS:
        if session.get(SourcingProjectRecord, str(project.sourcing_project_id)) is not None:
            continue
        session.add(_record_from_snapshot(project))
        seeded = True
    if seeded:
        session.flush()


def _snapshot_from_record(record: SourcingProjectRecord) -> SourcingProjectSnapshot:
    return SourcingProjectSnapshot(
        sourcing_project_id=UUID(str(record.sourcing_project_id)),
        org_id=UUID(str(record.org_id)),
        procurement_request_id=UUID(str(record.procurement_request_id)),
        procurement_request_version=record.procurement_request_version,
        title=record.title,
        category_id=UUID(str(record.category_id)),
        candidate_supplier_ids=[
            UUID(str(supplier_id)) for supplier_id in record.candidate_supplier_ids
        ],
        created_by=UUID(str(record.created_by)),
        status=SourcingStatus(record.status),
        version=record.version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _record_from_snapshot(project: SourcingProjectSnapshot) -> SourcingProjectRecord:
    return SourcingProjectRecord(
        sourcing_project_id=str(project.sourcing_project_id),
        org_id=str(project.org_id),
        procurement_request_id=str(project.procurement_request_id),
        procurement_request_version=project.procurement_request_version,
        title=project.title,
        category_id=str(project.category_id),
        candidate_supplier_ids=[
            str(supplier_id) for supplier_id in project.candidate_supplier_ids
        ],
        created_by=str(project.created_by),
        status=project.status,
        version=project.version,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def list_projects(status: SourcingStatus | None = None) -> list[SourcingProjectSnapshot]:
    with session_scope() as session:
        _seed_projects(session)
        statement = select(SourcingProjectRecord)
        if status is not None:
            statement = statement.where(SourcingProjectRecord.status == status)
        records = session.scalars(
            statement.order_by(SourcingProjectRecord.updated_at.desc())
        ).all()
        return [_snapshot_from_record(record) for record in records]


def get_project(project_id: UUID) -> SourcingProjectSnapshot | None:
    with session_scope() as session:
        _seed_projects(session)
        record = session.get(SourcingProjectRecord, str(project_id))
        if record is None:
            return None
        return _snapshot_from_record(record)


def upsert_project(project: SourcingProjectSnapshot) -> SourcingProjectSnapshot:
    with session_scope() as session:
        _seed_projects(session)
        record = session.get(SourcingProjectRecord, str(project.sourcing_project_id))
        if record is None:
            session.add(_record_from_snapshot(project))
            return project
        record.status = project.status
        record.version = project.version
        record.updated_at = project.updated_at
        record.title = project.title
        record.category_id = str(project.category_id)
        record.candidate_supplier_ids = [
            str(supplier_id) for supplier_id in project.candidate_supplier_ids
        ]
        return project
