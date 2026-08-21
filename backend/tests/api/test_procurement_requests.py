from collections.abc import Generator
from datetime import date, timedelta

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

PASSWORD = "correct horse battery staple"


def test_procurement_request_api_draft_submit_withdraw_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        user = User(login_name="buyer", display_name="Buyer")
        session.add_all([organization, user])
        session.flush()
        department = Organization(parent_id=organization.id, code="PROC", name="Procurement")
        session.add(department)
        session.flush()
        membership = Membership(
            user_id=user.id, organization_id=organization.id, department_id=department.id
        )
        role = Role(organization_id=organization.id, code="BUYER", name="Buyer")
        permissions = [
            Permission(code=code, name=code)
            for code in (
                "procurement.request.read",
                "procurement.request.create",
                "procurement.request.update",
                "procurement.request.submit",
            )
        ]
        category = Category(organization_id=organization.id, code="IT", name="IT")
        unit = Unit(code="EA", name="Each", decimal_places=0)
        session.add_all([membership, role, category, unit, *permissions])
        session.flush()
        material = Material(
            organization_id=organization.id,
            code="LAPTOP",
            name="Laptop",
            category_id=category.id,
            unit_code=unit.code,
        )
        session.add_all(
            [
                material,
                MembershipRole(membership_id=membership.id, role_id=role.id),
                RoleScopeGrant(role_id=role.id, scope_type="ORGANIZATION_TREE"),
                *[
                    RolePermission(role_id=role.id, permission_code=permission.code)
                    for permission in permissions
                ],
            ]
        )
        session.commit()
        AuthenticationService(
            session, BusinessSettings(_env_file=None, auth_session_ttl_minutes=60)
        ).set_password(user.id, PASSWORD)

    def override_session() -> Generator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"login_name": "buyer", "password": PASSWORD},
        )
        token = login.json()["data"]["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-ID": str(membership.id),
        }
        payload = {
            "org_id": str(organization.id),
            "department_id": str(department.id),
            "currency": "CNY",
            "required_date": (date.today() + timedelta(days=30)).isoformat(),
            "purpose": "Engineering laptops",
            "lines": [
                {
                    "material_id": str(material.id),
                    "category_id": str(category.id),
                    "description": "Laptop",
                    "quantity": "2",
                    "unit": "EA",
                    "estimated_unit_price": "5000.00",
                }
            ],
        }
        created = client.post("/api/v1/procurement-requests", headers=headers, json=payload)
        assert created.status_code == 201
        value = created.json()["data"]
        assert value["status"] == "DRAFT"
        assert value["estimated_total"] == "10000.00"

        listed = client.get(
            "/api/v1/procurement-requests",
            headers=headers,
            params={"organization_id": str(organization.id)},
        )
        assert listed.status_code == 200
        assert [item["request_id"] for item in listed.json()["data"]] == [value["request_id"]]

        submitted = client.post(
            f"/api/v1/procurement-requests/{value['request_id']}/submit",
            headers=headers,
            json={"expected_version": value["version"]},
        )
        assert submitted.status_code == 200
        submitted_value = submitted.json()["data"]
        assert submitted_value["status"] == "SUBMITTED"

        stale = client.put(
            f"/api/v1/procurement-requests/{value['request_id']}",
            headers=headers,
            json={
                "currency": payload["currency"],
                "required_date": payload["required_date"],
                "purpose": payload["purpose"],
                "lines": payload["lines"],
                "expected_version": value["version"],
            },
        )
        assert stale.status_code == 409

        withdrawn = client.post(
            f"/api/v1/procurement-requests/{value['request_id']}/withdraw",
            headers=headers,
            json={"expected_version": submitted_value["version"]},
        )
        assert withdrawn.status_code == 200
        assert withdrawn.json()["data"]["status"] == "DRAFT"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
