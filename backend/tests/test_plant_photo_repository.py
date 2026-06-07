from datetime import date, datetime, timezone

from sqlmodel import Session

from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto
from app.models.user import User
from app.repositories.plant_photo_repository import PlantPhotoRepository


def test_plant_photo_repository_lists_and_counts_owner_scoped_photos(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        owner_plant, other_owner_plant = _seed_plants(session, now)
        owner_photo_newer = _photo(
            owner_user_id="owner-a",
            plant_id=owner_plant.id,
            storage_key="plants/1/newer.webp",
            taken_date=date(2026, 6, 2),
            created_at=now,
        )
        owner_photo_older = _photo(
            owner_user_id="owner-a",
            plant_id=owner_plant.id,
            storage_key="plants/1/older.webp",
            taken_date=date(2026, 5, 30),
            created_at=now,
        )
        other_owner_photo = _photo(
            owner_user_id="owner-b",
            plant_id=other_owner_plant.id,
            storage_key="plants/2/other.webp",
            taken_date=date(2026, 6, 1),
            created_at=now,
        )
        session.add(owner_photo_newer)
        session.add(owner_photo_older)
        session.add(other_owner_photo)
        session.commit()

        repository = PlantPhotoRepository(session)

        photos = repository.list_for_plant("owner-a", owner_plant.id)

        assert [photo.storage_key for photo in photos] == [
            "plants/1/older.webp",
            "plants/1/newer.webp",
        ]
        assert repository.count_for_plant("owner-a", owner_plant.id) == 2
        assert repository.count_for_plant("owner-a", other_owner_plant.id) == 0


def test_plant_photo_repository_creates_and_sets_cover_only_within_owner_plant(
    test_engine,
):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        owner_plant, other_owner_plant = _seed_plants(session, now)
        repository = PlantPhotoRepository(session)

        created = repository.create(
            _photo(
                owner_user_id="owner-a",
                plant_id=owner_plant.id,
                storage_key="plants/1/photo.webp",
                taken_date=None,
                created_at=now,
            )
        )
        assert created.id

        assert repository.set_cover_photo("owner-b", owner_plant.id, created.id) is None
        assert repository.set_cover_photo("owner-a", other_owner_plant.id, created.id) is None
        updated = repository.set_cover_photo("owner-a", owner_plant.id, created.id)

        assert updated is not None
        assert updated.cover_photo_id == created.id


def test_plant_photo_repository_delete_clears_cover_reference(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
        owner_plant, _ = _seed_plants(session, now)
        repository = PlantPhotoRepository(session)
        created = repository.create(
            _photo(
                owner_user_id="owner-a",
                plant_id=owner_plant.id,
                storage_key="plants/1/photo.webp",
                taken_date=None,
                created_at=now,
            )
        )
        assert repository.set_cover_photo("owner-a", owner_plant.id, created.id)

        deleted = repository.delete_photo("owner-a", owner_plant.id, created.id)
        session.refresh(owner_plant)

        assert deleted is not None
        assert deleted.id == created.id
        assert owner_plant.cover_photo_id is None
        assert repository.get_for_plant("owner-a", owner_plant.id, created.id) is None


def _seed_plants(session: Session, now: datetime) -> tuple[Plant, Plant]:
    session.add(User(id="owner-a", clerk_user_id="clerk-owner-a", status="active"))
    session.add(User(id="owner-b", clerk_user_id="clerk-owner-b", status="active"))
    session.commit()
    owner_plant = Plant(
        owner_user_id="owner-a",
        name="Aのモンステラ",
        watering_cycle_days=7,
        created_at=now,
        updated_at=now,
    )
    other_owner_plant = Plant(
        owner_user_id="owner-b",
        name="Bのポトス",
        watering_cycle_days=7,
        created_at=now,
        updated_at=now,
    )
    session.add(owner_plant)
    session.add(other_owner_plant)
    session.commit()
    session.refresh(owner_plant)
    session.refresh(other_owner_plant)
    assert owner_plant.id is not None
    assert other_owner_plant.id is not None
    return owner_plant, other_owner_plant


def _photo(
    *,
    owner_user_id: str,
    plant_id: int,
    storage_key: str,
    taken_date: date | None,
    created_at: datetime,
) -> PlantPhoto:
    return PlantPhoto(
        owner_user_id=owner_user_id,
        plant_id=plant_id,
        storage_key=storage_key,
        taken_date=taken_date,
        created_at=created_at,
        updated_at=created_at,
    )
