from uuid import UUID

from app.contracts.sourcing import SourcingProjectSnapshot, SourcingStatus
from app.modules.sourcing.service import (
    get_sourcing_project as service_get_sourcing_project,
)
from app.modules.sourcing.service import (
    list_sourcing_projects as service_list_sourcing_projects,
)


def list_sourcing_projects(
    status: SourcingStatus | None = None,
) -> list[SourcingProjectSnapshot]:
    return service_list_sourcing_projects(status=status)


def get_sourcing_project(project_id: UUID) -> SourcingProjectSnapshot | None:
    return service_get_sourcing_project(project_id)
