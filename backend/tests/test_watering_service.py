from datetime import date, datetime, timezone

import pytest
from sqlmodel import Session

from app.domain.plant_constraints import MAX_WATERING_CYCLE_DAYS
from app.models import Plant, PlantPhoto, User, WateringRecord
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.services.watering_service import (
    WateringHeatmapRangeError,
    WateringPlantNotFoundError,
    WateringService,
)


FIXED_TODAY = date(2026, 5, 30)


def test_upcoming_care_groups_today_tomorrow_and_day_after_tomorrow_owned_plants(
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
        tomorrow = _create_plant(
            session,
            "owner-a",
            "明日予定のサンスベリア",
            last_watered_at=datetime(2026, 5, 29, 9, 0, tzinfo=timezone.utc),
            watering_cycle_days=2,
        )
        day_after_tomorrow = _create_plant(
            session,
            "owner-a",
            "明後日予定のホヤ",
            last_watered_at=datetime(2026, 5, 29, 9, 0, tzinfo=timezone.utc),
            watering_cycle_days=3,
        )
        other_owner = _create_plant(session, "owner-b", "Bの未記録")

        care = _service(session).get_upcoming_care("owner-a", days=3)

    assert care.start_date == FIXED_TODAY
    assert care.days == 3
    assert [(section.date, section.kind) for section in care.sections] == [
        (FIXED_TODAY, "today"),
        (date(2026, 5, 31), "tomorrow"),
        (date(2026, 6, 1), "day_after_tomorrow"),
    ]
    assert [item.plant_id for item in care.sections[0].items] == [
        unrecorded.id,
        due_today.id,
        overdue.id,
    ]
    assert [item.plant_id for item in care.sections[1].items] == [tomorrow.id]
    assert [item.plant_id for item in care.sections[2].items] == [day_after_tomorrow.id]
    assert other_owner.id not in [
        item.plant_id for section in care.sections for item in section.items
    ]

    assert care.sections[0].items[0].due_status == "unrecorded"
    assert care.sections[0].items[0].is_due_today is True
    assert care.sections[0].items[0].last_watered_at is None
    assert care.sections[0].items[0].next_watering_date is None
    assert care.sections[0].items[0].plant.name == "未記録のポトス"

    assert care.sections[0].items[1].due_status == "due_today"
    assert care.sections[0].items[1].next_watering_date == FIXED_TODAY

    assert care.sections[0].items[2].due_status == "overdue"
    assert care.sections[0].items[2].next_watering_date == date(2026, 5, 27)


def test_upcoming_care_uses_representative_photo_url(test_engine):
    with Session(test_engine) as session:
        plant = _create_plant(session, "owner-a", "写真つきのポトス")
        other_owner_plant = _create_plant(session, "owner-b", "Bのポトス")
        cover_photo = _add_photo(
            session,
            "owner-a",
            plant.id,
            image_url="https://example.com/cover.jpg",
        )
        other_owner_photo = _add_photo(
            session,
            "owner-b",
            other_owner_plant.id,
            image_url="https://example.com/other.jpg",
        )

        plant.cover_photo_id = cover_photo.id
        session.add(plant)
        session.commit()

        care = _service(session).get_upcoming_care("owner-a")
        assert care.sections[0].items[0].plant.image_url == "https://example.com/cover.jpg"

        plant.cover_photo_id = other_owner_photo.id
        session.add(plant)
        session.commit()

        mismatched_care = _service(session).get_upcoming_care("owner-a")
        assert mismatched_care.sections[0].items[0].plant.image_url is None


def test_upcoming_care_returns_default_today_section_and_empty_items(test_engine):
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

        empty_owner_care = service.get_upcoming_care("empty-owner")
        none_due_care = service.get_upcoming_care("owner-a")

    assert empty_owner_care.start_date == FIXED_TODAY
    assert empty_owner_care.days == 1
    assert [(section.date, section.kind, section.items) for section in empty_owner_care.sections] == [
        (FIXED_TODAY, "today", []),
    ]
    assert none_due_care.start_date == FIXED_TODAY
    assert none_due_care.days == 1
    assert none_due_care.sections[0].items == []


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


def test_get_plant_watering_does_not_overflow_with_legacy_large_cycle(test_engine):
    with Session(test_engine) as session:
        plant = _create_plant(
            session,
            "owner-a",
            "巨大周期が残った植物",
            last_watered_at=datetime(2026, 5, 20, 7, 30, tzinfo=timezone.utc),
            watering_cycle_days=MAX_WATERING_CYCLE_DAYS + 1,
        )

        detail = _service(session).get_plant_watering("owner-a", plant.id)

    assert detail.plant_id == plant.id
    assert detail.last_watered_at is not None
    assert detail.next_watering_date is None
    assert detail.is_due_today is False
    assert detail.due_status is None


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


def test_record_watering_creates_record_updates_summary_and_refreshes_state(
    test_engine,
):
    now = datetime(2026, 5, 30, 10, 15, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        plant = _create_plant(
            session,
            "owner-a",
            "水やりするホヤ",
            last_watered_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
            watering_cycle_days=7,
        )
        service = _service(session, now_provider=lambda: now)

        before = service.get_upcoming_care("owner-a")
        result = service.record_watering("owner-a", plant.id)
        after = service.get_upcoming_care("owner-a")
        session.refresh(plant)

    assert [item.plant_id for item in before.sections[0].items] == [plant.id]
    assert after.sections[0].items == []

    assert result.record.plant_id == plant.id
    assert result.record.watered_at == now
    assert result.state.plant_id == plant.id
    assert result.state.last_watered_at == now
    assert result.state.next_watering_date == date(2026, 6, 6)
    assert result.state.is_due_today is False
    assert result.state.due_status is None
    assert [record.id for record in result.state.history] == [result.record.id]
    assert plant.last_watered_at is not None
    assert _as_utc(plant.last_watered_at) == now
    assert "owner_user_id" not in result.model_dump()
    assert "ownerUserId" not in result.model_dump(by_alias=True)


def test_record_watering_uses_explicit_watered_at_when_provided(test_engine):
    now = datetime(2026, 5, 30, 10, 15, tzinfo=timezone.utc)
    explicit_watered_at = datetime(2026, 5, 29, 21, 30, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        plant = _create_plant(session, "owner-a", "夜に水やりしたポトス")
        result = _service(session, now_provider=lambda: now).record_watering(
            "owner-a",
            plant.id,
            watered_at=explicit_watered_at,
        )
        session.refresh(plant)

    assert result.record.watered_at == explicit_watered_at
    assert result.state.last_watered_at == explicit_watered_at
    assert result.state.next_watering_date == date(2026, 6, 6)
    assert plant.last_watered_at is not None
    assert _as_utc(plant.last_watered_at) == explicit_watered_at


def test_record_watering_hides_missing_and_other_owner_plants_without_records(
    test_engine,
):
    with Session(test_engine) as session:
        other_owner_plant = _create_plant(session, "owner-b", "Bのガジュマル")
        service = _service(session)

        with pytest.raises(WateringPlantNotFoundError):
            service.record_watering("owner-a", other_owner_plant.id)

        with pytest.raises(WateringPlantNotFoundError):
            service.record_watering("owner-a", 9999)

        other_owner_history = WateringRepository(session).list_for_plant(
            "owner-b",
            other_owner_plant.id,
        )

    assert other_owner_history == []


def test_record_watering_rolls_back_record_when_summary_update_fails(test_engine):
    now = datetime(2026, 5, 30, 10, 15, tzinfo=timezone.utc)

    with Session(test_engine) as session:
        plant = _create_plant(session, "owner-a", "rollback対象のシダ")
        service = WateringService(
            plant_repository=_FailingPlantRepository(session),
            watering_repository=WateringRepository(session),
            today_provider=lambda: FIXED_TODAY,
            now_provider=lambda: now,
        )

        with pytest.raises(RuntimeError, match="summary update failed"):
            service.record_watering("owner-a", plant.id)

        session.refresh(plant)
        history = WateringRepository(session).list_for_plant("owner-a", plant.id)

    assert plant.last_watered_at is None
    assert history == []


def test_get_watering_heatmap_fills_inclusive_range_and_distinct_plants(test_engine):
    with Session(test_engine) as session:
        pothos = _create_plant(session, "owner-a", "ポトス")
        monstera = _create_plant(session, "owner-a", "モンステラ")
        other_owner_plant = _create_plant(session, "owner-b", "Bのフィカス")
        _add_record(
            session,
            "owner-a",
            pothos.id,
            datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
        )
        _add_record(
            session,
            "owner-a",
            pothos.id,
            datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        )
        _add_record(
            session,
            "owner-a",
            monstera.id,
            datetime(2026, 5, 29, 9, 0, tzinfo=timezone.utc),
        )
        _add_record(
            session,
            "owner-b",
            other_owner_plant.id,
            datetime(2026, 5, 29, 9, 0, tzinfo=timezone.utc),
        )

        heatmap = _service(session).get_watering_heatmap(
            "owner-a",
            start_date=date(2026, 5, 28),
            end_date=date(2026, 5, 30),
        )
        pothos_id = pothos.id
        monstera_id = monstera.id

    assert heatmap.start_date == date(2026, 5, 28)
    assert heatmap.end_date == date(2026, 5, 30)
    assert [day.date for day in heatmap.days] == [
        date(2026, 5, 28),
        date(2026, 5, 29),
        date(2026, 5, 30),
    ]
    assert heatmap.days[0].plant_count == 1
    assert heatmap.days[0].level == 1
    assert [(plant.plant_id, plant.name) for plant in heatmap.days[0].plants] == [
        (pothos_id, "ポトス"),
    ]
    assert heatmap.days[1].plant_count == 1
    assert heatmap.days[1].level == 1
    assert [(plant.plant_id, plant.name) for plant in heatmap.days[1].plants] == [
        (monstera_id, "モンステラ"),
    ]
    assert heatmap.days[2].plant_count == 0
    assert heatmap.days[2].level == 0
    assert heatmap.days[2].plants == []


def test_get_watering_heatmap_groups_records_by_jst_date(test_engine):
    with Session(test_engine) as session:
        plant = _create_plant(session, "owner-a", "夜のポトス")
        included_record = _add_record(
            session,
            "owner-a",
            plant.id,
            datetime(2026, 5, 30, 15, 30, tzinfo=timezone.utc),
        )
        _add_record(
            session,
            "owner-a",
            plant.id,
            datetime(2026, 5, 31, 14, 59, tzinfo=timezone.utc),
        )
        _add_record(
            session,
            "owner-a",
            plant.id,
            datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc),
        )

        heatmap = _service(session).get_watering_heatmap(
            "owner-a",
            start_date=date(2026, 5, 31),
            end_date=date(2026, 5, 31),
        )

    assert included_record.watered_at.date() == date(2026, 5, 30)
    assert heatmap.days[0].date == date(2026, 5, 31)
    assert heatmap.days[0].plant_count == 1
    assert heatmap.days[0].plants[0].name == "夜のポトス"


def test_get_watering_heatmap_caps_level_at_four(test_engine):
    with Session(test_engine) as session:
        plants = [
            _create_plant(session, "owner-a", f"植物{i}")
            for i in range(1, 6)
        ]
        for plant in plants:
            _add_record(
                session,
                "owner-a",
                plant.id,
                datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc),
            )

        heatmap = _service(session).get_watering_heatmap(
            "owner-a",
            start_date=FIXED_TODAY,
            end_date=FIXED_TODAY,
        )

    assert heatmap.days[0].plant_count == 5
    assert heatmap.days[0].level == 4
    assert [plant.name for plant in heatmap.days[0].plants] == [
        "植物1",
        "植物2",
        "植物3",
        "植物4",
        "植物5",
    ]


def test_get_watering_heatmap_uses_default_recent_three_month_equivalent_range(
    test_engine,
):
    with Session(test_engine) as session:
        plant = _create_plant(session, "owner-a", "既定期間のホヤ")
        _add_record(
            session,
            "owner-a",
            plant.id,
            datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc),
        )

        heatmap = _service(session).get_watering_heatmap("owner-a")

    assert heatmap.start_date == date(2026, 3, 1)
    assert heatmap.end_date == FIXED_TODAY
    assert len(heatmap.days) == 91
    assert heatmap.days[0].date == date(2026, 3, 1)
    assert heatmap.days[-1].date == FIXED_TODAY
    assert heatmap.days[0].plant_count == 1
    assert heatmap.days[-1].plant_count == 0


