from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.core.settings.business import BusinessSettings
from app.main import app
from app.modules.identity.auth_service import AuthenticationService
from app.modules.identity.models import Membership, Organization, User

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "new correct horse battery staple"


def test_login_me_and_logout_api_flow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    settings = BusinessSettings(_env_file=None, auth_session_ttl_minutes=60)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(code="API-AUTH", name="API authentication")
        user = User(login_name="api-user", display_name="API User")
        session.add_all([organization, user])
        session.flush()
        session.add(Membership(user_id=user.id, organization_id=organization.id))
        session.commit()
        AuthenticationService(session, settings).set_password(user.id, PASSWORD)

    def override_session() -> Generator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        invalid = client.post(
            "/api/v1/auth/login",
            json={"login_name": "api-user", "password": "wrong password"},
        )
        assert invalid.status_code == 401
        assert invalid.headers["www-authenticate"] == "Bearer"

        login = client.post(
            "/api/v1/auth/login",
            json={"login_name": "api-user", "password": PASSWORD},
        )
        assert login.status_code == 200
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["data"]["login_name"] == "api-user"

        wrong_change = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "wrong password", "new_password": NEW_PASSWORD},
        )
        assert wrong_change.status_code == 400

        changed = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert changed.status_code == 200

        rejected = client.get("/api/v1/auth/me", headers=headers)
        assert rejected.status_code == 401
        old_password = client.post(
            "/api/v1/auth/login",
            json={"login_name": "api-user", "password": PASSWORD},
        )
        assert old_password.status_code == 401
        new_login = client.post(
            "/api/v1/auth/login",
            json={"login_name": "api-user", "password": NEW_PASSWORD},
        )
        new_token = new_login.json()["data"]["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        logout = client.post("/api/v1/auth/logout", headers=new_headers)
        assert logout.status_code == 200
        assert logout.json()["data"]["revoked"] is True

        rejected = client.get("/api/v1/auth/me", headers=new_headers)
        assert rejected.status_code == 401
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
