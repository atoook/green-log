from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.models.plant import Plant
from app.models.user import User


def make_alembic_config(database_url: str, legacy_owner_backfill_user_id: str | None = None) -> Config:
    config = Config("alembic.ini")
    config.attributes["settings"] = Settings(
        database_url=database_url,
        turso_database_url=None,
        turso_auth_token=None,
        legacy_owner_backfill_user_id=legacy_owner_backfill_user_id,
    )
    return config


def test_auth_migration_creates_users_and_required_plant_owner(tmp_path: Path):
    database_path = tmp_path / "auth-migration.db"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(make_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert "users" in inspector.get_table_names()
    user_columns = {column["name"]: column for column in inspector.get_columns("users")}
    assert user_columns["id"]["primary_key"] == 1
    assert not user_columns["id"]["nullable"]
    assert not user_columns["clerk_user_id"]["nullable"]
    assert not user_columns["status"]["nullable"]
    assert "primary_email" in user_columns
    assert "display_name" in user_columns
    assert "avatar_url" in user_columns
    assert user_columns["created_at"]["nullable"] is False
    assert user_columns["updated_at"]["nullable"] is False
    assert "TEXT" in str(user_columns["id"]["type"]).upper()
    assert any(
        "active" in constraint["sqltext"]
        and "disabled" in constraint["sqltext"]
        and "deleted" in constraint["sqltext"]
        for constraint in inspector.get_check_constraints("users")
    )

    user_indexes = inspector.get_indexes("users")
    assert any(index["unique"] and index["column_names"] == ["clerk_user_id"] for index in user_indexes)

    plant_columns = {column["name"]: column for column in inspector.get_columns("plants")}
    assert "owner_user_id" in plant_columns
    assert not plant_columns["owner_user_id"]["nullable"]
    assert any(
        foreign_key["referred_table"] == "users"
        and foreign_key["constrained_columns"] == ["owner_user_id"]
        and foreign_key["referred_columns"] == ["id"]
        for foreign_key in inspector.get_foreign_keys("plants")
    )
    assert any(
        index["column_names"] == ["owner_user_id", "id"]
        for index in inspector.get_indexes("plants")
    )


def test_auth_migration_refuses_existing_plants_without_backfill_user(tmp_path: Path):
    database_path = tmp_path / "auth-migration-existing.db"
    database_url = f"sqlite:///{database_path}"
    config = make_alembic_config(database_url)

    command.upgrade(config, "0001_create_plants")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO plants (
                    name, watering_cycle_days, created_at, updated_at
                ) VALUES (
                    'legacy plant', 7, '2026-05-30T00:00:00+00:00', '2026-05-30T00:00:00+00:00'
                )
                """
            )
        )

    with pytest.raises(RuntimeError, match="LEGACY_OWNER_BACKFILL_USER_ID"):
        command.upgrade(config, "head")

    inspector = inspect(engine)
    assert "users" not in inspector.get_table_names()
    assert "owner_user_id" not in {
        column["name"] for column in inspector.get_columns("plants")
    }


def test_auth_migration_backfills_existing_plants_when_owner_is_explicit(tmp_path: Path):
    database_path = tmp_path / "auth-migration-backfill.db"
    database_url = f"sqlite:///{database_path}"
    config = make_alembic_config(database_url, legacy_owner_backfill_user_id="legacy-owner")

    command.upgrade(config, "0001_create_plants")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO plants (
                    name, watering_cycle_days, created_at, updated_at
                ) VALUES (
                    'legacy plant', 7, '2026-05-30T00:00:00+00:00', '2026-05-30T00:00:00+00:00'
                )
                """
            )
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        owner_id = connection.execute(text("SELECT owner_user_id FROM plants")).scalar_one()
        user_id = connection.execute(text("SELECT id FROM users")).scalar_one()

    assert owner_id == "legacy-owner"
    assert user_id == "legacy-owner"


def test_auth_models_are_registered_in_sqlmodel_metadata():
    assert User.__table__.c.id.primary_key
    assert User.__table__.c.clerk_user_id.unique
    assert Plant.__table__.c.owner_user_id.foreign_keys
    assert not Plant.__table__.c.owner_user_id.nullable
