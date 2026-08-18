from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session, aliased

from app.modules.identity.auth_models import AuthSession, UserCredential
from app.modules.identity.models import Membership, Organization, User

Department = aliased(Organization)


class AuthenticationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def active_user_by_login(self, login_name: str) -> User | None:
        return self.session.scalar(
            select(User).where(
                User.login_name == login_name,
                User.status == "ACTIVE",
                User.deleted_at.is_(None),
            )
        )

    def active_user_by_id(self, user_id: UUID) -> User | None:
        return self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.status == "ACTIVE",
                User.deleted_at.is_(None),
            )
        )

    def credential(self, user_id: UUID, *, for_update: bool = False) -> UserCredential | None:
        statement = select(UserCredential).where(UserCredential.user_id == user_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def authentication_session(
        self, token_hash: str, now: datetime
    ) -> tuple[AuthSession, User] | None:
        statement = (
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                User.status == "ACTIVE",
                User.deleted_at.is_(None),
            )
        )
        row = self.session.execute(statement).one_or_none()
        return None if row is None else (row[0], row[1])

    def session_by_hash(self, token_hash: str) -> AuthSession | None:
        return self.session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))

    def active_memberships(self, user_id: UUID) -> tuple[Membership, ...]:
        statement = (
            select(Membership)
            .join(Organization, Organization.id == Membership.organization_id)
            .outerjoin(Department, Department.id == Membership.department_id)
            .where(
                Membership.user_id == user_id,
                Membership.status == "ACTIVE",
                Membership.deleted_at.is_(None),
                Organization.status == "ACTIVE",
                Organization.deleted_at.is_(None),
                or_(
                    Membership.department_id.is_(None),
                    and_(Department.status == "ACTIVE", Department.deleted_at.is_(None)),
                ),
            )
            .order_by(Membership.organization_id, Membership.id)
        )
        return tuple(self.session.scalars(statement))

    def revoke_user_sessions(self, user_id: UUID, revoked_at: datetime) -> None:
        self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at, version=AuthSession.version + 1)
        )
