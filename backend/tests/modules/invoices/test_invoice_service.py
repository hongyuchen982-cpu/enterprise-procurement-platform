from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.contracts.invoice import (
    InvoiceApproval,
    InvoiceCreate,
    InvoiceLineInput,
    InvoiceStatus,
)
from app.contracts.order import PurchaseOrderReceiptAllocation, PurchaseOrderStatus
from app.core.database import Base
from app.modules.identity.facade import IdentityFacade
from app.modules.identity.models import Membership, Organization, User
from app.modules.invoices.repository import InvoiceRepository
from app.modules.invoices.service import InvoiceService, InvoiceStateError
from app.modules.master_data.models import Category, Material, Unit
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.orders.models import PurchaseOrder, PurchaseOrderLine
from app.modules.procurement.models import ProcurementRequest, ProcurementRequestLine


def _business_fixture(
    session: Session,
    *,
    received_quantity: Decimal,
    ordered_quantity: Decimal,
) -> tuple[Membership, User, PurchaseOrder, PurchaseOrderLine]:
    organization = Organization(code="ROOT", name="Root")
    user = User(login_name="accountant", display_name="Accountant")
    session.add_all([organization, user])
    session.flush()
    membership = Membership(user_id=user.id, organization_id=organization.id)
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
    request = ProcurementRequest(
        request_no="PR-INVOICE",
        organization_id=organization.id,
        department_id=organization.id,
        requester_id=user.id,
        requester_membership_id=membership.id,
        status="APPROVED",
        currency="CNY",
        purpose="Laptops",
        required_date=date.today() + timedelta(days=20),
        estimated_total=Decimal("1000"),
    )
    session.add_all([material, request])
    session.flush()
    request_line = ProcurementRequestLine(
        request_id=request.id,
        line_no=1,
        material_id=material.id,
        category_id=category.id,
        description="Laptop",
        quantity=ordered_quantity,
        unit_code=unit.code,
        estimated_unit_price=Decimal("100"),
        estimated_amount=Decimal("1000"),
    )
    session.add(request_line)
    session.flush()
    order = PurchaseOrder(
        order_no="PO-INVOICE",
        organization_id=organization.id,
        procurement_request_id=request.id,
        supplier_id=material.id,
        status=("RECEIVED" if received_quantity == ordered_quantity else "PARTIALLY_RECEIVED"),
        currency="CNY",
        total_amount=Decimal("1130"),
        required_date=request.required_date,
    )
    order_line = PurchaseOrderLine(
        request_line_id=request_line.id,
        line_no=1,
        material_id=material.id,
        category_id=category.id,
        description="Laptop",
        unit_code=unit.code,
        ordered_quantity=ordered_quantity,
        received_quantity=received_quantity,
        invoiced_quantity=Decimal("0"),
        unit_price=Decimal("100"),
        tax_rate=Decimal("0.13"),
        line_amount=Decimal("1130"),
    )
    order.lines = [order_line]
    session.add(order)
    session.commit()
    return membership, user, order, order_line


def test_matched_invoice_approval_closes_fulfilled_order() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        membership, _, order, order_line = _business_fixture(
            session,
            received_quantity=Decimal("2"),
            ordered_quantity=Decimal("2"),
        )
        service = InvoiceService(
            InvoiceRepository(session),
            PurchaseOrderFacade(session),
            IdentityFacade(session),
        )
        invoice = service.create(
            InvoiceCreate(
                order_id=order.id,
                supplier_id=order.supplier_id,
                invoice_no="INV-001",
                invoice_date=date.today(),
                currency="CNY",
                lines=[
                    InvoiceLineInput(
                        order_line_id=order_line.id,
                        invoiced_quantity=Decimal("2"),
                        unit_price=Decimal("100"),
                        tax_rate=Decimal("0.13"),
                    )
                ],
            )
        )
        assert invoice.total_amount == Decimal("226.00")
        invoice = service.submit(invoice.invoice_id, invoice.version)
        assert invoice.status is InvoiceStatus.MATCHED
        assert invoice.lines[0].quantity_matched is True
        assert invoice.lines[0].price_matched is True
        invoice = service.approve(
            invoice.invoice_id,
            membership.id,
            InvoiceApproval(expected_version=invoice.version),
        )
        assert invoice.status is InvoiceStatus.APPROVED
        updated_order = PurchaseOrderFacade(session).get(order.id)
        assert updated_order.status is PurchaseOrderStatus.CLOSED
        assert updated_order.lines[0].invoiced_quantity == Decimal("2")
        with pytest.raises(InvoiceStateError, match="cannot be cancelled"):
            service.cancel(invoice.invoice_id, invoice.version)
    engine.dispose()


def test_invoice_variance_requires_explicit_approval_comment() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        membership, _, order, order_line = _business_fixture(
            session,
            received_quantity=Decimal("5"),
            ordered_quantity=Decimal("10"),
        )
        service = InvoiceService(
            InvoiceRepository(session),
            PurchaseOrderFacade(session),
            IdentityFacade(session),
        )
        invoice = service.create(
            InvoiceCreate(
                order_id=order.id,
                supplier_id=order.supplier_id,
                invoice_no="INV-EXCEPTION",
                invoice_date=date.today(),
                currency="CNY",
                lines=[
                    InvoiceLineInput(
                        order_line_id=order_line.id,
                        invoiced_quantity=Decimal("11"),
                        unit_price=Decimal("110"),
                        tax_rate=Decimal("0.13"),
                    )
                ],
            )
        )
        invoice = service.submit(invoice.invoice_id, invoice.version)
        assert invoice.status is InvoiceStatus.EXCEPTION
        assert invoice.lines[0].quantity_matched is False
        assert invoice.lines[0].price_matched is False
        with pytest.raises(InvoiceStateError, match="comment"):
            service.approve(
                invoice.invoice_id,
                membership.id,
                InvoiceApproval(expected_version=invoice.version),
            )
        invoice = service.approve(
            invoice.invoice_id,
            membership.id,
            InvoiceApproval(
                expected_version=invoice.version,
                comment="Variance reviewed and accepted",
            ),
        )
        assert invoice.status is InvoiceStatus.APPROVED
        assert invoice.approval_comment == "Variance reviewed and accepted"
        updated_order = PurchaseOrderFacade(session).get(order.id)
        assert updated_order.status is PurchaseOrderStatus.PARTIALLY_RECEIVED
        assert updated_order.lines[0].invoiced_quantity == Decimal("11")
        closed_order = PurchaseOrderFacade(session).record_receipt(
            order.id,
            [
                PurchaseOrderReceiptAllocation(
                    order_line_id=order_line.id,
                    accepted_quantity=Decimal("5"),
                )
            ],
        )
        assert closed_order.status is PurchaseOrderStatus.CLOSED
    engine.dispose()
