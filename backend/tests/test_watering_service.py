from datetime import date, datetime, timezone

import pytest
from sqlmodel import Session

from app.models import Plant, User, WateringRecord
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.services.watering_service import (
    WateringPlantNotFoundError,
    WateringService,
)


FIXED_TODAY = date(2026, 5, 30)


def test_today_care_includes_unrecorded_due_today_and_overdue_owned_plants(
    test_engine,
):
    with Session(test_engine) as session:
        unrecorded = _create_plant(session, "owner-a", "未記録のポトス")
        due_today = _create_plant(
            session,
            "owner-a",
            "今日予定のモンステラ",
            last_watered_at=datetime(2026, 5, 23, 9, 0, tzinfo=timezone.utc),
            watering_cycle_days=7,
        )
        overdue = _create_plant(
            session,
            "owner-a",
            "期限超過のフィカス",
            last_watered_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
            watering_cycle_days=7,
        )
        not_due = _create_plant(
            session,
            "owner-a",
            "まだ不要なサンスベリア",
            last_watered_at=datetime(2026, 5, 29, 9, 0, tzinfo=timezone.utc),
            watering_cycle_days=7,
        )
        other_owner = _create_plant(session, "owner-b", "Bの未記録")

        care = _service(session).get_today_care("owner-a")

    assert care.today == FIXED_TODAY
    assert [item.plant_id for item in care.items] == [
        unrecorded.id,
        due_today.id,
        overdue.id,
    ]
    assert not_due.id not in [item.plant_id for item in care.items]
    assert other_owner.id not in [item.plant_id for item in care.items]

    assert care.items[0].due_status == "unrecorded"
    assert care.items[0].is_due_today is True
    assert care.items[0].last_watered_at is None
    assert care.items[0].next_watering_date is None
    assert care.items[0].plant.name == "未記録のポトス"

    assert care.items[1].due_status == "due_today"
    assert care.items[1].next_watering_date == FIXED_TODAY

    assert care.items[2].due_status == "overdue"
    assert care.items[2].next_watering_date == date(2026, 5, 27)


def test_today_care_returns_empty_items_when_no_owned_plants_or_none_due(test_engine):
    with Session(test_engine) as session:
        _create_user(session, "empty-owner")
        _create_plant(
            session,
            "owner-a",
            "まだ不要なアグラオネマ",
            last_watered_at=datetime(2026, 5, 29, 8, 0, tzinfo=timezone.utc),
            watering_cycle_days=10,
        )
        service = _service(session)

        empty_owner_care = service.get_today_care("empty-owner")
        none_due_care = service.get_today_care("owner-a")

    assert empty_owner_care.today == FIXED_TODAY
    assert empty_owner_care.items == []
    assert none_due_care.today == FIXED_TODAY
    assert none_due_care.items == []


def test_get_plant_watering_calculates_next_date_from_current_cycle_and_history(
    test_engine,
):
    with Session(test_engine) as session:
        plant = _create_plant(
            session,
            "owner-a",
            "周期変更後のカラテア",
            last_watered_at=datetime(2026, 5, 20, 7, 30, tzinfo=timezone.utc),
            watering_cycle_days=10,
        )
        older_record = _add_record(
            session,
            "owner-a",
            plant.id,
            datetime(2026, 5, 18, 7, 30),
        )
        latest_record = _add_record(
            session,
            "owner-a",
            plant.id,
            datetime(2026, 5, 20, 7, 30, tzinfo=timezone.utc),
        )

        plant.watering_cycle_days = 12
        session.add(plant)
        session.commit()

        detail = _service(session).get_plant_watering("owner-a", plant.id)

    assert detail.plant_id == plant.id
    assert detail.last_watered_at is not None
    assert _as_utc(detail.last_watered_at) == datetime(
        2026,
        5,
        20,
        7,
        30,
        tzinfo=timezone.utc,
    )
    assert detail.next_watering_date == date(2026, 6, 1)
    assert detail.is_due_today is False
    assert detail.due_status is None
    assert [record.id for record in detail.history] == [
        latest_record.id,
        older_record.id,
    ]


def test_get_plant_watering_returns_unrecorded_detail_without_history(test_engine):
    with Session(test_engine) as session:
        plant = _create_plant(session, "owner-a", "初回待ちのシェフレラ")

        detail = _service(session).get_plant_watering("owner-a", plant.id)

    assert detail.plant_id == plant.id
    assert detail.last_watered_at is None
    assert detail.next_watering_date is None
    assert detail.is_due_today is True
    assert detail.due_status == "unrecorded"
    assert detail.history == []


def test_get_plant_watering_hides_missing_and_other_owner_plants(test_engine):
    with Session(test_engine) as session:
        other_owner_plant = _create_plant(session, "owner-b", "Bのペペロミア")
        service = _service(session)

        with pytest.raises(WateringPlantNotFoundError):
            service.get_plant_watering("owner-a", other_owner_plant.id)

        with pytest.raises(WateringPlantNotFoundError):
            service.get_plant_watering("owner-a", 9999)


def _service(session: Session) -> WateringService:
    return WateringService(
        plant_repository=PlantRepository(session),
        watering_repository=WateringRepository(session),
        today_provider=lambda: FIXED_TODAY,
    )


def _create_user(session: Session, owner_user_id: str) -> User:
    user = session.get(User, owner_user_id)
    if user is None:
        user = User(id=owner_user_id, clerk_user_id=f"clerk-{owner_user_id}")
        session.add(user)
        session.commit()
    return user


def _create_plant(
    session: Session,
    owner_user_id: str,
    name: str,
    *,
    last_watered_at: datetime | None = None,
    watering_cycle_days: int = 7,
) -> Plant:
    _create_user(session, owner_user_id)
    plant = Plant(
        owner_user_id=owner_user_id,
        name=name,
        watering_cycle_days=watering_cycle_days,
        last_watered_at=last_watered_at,
    )
    session.add(plant)
    session.commit()
    session.refresh(plant)
    return plant


def _add_record(
    session: Session,
    owner_user_id: str,
    plant_id: int,
    watered_at: datetime,
) -> WateringRecord:
    record = WateringRecord(
        owner_user_id=owner_user_id,
        plant_id=plant_id,
        watered_at=watered_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
