from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.receiving.models import Receipt, ReceiptLine


class ReceiptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def receipt(self, receipt_id: UUID) -> Receipt | None:
        return self.session.scalar(
            select(Receipt)
            .options(selectinload(Receipt.lines))
            .where(Receipt.id == receipt_id, Receipt.deleted_at.is_(None))
        )

    def receipts(self, organization_id: UUID) -> tuple[Receipt, ...]:
        return tuple(
            self.session.scalars(
                select(Receipt)
                .options(selectinload(Receipt.lines))
                .where(
                    Receipt.organization_id == organization_id,
                    Receipt.deleted_at.is_(None),
                )
                .order_by(Receipt.created_at.desc())
            )
        )

    def add(self, receipt: Receipt) -> None:
        self.session.add(receipt)

    def replace_lines(self, receipt: Receipt, lines: list[ReceiptLine]) -> None:
        receipt.lines.clear()
        self.session.flush()
        receipt.lines.extend(lines)

    def delete(self, receipt: Receipt) -> None:
        receipt.soft_delete()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
