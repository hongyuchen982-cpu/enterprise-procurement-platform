from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.contracts.master_data import (
    CategoryCreate,
    CategorySnapshot,
    MasterDataStatus,
    MaterialCreate,
    MaterialSnapshot,
    UnitCreate,
    UnitSnapshot,
)
from app.modules.master_data.models import Category, Material, Unit
from app.modules.master_data.repository import MasterDataRepository


class MasterDataNotFoundError(LookupError):
    pass


class MasterDataConflictError(ValueError):
    pass


class InvalidMasterDataReferenceError(ValueError):
    pass


class MasterDataService:
    def __init__(self, repository: MasterDataRepository) -> None:
        self.repository = repository

    def create_category(self, payload: CategoryCreate) -> CategorySnapshot:
        code = payload.code.strip().upper()
        if self.repository.category_by_code(payload.organization_id, code):
            raise MasterDataConflictError(f"category code already exists: {code}")
        if payload.parent_id is not None:
            parent = self.repository.category(payload.parent_id)
            if parent is None:
                raise MasterDataNotFoundError(str(payload.parent_id))
            if parent.organization_id != payload.organization_id:
                raise InvalidMasterDataReferenceError(
                    "parent category must belong to the same organization"
                )
        category = Category(
            organization_id=payload.organization_id,
            parent_id=payload.parent_id,
            code=code,
            name=payload.name.strip(),
        )
        self._persist(category, f"category code already exists: {code}")
        return self._category_snapshot(category)

    def list_categories(self, organization_id: UUID) -> tuple[CategorySnapshot, ...]:
        return tuple(
            self._category_snapshot(category)
            for category in self.repository.categories(organization_id)
        )

    def category(self, category_id: UUID) -> CategorySnapshot:
        category = self.repository.category(category_id)
        if category is None:
            raise MasterDataNotFoundError(str(category_id))
        return self._category_snapshot(category)

    def create_unit(self, payload: UnitCreate) -> UnitSnapshot:
        code = payload.code.strip().upper()
        if self.repository.unit(code):
            raise MasterDataConflictError(f"unit code already exists: {code}")
        unit = Unit(
            code=code,
            name=payload.name.strip(),
            decimal_places=payload.decimal_places,
        )
        self._persist(unit, f"unit code already exists: {code}")
        return self._unit_snapshot(unit)

    def list_units(self) -> tuple[UnitSnapshot, ...]:
        return tuple(self._unit_snapshot(unit) for unit in self.repository.units())

    def unit(self, code: str) -> UnitSnapshot:
        unit = self.repository.unit(code.strip().upper())
        if unit is None:
            raise MasterDataNotFoundError(code)
        return self._unit_snapshot(unit)

    def create_material(self, payload: MaterialCreate) -> MaterialSnapshot:
        code = payload.code.strip().upper()
        if self.repository.material_by_code(payload.organization_id, code):
            raise MasterDataConflictError(f"material code already exists: {code}")
        category = self.repository.category(payload.category_id)
        if category is None or category.status != MasterDataStatus.ACTIVE:
            raise MasterDataNotFoundError(str(payload.category_id))
        if category.organization_id != payload.organization_id:
            raise InvalidMasterDataReferenceError(
                "material category must belong to the same organization"
            )
        unit_code = payload.unit_code.strip().upper()
        unit = self.repository.unit(unit_code)
        if unit is None or unit.status != MasterDataStatus.ACTIVE:
            raise MasterDataNotFoundError(unit_code)
        material = Material(
            organization_id=payload.organization_id,
            code=code,
            name=payload.name.strip(),
            category_id=category.id,
            unit_code=unit.code,
            specification=payload.specification,
        )
        self._persist(material, f"material code already exists: {code}")
        return self._material_snapshot(material)

    def list_materials(self, organization_id: UUID) -> tuple[MaterialSnapshot, ...]:
        return tuple(
            self._material_snapshot(material)
            for material in self.repository.materials(organization_id)
        )

    def material(self, material_id: UUID) -> MaterialSnapshot:
        material = self.repository.material(material_id)
        if material is None:
            raise MasterDataNotFoundError(str(material_id))
        return self._material_snapshot(material)

    def _persist(self, value: Category | Unit | Material, conflict_message: str) -> None:
        self.repository.add(value)
        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise MasterDataConflictError(conflict_message) from exc

    @staticmethod
    def _category_snapshot(category: Category) -> CategorySnapshot:
        return CategorySnapshot(
            category_id=category.id,
            organization_id=category.organization_id,
            parent_id=category.parent_id,
            code=category.code,
            name=category.name,
            status=MasterDataStatus(category.status),
            version=category.version,
        )

    @staticmethod
    def _unit_snapshot(unit: Unit) -> UnitSnapshot:
        return UnitSnapshot(
            code=unit.code,
            name=unit.name,
            decimal_places=unit.decimal_places,
            status=MasterDataStatus(unit.status),
            version=unit.version,
        )

    @staticmethod
    def _material_snapshot(material: Material) -> MaterialSnapshot:
        return MaterialSnapshot(
            material_id=material.id,
            organization_id=material.organization_id,
            code=material.code,
            name=material.name,
            category_id=material.category_id,
            unit_code=material.unit_code,
            specification=material.specification,
            status=MasterDataStatus(material.status),
            version=material.version,
        )
