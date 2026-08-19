from collections.abc import Generator

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

PASSWORD = "correct horse battery staple"


def test_authenticated_organization_and_master_data_api_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        user = User(login_name="master-admin", display_name="Master Admin")
        session.add_all([organization, user])
        session.flush()
        membership = Membership(user_id=user.id, organization_id=organization.id)
        role = Role(organization_id=organization.id, code="ADMIN", name="Administrator")
        permissions = [
            Permission(code="organization.read", name="Read organizations"),
            Permission(code="organization.manage", name="Manage organizations"),
            Permission(code="master_data.read", name="Read master data"),
            Permission(code="master_data.manage", name="Manage master data"),
        ]
        session.add_all([membership, role, *permissions])
        session.flush()
        session.add(MembershipRole(membership_id=membership.id, role_id=role.id))
        session.add(RoleScopeGrant(role_id=role.id, scope_type="ORGANIZATION_TREE"))
        session.add_all(
            [
                RolePermission(role_id=role.id, permission_code=permission.code)
                for permission in permissions
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
            json={"login_name": "master-admin", "password": PASSWORD},
        )
        token = login.json()["data"]["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-ID": str(membership.id),
        }

        child = client.post(
            "/api/v1/organizations",
            headers=headers,
            json={"parent_id": str(organization.id), "code": "PROC", "name": "Procurement"},
        )
        assert child.status_code == 201

        tree = client.get(
            f"/api/v1/organizations/{organization.id}/tree",
            headers=headers,
        )
        assert tree.status_code == 200
        assert tree.json()["data"]["children"][0]["code"] == "PROC"

        unit = client.post(
            "/api/v1/master-data/units",
            headers=headers,
            json={"code": "EA", "name": "Each", "decimal_places": 0},
        )
        assert unit.status_code == 201
        category = client.post(
            "/api/v1/master-data/categories",
            headers=headers,
            json={"organization_id": str(organization.id), "code": "IT", "name": "IT"},
        )
        assert category.status_code == 201
        category_id = category.json()["data"]["category_id"]
        material = client.post(
            "/api/v1/master-data/materials",
            headers=headers,
            json={
                "organization_id": str(organization.id),
                "code": "LAPTOP",
                "name": "Laptop",
                "category_id": category_id,
                "unit_code": "EA",
            },
        )
        assert material.status_code == 201

        denied = client.get(
            f"/api/v1/organizations/{organization.id}/tree",
            headers={"Authorization": f"Bearer {token}", "X-Membership-ID": "0" * 32},
        )
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
