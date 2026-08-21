from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inventory.models import InventoryBalance, InventoryMovement


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def balance_for_update(
        self, organization_id: UUID, material_id: UUID
    ) -> InventoryBalance | None:
        return self.session.scalar(
            select(InventoryBalance)
            .where(
                InventoryBalance.organization_id == organization_id,
                InventoryBalance.material_id == material_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def movement_for_source_line(
        self, source_type: str, source_line_id: UUID
    ) -> InventoryMovement | None:
        return self.session.scalar(
            select(InventoryMovement).where(
                InventoryMovement.source_type == source_type,
                InventoryMovement.source_line_id == source_line_id,
            )
        )

    def balances(self, organization_id: UUID) -> tuple[InventoryBalance, ...]:
        return tuple(
            self.session.scalars(
                select(InventoryBalance)
                .where(InventoryBalance.organization_id == organization_id)
                .order_by(InventoryBalance.material_id)
            )
        )

    def movements(
        self,
        organization_id: UUID,
        material_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[InventoryMovement, ...]:
        statement = select(InventoryMovement).where(
            InventoryMovement.organization_id == organization_id
        )
        if material_id is not None:
            statement = statement.where(InventoryMovement.material_id == material_id)
        return tuple(
            self.session.scalars(
                statement.order_by(
                    InventoryMovement.occurred_at.desc(),
                    InventoryMovement.id.desc(),
                )
                .limit(limit)
                .offset(offset)
            )
        )

    def add(self, value: InventoryBalance | InventoryMovement) -> None:
        self.session.add(value)

    def flush(self) -> None:
        self.session.flush()

    def rollback(self) -> None:
        self.session.rollback()
