from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings


def make_alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.attributes["settings"] = Settings(
        database_url=database_url,
        turso_database_url=None,
        turso_auth_token=None,
        legacy_owner_backfill_user_id=None,
    )
    return config


def test_watering_migration_creates_summary_history_foreign_keys_and_indexes(
    tmp_path: Path,
):
    database_path = tmp_path / "watering-migration.db"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(make_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert "watering_records" in inspector.get_table_names()

    plant_columns = {column["name"]: column for column in inspector.get_columns("plants")}
    assert "last_watered_at" in plant_columns
    assert plant_columns["last_watered_at"]["nullable"] is True

    watering_columns = {
        column["name"]: column for column in inspector.get_columns("watering_records")
    }
    assert watering_columns["id"]["primary_key"] == 1
    assert "TEXT" in str(watering_columns["owner_user_id"]["type"]).upper()
    assert "INTEGER" in str(watering_columns["plant_id"]["type"]).upper()
    assert not watering_columns["owner_user_id"]["nullable"]
    assert not watering_columns["plant_id"]["nullable"]
    assert not watering_columns["watered_at"]["nullable"]
    assert not watering_columns["created_at"]["nullable"]

    foreign_keys = inspector.get_foreign_keys("watering_records")
    assert any(
        foreign_key["referred_table"] == "users"
        and foreign_key["constrained_columns"] == ["owner_user_id"]
        and foreign_key["referred_columns"] == ["id"]
        and not foreign_key.get("options", {}).get("ondelete")
        for foreign_key in foreign_keys
    )
    assert any(
        foreign_key["referred_table"] == "plants"
        and foreign_key["constrained_columns"] == ["plant_id"]
        and foreign_key["referred_columns"] == ["id"]
        and not foreign_key.get("options", {}).get("ondelete")
        for foreign_key in foreign_keys
    )

    watering_indexes = inspector.get_indexes("watering_records")
    assert any(
        index["name"] == "ix_watering_records_owner_user_id_plant_id_watered_at"
        and index["column_names"] == ["owner_user_id", "plant_id", "watered_at"]
        for index in watering_indexes
    )
    assert any(
        index["name"] == "ix_watering_records_owner_user_id_watered_at"
        and index["column_names"] == ["owner_user_id", "watered_at"]
        for index in watering_indexes
    )

    plant_indexes = inspector.get_indexes("plants")
    assert any(
        index["name"] == "ix_plants_owner_user_id_last_watered_at"
        and index["column_names"] == ["owner_user_id", "last_watered_at"]
        for index in plant_indexes
    )


def test_watering_migration_keeps_existing_plants_unrecorded_without_backfill(
    tmp_path: Path,
):
    database_path = tmp_path / "watering-migration-existing.db"
    database_url = f"sqlite:///{database_path}"
    config = make_alembic_config(database_url)

    command.upgrade(config, "0002_create_users_and_plant_owners")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (
                    id, clerk_user_id, status, created_at, updated_at
                ) VALUES (
                    'owner-1', 'clerk-owner-1', 'active',
                    '2026-05-30T00:00:00+00:00', '2026-05-30T00:00:00+00:00'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO plants (
                    owner_user_id, name, watering_cycle_days, created_at, updated_at
                ) VALUES (
                    'owner-1', 'Monstera', 7,
                    '2026-05-30T00:00:00+00:00', '2026-05-30T00:00:00+00:00'
                )
                """
            )
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        last_watered_at = connection.execute(
            text("SELECT last_watered_at FROM plants WHERE owner_user_id = 'owner-1'")
        ).scalar_one()
        watering_count = connection.execute(
            text("SELECT COUNT(*) FROM watering_records")
        ).scalar_one()

    assert last_watered_at is None
    assert watering_count == 0


def test_watering_migration_downgrade_removes_summary_history_and_indexes(
    tmp_path: Path,
):
    database_path = tmp_path / "watering-migration-downgrade.db"
    database_url = f"sqlite:///{database_path}"
    config = make_alembic_config(database_url)

    command.upgrade(config, "head")
    command.downgrade(config, "0002_create_users_and_plant_owners")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert "watering_records" not in inspector.get_table_names()
    assert "last_watered_at" not in {
        column["name"] for column in inspector.get_columns("plants")
    }
    assert not any(
        index["name"] == "ix_plants_owner_user_id_last_watered_at"
        for index in inspector.get_indexes("plants")
    )
