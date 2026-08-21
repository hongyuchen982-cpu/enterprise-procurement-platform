from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.procurement import ProcurementRequestSnapshot
from app.core.database import get_session
from app.modules.approval.facade import ApprovalFacade
from app.modules.approval.service import (
    ApprovalConflictError,
    ApprovalNotFoundError,
    ApprovalStateError,
    InvalidApprovalReferenceError,
)
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.procurement.facade import ProcurementFacade

router = APIRouter(tags=["member-a:approval"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


def _require_organization_access(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    organization_id: UUID,
) -> None:
    decision = IdentityFacade(session).evaluate(
        membership.membership_id,
        permission_code,
        AccessTarget(organization_id=organization_id),
    )
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)


def _request_allowed(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    request: ProcurementRequestSnapshot,
) -> bool:
    identity = IdentityFacade(session)
    return all(
        identity.evaluate(
            membership.membership_id,
            permission_code,
            AccessTarget(
                organization_id=request.org_id,
                department_id=request.department_id,
                owner_user_id=request.requester_id,
                category_id=line.category_id,
            ),
        ).allowed
        for line in request.lines
    )


def _require_request_access(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    request: ProcurementRequestSnapshot,
) -> None:
    if not _request_allowed(session, membership, permission_code, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="permission or data scope not granted for every request line",
        )


def _raise_domain_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ApprovalNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="approval not found"
        ) from exc
    if isinstance(exc, (ApprovalConflictError, ApprovalStateError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post(
    "/approval-templates",
    response_model=ApiResponse[ApprovalTemplateSnapshot],
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: ApprovalTemplateCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ApprovalTemplateSnapshot]:
    _require_organization_access(
        session, membership, "approval.template.manage", payload.organization_id
    )
    try:
        value = ApprovalFacade(session).create_template(payload)
    except (
        ApprovalConflictError,
        ApprovalStateError,
        InvalidApprovalReferenceError,
        LookupError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("/approval-templates", response_model=ApiResponse[list[ApprovalTemplateSnapshot]])
def list_templates(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[ApprovalTemplateSnapshot]]:
    _require_organization_access(session, membership, "approval.instance.read", organization_id)
    values = list(ApprovalFacade(session).list_templates(organization_id))
    return ApiResponse(data=values, meta=_meta(request))


@router.post(
    "/approvals",
    response_model=ApiResponse[ApprovalInstanceSnapshot],
    status_code=status.HTTP_201_CREATED,
)
def start_approval(
    payload: ApprovalStart,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ApprovalInstanceSnapshot]:
    try:
        procurement_request = ProcurementFacade(session).get(payload.request_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="request not found") from exc
    _require_request_access(session, membership, "approval.instance.start", procurement_request)
    try:
        value = ApprovalFacade(session).start(payload)
    except (
        ApprovalNotFoundError,
        ApprovalConflictError,
        ApprovalStateError,
        InvalidApprovalReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("/approvals", response_model=ApiResponse[list[ApprovalInstanceSnapshot]])
def list_approvals(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[ApprovalInstanceSnapshot]]:
    values = [
        value
        for value in ApprovalFacade(session).list_instances(organization_id)
        if _request_allowed(
            session,
            membership,
            "approval.instance.read",
            value.request_snapshot,
        )
    ]
    return ApiResponse(data=values, meta=_meta(request))


@router.get("/approvals/{instance_id}", response_model=ApiResponse[ApprovalInstanceSnapshot])
def get_approval(
    instance_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ApprovalInstanceSnapshot]:
    try:
        value = ApprovalFacade(session).get(instance_id)
    except ApprovalNotFoundError as exc:
        _raise_domain_error(exc)
    _require_request_access(session, membership, "approval.instance.read", value.request_snapshot)
    return ApiResponse(data=value, meta=_meta(request))


@router.post(
    "/approvals/{instance_id}/decisions",
    response_model=ApiResponse[ApprovalInstanceSnapshot],
)
def decide_approval(
    instance_id: UUID,
    payload: ApprovalDecisionInput,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ApprovalInstanceSnapshot]:
    facade = ApprovalFacade(session)
    try:
        current = facade.get(instance_id)
    except ApprovalNotFoundError as exc:
        _raise_domain_error(exc)
    _require_request_access(session, membership, "approval.task.decide", current.request_snapshot)
    try:
        value = facade.decide(instance_id, membership.membership_id, payload)
    except (
        ApprovalNotFoundError,
        ApprovalConflictError,
        ApprovalStateError,
        InvalidApprovalReferenceError,
        LookupError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.post(
    "/approvals/{instance_id}/transfers",
    response_model=ApiResponse[ApprovalInstanceSnapshot],
)
def transfer_approval(
    instance_id: UUID,
    payload: ApprovalTransferInput,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ApprovalInstanceSnapshot]:
    facade = ApprovalFacade(session)
    try:
        current = facade.get(instance_id)
    except ApprovalNotFoundError as exc:
        _raise_domain_error(exc)
    _require_request_access(session, membership, "approval.task.decide", current.request_snapshot)
    try:
        value = facade.transfer(instance_id, membership.membership_id, payload)
    except (
        ApprovalNotFoundError,
        ApprovalConflictError,
        ApprovalStateError,
        InvalidApprovalReferenceError,
        LookupError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.post(
    "/approvals/{instance_id}/cancel",
    response_model=ApiResponse[ApprovalInstanceSnapshot],
)
def cancel_approval(
    instance_id: UUID,
    payload: ApprovalCancelInput,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ApprovalInstanceSnapshot]:
    facade = ApprovalFacade(session)
    try:
        current = facade.get(instance_id)
    except ApprovalNotFoundError as exc:
        _raise_domain_error(exc)
    _require_request_access(
        session, membership, "approval.instance.start", current.request_snapshot
    )
    try:
        value = facade.cancel(instance_id, payload)
    except (
        ApprovalNotFoundError,
        ApprovalConflictError,
        ApprovalStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))
