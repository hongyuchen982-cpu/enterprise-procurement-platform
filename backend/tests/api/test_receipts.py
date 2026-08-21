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


def test_receipt_api_create_complete_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        user = User(login_name="receiver", display_name="Receiver")
        session.add_all([organization, user])
        session.flush()
        membership = Membership(user_id=user.id, organization_id=organization.id)
        role = Role(organization_id=organization.id, code="RECEIVER", name="Receiver")
        permissions = [
            Permission(code=code, name=code)
            for code in (
                "receipt.read",
                "receipt.create",
                "receipt.update",
                "receipt.complete",
                "receipt.cancel",
                "inventory.read",
                "audit.read",
            )
        ]
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
            request_no="PR-RECEIVING-API",
            organization_id=organization.id,
            department_id=organization.id,
            requester_id=user.id,
            requester_membership_id=membership.id,
            status="APPROVED",
            currency="CNY",
            purpose="Laptop",
            required_date=date.today() + timedelta(days=20),
            estimated_total=Decimal("100"),
        )
        session.add_all(
            [
                material,
                purchase_request,
                MembershipRole(membership_id=membership.id, role_id=role.id),
                RoleScopeGrant(role_id=role.id, scope_type="ORGANIZATION"),
                *[
                    RolePermission(role_id=role.id, permission_code=value.code)
                    for value in permissions
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
            order_no="PO-RECEIVING-API",
            organization_id=organization.id,
            procurement_request_id=purchase_request.id,
            supplier_id=material.id,
            status="ISSUED",
            currency="CNY",
            total_amount=Decimal("100"),
            required_date=purchase_request.required_date,
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
            ordered_quantity=Decimal("1"),
            received_quantity=Decimal("0"),
            invoiced_quantity=Decimal("0"),
            unit_price=Decimal("100"),
            tax_rate=Decimal("0"),
            line_amount=Decimal("100"),
        )
        session.add(order_line)
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
            json={"login_name": "receiver", "password": PASSWORD},
        ).json()["data"]["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-ID": str(membership.id),
        }
        created_response = client.post(
            "/api/v1/receipts",
            headers=headers,
            json={
                "order_id": str(order.id),
                "lines": [
                    {
                        "order_line_id": str(order_line.id),
                        "accepted_quantity": "1",
                        "rejected_quantity": "0",
                        "inspection_status": "PASSED",
                    }
                ],
            },
        )
        assert created_response.status_code == 201, created_response.text
        created = created_response.json()["data"]
        assert created["status"] == "DRAFT"

        completed_response = client.post(
            f"/api/v1/receipts/{created['receipt_id']}/complete",
            headers=headers,
            json={"expected_version": created["version"]},
        )
        assert completed_response.status_code == 200, completed_response.text
        completed = completed_response.json()["data"]
        assert completed["status"] == "COMPLETED"
        with Session(engine) as session:
            updated_order = PurchaseOrderFacade(session).get(order.id)
            assert updated_order.status == "RECEIVED"
            assert updated_order.lines[0].received_quantity == Decimal("1")
        balances_response = client.get(
            f"/api/v1/inventory/balances?organization_id={organization.id}",
            headers=headers,
        )
        assert balances_response.status_code == 200
        balances = balances_response.json()["data"]
        assert len(balances) == 1
        assert balances[0]["on_hand_quantity"] == "1.000000"

        movements_response = client.get(
            f"/api/v1/inventory/movements?organization_id={organization.id}",
            headers=headers,
        )
        assert movements_response.status_code == 200
        movements = movements_response.json()["data"]
        assert len(movements) == 1
        assert movements[0]["source_id"] == created["receipt_id"]

        audit_response = client.get(
            f"/api/v1/audit-log?organization_id={organization.id}&action=RECEIPT_COMPLETED",
            headers=headers,
        )
        assert audit_response.status_code == 200
        audit_entries = audit_response.json()["data"]
        assert len(audit_entries) == 1
        assert audit_entries[0]["object_id"] == created["receipt_id"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
