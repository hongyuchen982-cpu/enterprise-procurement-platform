from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.approval.models import ApprovalAction, ApprovalInstance, ApprovalTemplate


class ApprovalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def template(self, template_id: UUID) -> ApprovalTemplate | None:
        return self.session.scalar(
            select(ApprovalTemplate)
            .options(selectinload(ApprovalTemplate.steps))
            .where(
                ApprovalTemplate.id == template_id,
                ApprovalTemplate.deleted_at.is_(None),
            )
        )

    def template_by_code(self, organization_id: UUID, code: str) -> ApprovalTemplate | None:
        return self.session.scalar(
            select(ApprovalTemplate).where(
                ApprovalTemplate.organization_id == organization_id,
                ApprovalTemplate.code == code,
                ApprovalTemplate.deleted_at.is_(None),
            )
        )

    def templates(self, organization_id: UUID) -> tuple[ApprovalTemplate, ...]:
        statement = (
            select(ApprovalTemplate)
            .options(selectinload(ApprovalTemplate.steps))
            .where(
                ApprovalTemplate.organization_id == organization_id,
                ApprovalTemplate.deleted_at.is_(None),
            )
            .order_by(ApprovalTemplate.code)
        )
        return tuple(self.session.scalars(statement))

    def instance(self, instance_id: UUID) -> ApprovalInstance | None:
        return self.session.scalar(
            select(ApprovalInstance)
            .options(
                selectinload(ApprovalInstance.nodes),
                selectinload(ApprovalInstance.actions),
            )
            .where(ApprovalInstance.id == instance_id)
        )

    def instance_for_request(self, request_id: UUID) -> ApprovalInstance | None:
        return self.session.scalar(
            select(ApprovalInstance)
            .options(
                selectinload(ApprovalInstance.nodes),
                selectinload(ApprovalInstance.actions),
            )
            .where(ApprovalInstance.request_id == request_id)
        )

    def instances(self, organization_id: UUID) -> tuple[ApprovalInstance, ...]:
        statement = (
            select(ApprovalInstance)
            .options(
                selectinload(ApprovalInstance.nodes),
                selectinload(ApprovalInstance.actions),
            )
            .where(ApprovalInstance.organization_id == organization_id)
            .order_by(ApprovalInstance.created_at.desc())
        )
        return tuple(self.session.scalars(statement))

    def add(self, value: ApprovalTemplate | ApprovalInstance) -> None:
        self.session.add(value)

    def add_action(self, value: ApprovalAction) -> None:
        self.session.add(value)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
