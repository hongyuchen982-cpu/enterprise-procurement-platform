from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.contracts.inventory import (
    InventoryBalanceSnapshot,
    InventoryMovementSnapshot,
    InventoryMovementType,
    InventoryReceiptAllocation,
)
from app.core.database import utc_now
from app.modules.inventory.models import (
    InventoryBalance,
    InventoryMovement,
    InventoryMovementRecordType,
)
from app.modules.inventory.repository import InventoryRepository


class InventoryConflictError(ValueError):
    pass


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    def stage_receipt(self, allocations: list[InventoryReceiptAllocation]) -> None:
        grouped: defaultdict[tuple[UUID, UUID], list[InventoryReceiptAllocation]] = defaultdict(
            list
        )
        for allocation in allocations:
            grouped[(allocation.organization_id, allocation.material_id)].append(allocation)
        try:
            for (organization_id, material_id), values in grouped.items():
                balance = self.repository.balance_for_update(organization_id, material_id)
                if balance is None:
                    first = values[0]
                    balance = InventoryBalance(
                        organization_id=organization_id,
                        material_id=material_id,
                        category_id=first.category_id,
                        unit_code=first.unit,
                        on_hand_quantity=Decimal("0"),
                        total_received_quantity=Decimal("0"),
                    )
                    self.repository.add(balance)
                for value in values:
                    if self.repository.movement_for_source_line("RECEIPT", value.receipt_line_id):
                        raise InventoryConflictError("receipt line already posted to inventory")
                    if balance.category_id != value.category_id or balance.unit_code != value.unit:
                        raise InventoryConflictError(
                            "inventory material category or unit does not match the balance"
                        )
                    balance.on_hand_quantity += value.quantity
                    balance.total_received_quantity += value.quantity
                    self.repository.add(
                        InventoryMovement(
                            organization_id=organization_id,
                            material_id=material_id,
                            category_id=value.category_id,
                            unit_code=value.unit,
                            movement_type=InventoryMovementRecordType.RECEIPT,
                            quantity=value.quantity,
                            balance_after=balance.on_hand_quantity,
                            source_type="RECEIPT",
                            source_id=value.receipt_id,
                            source_line_id=value.receipt_line_id,
                            occurred_at=utc_now(),
                        )
                    )
            self.repository.flush()
        except IntegrityError as exc:
            self.repository.rollback()
            raise InventoryConflictError("inventory receipt was posted concurrently") from exc

    def balances(self, organization_id: UUID) -> tuple[InventoryBalanceSnapshot, ...]:
        return tuple(
            self.balance_snapshot(value) for value in self.repository.balances(organization_id)
        )

    def movements(
        self,
        organization_id: UUID,
        material_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[InventoryMovementSnapshot, ...]:
        return tuple(
            self.movement_snapshot(value)
            for value in self.repository.movements(
                organization_id,
                material_id,
                limit,
                offset,
            )
        )

    @staticmethod
    def balance_snapshot(balance: InventoryBalance) -> InventoryBalanceSnapshot:
        return InventoryBalanceSnapshot(
            balance_id=balance.id,
            organization_id=balance.organization_id,
            material_id=balance.material_id,
            category_id=balance.category_id,
            unit=balance.unit_code,
            on_hand_quantity=balance.on_hand_quantity,
            total_received_quantity=balance.total_received_quantity,
            version=balance.version,
            updated_at=balance.updated_at,
        )

    @staticmethod
    def movement_snapshot(movement: InventoryMovement) -> InventoryMovementSnapshot:
        return InventoryMovementSnapshot(
            movement_id=movement.id,
            organization_id=movement.organization_id,
            material_id=movement.material_id,
            category_id=movement.category_id,
            unit=movement.unit_code,
            movement_type=InventoryMovementType(movement.movement_type),
            quantity=movement.quantity,
            balance_after=movement.balance_after,
            source_type=movement.source_type,
            source_id=movement.source_id,
            source_line_id=movement.source_line_id,
            occurred_at=movement.occurred_at,
        )
