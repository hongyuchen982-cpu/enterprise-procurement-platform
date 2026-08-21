from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.approval import (
    ApprovalCancelInput,
    ApprovalDecisionInput,
    ApprovalInstanceSnapshot,
    ApprovalStart,
    ApprovalTemplateCreate,
    ApprovalTemplateSnapshot,
    ApprovalTransferInput,
)
from app.modules.approval.repository import ApprovalRepository
from app.modules.approval.service import ApprovalService
from app.modules.identity.facade import IdentityFacade
from app.modules.procurement.facade import ProcurementFacade


class ApprovalFacade:
    def __init__(self, session: Session) -> None:
        self.service = ApprovalService(
            ApprovalRepository(session),
            IdentityFacade(session),
            ProcurementFacade(session),
        )

    def create_template(self, payload: ApprovalTemplateCreate) -> ApprovalTemplateSnapshot:
        return self.service.create_template(payload)

    def list_templates(self, organization_id: UUID) -> tuple[ApprovalTemplateSnapshot, ...]:
        return self.service.list_templates(organization_id)

    def start(self, payload: ApprovalStart) -> ApprovalInstanceSnapshot:
        return self.service.start(payload)

    def get(self, instance_id: UUID) -> ApprovalInstanceSnapshot:
        return self.service.get(instance_id)

    def list_instances(self, organization_id: UUID) -> tuple[ApprovalInstanceSnapshot, ...]:
        return self.service.list_instances(organization_id)

    def decide(
        self,
        instance_id: UUID,
        actor_membership_id: UUID,
        payload: ApprovalDecisionInput,
    ) -> ApprovalInstanceSnapshot:
        return self.service.decide(instance_id, actor_membership_id, payload)

    def transfer(
        self,
        instance_id: UUID,
        actor_membership_id: UUID,
        payload: ApprovalTransferInput,
    ) -> ApprovalInstanceSnapshot:
        return self.service.transfer(instance_id, actor_membership_id, payload)

    def cancel(self, instance_id: UUID, payload: ApprovalCancelInput) -> ApprovalInstanceSnapshot:
        return self.service.cancel(instance_id, payload)
