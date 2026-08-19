from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.contracts.master_data import (
    CategoryCreate,
    CategorySnapshot,
    MaterialCreate,
    MaterialSnapshot,
    UnitCreate,
    UnitSnapshot,
)
from app.core.database import get_session
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade
from app.modules.master_data.facade import MasterDataFacade
from app.modules.master_data.service import (
    InvalidMasterDataReferenceError,
    MasterDataConflictError,
    MasterDataNotFoundError,
)

router = APIRouter(prefix="/master-data", tags=["member-a:master-data"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


def _require_access(
    session: Session,
    membership: MembershipContext,
    permission_code: str,
    organization_id: UUID,
    category_id: UUID | None = None,
) -> None:
    decision = IdentityFacade(session).evaluate(
        membership.membership_id,
        permission_code,
        AccessTarget(organization_id=organization_id, category_id=category_id),
    )
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)


def _raise_domain_error(exc: Exception) -> NoReturn:
    if isinstance(exc, MasterDataNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, MasterDataConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    ) from exc


@router.get("/categories", response_model=ApiResponse[list[CategorySnapshot]])
def list_categories(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[CategorySnapshot]]:
    _require_access(session, membership, "master_data.read", organization_id)
    values = list(MasterDataFacade(session).list_categories(organization_id))
    return ApiResponse(data=values, meta=_meta(request))


@router.post(
    "/categories",
    response_model=ApiResponse[CategorySnapshot],
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[CategorySnapshot]:
    _require_access(session, membership, "master_data.manage", payload.organization_id)
    try:
        value = MasterDataFacade(session).create_category(payload)
    except (
        MasterDataNotFoundError,
        MasterDataConflictError,
        InvalidMasterDataReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("/units", response_model=ApiResponse[list[UnitSnapshot]])
def list_units(
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[UnitSnapshot]]:
    _require_access(session, membership, "master_data.read", membership.organization_id)
    return ApiResponse(data=list(MasterDataFacade(session).list_units()), meta=_meta(request))


@router.post(
    "/units",
    response_model=ApiResponse[UnitSnapshot],
    status_code=status.HTTP_201_CREATED,
)
def create_unit(
    payload: UnitCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[UnitSnapshot]:
    _require_access(session, membership, "master_data.manage", membership.organization_id)
    try:
        value = MasterDataFacade(session).create_unit(payload)
    except MasterDataConflictError as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))


@router.get("/materials", response_model=ApiResponse[list[MaterialSnapshot]])
def list_materials(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[list[MaterialSnapshot]]:
    _require_access(session, membership, "master_data.read", organization_id)
    values = list(MasterDataFacade(session).list_materials(organization_id))
    return ApiResponse(data=values, meta=_meta(request))


@router.post(
    "/materials",
    response_model=ApiResponse[MaterialSnapshot],
    status_code=status.HTTP_201_CREATED,
)
def create_material(
    payload: MaterialCreate,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[MaterialSnapshot]:
    _require_access(
        session,
        membership,
        "master_data.manage",
        payload.organization_id,
        payload.category_id,
    )
    try:
        value = MasterDataFacade(session).create_material(payload)
    except (
        MasterDataNotFoundError,
        MasterDataConflictError,
        InvalidMasterDataReferenceError,
    ) as exc:
        _raise_domain_error(exc)
    return ApiResponse(data=value, meta=_meta(request))
