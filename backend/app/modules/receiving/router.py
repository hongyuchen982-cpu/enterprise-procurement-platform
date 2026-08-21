from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.order import PurchaseOrderSnapshot
from app.contracts.procurement import ProcurementRequestSnapshot
from app.contracts.receiving import (
    ReceiptCreate,
    ReceiptDeleteResult,
    ReceiptSnapshot,
    ReceiptTransition,
    ReceiptUpdate,
)
from app.core.database import get_session
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.procurement.facade import ProcurementFacade
from app.modules.receiving.facade import ReceiptFacade
from app.modules.receiving.service import (
    InvalidReceiptReferenceError,
    ReceiptConflictError,
    ReceiptNotFoundError,
    ReceiptStateError,
)

router = APIRouter(prefix="/receipts", tags=["member-a:receiving"])


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


def _require_access(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    request: ProcurementRequestSnapshot,
) -> None:
    if not _allowed(session, membership, permission_code, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="permission or data scope not granted for every request line",
        )


def _order_request(session: Session, order: PurchaseOrderSnapshot) -> ProcurementRequestSnapshot:
    return ProcurementFacade(session).get(order.procurement_request_id)


def _receipt_request(session: Session, receipt: ReceiptSnapshot) -> ProcurementRequestSnapshot:
    order = PurchaseOrderFacade(session).get(receipt.order_id)
    return _order_request(session, order)


def _raise_domain_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ReceiptNotFoundError):
        raise HTTPException(status_code=404, detail="receipt not found") from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail="referenced resource not found") from exc
    if isinstance(exc, (ReceiptConflictError, ReceiptStateError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("", response_model=ApiResponse[ReceiptSnapshot], status_code=201)
def create_receipt(
    payload: ReceiptCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ReceiptSnapshot]:
    try:
        order = PurchaseOrderFacade(session).get(payload.order_id)
        _require_access(session, membership, "receipt.create", _order_request(session, order))
        access = IdentityFacade(session).effective_access(membership.membership_id)
        value = ReceiptFacade(session).create(
            payload,
            membership.membership_id,
            access.user_id,
        )
    except (
        LookupError,
        InvalidReceiptReferenceError,
        ReceiptConflictError,
        ReceiptStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("", response_model=ApiResponse[list[ReceiptSnapshot]])
def list_receipts(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[ReceiptSnapshot]]:
    values = [
        value
        for value in ReceiptFacade(session).list(organization_id)
        if _allowed(
            session,
            membership,
            "receipt.read",
            _receipt_request(session, value),
        )
    ]
    return ApiResponse(data=values, meta=_meta(request))


@router.get("/{receipt_id}", response_model=ApiResponse[ReceiptSnapshot])
def get_receipt(
    receipt_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ReceiptSnapshot]:
    try:
        value = ReceiptFacade(session).get(receipt_id)
    except ReceiptNotFoundError as exc:
        _raise_domain_error(exc)
    _require_access(session, membership, "receipt.read", _receipt_request(session, value))
    return ApiResponse(data=value, meta=_meta(request))


@router.put("/{receipt_id}", response_model=ApiResponse[ReceiptSnapshot])
def update_receipt(
    receipt_id: UUID,
    payload: ReceiptUpdate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ReceiptSnapshot]:
    facade = ReceiptFacade(session)
    try:
        current = facade.get(receipt_id)
        _require_access(session, membership, "receipt.update", _receipt_request(session, current))
        value = facade.update(receipt_id, payload)
    except (
        ReceiptNotFoundError,
        ReceiptConflictError,
        ReceiptStateError,
        InvalidReceiptReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.delete("/{receipt_id}", response_model=ApiResponse[ReceiptDeleteResult])
def delete_receipt(
    receipt_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
    expected_version: Annotated[int, Query(ge=1)],
) -> ApiResponse[ReceiptDeleteResult]:
    facade = ReceiptFacade(session)
    try:
        current = facade.get(receipt_id)
        _require_access(session, membership, "receipt.update", _receipt_request(session, current))
        facade.delete(receipt_id, expected_version)
    except (ReceiptNotFoundError, ReceiptConflictError, ReceiptStateError) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=ReceiptDeleteResult(), meta=_meta(request))


@router.post("/{receipt_id}/complete", response_model=ApiResponse[ReceiptSnapshot])
def complete_receipt(
    receipt_id: UUID,
    payload: ReceiptTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ReceiptSnapshot]:
    facade = ReceiptFacade(session)
    try:
        current = facade.get(receipt_id)
        _require_access(session, membership, "receipt.complete", _receipt_request(session, current))
        value = facade.complete(receipt_id, payload.expected_version)
    except (
        ReceiptNotFoundError,
        ReceiptConflictError,
        ReceiptStateError,
        InvalidReceiptReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.post("/{receipt_id}/cancel", response_model=ApiResponse[ReceiptSnapshot])
def cancel_receipt(
    receipt_id: UUID,
    payload: ReceiptTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[ReceiptSnapshot]:
    facade = ReceiptFacade(session)
    try:
        current = facade.get(receipt_id)
        _require_access(session, membership, "receipt.cancel", _receipt_request(session, current))
        value = facade.cancel(receipt_id, payload.expected_version)
    except (ReceiptNotFoundError, ReceiptConflictError, ReceiptStateError) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))
