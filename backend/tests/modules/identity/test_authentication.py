from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.settings.business import BusinessSettings
from app.modules.identity.auth_models import AuthSession, UserCredential
from app.modules.identity.auth_service import (
    AuthenticationService,
    InvalidCredentialsError,
    WeakPasswordError,
    token_digest,
)
from app.modules.identity.models import Membership, Organization, User
from app.modules.identity.passwords import InvalidPasswordHashError, PasswordHasher

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "new correct horse battery staple"


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as value:
        yield value


@pytest.fixture
def settings() -> BusinessSettings:
    return BusinessSettings(
        _env_file=None,
        auth_session_ttl_minutes=60,
        auth_max_failed_attempts=3,
        auth_lockout_minutes=15,
    )


def seed_user(session: Session) -> User:
    organization = Organization(code="AUTH-ROOT", name="Authentication root")
    user = User(login_name=" Auth-User ", display_name="Authentication User")
    session.add_all([organization, user])
    session.flush()
    department = Organization(
        code="AUTH-DEPT", name="Authentication department", parent_id=organization.id
    )
    session.add(department)
    session.flush()
    session.add(
        Membership(
            user_id=user.id,
            organization_id=organization.id,
            department_id=department.id,
        )
    )
    session.commit()
    assert user.login_name == "auth-user"
    return user


def test_password_is_scrypt_hashed_and_never_stored_as_plaintext(
    session: Session, settings: BusinessSettings
) -> None:
    user = seed_user(session)
    AuthenticationService(session, settings).set_password(user.id, PASSWORD)

    credential = session.get(UserCredential, user.id)
    assert credential is not None
    assert credential.password_hash.startswith("$scrypt$")
    assert PASSWORD not in credential.password_hash
    assert PasswordHasher().verify(PASSWORD, credential.password_hash) is True


def test_login_authenticate_and_logout_lifecycle(
    session: Session, settings: BusinessSettings
) -> None:
    user = seed_user(session)
    service = AuthenticationService(session, settings)
    service.set_password(user.id, PASSWORD)

    login = service.login("AUTH-USER", PASSWORD, created_ip="127.0.0.1")
    assert login.user.user_id == user.id
    assert len(login.user.memberships) == 1
    stored_session = session.scalar(select(AuthSession))
    assert stored_session is not None
    assert stored_session.token_hash == token_digest(login.access_token)
    assert login.access_token not in stored_session.token_hash

    current_user = service.authenticate(login.access_token)
    assert current_user.user_id == user.id

    department = session.scalar(select(Organization).where(Organization.code == "AUTH-DEPT"))
    assert department is not None
    department.status = "DISABLED"
    session.commit()
    assert service.authenticate(login.access_token).memberships == ()

    service.logout(login.access_token)
    with pytest.raises(InvalidCredentialsError):
        service.authenticate(login.access_token)


def test_failed_logins_lock_account_without_revealing_valid_user(
    session: Session, settings: BusinessSettings
) -> None:
    user = seed_user(session)
    service = AuthenticationService(session, settings)
    service.set_password(user.id, PASSWORD)

    for _ in range(settings.auth_max_failed_attempts):
        with pytest.raises(InvalidCredentialsError, match="invalid login name or password"):
            service.login("auth-user", "wrong password")

    credential = session.get(UserCredential, user.id)
    assert credential is not None
    assert credential.failed_attempts == settings.auth_max_failed_attempts
    assert credential.locked_until is not None
    with pytest.raises(InvalidCredentialsError, match="invalid login name or password"):
        service.login("auth-user", PASSWORD)
    with pytest.raises(InvalidCredentialsError, match="invalid login name or password"):
        service.login("missing-user", PASSWORD)


def test_password_change_revokes_sessions_and_old_password(
    session: Session, settings: BusinessSettings
) -> None:
    user = seed_user(session)
    service = AuthenticationService(session, settings)
    service.set_password(user.id, PASSWORD)
    old_login = service.login("auth-user", PASSWORD)

    with pytest.raises(WeakPasswordError, match="must differ"):
        service.change_password(user.id, PASSWORD, PASSWORD)
    service.change_password(user.id, PASSWORD, NEW_PASSWORD)

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(old_login.access_token)
    with pytest.raises(InvalidCredentialsError):
        service.login("auth-user", PASSWORD)
    assert service.login("auth-user", NEW_PASSWORD).user.user_id == user.id


def test_expired_and_disabled_sessions_are_rejected(
    session: Session, settings: BusinessSettings
) -> None:
    user = seed_user(session)
    service = AuthenticationService(session, settings)
    service.set_password(user.id, PASSWORD)
    login = service.login("auth-user", PASSWORD)
    auth_session = session.scalar(select(AuthSession))
    assert auth_session is not None
    auth_session.created_at = datetime.now(UTC) - timedelta(hours=2)
    auth_session.expires_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(login.access_token)

    second_login = service.login("auth-user", PASSWORD)
    user.status = "DISABLED"
    session.commit()
    with pytest.raises(InvalidCredentialsError):
        service.authenticate(second_login.access_token)
    with pytest.raises(InvalidCredentialsError):
        service.authenticate("x" * 1000)


def test_password_policy_and_malformed_hash_are_rejected(
    session: Session, settings: BusinessSettings
) -> None:
    user = seed_user(session)
    with pytest.raises(WeakPasswordError):
        AuthenticationService(session, settings).set_password(user.id, "too-short")
    with pytest.raises(InvalidPasswordHashError):
        PasswordHasher().verify(PASSWORD, "$scrypt$bad")
    with pytest.raises(InvalidPasswordHashError):
        PasswordHasher().verify(
            PASSWORD,
            "$scrypt$16384$8$1$c2hvcnQ=$c2hvcnQ=",
        )
