from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings


def type_family(column_type: object) -> str:
    type_name = str(column_type).upper()
    for family in ("DATETIME", "INTEGER", "TEXT"):
        if family in type_name:
            return family
    return type_name


def column_schema(inspector, table_name: str) -> dict[str, dict[str, object]]:
    return {
        column["name"]: {
            "type": type_family(column["type"]),
            "nullable": bool(column["nullable"]),
            "primary_key": bool(column["primary_key"]),
        }
        for column in inspector.get_columns(table_name)
    }


def foreign_key_schema(
    inspector,
    table_name: str,
) -> dict[tuple[str, ...], dict[str, object]]:
    return {
        tuple(foreign_key["constrained_columns"]): {
            "referred_table": foreign_key["referred_table"],
            "referred_columns": tuple(foreign_key["referred_columns"]),
            "ondelete": foreign_key.get("options", {}).get("ondelete"),
        }
        for foreign_key in inspector.get_foreign_keys(table_name)
    }


def index_schema(inspector, table_name: str) -> dict[str, dict[str, object]]:
    return {
        index["name"]: {
            "columns": tuple(index["column_names"]),
            "unique": bool(index.get("unique")),
        }
        for index in inspector.get_indexes(table_name)
    }


def assert_named_schema(
    actual_schema: dict[str, dict[str, object]],
    expected_schema: dict[str, dict[str, object]],
) -> None:
    actual_subset = {name: actual_schema.get(name) for name in expected_schema}
    assert actual_subset == expected_schema, {
        "expected": expected_schema,
        "actual": actual_schema,
    }


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

    assert_named_schema(
        column_schema(inspector, "plants"),
        {
            "last_watered_at": {
                "type": "DATETIME",
                "nullable": True,
                "primary_key": False,
            },
        },
    )

    assert_named_schema(
        column_schema(inspector, "watering_records"),
        {
            "id": {
                "type": "INTEGER",
                "nullable": False,
                "primary_key": True,
            },
            "owner_user_id": {
                "type": "TEXT",
                "nullable": False,
                "primary_key": False,
            },
            "plant_id": {
                "type": "INTEGER",
                "nullable": False,
                "primary_key": False,
            },
            "watered_at": {
                "type": "DATETIME",
                "nullable": False,
                "primary_key": False,
            },
            "created_at": {
                "type": "DATETIME",
                "nullable": False,
                "primary_key": False,
            },
        },
    )

    assert foreign_key_schema(inspector, "watering_records") == {
        ("owner_user_id",): {
            "referred_table": "users",
            "referred_columns": ("id",),
            "ondelete": None,
        },
        ("plant_id",): {
            "referred_table": "plants",
            "referred_columns": ("id",),
            "ondelete": None,
        },
    }

    assert index_schema(inspector, "watering_records") == {
        "ix_watering_records_owner_user_id_plant_id_watered_at": {
            "columns": ("owner_user_id", "plant_id", "watered_at"),
            "unique": False,
        },
        "ix_watering_records_owner_user_id_watered_at": {
            "columns": ("owner_user_id", "watered_at"),
            "unique": False,
        },
    }

    assert_named_schema(
        index_schema(inspector, "plants"),
        {
            "ix_plants_owner_user_id_last_watered_at": {
                "columns": ("owner_user_id", "last_watered_at"),
                "unique": False,
            },
        },
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

    watering_leftovers = {
        "tables": [
            table_name
            for table_name in inspector.get_table_names()
            if table_name == "watering_records"
        ],
        "plant_columns": {
            column_name: schema
            for column_name, schema in column_schema(inspector, "plants").items()
            if column_name == "last_watered_at"
        },
        "plant_indexes": {
            index_name: schema
            for index_name, schema in index_schema(inspector, "plants").items()
            if index_name == "ix_plants_owner_user_id_last_watered_at"
        },
    }
    assert watering_leftovers == {
        "tables": [],
        "plant_columns": {},
        "plant_indexes": {},
    }
