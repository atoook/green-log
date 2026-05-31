from __future__ import annotations

import sys

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.config import Settings
from app.models.plant import Plant
from app.models.user import User
from app.models.watering_record import WateringRecord
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
    observed_heatmap_reads: list[tuple[str, str, str]] = []

    class SpyUserService(UserService):
        def get_or_create_from_clerk(self, profile: UserProfileInput) -> User:
            observed_clerk_user_ids.append(profile.clerk_user_id)
            return super().get_or_create_from_clerk(profile)

    class SpyWateringService(verify_turso_crud.WateringService):
        def get_watering_heatmap(self, owner_user_id, start_date=None, end_date=None):
            observed_heatmap_reads.append(
                (
                    owner_user_id,
                    start_date.isoformat() if start_date else "",
                    end_date.isoformat() if end_date else "",
                )
            )
            return super().get_watering_heatmap(owner_user_id, start_date, end_date)

    monkeypatch.setattr(verify_turso_crud, "create_database_engine", lambda settings: engine)
    monkeypatch.setattr(verify_turso_crud, "UserService", SpyUserService)
    monkeypatch.setattr(verify_turso_crud, "WateringService", SpyWateringService)

    result = verify_turso_crud.verify_plant_crud(Settings(database_url="sqlite://"))

    with Session(engine) as session:
        users = list(session.exec(select(User)).all())
        plants = list(session.exec(select(Plant)).all())
        watering_records = list(session.exec(select(WateringRecord)).all())

    smoke_users = [user for user in users if user.clerk_user_id.startswith("smoke-clerk-")]
    other_users = [
        user for user in users if user.clerk_user_id.startswith("smoke-other-clerk-")
    ]

    assert result.created_plant_id >= 1
    assert result.created_watering_record_id >= 1
    assert len(observed_clerk_user_ids) == 3
    assert observed_clerk_user_ids[0] == observed_clerk_user_ids[1]
    assert observed_clerk_user_ids[2].startswith("smoke-other-clerk-")
    assert len(users) == 2
    assert len(smoke_users) == 1
    assert len(other_users) == 1
    smoke_plants = [plant for plant in plants if plant.owner_user_id == smoke_users[0].id]
    other_plants = [plant for plant in plants if plant.owner_user_id == other_users[0].id]
    assert len(smoke_plants) == 1
    assert len(other_plants) == 1
    assert smoke_plants[0].owner_user_id != smoke_users[0].clerk_user_id
    smoke_records = [
        record for record in watering_records if record.owner_user_id == smoke_users[0].id
    ]
    other_records = [
        record for record in watering_records if record.owner_user_id == other_users[0].id
    ]
    assert len(smoke_records) == 1
    assert len(other_records) == 1
    assert smoke_records[0].id == result.created_watering_record_id
    assert smoke_records[0].plant_id == smoke_plants[0].id
    assert other_records[0].watered_at.date() == smoke_records[0].watered_at.date()
    assert smoke_plants[0].last_watered_at == smoke_records[0].watered_at
    assert observed_heatmap_reads == [
        (
            smoke_users[0].id,
            smoke_records[0].watered_at.date().isoformat(),
            smoke_records[0].watered_at.date().isoformat(),
        )
    ]


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


def test_assert_no_ownerless_watering_records_raises_when_rows_are_ownerless():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE watering_records (
                    id INTEGER PRIMARY KEY,
                    owner_user_id TEXT NULL,
                    plant_id INTEGER NOT NULL,
                    watered_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO watering_records (owner_user_id, plant_id, watered_at)
                VALUES (NULL, 1, '2026-05-30T00:00:00+00:00')
                """
            )
        )

    try:
        verify_turso_crud.assert_no_ownerless_watering_records(engine)
    except RuntimeError as error:
        assert "ownerless watering records" in str(error)
    else:
        raise AssertionError("ownerless watering records must fail smoke verification")


def test_main_prints_created_watering_record_id(monkeypatch, capsys):
    settings = Settings(database_url="sqlite://")
    observed_modes: list[str] = []
    migrated_settings: list[Settings] = []
    crud_settings: list[Settings] = []
    type_check_settings: list[Settings] = []

    def fake_build_settings(mode: str) -> Settings:
        observed_modes.append(mode)
        return settings

    def fake_verify_plant_crud(received_settings: Settings):
        crud_settings.append(received_settings)
        return verify_turso_crud.SmokeVerificationResult(
            created_plant_id=12,
            created_watering_record_id=34,
        )

    monkeypatch.setattr(sys, "argv", ["verify_turso_crud.py", "--mode", "local"])
    monkeypatch.setattr(verify_turso_crud, "build_settings", fake_build_settings)
    monkeypatch.setattr(
        verify_turso_crud,
        "run_migrations",
        lambda received_settings: migrated_settings.append(received_settings),
    )
    monkeypatch.setattr(verify_turso_crud, "verify_plant_crud", fake_verify_plant_crud)
    monkeypatch.setattr(
        verify_turso_crud,
        "verify_type_round_trip",
        lambda received_settings: type_check_settings.append(received_settings),
    )

    verify_turso_crud.main()

    captured = capsys.readouterr()
    assert observed_modes == ["local"]
    assert migrated_settings == [settings]
    assert crud_settings == [settings]
    assert type_check_settings == [settings]
    assert captured.out == "OK mode=local createdPlantId=12 createdWateringRecordId=34\n"
    assert captured.err == ""


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
