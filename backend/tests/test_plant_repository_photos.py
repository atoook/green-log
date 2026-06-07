from datetime import datetime, timezone

from sqlmodel import Session

from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto
from app.models.user import User
from app.repositories.plant_repository import PlantRepository


def test_repository_derives_cover_storage_key_only_for_owned_plant_photo(test_engine):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with Session(test_engine) as session:
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
        cover_photo = PlantPhoto(
            owner_user_id="owner-a",
            plant_id=owner_plant.id,
            storage_key="plants/1/cover.jpg",
            created_at=now,
            updated_at=now,
        )
        same_plant_photo = PlantPhoto(
            owner_user_id="owner-a",
            plant_id=owner_plant.id,
            storage_key="plants/1/other.jpg",
            created_at=now,
            updated_at=now,
        )
        other_owner_photo = PlantPhoto(
            owner_user_id="owner-b",
            plant_id=other_owner_plant.id,
            storage_key="plants/2/other-owner.jpg",
            created_at=now,
            updated_at=now,
        )
        session.add(cover_photo)
        session.add(same_plant_photo)
        session.add(other_owner_photo)
        session.commit()
        session.refresh(cover_photo)
        session.refresh(same_plant_photo)
        session.refresh(other_owner_photo)

        owner_plant.cover_photo_id = cover_photo.id
        session.add(owner_plant)
        session.commit()

        rows = PlantRepository(session).list_with_cover_image("owner-a")
        detail = PlantRepository(session).get_by_id_with_cover_image(
            "owner-a",
            owner_plant.id,
        )

        assert [(row.plant.id, row.cover_storage_key) for row in rows] == [
            (owner_plant.id, "plants/1/cover.jpg")
        ]
        assert detail is not None
        assert detail.cover_storage_key == "plants/1/cover.jpg"

        owner_plant.cover_photo_id = other_owner_photo.id
        session.add(owner_plant)
        session.commit()

        mismatched_owner_detail = PlantRepository(session).get_by_id_with_cover_image(
            "owner-a",
            owner_plant.id,
        )
        assert mismatched_owner_detail is not None
        assert mismatched_owner_detail.cover_storage_key is None

        owner_plant.cover_photo_id = same_plant_photo.id
        session.add(owner_plant)
        session.commit()

        same_owner_detail = PlantRepository(session).get_by_id_with_cover_image(
            "owner-a",
            owner_plant.id,
        )
        assert same_owner_detail is not None
        assert same_owner_detail.cover_storage_key == "plants/1/other.jpg"
