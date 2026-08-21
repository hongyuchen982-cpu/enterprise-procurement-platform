from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.inventory import (
    InventoryBalanceSnapshot,
    InventoryMovementSnapshot,
    InventoryReceiptAllocation,
)
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.service import InventoryService


class InventoryFacade:
    def __init__(self, session: Session) -> None:
        self.service = InventoryService(InventoryRepository(session))

    def stage_receipt(self, allocations: list[InventoryReceiptAllocation]) -> None:
        self.service.stage_receipt(allocations)

    def balances(self, organization_id: UUID) -> tuple[InventoryBalanceSnapshot, ...]:
        return self.service.balances(organization_id)

    def movements(
        self,
        organization_id: UUID,
        material_id: UUID | None = None,
    ) -> tuple[InventoryMovementSnapshot, ...]:
        return self.service.movements(organization_id, material_id)
