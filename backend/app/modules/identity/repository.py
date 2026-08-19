from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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


class IdentityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_membership(self, membership_id: UUID) -> Membership | None:
        statement = (
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(
                Membership.id == membership_id,
                Membership.status == "ACTIVE",
                User.status == "ACTIVE",
                Organization.status == "ACTIVE",
                Membership.deleted_at.is_(None),
                User.deleted_at.is_(None),
                Organization.deleted_at.is_(None),
            )
        )
        return self.session.scalar(statement)

    def permission_codes(self, membership_id: UUID) -> frozenset[str]:
        statement = (
            select(RolePermission.permission_code)
            .join(Role, Role.id == RolePermission.role_id)
            .join(MembershipRole, MembershipRole.role_id == Role.id)
            .join(Membership, Membership.id == MembershipRole.membership_id)
            .join(Permission, Permission.code == RolePermission.permission_code)
            .where(
                MembershipRole.membership_id == membership_id,
                Role.organization_id == Membership.organization_id,
                Role.status == "ACTIVE",
                Role.deleted_at.is_(None),
                Permission.deleted_at.is_(None),
            )
            .distinct()
        )
        return frozenset(self.session.scalars(statement))

    def scope_grants(self, membership_id: UUID) -> tuple[RoleScopeGrant, ...]:
        statement = (
            select(RoleScopeGrant)
            .join(Role, Role.id == RoleScopeGrant.role_id)
            .join(MembershipRole, MembershipRole.role_id == Role.id)
            .join(Membership, Membership.id == MembershipRole.membership_id)
            .where(
                MembershipRole.membership_id == membership_id,
                Role.organization_id == Membership.organization_id,
                Role.status == "ACTIVE",
                Role.deleted_at.is_(None),
                RoleScopeGrant.deleted_at.is_(None),
            )
            .order_by(RoleScopeGrant.scope_type, RoleScopeGrant.scope_ref)
        )
        return tuple(self.session.scalars(statement))

    def is_descendant_or_self(self, organization_id: UUID, ancestor_id: UUID) -> bool:
        current_id: UUID | None = organization_id
        visited: set[UUID] = set()
        while current_id is not None and current_id not in visited:
            if current_id == ancestor_id:
                return True
            visited.add(current_id)
            current_id = self.session.scalar(
                select(Organization.parent_id).where(
                    Organization.id == current_id, Organization.deleted_at.is_(None)
                )
            )
        return False
