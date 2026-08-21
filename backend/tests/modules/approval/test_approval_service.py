from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.contracts.approval import (
    ApprovalDecision,
    ApprovalDecisionInput,
    ApprovalInstanceStatus,
    ApprovalStart,
    ApprovalTemplateCreate,
    ApprovalTemplateStepInput,
    ApprovalTransferInput,
)
from app.contracts.procurement import (
    ProcurementRequestCreate,
    ProcurementRequestLineInput,
    ProcurementRequestStatus,
)
from app.core.database import Base
from app.modules.approval.repository import ApprovalRepository
from app.modules.approval.service import (
    ApprovalConflictError,
    ApprovalService,
    ApprovalStateError,
)
from app.modules.identity.facade import IdentityFacade
from app.modules.identity.models import Membership, Organization, User
from app.modules.master_data.models import Category, Material, Unit
from app.modules.procurement.facade import ProcurementFacade


def test_sequential_approval_updates_request_atomically() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        requester = User(login_name="requester", display_name="Requester")
        approver_one = User(login_name="approver-1", display_name="Approver One")
        approver_two = User(login_name="approver-2", display_name="Approver Two")
        outsider = User(login_name="outsider", display_name="Outsider")
        session.add_all([organization, requester, approver_one, approver_two, outsider])
        session.flush()
        memberships = [
            Membership(user_id=user.id, organization_id=organization.id)
            for user in (requester, approver_one, approver_two, outsider)
        ]
        category = Category(organization_id=organization.id, code="IT", name="IT")
        unit = Unit(code="EA", name="Each")
        session.add_all([*memberships, category, unit])
        session.flush()
        material = Material(
            organization_id=organization.id,
            code="LAPTOP",
            name="Laptop",
            category_id=category.id,
            unit_code=unit.code,
        )
        session.add(material)
        session.commit()

        procurement = ProcurementFacade(session)
        request = procurement.create(
            ProcurementRequestCreate(
                org_id=organization.id,
                department_id=organization.id,
                currency="CNY",
                required_date=date.today() + timedelta(days=30),
                purpose="Laptops",
                lines=[
                    ProcurementRequestLineInput(
                        material_id=material.id,
                        category_id=category.id,
                        description="Laptop",
                        quantity=Decimal("2"),
                        unit="EA",
                        estimated_unit_price=Decimal("5000"),
                    )
                ],
            ),
            memberships[0].id,
            requester.id,
        )
        request = procurement.submit(request.request_id, request.version)

        approval = ApprovalService(
            ApprovalRepository(session), IdentityFacade(session), procurement
        )
        template = approval.create_template(
            ApprovalTemplateCreate(
                organization_id=organization.id,
                code="STANDARD",
                name="Standard approval",
                steps=[
                    ApprovalTemplateStepInput(
                        name="Department approval",
                        approver_membership_id=memberships[1].id,
                    ),
                    ApprovalTemplateStepInput(
                        name="Finance approval",
                        approver_membership_id=memberships[2].id,
                    ),
                ],
            )
        )
        instance = approval.start(
            ApprovalStart(
                request_id=request.request_id,
                template_id=template.template_id,
                expected_request_version=request.version,
            )
        )

        assert instance.status is ApprovalInstanceStatus.PENDING
        assert [node.status for node in instance.nodes] == ["PENDING", "WAITING"]
        assert procurement.get(request.request_id).status is ProcurementRequestStatus.IN_APPROVAL

        with pytest.raises(ApprovalStateError, match="not assigned"):
            approval.decide(
                instance.instance_id,
                memberships[3].id,
                ApprovalDecisionInput(
                    decision=ApprovalDecision.APPROVE,
                    expected_version=instance.version,
                ),
            )

        instance = approval.transfer(
            instance.instance_id,
            memberships[1].id,
            ApprovalTransferInput(
                target_membership_id=memberships[3].id,
                expected_version=instance.version,
                comment="Delegated",
            ),
        )
        assert instance.nodes[0].approver_membership_id == memberships[3].id
        assert [action.action for action in instance.actions] == ["TRANSFER"]

        instance = approval.decide(
            instance.instance_id,
            memberships[3].id,
            ApprovalDecisionInput(
                decision=ApprovalDecision.APPROVE,
                expected_version=instance.version,
                comment="Approved",
            ),
        )
        assert instance.current_step_no == 2
        assert [node.status for node in instance.nodes] == ["APPROVED", "PENDING"]
        assert [action.action for action in instance.actions] == ["TRANSFER", "APPROVE"]

        with pytest.raises(ApprovalConflictError, match="version mismatch"):
            approval.decide(
                instance.instance_id,
                memberships[2].id,
                ApprovalDecisionInput(
                    decision=ApprovalDecision.APPROVE,
                    expected_version=1,
                ),
            )

        instance = approval.decide(
            instance.instance_id,
            memberships[2].id,
            ApprovalDecisionInput(
                decision=ApprovalDecision.APPROVE,
                expected_version=instance.version,
            ),
        )
        assert instance.status is ApprovalInstanceStatus.APPROVED
        assert [action.action for action in instance.actions] == [
            "TRANSFER",
            "APPROVE",
            "APPROVE",
        ]
        assert procurement.get(request.request_id).status is ProcurementRequestStatus.APPROVED
    engine.dispose()


