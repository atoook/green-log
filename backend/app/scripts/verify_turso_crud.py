from __future__ import annotations

import argparse
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import Settings
from app.db.engine import create_database_engine
from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto
from app.repositories.plant_repository import PlantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.watering_repository import WateringRepository
from app.schemas.plant import PlantCreate, PlantUpdate
from app.services.plant_service import PlantNotFoundError, PlantService
from app.services.user_service import UserProfileInput, UserService
from app.services.watering_service import (
    APP_TIMEZONE,
    WateringPlantNotFoundError,
    WateringService,
)


@dataclass(frozen=True)
class SmokeVerificationResult:
    created_plant_id: int
    created_plant_photo_id: str
    created_watering_record_id: int


class SmokeImageUrlResolver:
    def public_url(self, object_key: str) -> str:
        return f"https://example.invalid/{object_key}"


def run_migrations(settings: Settings) -> None:
    config = Config("alembic.ini")
    config.attributes["settings"] = settings
    command.upgrade(config, "head")


def build_settings(mode: str) -> Settings:
    file_settings = Settings()

    if mode == "turso":
        turso_url = os.getenv("TURSO_DATABASE_URL") or file_settings.turso_database_url
        token = os.getenv("TURSO_AUTH_TOKEN") or file_settings.turso_auth_token_value
        if not turso_url or not token:
            raise RuntimeError("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are required for turso mode")
        return Settings(turso_database_url=turso_url, turso_auth_token=token)

    return Settings(
        database_url=os.getenv("DATABASE_URL", file_settings.database_url),
        turso_database_url=None,
        turso_auth_token=None,
    )


