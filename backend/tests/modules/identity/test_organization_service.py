import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.contracts.organizations import MembershipCreate, OrganizationCreate
from app.core.database import Base
from app.modules.identity.facade import IdentityFacade
from app.modules.identity.models import Organization, User
from app.modules.identity.service import InvalidOrganizationRelationshipError


def test_organization_tree_and_membership_relationships() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        root = Organization(code="ROOT", name="Root organization")
        outside = Organization(code="OUTSIDE", name="Outside organization")
        user = User(login_name="org-user", display_name="Organization User")
        other_user = User(login_name="other-user", display_name="Other User")
        session.add_all([root, outside, user, other_user])
        session.commit()

        facade = IdentityFacade(session)
        department = facade.create_organization(
            OrganizationCreate(parent_id=root.id, code="dept-01", name="Procurement")
        )
        tree = facade.organization_tree(root.id)

        assert tree.code == "ROOT"
        assert tree.children[0].organization_id == department.organization_id
        assert tree.children[0].code == "DEPT-01"

        membership = facade.create_membership(
            MembershipCreate(
                user_id=user.id,
                organization_id=root.id,
                department_id=department.organization_id,
            )
        )
        assert membership.department_id == department.organization_id

        with pytest.raises(InvalidOrganizationRelationshipError):
            facade.create_membership(
                MembershipCreate(
                    user_id=other_user.id,
                    organization_id=root.id,
                    department_id=outside.id,
                )
            )
    engine.dispose()