def test_get_watering_heatmap_rejects_invalid_ranges(test_engine):
    with Session(test_engine) as session:
        service = _service(session)

        with pytest.raises(WateringHeatmapRangeError):
            service.get_watering_heatmap(
                "owner-a",
                start_date=date(2026, 5, 31),
                end_date=date(2026, 5, 30),
            )

        with pytest.raises(WateringHeatmapRangeError):
            service.get_watering_heatmap(
                "owner-a",
                start_date=date(2025, 5, 29),
                end_date=date(2026, 5, 30),
            )


class _FailingPlantRepository(PlantRepository):
    def update_last_watered_at(
        self,
        owner_user_id: str,
        plant_id: int,
        watered_at: datetime,
    ) -> Plant | None:
        raise RuntimeError("summary update failed")


def _service(
    session: Session,
    *,
    now_provider=None,
) -> WateringService:
    kwargs = {
        "plant_repository": PlantRepository(session),
        "watering_repository": WateringRepository(session),
        "today_provider": lambda: FIXED_TODAY,
    }
    if now_provider is not None:
        kwargs["now_provider"] = now_provider
    return WateringService(**kwargs)


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


def _add_photo(
    session: Session,
    owner_user_id: str,
    plant_id: int | None,
    *,
    image_url: str | None,
) -> PlantPhoto:
    if plant_id is None:
        raise ValueError("plant_id must be persisted before creating photos")

    photo = PlantPhoto(
        owner_user_id=owner_user_id,
        plant_id=plant_id,
        image_url=image_url,
    )
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
