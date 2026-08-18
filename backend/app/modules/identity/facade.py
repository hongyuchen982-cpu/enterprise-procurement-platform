from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.identity import AccessEvaluationResult, AccessTarget, EffectiveAccessSnapshot
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.service import AccessService


class IdentityFacade:
    """Stable entry point for permission and data-scope checks."""

    def __init__(self, session: Session) -> None:
        self.service = AccessService(IdentityRepository(session))

    def effective_access(self, membership_id: UUID) -> EffectiveAccessSnapshot:
        return self.service.effective_access(membership_id)

    def evaluate(
        self, membership_id: UUID, permission_code: str, target: AccessTarget
    ) -> AccessEvaluationResult:
        return self.service.evaluate(membership_id, permission_code, target)
