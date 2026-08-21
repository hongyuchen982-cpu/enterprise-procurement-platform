from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.contracts.order import (
    PurchaseOrderCreate,
    PurchaseOrderLineInput,
    PurchaseOrderStatus,
    PurchaseOrderUpdate,
)
from app.contracts.procurement import ProcurementRequestCreate, ProcurementRequestLineInput
from app.contracts.supplier import (
    QualificationStatus,
    RiskLevel,
    SupplierSnapshot,
    SupplierStatus,
)
from app.core.database import Base
from app.modules.identity.models import Membership, Organization, User
from app.modules.master_data.models import Category, Material, Unit
from app.modules.orders.repository import PurchaseOrderRepository
from app.modules.orders.service import (
    InvalidPurchaseOrderReferenceError,
    PurchaseOrderConflictError,
    PurchaseOrderService,
    PurchaseOrderStateError,
)
from app.modules.procurement.facade import ProcurementFacade
from app.modules.procurement.models import ProcurementRequest, ProcurementRequestRecordStatus


def test_order_draft_issue_cancel_and_quantity_allocation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        requester = User(login_name="requester", display_name="Requester")
        session.add_all([organization, requester])
        session.flush()
        membership = Membership(user_id=requester.id, organization_id=organization.id)
        category = Category(organization_id=organization.id, code="IT", name="IT")
        unit = Unit(code="EA", name="Each")
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

        procurement = ProcurementFacade(session)
        request = procurement.create(
            ProcurementRequestCreate(
                org_id=organization.id,
                department_id=organization.id,
                currency="CNY",
                required_date=date.today() + timedelta(days=30),
                purpose="Laptops",
                lines=[
                    ProcurementRequestLineInput(
                        material_id=material.id,
                        category_id=category.id,
                        description="Laptop",
                        quantity=Decimal("3"),
                        unit="EA",
                    )
                ],
            ),
            membership.id,
            requester.id,
        )
        record = session.get(ProcurementRequest, request.request_id)
        assert record is not None
        record.status = ProcurementRequestRecordStatus.APPROVED
        session.commit()
        request = procurement.get(request.request_id)

        supplier = SupplierSnapshot(
            supplier_id=material.id,
            org_id=organization.id,
            legal_name="Qualified Supplier",
            status=SupplierStatus.ACTIVE,
            qualification_status=QualificationStatus.QUALIFIED,
            category_ids=[category.id],
            risk_level=RiskLevel.LOW,
            is_frozen=False,
            version=1,
            updated_at=datetime.now(UTC),
        )
        service = PurchaseOrderService(
            PurchaseOrderRepository(session),
            procurement,
            supplier_lookup=lambda supplier_id: (
                supplier if supplier_id == supplier.supplier_id else None
            ),
        )
        payload = PurchaseOrderCreate(
            procurement_request_id=request.request_id,
            supplier_id=supplier.supplier_id,
            promised_date=date.today() + timedelta(days=15),
            lines=[
                PurchaseOrderLineInput(
                    request_line_id=request.lines[0].line_id,
                    ordered_quantity=Decimal("2"),
                    unit_price=Decimal("100"),
                    tax_rate=Decimal("0.13"),
                )
            ],
        )
        order = service.create(payload)

        assert order.status is PurchaseOrderStatus.DRAFT
        assert order.total_amount == Decimal("226.00")
        assert order.lines[0].received_quantity == 0

        with pytest.raises(PurchaseOrderConflictError, match="remaining approved quantity 1"):
            service.create(
                payload.model_copy(
                    update={
                        "lines": [
                            PurchaseOrderLineInput(
                                request_line_id=request.lines[0].line_id,
                                ordered_quantity=Decimal("2"),
                                unit_price=Decimal("90"),
                            )
                        ]
                    }
                )
            )

        updated = service.update(
            order.order_id,
            PurchaseOrderUpdate(
                expected_version=order.version,
                promised_date=payload.promised_date,
                lines=[
                    PurchaseOrderLineInput(
                        request_line_id=request.lines[0].line_id,
                        ordered_quantity=Decimal("1"),
                        unit_price=Decimal("80"),
                    )
                ],
            ),
        )
        assert updated.total_amount == Decimal("80.00")
        with pytest.raises(PurchaseOrderConflictError, match="version mismatch"):
            service.issue(updated.order_id, order.version)

        issued = service.issue(updated.order_id, updated.version)
        assert issued.status is PurchaseOrderStatus.ISSUED
        assert issued.issued_at is not None
        with pytest.raises(PurchaseOrderStateError, match="only draft"):
            service.update(
                issued.order_id,
                PurchaseOrderUpdate(
                    expected_version=issued.version,
                    lines=payload.lines,
                ),
            )
        cancelled = service.cancel(issued.order_id, issued.version)
        assert cancelled.status is PurchaseOrderStatus.CANCELLED
        assert cancelled.cancelled_at is not None
    engine.dispose()


def test_order_rejects_supplier_without_category_qualification() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        requester = User(login_name="requester", display_name="Requester")
        session.add_all([organization, requester])
        session.flush()
        membership = Membership(user_id=requester.id, organization_id=organization.id)
        category = Category(organization_id=organization.id, code="IT", name="IT")
        unit = Unit(code="EA", name="Each")
        session.add_all([membership, category, unit])
        session.commit()
        procurement = ProcurementFacade(session)
        request = procurement.create(
            ProcurementRequestCreate(
                org_id=organization.id,
                department_id=organization.id,
                currency="CNY",
                required_date=date.today() + timedelta(days=5),
                purpose="Services",
                lines=[
                    ProcurementRequestLineInput(
                        category_id=category.id,
                        description="Service",
                        quantity=Decimal("1"),
                        unit="EA",
                    )
                ],
            ),
            membership.id,
            requester.id,
        )
        record = session.get(ProcurementRequest, request.request_id)
        assert record is not None
        record.status = ProcurementRequestRecordStatus.APPROVED
        session.commit()
        request = procurement.get(request.request_id)
        supplier = SupplierSnapshot(
            supplier_id=requester.id,
            org_id=organization.id,
            legal_name="Wrong Category Supplier",
            status=SupplierStatus.ACTIVE,
            qualification_status=QualificationStatus.QUALIFIED,
            category_ids=[],
            risk_level=RiskLevel.LOW,
            is_frozen=False,
            version=1,
            updated_at=datetime.now(UTC),
        )
        service = PurchaseOrderService(
            PurchaseOrderRepository(session), procurement, supplier_lookup=lambda _: supplier
        )

        with pytest.raises(InvalidPurchaseOrderReferenceError, match="not qualified"):
            service.create(
                PurchaseOrderCreate(
                    procurement_request_id=request.request_id,
                    supplier_id=supplier.supplier_id,
                    lines=[
                        PurchaseOrderLineInput(
                            request_line_id=request.lines[0].line_id,
                            ordered_quantity=Decimal("1"),
                            unit_price=Decimal("1"),
                        )
                    ],
                )
            )
    engine.dispose()