def test_rejection_skips_remaining_nodes_and_rejects_request() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="ROOT", name="Root")
        requester = User(login_name="requester", display_name="Requester")
        approver = User(login_name="approver", display_name="Approver")
        session.add_all([organization, requester, approver])
        session.flush()
        requester_membership = Membership(user_id=requester.id, organization_id=organization.id)
        approver_membership = Membership(user_id=approver.id, organization_id=organization.id)
        category = Category(organization_id=organization.id, code="IT", name="IT")
        unit = Unit(code="EA", name="Each")
        session.add_all([requester_membership, approver_membership, category, unit])
        session.flush()
        material = Material(
            organization_id=organization.id,
            code="LAPTOP",
            name="Laptop",
            category_id=category.id,
            unit_code=unit.code,
        )
        session.add(material)
        session.commit()
        procurement = ProcurementFacade(session)
        request = procurement.create(
            ProcurementRequestCreate(
                org_id=organization.id,
                department_id=organization.id,
                currency="CNY",
                required_date=date.today() + timedelta(days=10),
                purpose="Laptop",
                lines=[
                    ProcurementRequestLineInput(
                        material_id=material.id,
                        category_id=category.id,
                        description="Laptop",
                        quantity=Decimal("1"),
                        unit="EA",
                    )
                ],
            ),
            requester_membership.id,
            requester.id,
        )
        request = procurement.submit(request.request_id, request.version)
        approval = ApprovalService(
            ApprovalRepository(session), IdentityFacade(session), procurement
        )
        template = approval.create_template(
            ApprovalTemplateCreate(
                organization_id=organization.id,
                code="REJECT",
                name="Rejection path",
                steps=[
                    ApprovalTemplateStepInput(
                        name="First", approver_membership_id=approver_membership.id
                    ),
                    ApprovalTemplateStepInput(
                        name="Second", approver_membership_id=approver_membership.id
                    ),
                ],
            )
        )
        instance = approval.start(
            ApprovalStart(
                request_id=request.request_id,
                template_id=template.template_id,
                expected_request_version=request.version,
            )
        )
        with pytest.raises(ApprovalStateError, match="comment"):
            approval.decide(
                instance.instance_id,
                approver_membership.id,
                ApprovalDecisionInput(
                    decision=ApprovalDecision.REJECT,
                    expected_version=instance.version,
                ),
            )
        instance = approval.decide(
            instance.instance_id,
            approver_membership.id,
            ApprovalDecisionInput(
                decision=ApprovalDecision.REJECT,
                expected_version=instance.version,
                comment="Insufficient justification",
            ),
        )

        assert instance.status is ApprovalInstanceStatus.REJECTED
        assert [node.status for node in instance.nodes] == ["REJECTED", "SKIPPED"]
        assert procurement.get(request.request_id).status is ProcurementRequestStatus.REJECTED
    engine.dispose()
