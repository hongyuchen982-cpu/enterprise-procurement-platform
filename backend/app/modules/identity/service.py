from uuid import UUID

from app.contracts.identity import (
    AccessEvaluationResult,
    AccessTarget,
    DataScopeGrantSnapshot,
    DataScopeType,
    EffectiveAccessSnapshot,
)
from app.modules.identity.repository import IdentityRepository


class MembershipNotActiveError(LookupError):
    pass


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
