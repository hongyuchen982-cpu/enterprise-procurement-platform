from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.master_data.models import Category, Material, Unit


class MasterDataRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def category(self, category_id: UUID) -> Category | None:
        return self.session.scalar(
            select(Category).where(Category.id == category_id, Category.deleted_at.is_(None))
        )

    def category_by_code(self, organization_id: UUID, code: str) -> Category | None:
        return self.session.scalar(
            select(Category).where(
                Category.organization_id == organization_id,
                Category.code == code,
                Category.deleted_at.is_(None),
            )
        )

    def categories(self, organization_id: UUID) -> tuple[Category, ...]:
        statement = (
            select(Category)
            .where(
                Category.organization_id == organization_id,
                Category.deleted_at.is_(None),
            )
            .order_by(Category.code)
        )
        return tuple(self.session.scalars(statement))

    def unit(self, code: str) -> Unit | None:
        return self.session.scalar(select(Unit).where(Unit.code == code, Unit.deleted_at.is_(None)))

    def units(self) -> tuple[Unit, ...]:
        return tuple(
            self.session.scalars(select(Unit).where(Unit.deleted_at.is_(None)).order_by(Unit.code))
        )

    def material_by_code(self, organization_id: UUID, code: str) -> Material | None:
        return self.session.scalar(
            select(Material).where(
                Material.organization_id == organization_id,
                Material.code == code,
                Material.deleted_at.is_(None),
            )
        )

    def materials(self, organization_id: UUID) -> tuple[Material, ...]:
        statement = (
            select(Material)
            .where(
                Material.organization_id == organization_id,
                Material.deleted_at.is_(None),
            )
            .order_by(Material.code)
        )
        return tuple(self.session.scalars(statement))

    def add(self, value: Category | Unit | Material) -> None:
        self.session.add(value)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
