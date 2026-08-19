from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.organizations import (
    MembershipCreate,
    MembershipSnapshot,
    OrganizationCreate,
    OrganizationSnapshot,
    OrganizationTreeNode,
)
from app.core.database import get_session
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.identity.service import (
    InvalidOrganizationRelationshipError,
    OrganizationConflictError,
    OrganizationNotFoundError,
)

router = APIRouter(prefix="/organizations", tags=["member-a:organizations"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


def _require_access(
    facade: IdentityFacade,
    membership: MembershipContext,
    permission_code: str,
    organization_id: UUID,
) -> None:
    decision = facade.evaluate(
        membership.membership_id,
        permission_code,
        AccessTarget(organization_id=organization_id),
    )
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)


@router.get("/{organization_id}/tree", response_model=ApiResponse[OrganizationTreeNode])
def organization_tree(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[OrganizationTreeNode]:
    facade = IdentityFacade(session)
    _require_access(facade, membership, "organization.read", organization_id)
    try:
        tree = facade.organization_tree(organization_id)
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="organization not found"
        ) from exc
    return ApiResponse(data=tree, meta=_meta(request))


@router.post(
    "", response_model=ApiResponse[OrganizationSnapshot], status_code=status.HTTP_201_CREATED
)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[OrganizationSnapshot]:
    facade = IdentityFacade(session)
    _require_access(facade, membership, "organization.manage", payload.parent_id)
    try:
        organization = facade.create_organization(payload)
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="parent not found"
        ) from exc
    except OrganizationConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ApiResponse(data=organization, meta=_meta(request))


@router.post(
    "/memberships",
    response_model=ApiResponse[MembershipSnapshot],
    status_code=status.HTTP_201_CREATED,
)
def create_membership(
    payload: MembershipCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[MembershipSnapshot]:
    facade = IdentityFacade(session)
    _require_access(facade, membership, "organization.manage", payload.organization_id)
    try:
        created = facade.create_membership(payload)
    except OrganizationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrganizationConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidOrganizationRelationshipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return ApiResponse(data=created, meta=_meta(request))
