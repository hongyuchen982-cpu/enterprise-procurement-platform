from collections.abc import Generator
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

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
from app.modules.procurement.models import ProcurementRequest, ProcurementRequestLine

PASSWORD = "correct horse battery staple"
SUPPLIER_ID = UUID("11111111-1111-4111-8111-111111111111")
ORGANIZATION_ID = UUID("22222222-2222-4222-8222-222222222222")
CATEGORY_ID = UUID("33333333-3333-4333-8333-333333333333")


def test_purchase_order_api_create_issue_cancel_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(id=ORGANIZATION_ID, code="ROOT", name="Root")
        user = User(login_name="buyer", display_name="Buyer")
        session.add_all([organization, user])
        session.flush()
        membership = Membership(user_id=user.id, organization_id=organization.id)
        role = Role(organization_id=organization.id, code="BUYER", name="Buyer")
        permissions = [
            Permission(code=code, name=code)
            for code in (
                "order.read",
                "order.create",
                "order.update",
                "order.issue",
                "order.cancel",
            )
        ]
        category = Category(id=CATEGORY_ID, organization_id=organization.id, code="IT", name="IT")
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
            request_no="PR-ORDER-API",
            organization_id=organization.id,
            department_id=organization.id,
            requester_id=user.id,
            requester_membership_id=membership.id,
            status="APPROVED",
            currency="CNY",
            purpose="Laptop",
            required_date=date.today() + timedelta(days=30),
            estimated_total=Decimal("100.00"),
            lines=[],
        )
        session.add_all(
            [
                material,
                MembershipRole(membership_id=membership.id, role_id=role.id),
                RoleScopeGrant(role_id=role.id, scope_type="ORGANIZATION"),
                *[
                    RolePermission(role_id=role.id, permission_code=permission.code)
                    for permission in permissions
                ],
                purchase_request,
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
            json={"login_name": "buyer", "password": PASSWORD},
        ).json()["data"]["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-ID": str(membership.id),
        }
        created_response = client.post(
            "/api/v1/purchase-orders",
            headers=headers,
            json={
                "procurement_request_id": str(purchase_request.id),
                "supplier_id": str(SUPPLIER_ID),
                "promised_date": str(date.today() + timedelta(days=20)),
                "lines": [
                    {
                        "request_line_id": str(request_line.id),
                        "ordered_quantity": "1",
                        "unit_price": "100",
                        "tax_rate": "0.13",
                    }
                ],
            },
        )
        assert created_response.status_code == 201, created_response.text
        created = created_response.json()["data"]
        assert created["status"] == "DRAFT"
        assert created["total_amount"] == "113.00"

        issued_response = client.post(
            f"/api/v1/purchase-orders/{created['order_id']}/issue",
            headers=headers,
            json={"expected_version": created["version"]},
        )
        assert issued_response.status_code == 200
        issued = issued_response.json()["data"]
        assert issued["status"] == "ISSUED"

        cancelled_response = client.post(
            f"/api/v1/purchase-orders/{created['order_id']}/cancel",
            headers=headers,
            json={"expected_version": issued["version"]},
        )
        assert cancelled_response.status_code == 200
        assert cancelled_response.json()["data"]["status"] == "CANCELLED"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
