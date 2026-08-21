from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.procurement import (
    ProcurementRequestCreate,
    ProcurementRequestDeleteResult,
    ProcurementRequestLineInput,
    ProcurementRequestSnapshot,
    ProcurementRequestTransition,
    ProcurementRequestUpdate,
)
from app.core.database import get_session
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.procurement.facade import ProcurementFacade
from app.modules.procurement.service import (
    InvalidProcurementReferenceError,
    ProcurementRequestConflictError,
    ProcurementRequestNotFoundError,
    ProcurementRequestStateError,
)

router = APIRouter(prefix="/procurement-requests", tags=["member-a:procurement"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


def _allowed(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    organization_id: UUID,
    department_id: UUID,
    owner_user_id: UUID,
    category_ids: list[UUID],
) -> bool:
    identity = IdentityFacade(session)
    return all(
        identity.evaluate(
            membership.membership_id,
            permission_code,
            AccessTarget(
                organization_id=organization_id,
                department_id=department_id,
                owner_user_id=owner_user_id,
                category_id=category_id,
            ),
        ).allowed
        for category_id in category_ids
    )


def _require_payload_access(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    organization_id: UUID,
    department_id: UUID,
    owner_user_id: UUID,
    lines: list[ProcurementRequestLineInput],
) -> None:
    if not _allowed(
        session,
        membership,
        permission_code,
        organization_id,
        department_id,
        owner_user_id,
        [line.category_id for line in lines],
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="permission or data scope not granted for every request line",
        )


def _require_snapshot_access(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    value: ProcurementRequestSnapshot,
) -> None:
    if not _allowed(
        session,
        membership,
        permission_code,
        value.org_id,
        value.department_id,
        value.requester_id,
        [line.category_id for line in value.lines],
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="permission or data scope not granted for every request line",
        )


def _raise_domain_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProcurementRequestNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="request not found"
        ) from exc
    if isinstance(exc, (ProcurementRequestConflictError, ProcurementRequestStateError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("", response_model=ApiResponse[ProcurementRequestSnapshot], status_code=201)
def create_request(
    payload: ProcurementRequestCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ProcurementRequestSnapshot]:
    access = IdentityFacade(session).effective_access(membership.membership_id)
    _require_payload_access(
        session,
        membership,
        "procurement.request.create",
        payload.org_id,
        payload.department_id,
        access.user_id,
        payload.lines,
    )
    try:
        value = ProcurementFacade(session).create(payload, membership.membership_id, access.user_id)
    except InvalidProcurementReferenceError as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("", response_model=ApiResponse[list[ProcurementRequestSnapshot]])
def list_requests(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[ProcurementRequestSnapshot]]:
    values = [
        value
        for value in ProcurementFacade(session).list(organization_id)
        if _allowed(
            session,
            membership,
            "procurement.request.read",
            value.org_id,
            value.department_id,
            value.requester_id,
            [line.category_id for line in value.lines],
        )
    ]
    return ApiResponse(data=values, meta=_meta(request))


@router.get("/{request_id}", response_model=ApiResponse[ProcurementRequestSnapshot])
def get_request(
    request_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ProcurementRequestSnapshot]:
    try:
        value = ProcurementFacade(session).get(request_id)
    except ProcurementRequestNotFoundError as exc:
        _raise_domain_error(exc)
    _require_snapshot_access(session, membership, "procurement.request.read", value)
    return ApiResponse(data=value, meta=_meta(request))


@router.put("/{request_id}", response_model=ApiResponse[ProcurementRequestSnapshot])
def update_request(
    request_id: UUID,
    payload: ProcurementRequestUpdate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ProcurementRequestSnapshot]:
    facade = ProcurementFacade(session)
    try:
        current = facade.get(request_id)
        _require_snapshot_access(session, membership, "procurement.request.update", current)
        _require_payload_access(
            session,
            membership,
            "procurement.request.update",
            current.org_id,
            current.department_id,
            current.requester_id,
            payload.lines,
        )
        value = facade.update(request_id, payload)
    except (
        ProcurementRequestNotFoundError,
        ProcurementRequestConflictError,
        ProcurementRequestStateError,
        InvalidProcurementReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.delete("/{request_id}", response_model=ApiResponse[ProcurementRequestDeleteResult])
def delete_request(
    request_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
    expected_version: Annotated[int, Query(ge=1)],
) -> ApiResponse[ProcurementRequestDeleteResult]:
    facade = ProcurementFacade(session)
    try:
        current = facade.get(request_id)
        _require_snapshot_access(session, membership, "procurement.request.update", current)
        facade.delete(request_id, expected_version)
    except (
        ProcurementRequestNotFoundError,
        ProcurementRequestConflictError,
        ProcurementRequestStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=ProcurementRequestDeleteResult(), meta=_meta(request))


@router.post("/{request_id}/submit", response_model=ApiResponse[ProcurementRequestSnapshot])
def submit_request(
    request_id: UUID,
    payload: ProcurementRequestTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ProcurementRequestSnapshot]:
    facade = ProcurementFacade(session)
    try:
        current = facade.get(request_id)
        _require_snapshot_access(session, membership, "procurement.request.submit", current)
        value = facade.submit(request_id, payload.expected_version)
    except (
        ProcurementRequestNotFoundError,
        ProcurementRequestConflictError,
        ProcurementRequestStateError,
        InvalidProcurementReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.post("/{request_id}/withdraw", response_model=ApiResponse[ProcurementRequestSnapshot])
def withdraw_request(
    request_id: UUID,
    payload: ProcurementRequestTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ProcurementRequestSnapshot]:
    facade = ProcurementFacade(session)
    try:
        current = facade.get(request_id)
        _require_snapshot_access(session, membership, "procurement.request.submit", current)
        value = facade.withdraw(request_id, payload.expected_version)
    except (
        ProcurementRequestNotFoundError,
        ProcurementRequestConflictError,
        ProcurementRequestStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))
