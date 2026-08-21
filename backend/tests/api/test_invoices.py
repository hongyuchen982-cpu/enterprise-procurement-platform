from collections.abc import Generator
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import Base, get_session
from app.core.settings.business import BusinessSettings
from app.main import app
from app.modules.identity.auth_service import AuthenticationService
from app.modules.identity.models import (
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    RoleScopeGrant,
    User,
)
from app.modules.master_data.models import Category, Material, Unit
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.orders.models import PurchaseOrder, PurchaseOrderLine
from app.modules.procurement.models import ProcurementRequest, ProcurementRequestLine

PASSWORD = "correct horse battery staple"


def test_invoice_api_match_and_approve_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        user = User(login_name="accountant", display_name="Accountant")
        session.add_all([organization, user])
        session.flush()
        membership = Membership(user_id=user.id, organization_id=organization.id)
        role = Role(organization_id=organization.id, code="ACCOUNTANT", name="Accountant")
        permission_codes = (
            "invoice.read",
            "invoice.create",
            "invoice.update",
            "invoice.submit",
            "invoice.approve",
            "invoice.cancel",
            "audit.read",
        )
        permissions = [Permission(code=code, name=code) for code in permission_codes]
        category = Category(organization_id=organization.id, code="IT", name="IT")
        unit = Unit(code="EA", name="Each")
        session.add_all([membership, role, *permissions, category, unit])
        session.flush()
        material = Material(
            organization_id=organization.id,
            code="LAPTOP",
            name="Laptop",
            category_id=category.id,
            unit_code=unit.code,
        )
        purchase_request = ProcurementRequest(
            request_no="PR-INVOICE-API",
            organization_id=organization.id,
            department_id=organization.id,
            requester_id=user.id,
            requester_membership_id=membership.id,
            status="APPROVED",
            currency="CNY",
            purpose="Laptop",
            required_date=date.today() + timedelta(days=10),
            estimated_total=Decimal("100"),
        )
        session.add_all(
            [
                material,
                purchase_request,
                MembershipRole(membership_id=membership.id, role_id=role.id),
                RoleScopeGrant(role_id=role.id, scope_type="ORGANIZATION"),
                *[
                    RolePermission(role_id=role.id, permission_code=code)
                    for code in permission_codes
                ],
            ]
        )
        session.flush()
        request_line = ProcurementRequestLine(
            request_id=purchase_request.id,
            line_no=1,
            material_id=material.id,
            category_id=category.id,
            description="Laptop",
            quantity=Decimal("1"),
            unit_code=unit.code,
            estimated_unit_price=Decimal("100"),
            estimated_amount=Decimal("100"),
        )
        session.add(request_line)
        session.flush()
        order = PurchaseOrder(
            order_no="PO-INVOICE-API",
            organization_id=organization.id,
            procurement_request_id=purchase_request.id,
            supplier_id=material.id,
            status="RECEIVED",
            currency="CNY",
            total_amount=Decimal("100"),
            required_date=purchase_request.required_date,
        )
        order_line = PurchaseOrderLine(
            request_line_id=request_line.id,
            line_no=1,
            material_id=material.id,
            category_id=category.id,
            description="Laptop",
            unit_code=unit.code,
            ordered_quantity=Decimal("1"),
            received_quantity=Decimal("1"),
            invoiced_quantity=Decimal("0"),
            unit_price=Decimal("100"),
            tax_rate=Decimal("0"),
            line_amount=Decimal("100"),
        )
        order.lines = [order_line]
        session.add(order)
        session.commit()
        authentication = AuthenticationService(
            session, BusinessSettings(_env_file=None, auth_session_ttl_minutes=60)
        )
        authentication.set_password(user.id, PASSWORD)

    def override_session() -> Generator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        token = client.post(
            "/api/v1/auth/login",
            json={"login_name": "accountant", "password": PASSWORD},
        ).json()["data"]["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-ID": str(membership.id),
        }
        created_response = client.post(
            "/api/v1/invoices",
            headers=headers,
            json={
                "order_id": str(order.id),
                "supplier_id": str(order.supplier_id),
                "invoice_no": "INV-API-001",
                "invoice_date": str(date.today()),
                "currency": "CNY",
                "lines": [
                    {
                        "order_line_id": str(order_line.id),
                        "invoiced_quantity": "1",
                        "unit_price": "100",
                        "tax_rate": "0",
                    }
                ],
            },
        )
        assert created_response.status_code == 201, created_response.text
        created = created_response.json()["data"]

        submitted_response = client.post(
            f"/api/v1/invoices/{created['invoice_id']}/submit",
            headers=headers,
            json={"expected_version": created["version"]},
        )
        assert submitted_response.status_code == 200, submitted_response.text
        submitted = submitted_response.json()["data"]
        assert submitted["status"] == "MATCHED"

        approved_response = client.post(
            f"/api/v1/invoices/{created['invoice_id']}/approve",
            headers=headers,
            json={"expected_version": submitted["version"]},
        )
        assert approved_response.status_code == 200, approved_response.text
        assert approved_response.json()["data"]["status"] == "APPROVED"
        with Session(engine) as session:
            updated_order = PurchaseOrderFacade(session).get(order.id)
            assert updated_order.status == "CLOSED"
            assert updated_order.lines[0].invoiced_quantity == Decimal("1")
        audit_response = client.get(
            f"/api/v1/audit-log?organization_id={organization.id}&action=INVOICE_APPROVED",
            headers=headers,
        )
        assert audit_response.status_code == 200
        entries = audit_response.json()["data"]
        assert len(entries) == 1
        assert entries[0]["object_id"] == created["invoice_id"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
