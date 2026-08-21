from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.invoice import (
    InvoiceApproval,
    InvoiceCreate,
    InvoiceDeleteResult,
    InvoiceSnapshot,
    InvoiceTransition,
    InvoiceUpdate,
)
from app.contracts.procurement import ProcurementRequestSnapshot
from app.core.database import get_session
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.invoices.facade import InvoiceFacade
from app.modules.invoices.service import (
    InvalidInvoiceReferenceError,
    InvoiceConflictError,
    InvoiceNotFoundError,
    InvoiceStateError,
)
from app.modules.orders.facade import PurchaseOrderFacade
from app.modules.procurement.facade import ProcurementFacade

router = APIRouter(prefix="/invoices", tags=["member-a:invoices"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


def _invoice_request(session: Session, order_id: UUID) -> ProcurementRequestSnapshot:
    order = PurchaseOrderFacade(session).get(order_id)
    return ProcurementFacade(session).get(order.procurement_request_id)


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


def _raise_domain_error(exc: Exception) -> NoReturn:
    if isinstance(exc, InvoiceNotFoundError):
        raise HTTPException(status_code=404, detail="invoice not found") from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail="referenced resource not found") from exc
    if isinstance(exc, (InvoiceConflictError, InvoiceStateError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("", response_model=ApiResponse[InvoiceSnapshot], status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[InvoiceSnapshot]:
    try:
        source = _invoice_request(session, payload.order_id)
        _require_access(session, membership, "invoice.create", source)
        value = InvoiceFacade(session).create(payload)
    except (
        LookupError,
        InvalidInvoiceReferenceError,
        InvoiceConflictError,
        InvoiceStateError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("", response_model=ApiResponse[list[InvoiceSnapshot]])
def list_invoices(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[InvoiceSnapshot]]:
    values = [
        value
        for value in InvoiceFacade(session).list(organization_id)
        if _allowed(
            session,
            membership,
            "invoice.read",
            _invoice_request(session, value.order_id),
        )
    ]
    return ApiResponse(data=values, meta=_meta(request))


@router.get("/{invoice_id}", response_model=ApiResponse[InvoiceSnapshot])
def get_invoice(
    invoice_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[InvoiceSnapshot]:
    try:
        value = InvoiceFacade(session).get(invoice_id)
    except InvoiceNotFoundError as exc:
        _raise_domain_error(exc)
    _require_access(
        session,
        membership,
        "invoice.read",
        _invoice_request(session, value.order_id),
    )
    return ApiResponse(data=value, meta=_meta(request))


@router.put("/{invoice_id}", response_model=ApiResponse[InvoiceSnapshot])
def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[InvoiceSnapshot]:
    facade = InvoiceFacade(session)
    try:
        current = facade.get(invoice_id)
        _require_access(
            session,
            membership,
            "invoice.update",
            _invoice_request(session, current.order_id),
        )
        value = facade.update(invoice_id, payload)
    except (
        InvoiceNotFoundError,
        InvoiceConflictError,
        InvoiceStateError,
        InvalidInvoiceReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.delete("/{invoice_id}", response_model=ApiResponse[InvoiceDeleteResult])
def delete_invoice(
    invoice_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
    expected_version: Annotated[int, Query(ge=1)],
) -> ApiResponse[InvoiceDeleteResult]:
    facade = InvoiceFacade(session)
    try:
        current = facade.get(invoice_id)
        _require_access(
            session,
            membership,
            "invoice.update",
            _invoice_request(session, current.order_id),
        )
        facade.delete(invoice_id, expected_version)
    except (InvoiceNotFoundError, InvoiceConflictError, InvoiceStateError) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=InvoiceDeleteResult(), meta=_meta(request))


@router.post("/{invoice_id}/submit", response_model=ApiResponse[InvoiceSnapshot])
def submit_invoice(
    invoice_id: UUID,
    payload: InvoiceTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[InvoiceSnapshot]:
    facade = InvoiceFacade(session)
    try:
        current = facade.get(invoice_id)
        _require_access(
            session,
            membership,
            "invoice.submit",
            _invoice_request(session, current.order_id),
        )
        value = facade.submit(invoice_id, payload.expected_version)
    except (
        InvoiceNotFoundError,
        InvoiceConflictError,
        InvoiceStateError,
        InvalidInvoiceReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.post("/{invoice_id}/approve", response_model=ApiResponse[InvoiceSnapshot])
def approve_invoice(
    invoice_id: UUID,
    payload: InvoiceApproval,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[InvoiceSnapshot]:
    facade = InvoiceFacade(session)
    try:
        current = facade.get(invoice_id)
        _require_access(
            session,
            membership,
            "invoice.approve",
            _invoice_request(session, current.order_id),
        )
        value = facade.approve(invoice_id, membership.membership_id, payload)
    except (
        InvoiceNotFoundError,
        InvoiceConflictError,
        InvoiceStateError,
        InvalidInvoiceReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.post("/{invoice_id}/cancel", response_model=ApiResponse[InvoiceSnapshot])
def cancel_invoice(
    invoice_id: UUID,
    payload: InvoiceTransition,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[InvoiceSnapshot]:
    facade = InvoiceFacade(session)
    try:
        current = facade.get(invoice_id)
        _require_access(
            session,
            membership,
            "invoice.cancel",
            _invoice_request(session, current.order_id),
        )
        value = facade.cancel(invoice_id, payload.expected_version)
    except (InvoiceNotFoundError, InvoiceConflictError, InvoiceStateError) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))
