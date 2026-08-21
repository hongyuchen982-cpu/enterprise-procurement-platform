from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.contracts.approval import (
    ApprovalActionSnapshot,
    ApprovalActionType,
    ApprovalCancelInput,
    ApprovalDecision,
    ApprovalDecisionInput,
    ApprovalInstanceSnapshot,
    ApprovalInstanceStatus,
    ApprovalNodeSnapshot,
    ApprovalNodeStatus,
    ApprovalRecordStatus,
    ApprovalStart,
    ApprovalTemplateCreate,
    ApprovalTemplateSnapshot,
    ApprovalTemplateStepSnapshot,
    ApprovalTransferInput,
)
from app.contracts.organizations import OrganizationStatus
from app.contracts.procurement import ProcurementRequestSnapshot, ProcurementRequestStatus
from app.core.database import utc_now
from app.modules.approval.models import (
    ApprovalAction,
    ApprovalInstance,
    ApprovalInstanceRecordStatus,
    ApprovalNode,
    ApprovalNodeRecordStatus,
    ApprovalTemplate,
    ApprovalTemplateRecordStatus,
    ApprovalTemplateStep,
)
from app.modules.approval.repository import ApprovalRepository
from app.modules.identity.facade import IdentityFacade
from app.modules.procurement.facade import ProcurementFacade


class ApprovalNotFoundError(LookupError):
    pass


class ApprovalConflictError(ValueError):
    pass


class ApprovalStateError(ValueError):
    pass


class InvalidApprovalReferenceError(ValueError):
    pass


