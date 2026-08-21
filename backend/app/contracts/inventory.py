from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.contracts.common import ContractModel


class InventoryMovementType(StrEnum):
    RECEIPT = "RECEIPT"


class InventoryReceiptAllocation(ContractModel):
    receipt_id: UUID
    receipt_line_id: UUID
    organization_id: UUID
    material_id: UUID
    category_id: UUID
    unit: str
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class InventoryBalanceSnapshot(ContractModel):
    balance_id: UUID
    organization_id: UUID
    material_id: UUID
    category_id: UUID
    unit: str
    on_hand_quantity: Decimal = Field(ge=0)
    total_received_quantity: Decimal = Field(ge=0)
    version: int = Field(ge=1)
    updated_at: datetime


class InventoryMovementSnapshot(ContractModel):
    movement_id: UUID
    organization_id: UUID
    material_id: UUID
    category_id: UUID
    unit: str
    movement_type: InventoryMovementType
    quantity: Decimal = Field(gt=0)
    balance_after: Decimal = Field(ge=0)
    source_type: str
    source_id: UUID
    source_line_id: UUID
    occurred_at: datetime
