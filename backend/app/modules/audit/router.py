from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.contracts.audit import AuditEntrySnapshot
from app.contracts.auth import MembershipContext
from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessTarget
from app.core.database import get_session
from app.modules.audit.facade import AuditFacade
from app.modules.identity.auth_api import get_membership_context
from app.modules.identity.facade import IdentityFacade

router = APIRouter(prefix="/audit-log", tags=["member-a:audit"])


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


@router.get("", response_model=ApiResponse[list[AuditEntrySnapshot]])
def list_audit_entries(
    organization_id: UUID,
    request: Request,
    membership: Annotated[MembershipContext, Depends(get_membership_context)],
    session: Annotated[Session, Depends(get_session)],
    object_type: str | None = None,
    object_id: UUID | None = None,
    action: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiResponse[list[AuditEntrySnapshot]]:
    decision = IdentityFacade(session).evaluate(
        membership.membership_id,
        "audit.read",
        AccessTarget(organization_id=organization_id),
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=decision.reason,
        )
    values = list(
        AuditFacade(session).list(
            organization_id,
            object_type,
            object_id,
            action,
            limit,
            offset,
        )
    )
    return ApiResponse(data=values, meta=_meta(request))
