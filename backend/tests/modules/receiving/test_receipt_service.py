from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.contracts.order import PurchaseOrderStatus
from app.contracts.receiving import (
    InspectionStatus,
    ReceiptCreate,
    ReceiptLineInput,
    ReceiptStatus,
    ReceiptUpdate,
)
from app.core.database import Base
from app.modules.identity.facade import IdentityFacade
from app.modules.identity.models import Membership, Organization, User
from app.modules.master_data.models import Category, Material, Unit
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.orders.models import PurchaseOrder, PurchaseOrderLine
from app.modules.procurement.models import ProcurementRequest, ProcurementRequestLine
from app.modules.receiving.repository import ReceiptRepository
from app.modules.receiving.service import ReceiptConflictError, ReceiptService, ReceiptStateError


def test_receipt_inspection_completion_updates_order_quantities_atomically() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        receiver = User(login_name="receiver", display_name="Receiver")
        session.add_all([organization, receiver])
        session.flush()
        membership = Membership(user_id=receiver.id, organization_id=organization.id)
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
            request_no="PR-RECEIVING-SERVICE",
            organization_id=organization.id,
            department_id=organization.id,
            requester_id=receiver.id,
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
            quantity=Decimal("10"),
            unit_code=unit.code,
            estimated_unit_price=Decimal("100"),
            estimated_amount=Decimal("1000"),
        )
        session.add(request_line)
        session.flush()
        order = PurchaseOrder(
            order_no="PO-RECEIVING-SERVICE",
            organization_id=organization.id,
            procurement_request_id=request.id,
            supplier_id=material.id,
            status="ISSUED",
            currency="CNY",
            total_amount=Decimal("1000"),
            required_date=request.required_date,
            lines=[],
        )
        session.add(order)
        session.flush()
        order_line = PurchaseOrderLine(
            order_id=order.id,
            request_line_id=request_line.id,
            line_no=1,
            material_id=material.id,
            category_id=category.id,
            description="Laptop",
            unit_code=unit.code,
            ordered_quantity=Decimal("10"),
            received_quantity=Decimal("0"),
            invoiced_quantity=Decimal("0"),
            unit_price=Decimal("100"),
            tax_rate=Decimal("0"),
            line_amount=Decimal("1000"),
        )
        session.add(order_line)
        session.commit()
        session.expire(order, ["lines"])

        service = ReceiptService(
            ReceiptRepository(session),
            PurchaseOrderFacade(session),
            IdentityFacade(session),
        )
        receipt = service.create(
            ReceiptCreate(
                order_id=order.id,
                lines=[
                    ReceiptLineInput(
                        order_line_id=order_line.id,
                        accepted_quantity=Decimal("4"),
                        rejected_quantity=Decimal("1"),
                        inspection_status=InspectionStatus.PENDING,
                    )
                ],
            ),
            membership.id,
            receiver.id,
        )
        with pytest.raises(ReceiptStateError, match="inspections"):
            service.complete(receipt.receipt_id, receipt.version)

        receipt = service.update(
            receipt.receipt_id,
            ReceiptUpdate(
                expected_version=receipt.version,
                lines=[
                    ReceiptLineInput(
                        order_line_id=order_line.id,
                        accepted_quantity=Decimal("4"),
                        rejected_quantity=Decimal("1"),
                        inspection_status=InspectionStatus.PASSED,
                    )
                ],
            ),
        )
        receipt = service.complete(receipt.receipt_id, receipt.version)
        assert receipt.status is ReceiptStatus.COMPLETED
        assert receipt.received_at is not None
        updated_order = PurchaseOrderFacade(session).get(order.id)
        assert updated_order.status is PurchaseOrderStatus.PARTIALLY_RECEIVED
        assert updated_order.lines[0].received_quantity == Decimal("4")

        with pytest.raises(ReceiptConflictError, match="remaining 6"):
            service.create(
                ReceiptCreate(
                    order_id=order.id,
                    lines=[
                        ReceiptLineInput(
                            order_line_id=order_line.id,
                            accepted_quantity=Decimal("7"),
                            rejected_quantity=Decimal("0"),
                            inspection_status=InspectionStatus.PASSED,
                        )
                    ],
                ),
                membership.id,
                receiver.id,
            )

        final_receipt = service.create(
            ReceiptCreate(
                order_id=order.id,
                lines=[
                    ReceiptLineInput(
                        order_line_id=order_line.id,
                        accepted_quantity=Decimal("6"),
                        rejected_quantity=Decimal("0"),
                        inspection_status=InspectionStatus.PASSED,
                    )
                ],
            ),
            membership.id,
            receiver.id,
        )
        final_receipt = service.complete(final_receipt.receipt_id, final_receipt.version)
        assert final_receipt.status is ReceiptStatus.COMPLETED
        final_order = PurchaseOrderFacade(session).get(order.id)
        assert final_order.status is PurchaseOrderStatus.RECEIVED
        assert final_order.lines[0].received_quantity == Decimal("10")
        with pytest.raises(ReceiptStateError, match="only draft"):
            service.cancel(final_receipt.receipt_id, final_receipt.version)
    engine.dispose()
