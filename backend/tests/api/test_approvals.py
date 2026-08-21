from collections.abc import Generator
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.contracts.procurement import ProcurementRequestCreate, ProcurementRequestLineInput
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
from app.modules.procurement.facade import ProcurementFacade

PASSWORD = "correct horse battery staple"


def test_approval_api_template_start_and_decide_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        requester = User(login_name="requester", display_name="Requester")
        approver = User(login_name="approver", display_name="Approver")
        session.add_all([organization, requester, approver])
        session.flush()
        requester_membership = Membership(user_id=requester.id, organization_id=organization.id)
        approver_membership = Membership(user_id=approver.id, organization_id=organization.id)
        requester_role = Role(organization_id=organization.id, code="REQUESTER", name="Requester")
        approver_role = Role(organization_id=organization.id, code="APPROVER", name="Approver")
        permission_codes = (
            "approval.template.manage",
            "approval.instance.start",
            "approval.instance.read",
            "approval.task.decide",
        )
        permissions = [Permission(code=code, name=code) for code in permission_codes]
        category = Category(organization_id=organization.id, code="IT", name="IT")
        unit = Unit(code="EA", name="Each")
        session.add_all(
            [
                requester_membership,
                approver_membership,
                requester_role,
                approver_role,
                category,
                unit,
                *permissions,
            ]
        )
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
                MembershipRole(membership_id=requester_membership.id, role_id=requester_role.id),
                MembershipRole(membership_id=approver_membership.id, role_id=approver_role.id),
                RoleScopeGrant(role_id=requester_role.id, scope_type="ORGANIZATION"),
                RoleScopeGrant(role_id=approver_role.id, scope_type="ORGANIZATION"),
                *[
                    RolePermission(role_id=requester_role.id, permission_code=code)
                    for code in (
                        "approval.template.manage",
                        "approval.instance.start",
                        "approval.instance.read",
                    )
                ],
                RolePermission(role_id=approver_role.id, permission_code="approval.instance.read"),
                RolePermission(role_id=approver_role.id, permission_code="approval.task.decide"),
            ]
        )
        session.commit()
        authentication = AuthenticationService(
            session, BusinessSettings(_env_file=None, auth_session_ttl_minutes=60)
        )
        authentication.set_password(requester.id, PASSWORD)
        authentication.set_password(approver.id, PASSWORD)
        procurement = ProcurementFacade(session)
        request_payload = ProcurementRequestCreate(
            org_id=organization.id,
            department_id=organization.id,
            currency="CNY",
            required_date=date.today() + timedelta(days=30),
            purpose="Laptop",
            lines=[
                ProcurementRequestLineInput(
                    material_id=material.id,
                    category_id=category.id,
                    description="Laptop",
                    quantity=Decimal("1"),
                    unit="EA",
                )
            ],
        )
        procurement_request = procurement.create(
            request_payload,
            requester_membership.id,
            requester.id,
        )
        procurement_request = procurement.submit(
            procurement_request.request_id, procurement_request.version
        )
        cancellable_request = procurement.create(
            request_payload,
            requester_membership.id,
            requester.id,
        )
        cancellable_request = procurement.submit(
            cancellable_request.request_id, cancellable_request.version
        )

    def override_session() -> Generator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        requester_login = client.post(
            "/api/v1/auth/login",
            json={"login_name": "requester", "password": PASSWORD},
        ).json()["data"]["access_token"]
        requester_headers = {
            "Authorization": f"Bearer {requester_login}",
            "X-Membership-ID": str(requester_membership.id),
        }
        template_response = client.post(
            "/api/v1/approval-templates",
            headers=requester_headers,
            json={
                "organization_id": str(organization.id),
                "code": "STANDARD",
                "name": "Standard",
                "steps": [
                    {
                        "name": "Manager approval",
                        "approver_membership_id": str(approver_membership.id),
                    }
                ],
            },
        )
        assert template_response.status_code == 201
        template = template_response.json()["data"]

        start_response = client.post(
            "/api/v1/approvals",
            headers=requester_headers,
            json={
                "request_id": str(procurement_request.request_id),
                "template_id": template["template_id"],
                "expected_request_version": procurement_request.version,
            },
        )
        assert start_response.status_code == 201
        instance = start_response.json()["data"]
        assert instance["status"] == "PENDING"

        approver_login = client.post(
            "/api/v1/auth/login",
            json={"login_name": "approver", "password": PASSWORD},
        ).json()["data"]["access_token"]
        approver_headers = {
            "Authorization": f"Bearer {approver_login}",
            "X-Membership-ID": str(approver_membership.id),
        }
        decision_response = client.post(
            f"/api/v1/approvals/{instance['instance_id']}/decisions",
            headers=approver_headers,
            json={
                "decision": "APPROVE",
                "expected_version": instance["version"],
                "comment": "Approved",
            },
        )
        assert decision_response.status_code == 200
        assert decision_response.json()["data"]["status"] == "APPROVED"

        cancellable_start = client.post(
            "/api/v1/approvals",
            headers=requester_headers,
            json={
                "request_id": str(cancellable_request.request_id),
                "template_id": template["template_id"],
                "expected_request_version": cancellable_request.version,
            },
        )
        assert cancellable_start.status_code == 201
        cancellable_instance = cancellable_start.json()["data"]
        cancelled = client.post(
            f"/api/v1/approvals/{cancellable_instance['instance_id']}/cancel",
            headers=requester_headers,
            json={"expected_version": cancellable_instance["version"]},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["data"]["status"] == "CANCELLED"
        with Session(engine) as session:
            assert (
                ProcurementFacade(session).get(procurement_request.request_id).status == "APPROVED"
            )
            assert (
                ProcurementFacade(session).get(cancellable_request.request_id).status == "SUBMITTED"
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
