from datetime import date, datetime, timezone

import pytest
from sqlmodel import Session

from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto
from app.models.user import User
from app.repositories.plant_photo_repository import PlantPhotoRepository
from app.repositories.user_repository import UserRepository
from app.schemas.plant_photo import PlantPhotoCreate
from app.services.plant_photo_service import (
    PlantPhotoNotFoundError,
    PlantPhotoQuotaExceededError,
    PlantPhotoService,
)


class FakeStorage:
    def __init__(self, *, fail_delete: bool = False) -> None:
        self.fail_delete = fail_delete
        self.deletes: list[str] = []

    def upload_object(self, **kwargs) -> None:
        raise AssertionError("upload must not run in lifecycle tests")

    def delete_object(self, object_key: str) -> None:
        self.deletes.append(object_key)
        if self.fail_delete:
            raise RuntimeError("storage delete failed")


class FakeUrlResolver:
    def public_url(self, object_key: str) -> str:
        return f"https://cdn.example.invalid/{object_key}"


def test_register_photo_revalidates_quota_and_returns_display_schema(test_engine):
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        service = _service(session)

        photo = service.register_photo(
            owner_user_id="owner-a",
            plant_id=plant.id,
            payload=PlantPhotoCreate(
                object_key=f"plants/{plant.id}/photo.webp",
                taken_date=date(2026, 6, 1),
                comment="葉が増えた",
            ),
        )

        assert photo.plant_id == plant.id
        assert photo.image_url == f"https://cdn.example.invalid/plants/{plant.id}/photo.webp"
        assert photo.taken_date == date(2026, 6, 1)
        assert photo.comment == "葉が増えた"
        assert photo.is_cover is False


def test_register_photo_rejects_quota_race_without_creating_record(test_engine):
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

        with pytest.raises(PlantPhotoQuotaExceededError):
            _service(session).register_photo(
                owner_user_id="owner-a",
                plant_id=plant.id,
                payload=PlantPhotoCreate(object_key=f"plants/{plant.id}/extra.webp"),
            )

        assert PlantPhotoRepository(session).count_for_plant("owner-a", plant.id) == 5


def test_get_gallery_returns_quota_and_cover_state(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        repository = PlantPhotoRepository(session)
        older = repository.create(
            _photo(
                "owner-a",
                plant.id,
                f"plants/{plant.id}/older.webp",
                now,
                taken_date=date(2026, 5, 30),
            )
        )
        newer = repository.create(
            _photo(
                "owner-a",
                plant.id,
                f"plants/{plant.id}/newer.webp",
                now,
                taken_date=date(2026, 6, 1),
            )
        )
        assert repository.set_cover_photo("owner-a", plant.id, newer.id)

        gallery = _service(session).get_gallery("owner-a", plant.id)

        assert gallery.quota.current_count == 2
        assert gallery.quota.max_count == 5
        assert gallery.quota.unlimited is False
        assert gallery.cover_photo_id == newer.id
        assert [(photo.id, photo.is_cover) for photo in gallery.photos] == [
            (older.id, False),
            (newer.id, True),
        ]


def test_set_cover_photo_rejects_photo_outside_gallery(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        other = _seed_user_and_plant(session, owner_user_id="owner-b", plant_name="B")
        other_photo = PlantPhotoRepository(session).create(
            _photo("owner-b", other.id, f"plants/{other.id}/other.webp", now)
        )

        with pytest.raises(PlantPhotoNotFoundError):
            _service(session).set_cover_photo("owner-a", plant.id, other_photo.id)

        session.refresh(plant)
        assert plant.cover_photo_id is None


def test_delete_photo_deletes_storage_then_record_and_clears_cover(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        repository = PlantPhotoRepository(session)
        photo = repository.create(
            _photo("owner-a", plant.id, f"plants/{plant.id}/photo.webp", now)
        )
        assert repository.set_cover_photo("owner-a", plant.id, photo.id)
        storage = FakeStorage()

        deleted = _service(session, storage=storage).delete_photo(
            "owner-a",
            plant.id,
            photo.id,
        )
        session.refresh(plant)

        assert deleted.id == photo.id
        assert storage.deletes == [f"plants/{plant.id}/photo.webp"]
        assert plant.cover_photo_id is None
        assert repository.get_for_plant("owner-a", plant.id, photo.id) is None


def test_delete_photo_keeps_record_when_storage_delete_fails(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        plant = _seed_user_and_plant(session)
        repository = PlantPhotoRepository(session)
        photo = repository.create(
            _photo("owner-a", plant.id, f"plants/{plant.id}/photo.webp", now)
        )
        assert repository.set_cover_photo("owner-a", plant.id, photo.id)
        storage = FakeStorage(fail_delete=True)

        with pytest.raises(RuntimeError):
            _service(session, storage=storage).delete_photo(
                "owner-a",
                plant.id,
                photo.id,
            )
        session.refresh(plant)

        assert plant.cover_photo_id == photo.id
        assert repository.get_for_plant("owner-a", plant.id, photo.id) is not None


def _seed_user_and_plant(
    session: Session,
    *,
    owner_user_id: str = "owner-a",
    plant_name: str = "Aのモンステラ",
) -> Plant:
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    session.add(
        User(
            id=owner_user_id,
            clerk_user_id=f"clerk-{owner_user_id}",
            status="active",
        )
    )
    session.commit()
    plant = Plant(
        owner_user_id=owner_user_id,
        name=plant_name,
        watering_cycle_days=7,
        created_at=now,
        updated_at=now,
    )
    session.add(plant)
    session.commit()
    session.refresh(plant)
    assert plant.id is not None
    return plant


def _photo(
    owner_user_id: str,
    plant_id: int,
    storage_key: str,
    created_at: datetime,
    *,
    taken_date: date | None = None,
) -> PlantPhoto:
    return PlantPhoto(
        owner_user_id=owner_user_id,
        plant_id=plant_id,
        storage_key=storage_key,
        taken_date=taken_date,
        created_at=created_at,
        updated_at=created_at,
    )


def _service(
    session: Session,
    *,
    storage: FakeStorage | None = None,
) -> PlantPhotoService:
    return PlantPhotoService(
        photo_repository=PlantPhotoRepository(session),
        user_repository=UserRepository(session),
        storage=storage or FakeStorage(),
        url_resolver=FakeUrlResolver(),
    )
