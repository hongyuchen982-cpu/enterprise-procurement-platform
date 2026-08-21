from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.identity import AccessEvaluationResult, AccessTarget, EffectiveAccessSnapshot
from app.contracts.organizations import (
    MembershipCreate,
    MembershipSnapshot,
    OrganizationCreate,
    OrganizationSnapshot,
    OrganizationTreeNode,
)
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.service import AccessService, OrganizationService


class IdentityFacade:
    """Stable entry point for permission and data-scope checks."""

    def __init__(self, session: Session) -> None:
        repository = IdentityRepository(session)
        self.service = AccessService(repository)
        self.organizations = OrganizationService(repository)

    def effective_access(self, membership_id: UUID) -> EffectiveAccessSnapshot:
        return self.service.effective_access(membership_id)

    def evaluate(
        self, membership_id: UUID, permission_code: str, target: AccessTarget
    ) -> AccessEvaluationResult:
        return self.service.evaluate(membership_id, permission_code, target)

    def create_organization(self, payload: OrganizationCreate) -> OrganizationSnapshot:
        return self.organizations.create_organization(payload)

    def organization(self, organization_id: UUID) -> OrganizationSnapshot:
        return self.organizations.organization(organization_id)

    def organization_tree(self, root_id: UUID) -> OrganizationTreeNode:
        return self.organizations.organization_tree(root_id)

    def create_membership(self, payload: MembershipCreate) -> MembershipSnapshot:
        return self.organizations.create_membership(payload)

    def membership(self, membership_id: UUID) -> MembershipSnapshot:
        return self.organizations.membership(membership_id)

    def is_descendant_or_self(self, organization_id: UUID, ancestor_id: UUID) -> bool:
        return self.organizations.is_descendant_or_self(organization_id, ancestor_id)
