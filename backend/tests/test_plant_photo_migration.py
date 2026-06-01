from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import Settings


def type_family(column_type: object) -> str:
    type_name = str(column_type).upper()
    for family in ("DATETIME", "DATE", "INTEGER", "TEXT"):
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


def test_plant_photo_migration_creates_photo_table_and_cover_reference(
    tmp_path: Path,
):
    database_path = tmp_path / "plant-photo-migration.db"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(make_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert "plant_photos" in inspector.get_table_names()

    assert_named_schema(
        column_schema(inspector, "plant_photos"),
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
            "image_url": {
                "type": "TEXT",
                "nullable": True,
                "primary_key": False,
            },
            "storage_key": {
                "type": "TEXT",
                "nullable": True,
                "primary_key": False,
            },
            "taken_date": {
                "type": "DATE",
                "nullable": True,
                "primary_key": False,
            },
            "comment": {
                "type": "TEXT",
                "nullable": True,
                "primary_key": False,
            },
            "created_at": {
                "type": "DATETIME",
                "nullable": False,
                "primary_key": False,
            },
            "updated_at": {
                "type": "DATETIME",
                "nullable": False,
                "primary_key": False,
            },
        },
    )

    assert foreign_key_schema(inspector, "plant_photos") == {
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

    assert index_schema(inspector, "plant_photos") == {
        "ix_plant_photos_owner_user_id_plant_id_created_at": {
            "columns": ("owner_user_id", "plant_id", "created_at"),
            "unique": False,
        },
        "ix_plant_photos_owner_user_id_plant_id_taken_date": {
            "columns": ("owner_user_id", "plant_id", "taken_date"),
            "unique": False,
        },
    }

    plant_columns = column_schema(inspector, "plants")
    assert_named_schema(
        plant_columns,
        {
            "cover_photo_id": {
                "type": "INTEGER",
                "nullable": True,
                "primary_key": False,
            },
        },
    )
    assert "image_url" not in plant_columns
    assert_named_schema(
        index_schema(inspector, "plants"),
        {
            "ix_plants_cover_photo_id": {
                "columns": ("cover_photo_id",),
                "unique": False,
            },
        },
    )
    assert ("cover_photo_id",) not in foreign_key_schema(inspector, "plants")


def test_plant_photo_migration_downgrade_removes_photo_schema(
    tmp_path: Path,
):
    database_path = tmp_path / "plant-photo-migration-downgrade.db"
    database_url = f"sqlite:///{database_path}"
    config = make_alembic_config(database_url)

    command.upgrade(config, "head")
    command.downgrade(config, "0003_create_watering_records")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    photo_leftovers = {
        "tables": [
            table_name
            for table_name in inspector.get_table_names()
            if table_name == "plant_photos"
        ],
        "plant_columns": {
            column_name: schema
            for column_name, schema in column_schema(inspector, "plants").items()
            if column_name == "cover_photo_id"
        },
        "plant_indexes": {
            index_name: schema
            for index_name, schema in index_schema(inspector, "plants").items()
            if index_name == "ix_plants_cover_photo_id"
        },
    }
    assert photo_leftovers == {
        "tables": [],
        "plant_columns": {},
        "plant_indexes": {},
    }