def verify_plant_crud(settings: Settings) -> SmokeVerificationResult:
    engine = create_database_engine(settings)
    smoke_name = f"__green_log_smoke_{uuid.uuid4()}"
    smoke_clerk_user_id = f"smoke-clerk-{uuid.uuid4()}"
    other_clerk_user_id = f"smoke-other-clerk-{uuid.uuid4()}"

    with Session(engine) as session:
        user_service = UserService(UserRepository(session))
        smoke_profile = UserProfileInput(
            clerk_user_id=smoke_clerk_user_id,
            primary_email=f"{smoke_clerk_user_id}@example.invalid",
            display_name="Green Log Smoke User",
        )
        smoke_user = user_service.get_or_create_from_clerk(smoke_profile)
        reused_smoke_user = user_service.get_or_create_from_clerk(smoke_profile)
        if reused_smoke_user.id != smoke_user.id:
            raise RuntimeError("Smoke user upsert created duplicate application users")

        other_user = user_service.get_or_create_from_clerk(
            UserProfileInput(
                clerk_user_id=other_clerk_user_id,
                primary_email=f"{other_clerk_user_id}@example.invalid",
                display_name="Green Log Smoke Other User",
            )
        )

        image_url_resolver = SmokeImageUrlResolver()
        service = PlantService(PlantRepository(session), image_url_resolver)
        created = service.create_plant(
            smoke_user.id,
            PlantCreate(
                name=smoke_name,
                acquired_date=None,
                memo="smoke verification",
                watering_cycle_days=7,
            )
        )
        other_created = service.create_plant(
            other_user.id,
            PlantCreate(
                name=f"{smoke_name}_other_owner",
                acquired_date=None,
                memo="smoke verification other owner",
                watering_cycle_days=7,
            ),
        )

        smoke_plant = session.get(Plant, created.id)
        other_plant = session.get(Plant, other_created.id)
        if smoke_plant is None or other_plant is None:
            raise RuntimeError("Created smoke plants disappeared before photo verification")

        cover_photo = PlantPhoto(
            owner_user_id=smoke_user.id,
            plant_id=created.id,
            storage_key=f"plants/{created.id}/cover.jpg",
        )
        secondary_photo = PlantPhoto(
            owner_user_id=smoke_user.id,
            plant_id=created.id,
            storage_key=f"plants/{created.id}/secondary.jpg",
        )
        other_owner_photo = PlantPhoto(
            owner_user_id=other_user.id,
            plant_id=other_created.id,
            storage_key=f"plants/{other_created.id}/cover.jpg",
        )
        session.add(cover_photo)
        session.add(secondary_photo)
        session.add(other_owner_photo)
        session.commit()
        session.refresh(cover_photo)
        session.refresh(secondary_photo)
        session.refresh(other_owner_photo)

        if cover_photo.id is None:
            raise RuntimeError("Plant photo create did not return a generated id")
        cover_photo_id = cover_photo.id
        smoke_plant.cover_photo_id = cover_photo_id
        session.add(smoke_plant)
        session.commit()

        plants = service.list_plants(smoke_user.id)
        detail = service.get_plant(smoke_user.id, created.id)
        cover_image_url = image_url_resolver.public_url(cover_photo.storage_key)
        if detail.image_url != cover_image_url:
            raise RuntimeError("Detail read did not expose the smoke cover photo URL")
        if not any(plant.id == created.id and plant.image_url == cover_image_url for plant in plants):
            raise RuntimeError("List read did not expose the smoke cover photo URL")

        smoke_plant.cover_photo_id = other_owner_photo.id
        session.add(smoke_plant)
        session.commit()
        mismatched_detail = service.get_plant(smoke_user.id, created.id)
        if mismatched_detail.image_url is not None:
            raise RuntimeError("Other-owner photo was exposed as the smoke cover photo")

        smoke_plant.cover_photo_id = cover_photo_id
        session.add(smoke_plant)
        session.commit()

        watering_service = WateringService(
            PlantRepository(session),
            WateringRepository(session),
            image_url_resolver=image_url_resolver,
        )

        initial_watering = watering_service.get_plant_watering(smoke_user.id, created.id)
        if initial_watering.last_watered_at is not None:
            raise RuntimeError("New smoke plant unexpectedly had a last watered timestamp")
        if initial_watering.next_watering_date is not None:
            raise RuntimeError("New smoke plant unexpectedly had a next watering date")
        if initial_watering.history:
            raise RuntimeError("New smoke plant unexpectedly had watering history")

        initial_upcoming_care = watering_service.get_upcoming_care(smoke_user.id)
        if not any(
            item.plant_id == created.id
            and item.due_status == "unrecorded"
            and item.plant.image_url == cover_image_url
            for section in initial_upcoming_care.sections
            for item in section.items
        ):
            raise RuntimeError("Unwatered smoke plant was not listed with its cover photo")

        try:
            watering_service.record_watering(other_user.id, created.id)
        except WateringPlantNotFoundError:
            pass
        else:
            raise RuntimeError("Other user created a watering record for the smoke plant")

        watered_at = datetime.now(timezone.utc).replace(microsecond=0)
        watering_result = watering_service.record_watering(
            smoke_user.id,
            created.id,
            watered_at=watered_at,
        )
        watering_service.record_watering(
            other_user.id,
            other_created.id,
            watered_at=watered_at,
        )
        current_smoke_name = f"{smoke_name}_current"
        watered_on = watered_at.astimezone(APP_TIMEZONE).date()
        updated_detail = service.update_plant(
            smoke_user.id,
            created.id,
            PlantUpdate(
                name=current_smoke_name,
                acquired_date=watered_on,
                memo=None,
                watering_cycle_days=10,
            ),
        )
        if updated_detail.name != current_smoke_name:
            raise RuntimeError("Smoke plant update did not return the updated name")
        if updated_detail.memo is not None:
            raise RuntimeError("Smoke plant update did not clear memo")
        if updated_detail.watering_cycle_days != 10:
            raise RuntimeError("Smoke plant update did not persist the new watering cycle")

        try:
            service.update_plant(
                other_user.id,
                created.id,
                PlantUpdate(name=f"{smoke_name}_forbidden"),
            )
        except PlantNotFoundError:
            pass
        else:
            raise RuntimeError("Other user updated the smoke plant")

        watering_detail = watering_service.get_plant_watering(smoke_user.id, created.id)
        upcoming_care_after_record = watering_service.get_upcoming_care(smoke_user.id)
        heatmap = watering_service.get_watering_heatmap(
            smoke_user.id,
            start_date=watered_on,
            end_date=watered_on,
        )

    if created.id < 1:
        raise RuntimeError("Plant create did not return a generated id")
    if not any(plant.id == created.id for plant in plants):
        raise RuntimeError("Created plant was not returned by list")
    if detail.name != smoke_name:
        raise RuntimeError("Detail read did not return the created plant")
    if watering_result.record.id < 1:
        raise RuntimeError("Watering record create did not return a generated id")
    if watering_result.record.plant_id != created.id:
        raise RuntimeError("Watering record was not linked to the created plant")
    if watering_result.record.watered_at != watering_result.state.last_watered_at:
        raise RuntimeError("Latest watering state did not match the created record")
    expected_next_watering_date = (
        watering_result.record.watered_at.astimezone(APP_TIMEZONE).date() + timedelta(days=7)
    )
    if watering_result.state.next_watering_date != expected_next_watering_date:
        raise RuntimeError("Next watering date did not match the plant watering cycle")
    if not watering_detail.history:
        raise RuntimeError("Watering detail did not include the created record in history")
    updated_next_watering_date = (
        watering_result.record.watered_at.astimezone(APP_TIMEZONE).date() + timedelta(days=10)
    )
    if watering_detail.next_watering_date != updated_next_watering_date:
        raise RuntimeError("Watering detail did not use the updated plant watering cycle")
    if watering_detail.history[0].id != watering_result.record.id:
        raise RuntimeError("Watering history did not return the newest created record first")
    if any(
        item.plant_id == created.id
        for section in upcoming_care_after_record.sections
        for item in section.items
    ):
        raise RuntimeError("Freshly watered smoke plant was still listed in today's care")
    if heatmap.start_date != watered_on or heatmap.end_date != watered_on:
        raise RuntimeError("Watering heatmap did not use the requested smoke record date")
    if len(heatmap.days) != 1:
        raise RuntimeError("Watering heatmap did not return exactly the requested smoke date")
    heatmap_day = heatmap.days[0]
    if heatmap_day.date != watered_on:
        raise RuntimeError("Watering heatmap day did not match the smoke record date")
    if heatmap_day.plant_count != 1:
        raise RuntimeError("Watering heatmap mixed in ownerless or other-owner records")
    if heatmap_day.level != 1:
        raise RuntimeError("Watering heatmap level did not match one watered plant")
    heatmap_plants = [(plant.plant_id, plant.name) for plant in heatmap_day.plants]
    if heatmap_plants != [(created.id, current_smoke_name)]:
        raise RuntimeError("Watering heatmap did not expose the current smoke plant name")

    assert_no_ownerless_plants(engine)
    assert_no_ownerless_plant_photos(engine)
    assert_no_ownerless_watering_records(engine)

    return SmokeVerificationResult(
        created_plant_id=created.id,
        created_plant_photo_id=cover_photo_id,
        created_watering_record_id=watering_result.record.id,
    )