class ApprovalService:
    def __init__(
        self,
        repository: ApprovalRepository,
        identity: IdentityFacade,
        procurement: ProcurementFacade,
    ) -> None:
        self.repository = repository
        self.identity = identity
        self.procurement = procurement

    def create_template(self, payload: ApprovalTemplateCreate) -> ApprovalTemplateSnapshot:
        organization = self.identity.organization(payload.organization_id)
        if organization.status is not OrganizationStatus.ACTIVE:
            raise InvalidApprovalReferenceError("active organization not found")
        if self.repository.template_by_code(payload.organization_id, payload.code):
            raise ApprovalConflictError(f"template code already exists: {payload.code}")
        steps: list[ApprovalTemplateStep] = []
        for step_no, payload_step in enumerate(payload.steps, start=1):
            membership = self.identity.membership(payload_step.approver_membership_id)
            if membership.organization_id != payload.organization_id:
                raise InvalidApprovalReferenceError(
                    f"step {step_no} approver must belong to the template organization"
                )
            steps.append(
                ApprovalTemplateStep(
                    step_no=step_no,
                    name=payload_step.name,
                    approver_membership_id=payload_step.approver_membership_id,
                )
            )
        template = ApprovalTemplate(
            organization_id=payload.organization_id,
            code=payload.code,
            name=payload.name,
            steps=steps,
        )
        self.repository.add(template)
        self._commit(f"template code already exists: {payload.code}")
        return self.template_snapshot(template)

    def list_templates(self, organization_id: UUID) -> tuple[ApprovalTemplateSnapshot, ...]:
        return tuple(
            self.template_snapshot(template)
            for template in self.repository.templates(organization_id)
        )

    def start(self, payload: ApprovalStart) -> ApprovalInstanceSnapshot:
        if self.repository.instance_for_request(payload.request_id):
            raise ApprovalConflictError("request already has an approval instance")
        template = self._template(payload.template_id)
        if template.status != ApprovalTemplateRecordStatus.ACTIVE:
            raise ApprovalStateError("approval template is disabled")
        if not template.steps:
            raise ApprovalStateError("approval template has no steps")
        try:
            request = self.procurement.get(payload.request_id)
        except (LookupError, ValueError) as exc:
            raise InvalidApprovalReferenceError("procurement request not found") from exc
        if request.status is not ProcurementRequestStatus.SUBMITTED:
            raise ApprovalStateError("only submitted requests can start approval")
        if request.version != payload.expected_request_version:
            raise ApprovalConflictError(
                f"request version mismatch: expected {payload.expected_request_version}, "
                f"current {request.version}"
            )
        if template.organization_id != request.org_id:
            raise InvalidApprovalReferenceError(
                "template and request must belong to the same organization"
            )
        nodes = [
            ApprovalNode(
                step_no=step.step_no,
                name=step.name,
                approver_membership_id=step.approver_membership_id,
                status=(
                    ApprovalNodeRecordStatus.PENDING
                    if step.step_no == 1
                    else ApprovalNodeRecordStatus.WAITING
                ),
            )
            for step in template.steps
        ]
        instance = ApprovalInstance(
            organization_id=request.org_id,
            request_id=request.request_id,
            template_id=template.id,
            current_step_no=1,
            request_version=request.version + 1,
            request_snapshot=request.model_dump(mode="json"),
            nodes=nodes,
        )
        self.repository.add(instance)
        try:
            self.procurement.begin_approval(request.request_id, request.version)
        except (LookupError, ValueError) as exc:
            self.repository.rollback()
            raise ApprovalConflictError(str(exc)) from exc
        return self.instance_snapshot(instance)

    def get(self, instance_id: UUID) -> ApprovalInstanceSnapshot:
        return self.instance_snapshot(self._instance(instance_id))

    def list_instances(self, organization_id: UUID) -> tuple[ApprovalInstanceSnapshot, ...]:
        return tuple(
            self.instance_snapshot(instance)
            for instance in self.repository.instances(organization_id)
        )

    def decide(
        self,
        instance_id: UUID,
        actor_membership_id: UUID,
        payload: ApprovalDecisionInput,
    ) -> ApprovalInstanceSnapshot:
        instance = self._instance(instance_id)
        if instance.version != payload.expected_version:
            raise ApprovalConflictError(
                f"version mismatch: expected {payload.expected_version}, current {instance.version}"
            )
        if instance.status != ApprovalInstanceRecordStatus.PENDING:
            raise ApprovalStateError("approval instance is already complete")
        actor = self.identity.membership(actor_membership_id)
        if actor.organization_id != instance.organization_id:
            raise InvalidApprovalReferenceError("approver organization does not match")
        node = next(
            (
                candidate
                for candidate in instance.nodes
                if candidate.step_no == instance.current_step_no
            ),
            None,
        )
        if node is None or node.status != ApprovalNodeRecordStatus.PENDING:
            raise ApprovalStateError("current approval node is not pending")
        if node.approver_membership_id != actor_membership_id:
            raise ApprovalStateError("membership is not assigned to the current approval node")
        if payload.decision is ApprovalDecision.REJECT and payload.comment is None:
            raise ApprovalStateError("rejection comment is required")
        node.decision_comment = payload.comment
        node.decided_by_membership_id = actor_membership_id
        node.decided_at = utc_now()
        if payload.decision is ApprovalDecision.REJECT:
            node.status = ApprovalNodeRecordStatus.REJECTED
            self.repository.add_action(
                ApprovalAction(
                    instance=instance,
                    node_id=node.id,
                    action=ApprovalActionType.REJECT,
                    actor_membership_id=actor_membership_id,
                    comment=payload.comment,
                )
            )
            for remaining in instance.nodes:
                if remaining.step_no > node.step_no:
                    remaining.status = ApprovalNodeRecordStatus.SKIPPED
            instance.status = ApprovalInstanceRecordStatus.REJECTED
            instance.request_version += 1
            self._complete_request(instance, approved=False)
            return self.instance_snapshot(instance)
        node.status = ApprovalNodeRecordStatus.APPROVED
        self.repository.add_action(
            ApprovalAction(
                instance=instance,
                node_id=node.id,
                action=ApprovalActionType.APPROVE,
                actor_membership_id=actor_membership_id,
                comment=payload.comment,
            )
        )
        next_node = next(
            (candidate for candidate in instance.nodes if candidate.step_no == node.step_no + 1),
            None,
        )
        if next_node is not None:
            next_node.status = ApprovalNodeRecordStatus.PENDING
            instance.current_step_no = next_node.step_no
            self._commit("approval was updated concurrently")
            return self.instance_snapshot(instance)
        instance.status = ApprovalInstanceRecordStatus.APPROVED
        instance.request_version += 1
        self._complete_request(instance, approved=True)
        return self.instance_snapshot(instance)

    def transfer(
        self,
        instance_id: UUID,
        actor_membership_id: UUID,
        payload: ApprovalTransferInput,
    ) -> ApprovalInstanceSnapshot:
        instance = self._instance(instance_id)
        if instance.version != payload.expected_version:
            raise ApprovalConflictError(
                f"version mismatch: expected {payload.expected_version}, current {instance.version}"
            )
        if instance.status != ApprovalInstanceRecordStatus.PENDING:
            raise ApprovalStateError("approval instance is already complete")
        node = next(
            (
                candidate
                for candidate in instance.nodes
                if candidate.step_no == instance.current_step_no
            ),
            None,
        )
        if node is None or node.status != ApprovalNodeRecordStatus.PENDING:
            raise ApprovalStateError("current approval node is not pending")
        if node.approver_membership_id != actor_membership_id:
            raise ApprovalStateError("membership is not assigned to the current approval node")
        if payload.target_membership_id == actor_membership_id:
            raise ApprovalStateError("approval node is already assigned to that membership")
        try:
            target = self.identity.membership(payload.target_membership_id)
        except LookupError as exc:
            raise InvalidApprovalReferenceError("active target membership not found") from exc
        if target.organization_id != instance.organization_id:
            raise InvalidApprovalReferenceError(
                "target membership must belong to the approval organization"
            )
        self.repository.add_action(
            ApprovalAction(
                instance=instance,
                node_id=node.id,
                action=ApprovalActionType.TRANSFER,
                actor_membership_id=actor_membership_id,
                target_membership_id=payload.target_membership_id,
                comment=payload.comment,
            )
        )
        node.approver_membership_id = payload.target_membership_id
        instance.updated_at = utc_now()
        self._commit("approval was updated concurrently")
        return self.instance_snapshot(instance)

    def cancel(self, instance_id: UUID, payload: ApprovalCancelInput) -> ApprovalInstanceSnapshot:
        instance = self._instance(instance_id)
        if instance.version != payload.expected_version:
            raise ApprovalConflictError(
                f"version mismatch: expected {payload.expected_version}, current {instance.version}"
            )
        if instance.status != ApprovalInstanceRecordStatus.PENDING:
            raise ApprovalStateError("approval instance is already complete")
        if instance.actions:
            raise ApprovalStateError("approval cannot be cancelled after the first action")
        instance.status = ApprovalInstanceRecordStatus.CANCELLED
        for node in instance.nodes:
            node.status = ApprovalNodeRecordStatus.SKIPPED
        instance.request_version += 1
        try:
            self.procurement.cancel_approval(instance.request_id, instance.request_version - 1)
        except (LookupError, ValueError) as exc:
            self.repository.rollback()
            raise ApprovalConflictError(str(exc)) from exc
        return self.instance_snapshot(instance)

    def _complete_request(self, instance: ApprovalInstance, approved: bool) -> None:
        try:
            self.procurement.complete_approval(
                instance.request_id,
                instance.request_version - 1,
                approved,
            )
        except (LookupError, ValueError) as exc:
            self.repository.rollback()
            raise ApprovalConflictError(str(exc)) from exc

    def _template(self, template_id: UUID) -> ApprovalTemplate:
        template = self.repository.template(template_id)
        if template is None:
            raise ApprovalNotFoundError(str(template_id))
        return template

    def _instance(self, instance_id: UUID) -> ApprovalInstance:
        instance = self.repository.instance(instance_id)
        if instance is None:
            raise ApprovalNotFoundError(str(instance_id))
        return instance

    def _commit(self, message: str) -> None:
        try:
            self.repository.commit()
        except (IntegrityError, StaleDataError) as exc:
            self.repository.rollback()
            raise ApprovalConflictError(message) from exc

    @staticmethod
    def template_snapshot(template: ApprovalTemplate) -> ApprovalTemplateSnapshot:
        return ApprovalTemplateSnapshot(
            template_id=template.id,
            organization_id=template.organization_id,
            code=template.code,
            name=template.name,
            status=ApprovalRecordStatus(template.status),
            steps=[
                ApprovalTemplateStepSnapshot(
                    step_id=step.id,
                    step_no=step.step_no,
                    name=step.name,
                    approver_membership_id=step.approver_membership_id,
                )
                for step in template.steps
            ],
            version=template.version,
        )

    @staticmethod
    def instance_snapshot(instance: ApprovalInstance) -> ApprovalInstanceSnapshot:
        return ApprovalInstanceSnapshot(
            instance_id=instance.id,
            organization_id=instance.organization_id,
            request_id=instance.request_id,
            template_id=instance.template_id,
            status=ApprovalInstanceStatus(instance.status),
            current_step_no=instance.current_step_no,
            request_version=instance.request_version,
            request_snapshot=ProcurementRequestSnapshot.model_validate(instance.request_snapshot),
            nodes=[
                ApprovalNodeSnapshot(
                    node_id=node.id,
                    step_no=node.step_no,
                    name=node.name,
                    approver_membership_id=node.approver_membership_id,
                    status=ApprovalNodeStatus(node.status),
                    decision_comment=node.decision_comment,
                    decided_by_membership_id=node.decided_by_membership_id,
                    decided_at=node.decided_at,
                )
                for node in instance.nodes
            ],
            actions=[
                ApprovalActionSnapshot(
                    action_id=action.id,
                    node_id=action.node_id,
                    action=ApprovalActionType(action.action),
                    actor_membership_id=action.actor_membership_id,
                    target_membership_id=action.target_membership_id,
                    comment=action.comment,
                    created_at=action.created_at,
                )
                for action in instance.actions
            ],
            version=instance.version,
        )
