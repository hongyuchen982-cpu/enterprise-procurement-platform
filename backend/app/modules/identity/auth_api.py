from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.contracts.auth import (
    ChangePasswordRequest,
    CurrentUser,
    LoginRequest,
    LoginResult,
    LogoutResult,
    MembershipContext,
)
from app.contracts.common import ApiResponse, ResponseMeta
from app.core.database import get_session
from app.modules.identity.auth_service import (
    AuthenticationService,
    InvalidCredentialsError,
    WeakPasswordError,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticationContext:
    raw_token: str = field(repr=False)
    user: CurrentUser


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        timestamp=datetime.now(UTC),
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_authentication_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> AuthenticationContext:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _unauthorized()
    try:
        user = AuthenticationService(session).authenticate(credentials.credentials)
    except InvalidCredentialsError as exc:
        raise _unauthorized() from exc
    return AuthenticationContext(raw_token=credentials.credentials, user=user)


def get_membership_context(
    membership_id: Annotated[UUID, Header(alias="X-Membership-ID")],
    context: Annotated[AuthenticationContext, Depends(get_authentication_context)],
) -> MembershipContext:
    membership = next(
        (
            candidate
            for candidate in context.user.memberships
            if candidate.membership_id == membership_id
        ),
        None,
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="membership does not belong to the authenticated user",
        )
    return membership


@router.post("/login", response_model=ApiResponse[LoginResult])
def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[LoginResult]:
    try:
        result = AuthenticationService(session).login(
            payload.login_name,
            payload.password.get_secret_value(),
            created_ip=None if request.client is None else request.client.host[:45],
            user_agent=request.headers.get("user-agent", "")[:512] or None,
        )
    except InvalidCredentialsError as exc:
        raise _unauthorized() from exc
    return ApiResponse(data=result, meta=_meta(request))


@router.get("/me", response_model=ApiResponse[CurrentUser])
def me(
    request: Request,
    context: Annotated[AuthenticationContext, Depends(get_authentication_context)],
) -> ApiResponse[CurrentUser]:
    return ApiResponse(data=context.user, meta=_meta(request))


@router.post("/logout", response_model=ApiResponse[LogoutResult])
def logout(
    request: Request,
    context: Annotated[AuthenticationContext, Depends(get_authentication_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[LogoutResult]:
    AuthenticationService(session).logout(context.raw_token)
    return ApiResponse(data=LogoutResult(), meta=_meta(request))


@router.post("/change-password", response_model=ApiResponse[LogoutResult])
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    context: Annotated[AuthenticationContext, Depends(get_authentication_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ApiResponse[LogoutResult]:
    try:
        AuthenticationService(session).change_password(
            context.user.user_id,
            payload.current_password.get_secret_value(),
            payload.new_password.get_secret_value(),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current password is invalid",
        ) from exc
    except WeakPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ApiResponse(data=LogoutResult(), meta=_meta(request))
