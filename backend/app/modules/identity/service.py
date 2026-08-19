from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.contracts.identity import (
    AccessEvaluationResult,
    AccessTarget,
    DataScopeGrantSnapshot,
    DataScopeType,
    EffectiveAccessSnapshot,
)
from app.contracts.organizations import (
    MembershipCreate,
    MembershipSnapshot,
    OrganizationCreate,
    OrganizationSnapshot,
    OrganizationStatus,
    OrganizationTreeNode,
)
from app.modules.identity.models import Membership, Organization
from app.modules.identity.repository import IdentityRepository


class MembershipNotActiveError(LookupError):
    pass


class OrganizationNotFoundError(LookupError):
    pass


class OrganizationConflictError(ValueError):
    pass


class InvalidOrganizationRelationshipError(ValueError):
    pass


class OrganizationService:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    def create_organization(self, payload: OrganizationCreate) -> OrganizationSnapshot:
        parent = self.repository.organization(payload.parent_id)
        if parent is None or parent.status != OrganizationStatus.ACTIVE:
            raise OrganizationNotFoundError(str(payload.parent_id))
        code = payload.code.strip().upper()
        if self.repository.organization_by_code(code) is not None:
            raise OrganizationConflictError(f"organization code already exists: {code}")
        organization = Organization(
            parent_id=parent.id,
            code=code,
            name=payload.name.strip(),
        )
        self.repository.add(organization)
        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise OrganizationConflictError(f"organization code already exists: {code}") from exc
        return self._organization_snapshot(organization)

    def organization(self, organization_id: UUID) -> OrganizationSnapshot:
        organization = self.repository.organization(organization_id)
        if organization is None:
            raise OrganizationNotFoundError(str(organization_id))
        return self._organization_snapshot(organization)

    def organization_tree(self, root_id: UUID) -> OrganizationTreeNode:
        root = self.repository.organization(root_id)
        if root is None:
            raise OrganizationNotFoundError(str(root_id))
        return self._tree_node(root, set())

    def create_membership(self, payload: MembershipCreate) -> MembershipSnapshot:
        user = self.repository.user(payload.user_id)
        organization = self.repository.organization(payload.organization_id)
        if (
            user is None
            or organization is None
            or user.status != OrganizationStatus.ACTIVE
            or organization.status != OrganizationStatus.ACTIVE
        ):
            raise OrganizationNotFoundError("user or organization not found")
        if self.repository.membership_for_user_and_organization(user.id, organization.id):
            raise OrganizationConflictError("membership already exists")
        if payload.department_id is not None:
            department = self.repository.organization(payload.department_id)
            if (
                department is None
                or department.status != OrganizationStatus.ACTIVE
                or not self.repository.is_descendant_or_self(department.id, organization.id)
            ):
                raise InvalidOrganizationRelationshipError(
                    "department must belong to the membership organization tree"
                )
        membership = Membership(
            user_id=user.id,
            organization_id=organization.id,
            department_id=payload.department_id,
        )
        self.repository.add(membership)
        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise OrganizationConflictError("membership already exists") from exc
        return MembershipSnapshot(
            membership_id=membership.id,
            user_id=membership.user_id,
            organization_id=membership.organization_id,
            department_id=membership.department_id,
            status=OrganizationStatus(membership.status),
            version=membership.version,
        )

    def _tree_node(self, organization: Organization, visited: set[UUID]) -> OrganizationTreeNode:
        if organization.id in visited:
            raise InvalidOrganizationRelationshipError("organization hierarchy contains a cycle")
        path = visited | {organization.id}
        children = tuple(
            self._tree_node(child, path)
            for child in self.repository.organization_children(organization.id)
        )
        snapshot = self._organization_snapshot(organization)
        return OrganizationTreeNode(**snapshot.model_dump(), children=children)

    @staticmethod
    def _organization_snapshot(organization: Organization) -> OrganizationSnapshot:
        return OrganizationSnapshot(
            organization_id=organization.id,
            parent_id=organization.parent_id,
            code=organization.code,
            name=organization.name,
            status=OrganizationStatus(organization.status),
            version=organization.version,
        )


class AccessService:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    def effective_access(self, membership_id: UUID) -> EffectiveAccessSnapshot:
        membership = self.repository.get_active_membership(membership_id)
        if membership is None:
            raise MembershipNotActiveError(str(membership_id))
        grants = tuple(
            DataScopeGrantSnapshot(
                scope_type=DataScopeType(grant.scope_type), scope_ref=grant.scope_ref
            )
            for grant in self.repository.scope_grants(membership_id)
        )
        return EffectiveAccessSnapshot(
            membership_id=membership.id,
            user_id=membership.user_id,
            organization_id=membership.organization_id,
            department_id=membership.department_id,
            permission_codes=self.repository.permission_codes(membership_id),
            data_scopes=grants,
        )

    def evaluate(
        self, membership_id: UUID, permission_code: str, target: AccessTarget
    ) -> AccessEvaluationResult:
        access = self.effective_access(membership_id)
        if permission_code not in access.permission_codes:
            return AccessEvaluationResult(allowed=False, reason="permission_not_granted")
        for grant in access.data_scopes:
            if self._scope_matches(grant, access, target):
                return AccessEvaluationResult(allowed=True, reason="permission_and_scope_granted")
        return AccessEvaluationResult(allowed=False, reason="data_scope_not_granted")

    def _scope_matches(
        self,
        grant: DataScopeGrantSnapshot,
        access: EffectiveAccessSnapshot,
        target: AccessTarget,
    ) -> bool:
        if grant.scope_type is DataScopeType.ALL:
            return True
        if grant.scope_type is DataScopeType.SELF:
            return target.owner_user_id == access.user_id
        if grant.scope_type is DataScopeType.DEPARTMENT:
            expected = grant.scope_ref or access.department_id
            return expected is not None and target.department_id == expected
        if grant.scope_type is DataScopeType.ORGANIZATION:
            expected = grant.scope_ref or access.organization_id
            return target.organization_id == expected
        if grant.scope_type is DataScopeType.ORGANIZATION_TREE:
            ancestor = grant.scope_ref or access.organization_id
            return target.organization_id is not None and self.repository.is_descendant_or_self(
                target.organization_id, ancestor
            )
        if grant.scope_type is DataScopeType.CATEGORY:
            return grant.scope_ref is not None and target.category_id == grant.scope_ref
        if grant.scope_type is DataScopeType.SUPPLIER:
            return grant.scope_ref is not None and target.supplier_id == grant.scope_ref
        return False
