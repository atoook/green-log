from __future__ import annotations

import argparse
import os
import uuid
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.db.engine import create_database_engine
from app.repositories.plant_repository import PlantRepository
from app.schemas.plant import PlantCreate
from app.services.plant_service import PlantService


def run_migrations(settings: Settings) -> None:
    os.environ["DATABASE_URL"] = settings.resolved_database_url
    if settings.turso_auth_token:
        os.environ["TURSO_DATABASE_URL"] = settings.resolved_database_url
        os.environ["TURSO_AUTH_TOKEN"] = settings.turso_auth_token
    else:
        os.environ.pop("TURSO_DATABASE_URL", None)
        os.environ.pop("TURSO_AUTH_TOKEN", None)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.attributes["settings"] = settings
    command.upgrade(config, "head")


def build_settings(mode: str) -> Settings:
    file_settings = Settings()

    if mode == "turso":
        turso_url = os.getenv("TURSO_DATABASE_URL") or file_settings.turso_database_url
        token = os.getenv("TURSO_AUTH_TOKEN") or file_settings.turso_auth_token
        if not turso_url or not token:
            raise RuntimeError("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are required for turso mode")
        return Settings(turso_database_url=turso_url, turso_auth_token=token)

    return Settings(
        database_url=os.getenv("DATABASE_URL", file_settings.database_url),
        turso_database_url=None,
        turso_auth_token=None,
    )


def verify_plant_crud(settings: Settings) -> int:
    engine = create_database_engine(settings)
    smoke_name = f"__green_log_smoke_{uuid.uuid4()}"

    with Session(engine) as session:
        service = PlantService(PlantRepository(session))
        created = service.create_plant(
            PlantCreate(
                name=smoke_name,
                acquired_date=None,
                memo="smoke verification",
                image_url=None,
                watering_cycle_days=7,
            )
        )
        plants = service.list_plants()
        detail = service.get_plant(created.id)

    if created.id < 1:
        raise RuntimeError("Plant create did not return a generated id")
    if not any(plant.id == created.id for plant in plants):
        raise RuntimeError("Created plant was not returned by list")
    if detail.name != smoke_name:
        raise RuntimeError("Detail read did not return the created plant")

    return created.id


def verify_type_round_trip(settings: Settings) -> None:
    engine = create_database_engine(settings)
    probe_id = str(uuid.uuid4())
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS __green_log_type_probe (
                    id TEXT PRIMARY KEY,
                    observed_at DATETIME NOT NULL,
                    is_healthy BOOLEAN NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO __green_log_type_probe (id, observed_at, is_healthy)
                VALUES (:id, :observed_at, :is_healthy)
                """
            ),
            {"id": probe_id, "observed_at": observed_at, "is_healthy": True},
        )
        row = connection.execute(
            text(
                """
                SELECT id, observed_at, is_healthy
                FROM __green_log_type_probe
                WHERE id = :id
                """
            ),
            {"id": probe_id},
        ).one()

    if row.id != probe_id:
        raise RuntimeError("UUID text did not round trip")
    if datetime.fromisoformat(str(row.observed_at)) != datetime.fromisoformat(observed_at):
        raise RuntimeError("UTC datetime text did not round trip")
    if row.is_healthy not in (1, True):
        raise RuntimeError("Boolean value did not round trip as true")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Green Log database CRUD and type behavior.")
    parser.add_argument("--mode", choices=["local", "turso"], default="local")
    args = parser.parse_args()

    settings = build_settings(args.mode)
    run_migrations(settings)
    created_id = verify_plant_crud(settings)
    verify_type_round_trip(settings)
    print(f"OK mode={args.mode} createdPlantId={created_id}")


if __name__ == "__main__":
    main()
