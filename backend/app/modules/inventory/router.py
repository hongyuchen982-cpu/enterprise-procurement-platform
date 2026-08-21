from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.inventory import InventoryBalanceSnapshot, InventoryMovementSnapshot
from app.core.database import get_session
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.inventory.facade import InventoryFacade

router = APIRouter(prefix="/inventory", tags=["member-a:inventory"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


def _allowed(
    session: Session,
    membership: MembershipContext,
    organization_id: UUID,
    category_id: UUID,
) -> bool:
    return (
        IdentityFacade(session)
        .evaluate(
            membership.membership_id,
            "inventory.read",
            AccessTarget(
                organization_id=organization_id,
                category_id=category_id,
            ),
        )
        .allowed
    )


@router.get("/balances", response_model=ApiResponse[list[InventoryBalanceSnapshot]])
def list_balances(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[InventoryBalanceSnapshot]]:
    values = [
        value
        for value in InventoryFacade(session).balances(organization_id)
        if _allowed(
            session,
            membership,
            value.organization_id,
            value.category_id,
        )
    ]
    return ApiResponse(data=values, meta=_meta(request))


@router.get("/movements", response_model=ApiResponse[list[InventoryMovementSnapshot]])
def list_movements(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
    material_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiResponse[list[InventoryMovementSnapshot]]:
    values = [
        value
        for value in InventoryFacade(session).movements(
            organization_id,
            material_id,
            limit,
            offset,
        )
        if _allowed(
            session,
            membership,
            value.organization_id,
            value.category_id,
        )
    ]
    return ApiResponse(data=values, meta=_meta(request))
