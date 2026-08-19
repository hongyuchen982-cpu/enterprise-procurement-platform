from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.master_data import (
    CategoryCreate,
    CategorySnapshot,
    MaterialCreate,
    MaterialSnapshot,
    UnitCreate,
    UnitSnapshot,
)
from app.contracts.organizations import OrganizationStatus
from app.modules.identity.facade import IdentityFacade
from app.modules.master_data.repository import MasterDataRepository
from app.modules.master_data.service import MasterDataNotFoundError, MasterDataService


class MasterDataFacade:
    """Stable entry point for procurement master-data consumers."""

    def __init__(self, session: Session) -> None:
        self.identity = IdentityFacade(session)
        self.service = MasterDataService(MasterDataRepository(session))

    def create_category(self, payload: CategoryCreate) -> CategorySnapshot:
        self._require_active_organization(payload.organization_id)
        return self.service.create_category(payload)

    def list_categories(self, organization_id: UUID) -> tuple[CategorySnapshot, ...]:
        return self.service.list_categories(organization_id)

    def create_unit(self, payload: UnitCreate) -> UnitSnapshot:
        return self.service.create_unit(payload)

    def list_units(self) -> tuple[UnitSnapshot, ...]:
        return self.service.list_units()

    def create_material(self, payload: MaterialCreate) -> MaterialSnapshot:
        self._require_active_organization(payload.organization_id)
        return self.service.create_material(payload)

    def list_materials(self, organization_id: UUID) -> tuple[MaterialSnapshot, ...]:
        return self.service.list_materials(organization_id)

    def _require_active_organization(self, organization_id: UUID) -> None:
        try:
            organization = self.identity.organization(organization_id)
        except LookupError as exc:
            raise MasterDataNotFoundError(str(organization_id)) from exc
        if organization.status is not OrganizationStatus.ACTIVE:
            raise MasterDataNotFoundError(str(organization_id))
