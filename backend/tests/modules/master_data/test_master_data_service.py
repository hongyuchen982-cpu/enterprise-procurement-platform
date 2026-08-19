import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.contracts.master_data import CategoryCreate, MaterialCreate, UnitCreate
from app.core.database import Base
from app.modules.identity.models import Organization
from app.modules.master_data.facade import MasterDataFacade
from app.modules.master_data.service import (
    InvalidMasterDataReferenceError,
    MasterDataConflictError,
)


def test_master_data_creation_and_reference_validation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ORG-A", name="Organization A")
        other = Organization(code="ORG-B", name="Organization B")
        session.add_all([organization, other])
        session.commit()
        facade = MasterDataFacade(session)

        unit = facade.create_unit(UnitCreate(code="ea", name="Each", decimal_places=0))
        category = facade.create_category(
            CategoryCreate(organization_id=organization.id, code="it", name="IT equipment")
        )
        material = facade.create_material(
            MaterialCreate(
                organization_id=organization.id,
                code="laptop-01",
                name="Business laptop",
                category_id=category.category_id,
                unit_code=unit.code,
                specification="16 GB RAM",
            )
        )

        assert unit.code == "EA"
        assert category.code == "IT"
        assert material.code == "LAPTOP-01"
        assert facade.list_materials(organization.id) == (material,)

        with pytest.raises(MasterDataConflictError):
            facade.create_unit(UnitCreate(code="EA", name="Duplicate"))
        with pytest.raises(InvalidMasterDataReferenceError):
            facade.create_material(
                MaterialCreate(
                    organization_id=other.id,
                    code="INVALID",
                    name="Invalid material",
                    category_id=category.category_id,
                    unit_code=unit.code,
                )
            )
    engine.dispose()
