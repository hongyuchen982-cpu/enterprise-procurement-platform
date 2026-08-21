from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.order import (
    PurchaseOrderCreate,
    PurchaseOrderDeleteResult,
    PurchaseOrderSnapshot,
    PurchaseOrderTransition,
    PurchaseOrderUpdate,
)
from app.contracts.procurement import ProcurementRequestSnapshot
from app.core.database import get_session
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.orders.service import (
    InvalidPurchaseOrderReferenceError,
    PurchaseOrderConflictError,
    PurchaseOrderNotFoundError,
    PurchaseOrderStateError,
)
from app.modules.procurement.facade import ProcurementFacade

router = APIRouter(prefix="/purchase-orders", tags=["member-a:orders"])


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


def _request_for_order(
    session: Session, order: PurchaseOrderSnapshot
) -> ProcurementRequestSnapshot:
    return ProcurementFacade(session).get(order.procurement_request_id)


def _raise_domain_error(exc: Exception) -> NoReturn:
    if isinstance(exc, PurchaseOrderNotFoundError):
        raise HTTPException(status_code=404, detail="purchase order not found") from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail="referenced resource not found") from exc
    if isinstance(exc, (PurchaseOrderConflictError, PurchaseOrderStateError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("", response_model=ApiResponse[PurchaseOrderSnapshot], status_code=201)
def create_order(
    payload: PurchaseOrderCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[PurchaseOrderSnapshot]:
    try:
        procurement_request = ProcurementFacade(session).get(payload.procurement_request_id)
        _require_access(session, membership, "order.create", procurement_request)
        value = PurchaseOrderFacade(session).create(payload)
    except (
        LookupError,
        InvalidPurchaseOrderReferenceError,
        PurchaseOrderConflictError,
        PurchaseOrderStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("", response_model=ApiResponse[list[PurchaseOrderSnapshot]])
def list_orders(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[PurchaseOrderSnapshot]]:
    values = [
        value
        for value in PurchaseOrderFacade(session).list(organization_id)
        if _allowed(
            session,
            membership,
            "order.read",
            _request_for_order(session, value),
        )
    ]
    return ApiResponse(data=values, meta=_meta(request))


@router.get("/{order_id}", response_model=ApiResponse[PurchaseOrderSnapshot])
def get_order(
    order_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[PurchaseOrderSnapshot]:
    try:
        value = PurchaseOrderFacade(session).get(order_id)
    except PurchaseOrderNotFoundError as exc:
        _raise_domain_error(exc)
    _require_access(session, membership, "order.read", _request_for_order(session, value))
    return ApiResponse(data=value, meta=_meta(request))


@router.put("/{order_id}", response_model=ApiResponse[PurchaseOrderSnapshot])
def update_order(
    order_id: UUID,
    payload: PurchaseOrderUpdate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[PurchaseOrderSnapshot]:
    facade = PurchaseOrderFacade(session)
    try:
        current = facade.get(order_id)
        _require_access(session, membership, "order.update", _request_for_order(session, current))
        value = facade.update(order_id, payload)
    except (
        PurchaseOrderNotFoundError,
        PurchaseOrderConflictError,
        PurchaseOrderStateError,
        InvalidPurchaseOrderReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.delete("/{order_id}", response_model=ApiResponse[PurchaseOrderDeleteResult])
def delete_order(
    order_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
    expected_version: Annotated[int, Query(ge=1)],
) -> ApiResponse[PurchaseOrderDeleteResult]:
    facade = PurchaseOrderFacade(session)
    try:
        current = facade.get(order_id)
        _require_access(session, membership, "order.update", _request_for_order(session, current))
        facade.delete(order_id, expected_version)
    except (
        PurchaseOrderNotFoundError,
        PurchaseOrderConflictError,
        PurchaseOrderStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=PurchaseOrderDeleteResult(), meta=_meta(request))


@router.post("/{order_id}/issue", response_model=ApiResponse[PurchaseOrderSnapshot])
def issue_order(
    order_id: UUID,
    payload: PurchaseOrderTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[PurchaseOrderSnapshot]:
    facade = PurchaseOrderFacade(session)
    try:
        current = facade.get(order_id)
        _require_access(session, membership, "order.issue", _request_for_order(session, current))
        value = facade.issue(order_id, payload.expected_version)
    except (
        PurchaseOrderNotFoundError,
        PurchaseOrderConflictError,
        PurchaseOrderStateError,
        InvalidPurchaseOrderReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.post("/{order_id}/cancel", response_model=ApiResponse[PurchaseOrderSnapshot])
def cancel_order(
    order_id: UUID,
    payload: PurchaseOrderTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[PurchaseOrderSnapshot]:
    facade = PurchaseOrderFacade(session)
    try:
        current = facade.get(order_id)
        _require_access(session, membership, "order.cancel", _request_for_order(session, current))
        value = facade.cancel(order_id, payload.expected_version)
    except (
        PurchaseOrderNotFoundError,
        PurchaseOrderConflictError,
        PurchaseOrderStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))