def assert_no_ownerless_plants(engine) -> None:
    with engine.connect() as connection:
        ownerless_count = connection.execute(
            text("SELECT COUNT(*) FROM plants WHERE owner_user_id IS NULL")
        ).scalar_one()

    if ownerless_count:
        raise RuntimeError(f"Smoke verification found {ownerless_count} ownerless plants")


def assert_no_ownerless_watering_records(engine) -> None:
    with engine.connect() as connection:
        ownerless_count = connection.execute(
            text("SELECT COUNT(*) FROM watering_records WHERE owner_user_id IS NULL")
        ).scalar_one()

    if ownerless_count:
        raise RuntimeError(
            f"Smoke verification found {ownerless_count} ownerless watering records"
        )


def assert_no_ownerless_plant_photos(engine) -> None:
    with engine.connect() as connection:
        ownerless_count = connection.execute(
            text("SELECT COUNT(*) FROM plant_photos WHERE owner_user_id IS NULL")
        ).scalar_one()

    if ownerless_count:
        raise RuntimeError(
            f"Smoke verification found {ownerless_count} ownerless plant photos"
        )


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
    parser = argparse.ArgumentParser(description="Verify Green Mate database CRUD and type behavior.")
    parser.add_argument("--mode", choices=["local", "turso"], default="local")
    args = parser.parse_args()

    settings = build_settings(args.mode)
    run_migrations(settings)
    result = verify_plant_crud(settings)
    verify_type_round_trip(settings)
    print(
        "OK "
        f"mode={args.mode} "
        f"createdPlantId={result.created_plant_id} "
        f"createdWateringRecordId={result.created_watering_record_id}"
    )


if __name__ == "__main__":
    main()
