from datetime import datetime, timezone

from sqlmodel import Session

from app.models import Plant, User
from app.repositories.plant_repository import PlantRepository


def test_plant_model_has_nullable_last_watered_at_summary_without_schedule_state():
    columns = Plant.__table__.c

    assert "last_watered_at" in columns
    assert columns.last_watered_at.nullable
    assert "next_watering_date" not in columns

    indexes = {
        index.name: [column.name for column in index.columns]
        for index in Plant.__table__.indexes
    }
    assert indexes["ix_plants_owner_user_id_last_watered_at"] == [
        "owner_user_id",
        "last_watered_at",
    ]


def test_repository_reads_unrecorded_summary_and_updates_owned_plant_without_commit(
    monkeypatch,
    test_engine,
):
    watered_at = datetime(2026, 5, 30, 8, 15, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        session.add_all(
            [
                User(id="owner-a", clerk_user_id="clerk-owner-a"),
                User(id="owner-b", clerk_user_id="clerk-owner-b"),
            ]
        )
        plant = Plant(
            owner_user_id="owner-a",
            name="Aのモンステラ",
            watering_cycle_days=7,
        )
        session.add(plant)
        session.commit()
        session.refresh(plant)

        repository = PlantRepository(session)
        unrecorded = repository.get_by_id("owner-a", plant.id)

        assert unrecorded is not None
        assert unrecorded.last_watered_at is None

        def fail_on_commit() -> None:
            raise AssertionError("update_last_watered_at must not commit")

        monkeypatch.setattr(session, "commit", fail_on_commit)

        other_owner_result = repository.update_last_watered_at(
            "owner-b",
            plant.id,
            watered_at,
        )
        still_unrecorded = repository.get_by_id("owner-a", plant.id)

        assert other_owner_result is None
        assert still_unrecorded is not None
        assert still_unrecorded.last_watered_at is None

        updated = repository.update_last_watered_at(
            "owner-a",
            plant.id,
            watered_at,
        )

        assert updated is not None
        assert updated.last_watered_at == watered_at
        assert updated.name == "Aのモンステラ"
        assert updated.watering_cycle_days == 7


def test_repository_persists_last_watered_at_after_caller_commits(test_engine):
    watered_at = datetime(2026, 5, 30, 9, 0, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        session.add(User(id="owner-a", clerk_user_id="clerk-owner-a"))
        plant = Plant(
            owner_user_id="owner-a",
            name="Aのポトス",
            watering_cycle_days=10,
        )
        session.add(plant)
        session.commit()
        session.refresh(plant)
        plant_id = plant.id

        repository = PlantRepository(session)
        updated = repository.update_last_watered_at(
            "owner-a",
            plant_id,
            watered_at,
        )
        assert updated is not None
        session.commit()

    with Session(test_engine) as session:
        reloaded = PlantRepository(session).get_by_id("owner-a", plant_id)

    assert reloaded is not None
    assert reloaded.last_watered_at is not None
    assert _as_utc(reloaded.last_watered_at) == watered_at


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
