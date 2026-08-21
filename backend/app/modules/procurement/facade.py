from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.procurement import (
    ProcurementRequestCreate,
    ProcurementRequestSnapshot,
    ProcurementRequestUpdate,
)
from app.modules.identity.facade import IdentityFacade
from app.modules.master_data.facade import MasterDataFacade
from app.modules.procurement.repository import ProcurementRepository
from app.modules.procurement.service import ProcurementRequestService


class ProcurementFacade:
    def __init__(self, session: Session) -> None:
        self.service = ProcurementRequestService(
            ProcurementRepository(session),
            IdentityFacade(session),
            MasterDataFacade(session),
        )

    def create(
        self,
        payload: ProcurementRequestCreate,
        requester_membership_id: UUID,
        requester_id: UUID,
    ) -> ProcurementRequestSnapshot:
        return self.service.create(payload, requester_membership_id, requester_id)

    def get(self, request_id: UUID) -> ProcurementRequestSnapshot:
        return self.service.get(request_id)

    def get_for_update(self, request_id: UUID) -> ProcurementRequestSnapshot:
        return self.service.get_for_update(request_id)

    def list(self, organization_id: UUID) -> tuple[ProcurementRequestSnapshot, ...]:
        return self.service.list_requests(organization_id)

    def update(
        self, request_id: UUID, payload: ProcurementRequestUpdate
    ) -> ProcurementRequestSnapshot:
        return self.service.update(request_id, payload)

    def delete(self, request_id: UUID, expected_version: int) -> None:
        self.service.delete(request_id, expected_version)

    def submit(self, request_id: UUID, expected_version: int) -> ProcurementRequestSnapshot:
        return self.service.submit(request_id, expected_version)

    def withdraw(self, request_id: UUID, expected_version: int) -> ProcurementRequestSnapshot:
        return self.service.withdraw(request_id, expected_version)

    def begin_approval(self, request_id: UUID, expected_version: int) -> ProcurementRequestSnapshot:
        return self.service.begin_approval(request_id, expected_version)

    def complete_approval(
        self, request_id: UUID, expected_version: int, approved: bool
    ) -> ProcurementRequestSnapshot:
        return self.service.complete_approval(request_id, expected_version, approved)

    def cancel_approval(
        self, request_id: UUID, expected_version: int
    ) -> ProcurementRequestSnapshot:
        return self.service.cancel_approval(request_id, expected_version)
