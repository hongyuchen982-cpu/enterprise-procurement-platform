from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.contracts.sourcing import (
    SourcingProjectCreate,
    SourcingProjectSnapshot,
    SourcingProjectStatusUpdate,
    SourcingStatus,
)
from app.modules.sourcing import repository
from app.modules.suppliers.facade import get_supplier_snapshot

_ALLOWED_STATUS_TRANSITIONS: dict[SourcingStatus, set[SourcingStatus]] = {
    SourcingStatus.DRAFT: {SourcingStatus.ACTIVE, SourcingStatus.CANCELLED},
    SourcingStatus.ACTIVE: {
        SourcingStatus.AWARDED,
        SourcingStatus.CLOSED,
        SourcingStatus.CANCELLED,
    },
    SourcingStatus.AWARDED: {SourcingStatus.CLOSED},
    SourcingStatus.CLOSED: set(),
    SourcingStatus.CANCELLED: set(),
}


class UnknownCandidateSupplierError(ValueError):
    def __init__(self, supplier_id: UUID) -> None:
        self.supplier_id = supplier_id
        super().__init__(f"Candidate supplier {supplier_id} does not exist.")


class InvalidSourcingStatusTransitionError(ValueError):
    def __init__(self, from_status: SourcingStatus, to_status: SourcingStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Cannot change sourcing project status from {from_status} to {to_status}."
        )


def list_sourcing_projects(
    status: SourcingStatus | None = None,
) -> list[SourcingProjectSnapshot]:
    return repository.list_projects(status=status)


def get_sourcing_project(project_id: UUID) -> SourcingProjectSnapshot | None:
    return repository.get_project(project_id)


def create_sourcing_project(command: SourcingProjectCreate) -> SourcingProjectSnapshot:
    for supplier_id in command.candidate_supplier_ids:
        if get_supplier_snapshot(supplier_id) is None:
            raise UnknownCandidateSupplierError(supplier_id)

    now = datetime.now(UTC)
    project = SourcingProjectSnapshot(
        sourcing_project_id=uuid4(),
        org_id=command.org_id,
        procurement_request_id=command.procurement_request_id,
        procurement_request_version=command.procurement_request_version,
        title=command.title,
        category_id=command.category_id,
        candidate_supplier_ids=command.candidate_supplier_ids,
        created_by=command.created_by,
        status=SourcingStatus.DRAFT,
        version=1,
        created_at=now,
        updated_at=now,
    )
    return repository.upsert_project(project)


def update_sourcing_project_status(
    project_id: UUID, command: SourcingProjectStatusUpdate
) -> SourcingProjectSnapshot | None:
    project = repository.get_project(project_id)
    if project is None:
        return None
    if command.status == project.status:
        return project
    if command.status not in _ALLOWED_STATUS_TRANSITIONS[project.status]:
        raise InvalidSourcingStatusTransitionError(project.status, command.status)

    updated_project = project.model_copy(
        update={
            "status": command.status,
            "version": project.version + 1,
            "updated_at": datetime.now(UTC),
        }
    )
    return repository.upsert_project(updated_project)
