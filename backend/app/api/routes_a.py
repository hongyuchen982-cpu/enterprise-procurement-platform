from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.contracts.common import ApiResponse, ResponseMeta
from app.contracts.identity import AccessEvaluationRequest, AccessEvaluationResult
from app.core.database import get_session
from app.modules.identity.auth_api import (
    AuthenticationContext,
    get_authentication_context,
)
from app.modules.identity.auth_api import (
    router as auth_router,
)
from app.modules.identity.facade import IdentityFacade
from app.modules.identity.service import MembershipNotActiveError
from app.modules.master_data.router import router as master_data_router
from app.modules.organizations.router import router as organizations_router

router = APIRouter(prefix="/api/v1", tags=["member-a"])
router.include_router(auth_router)
router.include_router(organizations_router)
router.include_router(master_data_router)


@router.post("/access/evaluate", response_model=ApiResponse[AccessEvaluationResult])
def evaluate_access(
    payload: AccessEvaluationRequest,
    request: Request,
    context: Annotated[AuthenticationContext, Depends(get_authentication_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[AccessEvaluationResult]:
    if not any(
        membership.membership_id == payload.membership_id for membership in context.user.memberships
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="membership does not belong to the authenticated user",
        )
    try:
        result = IdentityFacade(session).evaluate(
            payload.membership_id, payload.permission_code, payload.target
        )
    except MembershipNotActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="active membership not found"
        ) from exc
    return ApiResponse(
        data=result,
        meta=ResponseMeta(
            request_id=request.state.request_id,
            trace_id=request.state.trace_id,
            timestamp=datetime.now(UTC),
        ),
    )
