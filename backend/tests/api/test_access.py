from collections.abc import Generator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.contracts.identity import DataScopeType
from app.core.database import Base, get_session
from app.main import app
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


def test_access_evaluation_api_returns_contract_response() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    organization_id, user_id, membership_id, role_id = uuid4(), uuid4(), uuid4(), uuid4()
    with Session(engine) as session:
        session.add_all(
            [
                Organization(id=organization_id, code="ROOT", name="Root"),
                User(id=user_id, login_name="buyer", display_name="Buyer"),
                Membership(
                    id=membership_id,
                    user_id=user_id,
                    organization_id=organization_id,
                ),
                Permission(code="procurement.request.read", name="Read requests"),
                Role(id=role_id, organization_id=organization_id, code="BUYER", name="Buyer"),
                MembershipRole(membership_id=membership_id, role_id=role_id),
                RolePermission(role_id=role_id, permission_code="procurement.request.read"),
                RoleScopeGrant(role_id=role_id, scope_type=DataScopeType.ALL),
            ]
        )
        session.commit()

    def override_session() -> Generator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).post(
            "/api/v1/access/evaluate",
            json={
                "membership_id": str(membership_id),
                "permission_code": "procurement.request.read",
                "target": {"organization_id": str(organization_id)},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"] == {
        "allowed": True,
        "reason": "permission_and_scope_granted",
    }
