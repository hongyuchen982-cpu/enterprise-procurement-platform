from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.contracts.identity import AccessTarget, DataScopeType
from app.core.database import Base
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
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.service import AccessService, MembershipNotActiveError


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def seed_access(session: Session, scope_type: DataScopeType) -> dict[str, UUID]:
    root_id, child_id, outsider_id = uuid4(), uuid4(), uuid4()
    user_id, membership_id, role_id = uuid4(), uuid4(), uuid4()
    session.add_all(
        [
            Organization(id=root_id, code="ROOT", name="Root"),
            Organization(id=child_id, parent_id=root_id, code="CHILD", name="Child"),
            Organization(id=outsider_id, code="OTHER", name="Other"),
            User(id=user_id, login_name="buyer", display_name="Buyer"),
            Membership(id=membership_id, user_id=user_id, organization_id=root_id),
            Permission(code="procurement.request.read", name="Read procurement requests"),
            Role(id=role_id, organization_id=root_id, code="BUYER", name="Buyer"),
            MembershipRole(membership_id=membership_id, role_id=role_id),
            RolePermission(role_id=role_id, permission_code="procurement.request.read"),
            RoleScopeGrant(role_id=role_id, scope_type=scope_type, scope_ref=root_id),
        ]
    )
    session.commit()
    return {
        "root_id": root_id,
        "child_id": child_id,
        "outsider_id": outsider_id,
        "user_id": user_id,
        "membership_id": membership_id,
    }


def test_permission_and_organization_tree_scope_allow_descendant(session: Session) -> None:
    ids = seed_access(session, DataScopeType.ORGANIZATION_TREE)
    result = AccessService(IdentityRepository(session)).evaluate(
        ids["membership_id"],
        "procurement.request.read",
        AccessTarget(organization_id=ids["child_id"]),
    )
    assert result.allowed is True
    assert result.reason == "permission_and_scope_granted"


def test_scope_rejects_unrelated_organization(session: Session) -> None:
    ids = seed_access(session, DataScopeType.ORGANIZATION_TREE)
    result = AccessService(IdentityRepository(session)).evaluate(
        ids["membership_id"],
        "procurement.request.read",
        AccessTarget(organization_id=ids["outsider_id"]),
    )
    assert result.allowed is False
    assert result.reason == "data_scope_not_granted"


def test_missing_permission_is_rejected_before_scope(session: Session) -> None:
    ids = seed_access(session, DataScopeType.ALL)
    result = AccessService(IdentityRepository(session)).evaluate(
        ids["membership_id"],
        "procurement.request.approve",
        AccessTarget(organization_id=ids["root_id"]),
    )
    assert result.allowed is False
    assert result.reason == "permission_not_granted"


def test_disabled_membership_has_no_effective_access(session: Session) -> None:
    ids = seed_access(session, DataScopeType.ALL)
    membership = session.get(Membership, ids["membership_id"])
    assert membership is not None
    membership.status = "DISABLED"
    session.commit()

    with pytest.raises(MembershipNotActiveError):
        AccessService(IdentityRepository(session)).effective_access(ids["membership_id"])


def test_role_from_another_organization_is_ignored(session: Session) -> None:
    ids = seed_access(session, DataScopeType.ORGANIZATION)
    foreign_role_id = uuid4()
    session.add_all(
        [
            Permission(code="procurement.request.approve", name="Approve requests"),
            Role(
                id=foreign_role_id,
                organization_id=ids["outsider_id"],
                code="FOREIGN_APPROVER",
                name="Foreign approver",
            ),
            MembershipRole(membership_id=ids["membership_id"], role_id=foreign_role_id),
            RolePermission(role_id=foreign_role_id, permission_code="procurement.request.approve"),
            RoleScopeGrant(role_id=foreign_role_id, scope_type=DataScopeType.ALL),
        ]
    )
    session.commit()

    result = AccessService(IdentityRepository(session)).evaluate(
        ids["membership_id"],
        "procurement.request.approve",
        AccessTarget(organization_id=ids["root_id"]),
    )
    assert result.allowed is False
    assert result.reason == "permission_not_granted"
