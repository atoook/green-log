from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.config import Settings
from app.models.plant import Plant
from app.models.user import User
from app.scripts import verify_turso_crud
from app.services.user_service import UserProfileInput, UserService


def make_test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def test_verify_plant_crud_uses_application_user_upsert(monkeypatch):
    engine = make_test_engine()
    observed_clerk_user_ids: list[str] = []

    class SpyUserService(UserService):
        def get_or_create_from_clerk(self, profile: UserProfileInput) -> User:
            observed_clerk_user_ids.append(profile.clerk_user_id)
            return super().get_or_create_from_clerk(profile)

    monkeypatch.setattr(verify_turso_crud, "create_database_engine", lambda settings: engine)
    monkeypatch.setattr(verify_turso_crud, "UserService", SpyUserService)

    created_id = verify_turso_crud.verify_plant_crud(Settings(database_url="sqlite://"))

    with Session(engine) as session:
        users = list(session.exec(select(User)).all())
        plants = list(session.exec(select(Plant)).all())

    assert created_id >= 1
    assert len(observed_clerk_user_ids) == 2
    assert observed_clerk_user_ids[0] == observed_clerk_user_ids[1]
    assert len(users) == 1
    assert users[0].clerk_user_id.startswith("smoke-clerk-")
    assert len(plants) == 1
    assert plants[0].owner_user_id == users[0].id
    assert plants[0].owner_user_id != users[0].clerk_user_id


def test_assert_no_ownerless_plants_raises_when_rows_are_ownerless():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE plants (
                    id INTEGER PRIMARY KEY,
                    owner_user_id TEXT NULL,
                    name TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text("INSERT INTO plants (owner_user_id, name) VALUES (NULL, 'orphan')")
        )

    try:
        verify_turso_crud.assert_no_ownerless_plants(engine)
    except RuntimeError as error:
        assert "ownerless" in str(error)
    else:
        raise AssertionError("ownerless plants must fail smoke verification")


def test_build_settings_turso_requires_url_and_token(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        verify_turso_crud,
        "Settings",
        lambda **kwargs: Settings(
            database_url=kwargs.get("database_url", "sqlite:///./green_log.db"),
            turso_database_url=kwargs.get("turso_database_url"),
            turso_auth_token=kwargs.get("turso_auth_token"),
        ),
    )

    try:
        verify_turso_crud.build_settings("turso")
    except RuntimeError as error:
        assert "TURSO_DATABASE_URL and TURSO_AUTH_TOKEN" in str(error)
    else:
        raise AssertionError("turso mode must require both URL and token")


def test_build_settings_turso_preserves_auth_token(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://green-log.example.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "secret-token")

    settings = verify_turso_crud.build_settings("turso")

    assert settings.turso_database_url == "libsql://green-log.example.turso.io"
    assert settings.turso_auth_token_value == "secret-token"
