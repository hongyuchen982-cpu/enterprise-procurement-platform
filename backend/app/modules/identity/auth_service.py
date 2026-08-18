import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.auth import CurrentUser, LoginResult, MembershipContext
from app.core.settings.business import BusinessSettings, get_business_settings
from app.modules.identity.auth_models import AuthSession, UserCredential
from app.modules.identity.auth_repository import AuthenticationRepository
from app.modules.identity.passwords import InvalidPasswordHashError, PasswordHasher

DEFAULT_PASSWORD_HASHER = PasswordHasher()
DUMMY_PASSWORD_HASH = DEFAULT_PASSWORD_HASHER.hash("not-a-real-password")


class InvalidCredentialsError(ValueError):
    pass


class WeakPasswordError(ValueError):
    pass


class UserNotFoundError(LookupError):
    pass


def token_digest(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AuthenticationService:
    def __init__(
        self,
        session: Session,
        settings: BusinessSettings | None = None,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_business_settings()
        self.password_hasher = password_hasher or DEFAULT_PASSWORD_HASHER
        self.repository = AuthenticationRepository(session)

    def set_password(self, user_id: UUID, new_password: str) -> None:
        user = self.repository.active_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        self._write_password(user_id, new_password, datetime.now(UTC))
        self.session.commit()

    def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        if self.repository.active_user_by_id(user_id) is None:
            raise InvalidCredentialsError("account is not active")
        credential = self.repository.credential(user_id, for_update=True)
        if credential is None or not self._verify(current_password, credential.password_hash):
            raise InvalidCredentialsError("invalid current password")
        if self._verify(new_password, credential.password_hash):
            raise WeakPasswordError("new password must differ from current password")
        self._write_password(user_id, new_password, datetime.now(UTC))
        self.session.commit()

    def login(
        self,
        login_name: str,
        password: str,
        created_ip: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        now = datetime.now(UTC)
        normalized_login = login_name.strip().casefold()
        user = self.repository.active_user_by_login(normalized_login)
        credential = None if user is None else self.repository.credential(user.id, for_update=True)
        password_hash = DUMMY_PASSWORD_HASH if credential is None else credential.password_hash
        password_valid = self._verify(password, password_hash)
        locked = (
            credential is not None
            and credential.locked_until is not None
            and _utc(credential.locked_until) > now
        )

        if user is None or credential is None or not password_valid or locked:
            if credential is not None and not locked:
                credential.failed_attempts += 1
                if credential.failed_attempts >= self.settings.auth_max_failed_attempts:
                    credential.locked_until = now + timedelta(
                        minutes=self.settings.auth_lockout_minutes
                    )
                self.session.commit()
            raise InvalidCredentialsError("invalid login name or password")

        credential.failed_attempts = 0
        credential.locked_until = None
        raw_token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(minutes=self.settings.auth_session_ttl_minutes)
        self.session.add(
            AuthSession(
                user_id=user.id,
                token_hash=token_digest(raw_token),
                expires_at=expires_at,
                created_ip=created_ip,
                user_agent=user_agent,
            )
        )
        self.session.commit()
        return LoginResult(
            access_token=raw_token,
            expires_at=expires_at,
            user=self._current_user(user.id),
        )

    def authenticate(self, raw_token: str) -> CurrentUser:
        if not 32 <= len(raw_token) <= 256:
            raise InvalidCredentialsError("missing bearer token")
        result = self.repository.authentication_session(token_digest(raw_token), datetime.now(UTC))
        if result is None:
            raise InvalidCredentialsError("invalid or expired bearer token")
        _, user = result
        return self._current_user(user.id)

    def logout(self, raw_token: str) -> None:
        auth_session = self.repository.session_by_hash(token_digest(raw_token))
        if auth_session is not None and auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(UTC)
            self.session.commit()

    def _write_password(self, user_id: UUID, new_password: str, now: datetime) -> None:
        try:
            password_hash = self.password_hasher.hash(new_password)
        except ValueError as exc:
            raise WeakPasswordError(str(exc)) from exc
        credential = self.repository.credential(user_id, for_update=True)
        if credential is None:
            credential = UserCredential(
                user_id=user_id,
                password_hash=password_hash,
                password_changed_at=now,
            )
            self.session.add(credential)
        else:
            credential.password_hash = password_hash
            credential.password_changed_at = now
            credential.failed_attempts = 0
            credential.locked_until = None
        self.repository.revoke_user_sessions(user_id, now)

    def _current_user(self, user_id: UUID) -> CurrentUser:
        user = self.repository.active_user_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError("account is not active")
        memberships = tuple(
            MembershipContext(
                membership_id=membership.id,
                organization_id=membership.organization_id,
                department_id=membership.department_id,
            )
            for membership in self.repository.active_memberships(user_id)
        )
        return CurrentUser(
            user_id=user.id,
            login_name=user.login_name,
            display_name=user.display_name,
            memberships=memberships,
        )

    def _verify(self, password: str, encoded: str) -> bool:
        try:
            return self.password_hasher.verify(password, encoded)
        except InvalidPasswordHashError:
            return False
