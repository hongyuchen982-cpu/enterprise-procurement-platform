from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.modules.identity.models import User
from app.modules.identity.repository import IdentityRepository


def test_all_constraints_and_indexes_have_stable_names() -> None:
    for table in Base.metadata.tables.values():
        assert all(constraint.name for constraint in table.constraints), table.name
        assert all(index.name for index in table.indexes), table.name


def test_version_timestamps_and_soft_delete_are_consistent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        user = User(login_name="versioned-user", display_name="Version One")
        session.add(user)
        session.commit()

        assert user.version == 1
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.deleted_at is None

        user.display_name = "Version Two"
        session.commit()
        assert user.version == 2

        user.soft_delete()
        session.commit()
        assert user.deleted_at is not None


def test_soft_deleted_membership_is_not_authorized() -> None:
    from uuid import uuid4

    from app.modules.identity.models import Membership, Organization

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    organization = Organization(code="SOFT-DELETE-ORG", name="Soft delete org")
    user = User(login_name="soft-delete-user", display_name="Soft delete user")

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([organization, user])
        session.flush()
        membership = Membership(id=uuid4(), user_id=user.id, organization_id=organization.id)
        session.add(membership)
        session.commit()

        membership.soft_delete()
        session.commit()

        assert IdentityRepository(session).get_active_membership(membership.id) is None
