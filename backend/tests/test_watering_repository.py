from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import Plant, User, WateringRecord
from app.repositories.watering_repository import WateringRepository


def test_add_creates_record_for_owned_plant_without_commit(monkeypatch, test_engine):
    watered_at = datetime(2026, 5, 30, 8, 30, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        plant = _create_user_and_plant(session, "owner-a", "Aのモンステラ")
        repository = WateringRepository(session)

        def fail_on_commit() -> None:
            raise AssertionError("WateringRepository.add must not commit")

        monkeypatch.setattr(session, "commit", fail_on_commit)

        record = repository.add(
            WateringRecord(
                owner_user_id="owner-a",
                plant_id=plant.id,
                watered_at=watered_at,
            )
        )

        assert record is not None
        assert record.id is not None
        assert record.owner_user_id == "owner-a"
        assert record.plant_id == plant.id
        assert _as_utc(record.watered_at) == watered_at

        stored = session.get(WateringRecord, record.id)
        assert stored is not None
        assert stored.owner_user_id == "owner-a"


def test_add_does_not_create_records_for_other_owner_or_missing_plant(test_engine):
    watered_at = datetime(2026, 5, 30, 9, 0, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        plant = _create_user_and_plant(session, "owner-a", "Aのポトス")
        session.add(User(id="owner-b", clerk_user_id="clerk-owner-b"))
        session.commit()
        repository = WateringRepository(session)

        other_owner_record = repository.add(
            WateringRecord(
                owner_user_id="owner-b",
                plant_id=plant.id,
                watered_at=watered_at,
            )
        )
        missing_plant_record = repository.add(
            WateringRecord(
                owner_user_id="owner-a",
                plant_id=9999,
                watered_at=watered_at,
            )
        )
        session.commit()

        records = session.exec(select(WateringRecord)).all()

    assert other_owner_record is None
    assert missing_plant_record is None
    assert records == []


def test_list_for_plant_returns_owned_history_newest_first_with_limits(test_engine):
    base_watered_at = datetime(2026, 5, 30, 10, 0, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        plant = _create_user_and_plant(session, "owner-a", "Aのフィカス")
        other_plant = _create_user_and_plant(
            session,
            "owner-b",
            "Bのフィカス",
            clerk_user_id="clerk-owner-b",
        )
        repository = WateringRepository(session)

        for offset_days in range(25):
            repository.add(
                WateringRecord(
                    owner_user_id="owner-a",
                    plant_id=plant.id,
                    watered_at=base_watered_at - timedelta(days=offset_days),
                )
            )
        repository.add(
            WateringRecord(
                owner_user_id="owner-b",
                plant_id=other_plant.id,
                watered_at=base_watered_at,
            )
        )
        session.commit()

        history = repository.list_for_plant("owner-a", plant.id)
        limited_history = repository.list_for_plant("owner-a", plant.id, limit=2)
        unlimited_history = repository.list_for_plant("owner-a", plant.id, limit=None)
        other_owner_history = repository.list_for_plant("owner-b", plant.id)

    assert len(history) == 20
    assert _as_utc(history[0].watered_at) == base_watered_at
    assert _as_utc(history[-1].watered_at) == base_watered_at - timedelta(days=19)
    assert len(limited_history) == 2
    assert [_as_utc(record.watered_at) for record in limited_history] == [
        base_watered_at,
        base_watered_at - timedelta(days=1),
    ]
    assert len(unlimited_history) == 25
    assert other_owner_history == []


def test_list_for_plant_returns_empty_history_for_owned_plant_without_records(
    test_engine,
):
    with Session(test_engine) as session:
        plant = _create_user_and_plant(session, "owner-a", "Aのサンスベリア")
        repository = WateringRepository(session)

        history = repository.list_for_plant("owner-a", plant.id)

    assert history == []


def _create_user_and_plant(
    session: Session,
    owner_user_id: str,
    name: str,
    *,
    clerk_user_id: str | None = None,
) -> Plant:
    session.add(
        User(
            id=owner_user_id,
            clerk_user_id=clerk_user_id or f"clerk-{owner_user_id}",
        )
    )
    plant = Plant(
        owner_user_id=owner_user_id,
        name=name,
        watering_cycle_days=7,
    )
    session.add(plant)
    session.commit()
    session.refresh(plant)
    return plant


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
