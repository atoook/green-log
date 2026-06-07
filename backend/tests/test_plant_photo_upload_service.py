from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto
from app.models.user import User
from app.repositories.plant_photo_repository import PlantPhotoRepository
from app.repositories.user_repository import UserRepository
from app.services.plant_photo_service import (
    PlantPhotoNotFoundError,
    PlantPhotoQuotaExceededError,
    PlantPhotoService,
    PlantPhotoValidationError,
)


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[dict[str, object]] = []

    def upload_object(
        self,
        *,
        object_key: str,
        body: bytes,
        content_type: str,
    ) -> None:
        self.uploads.append(
            {
                "object_key": object_key,
                "body": body,
                "content_type": content_type,
            }
        )


def test_upload_photo_validates_and_stores_s3_object(test_engine):
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        storage = FakeStorage()
        service = _service(session, storage, photo_id_factory=lambda: "photo-uuid")

        object_key = service.upload_photo(
            owner_user_id="owner-a",
            plant_id=plant.id,
            filename="growth.WEBP",
            content_type="image/webp",
            body=b"image-bytes",
        )

        assert object_key == f"plants/{plant.id}/photo-uuid.webp"
        assert "owner-a" not in object_key
        assert storage.uploads == [
            {
                "object_key": object_key,
                "body": b"image-bytes",
                "content_type": "image/webp",
            }
        ]


def test_upload_photo_rejects_quota_before_s3_for_limited_user(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        for index in range(5):
            session.add(
                PlantPhoto(
                    owner_user_id="owner-a",
                    plant_id=plant.id,
                    storage_key=f"plants/{plant.id}/{index}.webp",
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()
        storage = FakeStorage()

        with pytest.raises(PlantPhotoQuotaExceededError):
            _service(session, storage).upload_photo(
                owner_user_id="owner-a",
                plant_id=plant.id,
                filename="extra.webp",
                content_type="image/webp",
                body=b"image-bytes",
            )

        assert storage.uploads == []


def test_upload_photo_allows_unlimited_user_over_general_limit(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session, photo_upload_unlimited=True)
        for index in range(5):
            session.add(
                PlantPhoto(
                    owner_user_id="owner-a",
                    plant_id=plant.id,
                    storage_key=f"plants/{plant.id}/{index}.webp",
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()
        storage = FakeStorage()

        object_key = _service(
            session,
            storage,
            photo_id_factory=lambda: "photo-uuid",
        ).upload_photo(
            owner_user_id="owner-a",
            plant_id=plant.id,
            filename="extra.webp",
            content_type="image/webp",
            body=b"image-bytes",
        )

        assert object_key == f"plants/{plant.id}/photo-uuid.webp"
        assert len(storage.uploads) == 1


@pytest.mark.parametrize(
    ("filename", "content_type", "body"),
    [
        ("photo.gif", "image/gif", b"image-bytes"),
        ("photo.webp", "application/octet-stream", b"image-bytes"),
        ("photo.webp", "image/webp", b""),
        ("photo.webp", "image/webp", b"x" * (5 * 1024 * 1024 + 1)),
    ],
)
def test_upload_photo_rejects_invalid_file_before_s3(
    test_engine,
    filename,
    content_type,
    body,
):
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        storage = FakeStorage()

        with pytest.raises(PlantPhotoValidationError):
            _service(session, storage).upload_photo(
                owner_user_id="owner-a",
                plant_id=plant.id,
                filename=filename,
                content_type=content_type,
                body=body,
            )

        assert storage.uploads == []


def test_upload_photo_rejects_other_owner_plant_before_s3(test_engine):
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        session.add(User(id="owner-b", clerk_user_id="clerk-owner-b", status="active"))
        session.commit()
        storage = FakeStorage()

        with pytest.raises(PlantPhotoNotFoundError):
            _service(session, storage).upload_photo(
                owner_user_id="owner-b",
                plant_id=plant.id,
                filename="photo.webp",
                content_type="image/webp",
                body=b"image-bytes",
            )

        assert storage.uploads == []


def _seed_user_and_plant(
    session: Session,
    *,
    photo_upload_unlimited: bool = False,
) -> Plant:
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    session.add(
        User(
            id="owner-a",
            clerk_user_id="clerk-owner-a",
            status="active",
            photo_upload_unlimited=photo_upload_unlimited,
        )
    )
    session.commit()
    plant = Plant(
        owner_user_id="owner-a",
        name="Aのモンステラ",
        watering_cycle_days=7,
        created_at=now,
        updated_at=now,
    )
    session.add(plant)
    session.commit()
    session.refresh(plant)
    assert plant.id is not None
    return plant


def _service(
    session: Session,
    storage: FakeStorage,
    *,
    photo_id_factory=lambda: "generated-photo-id",
) -> PlantPhotoService:
    return PlantPhotoService(
        photo_repository=PlantPhotoRepository(session),
        user_repository=UserRepository(session),
        storage=storage,
        photo_id_factory=photo_id_factory,
    )
