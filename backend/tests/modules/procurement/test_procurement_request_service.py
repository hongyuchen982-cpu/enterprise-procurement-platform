from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.contracts.procurement import (
    ProcurementRequestCreate,
    ProcurementRequestLineInput,
    ProcurementRequestStatus,
    ProcurementRequestUpdate,
)
from app.core.database import Base
from app.modules.identity.facade import IdentityFacade
from app.modules.identity.models import Membership, Organization, User
from app.modules.master_data.facade import MasterDataFacade
from app.modules.master_data.models import Category, Material, Unit
from app.modules.procurement.repository import ProcurementRepository
from app.modules.procurement.service import (
    InvalidProcurementReferenceError,
    ProcurementRequestConflictError,
    ProcurementRequestService,
    ProcurementRequestStateError,
)

TODAY = date(2026, 8, 20)
REQUIRED_DATE = date(2026, 9, 1)


def _payload(
    organization: Organization,
    department: Organization,
    category: Category,
    material: Material,
) -> ProcurementRequestCreate:
    return ProcurementRequestCreate(
        org_id=organization.id,
        department_id=department.id,
        currency="cny",
        required_date=REQUIRED_DATE,
        purpose="Developer workstations",
        lines=[
            ProcurementRequestLineInput(
                material_id=material.id,
                category_id=category.id,
                description="Laptop",
                quantity=Decimal("2.500000"),
                unit="ea",
                estimated_unit_price=Decimal("1234.56"),
            )
        ],
    )


def test_draft_update_submit_withdraw_and_version_guards() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        user = User(login_name="buyer", display_name="Buyer")
        session.add_all([organization, user])
        session.flush()
        department = Organization(parent_id=organization.id, code="IT", name="IT")
        session.add(department)
        session.flush()
        membership = Membership(
            user_id=user.id, organization_id=organization.id, department_id=department.id
        )
        category = Category(organization_id=organization.id, code="HW", name="Hardware")
        unit = Unit(code="EA", name="Each", decimal_places=0)
        session.add_all([membership, category, unit])
        session.flush()
        material = Material(
            organization_id=organization.id,
            code="LAPTOP",
            name="Laptop",
            category_id=category.id,
            unit_code=unit.code,
        )
        session.add(material)
        session.commit()

        service = ProcurementRequestService(
            ProcurementRepository(session),
            IdentityFacade(session),
            MasterDataFacade(session),
            today=lambda: TODAY,
        )
        created = service.create(
            _payload(organization, department, category, material), membership.id, user.id
        )

        assert created.status is ProcurementRequestStatus.DRAFT
        assert created.currency == "CNY"
        assert created.estimated_total == Decimal("3086.40")
        assert created.version == 1

        update = ProcurementRequestUpdate(
            expected_version=created.version,
            currency="USD",
            required_date=REQUIRED_DATE,
            purpose="Updated purpose",
            lines=[
                ProcurementRequestLineInput(
                    material_id=material.id,
                    category_id=category.id,
                    description="Laptop",
                    quantity=Decimal("1"),
                    unit="EA",
                    estimated_unit_price=Decimal("1000.00"),
                )
            ],
        )
        updated = service.update(created.request_id, update)
        assert updated.estimated_total == Decimal("1000.00")
        assert updated.version == 2

        same_total_update = update.model_copy(
            update={
                "expected_version": updated.version,
                "lines": [update.lines[0].model_copy(update={"description": "Renamed laptop"})],
            }
        )
        updated = service.update(created.request_id, same_total_update)
        assert updated.lines[0].description == "Renamed laptop"
        assert updated.version == 3

        with pytest.raises(ProcurementRequestConflictError):
            service.submit(created.request_id, expected_version=1)

        submitted = service.submit(created.request_id, expected_version=updated.version)
        assert submitted.status is ProcurementRequestStatus.SUBMITTED
        assert submitted.submitted_at is not None

        with pytest.raises(ProcurementRequestStateError):
            service.update(
                created.request_id,
                update.model_copy(update={"expected_version": submitted.version}),
            )

        withdrawn = service.withdraw(created.request_id, expected_version=submitted.version)
        assert withdrawn.status is ProcurementRequestStatus.DRAFT
        assert withdrawn.submitted_at is None

        overflow = update.model_copy(
            update={
                "expected_version": withdrawn.version,
                "lines": [
                    update.lines[0].model_copy(
                        update={
                            "quantity": Decimal("2"),
                            "estimated_unit_price": Decimal("9999999999999999.99"),
                        }
                    )
                ],
            }
        )
        with pytest.raises(InvalidProcurementReferenceError, match="money range"):
            service.update(created.request_id, overflow)
    engine.dispose()


def test_rejects_past_dates_and_cross_organization_master_data() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="A", name="A")
        other = Organization(code="B", name="B")
        user = User(login_name="buyer", display_name="Buyer")
        session.add_all([organization, other, user])
        session.flush()
        department = Organization(parent_id=organization.id, code="A-IT", name="A IT")
        session.add(department)
        session.flush()
        membership = Membership(user_id=user.id, organization_id=organization.id)
        category = Category(organization_id=other.id, code="HW", name="Hardware")
        unit = Unit(code="EA", name="Each")
        session.add_all([membership, category, unit])
        session.flush()
        material = Material(
            organization_id=other.id,
            code="LAPTOP",
            name="Laptop",
            category_id=category.id,
            unit_code=unit.code,
        )
        session.add(material)
        session.commit()
        service = ProcurementRequestService(
            ProcurementRepository(session),
            IdentityFacade(session),
            MasterDataFacade(session),
            today=lambda: TODAY,
        )
        payload = _payload(organization, department, category, material)

        with pytest.raises(InvalidProcurementReferenceError, match="category"):
            service.create(payload, membership.id, user.id)

        with pytest.raises(InvalidProcurementReferenceError, match="past"):
            service.create(
                payload.model_copy(update={"required_date": date(2026, 8, 19)}),
                membership.id,
                user.id,
            )
    engine.dispose()
