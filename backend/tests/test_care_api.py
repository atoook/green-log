from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.db.session import get_session
from app.models import Plant, User, WateringRecord
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.routers.care import get_watering_service, router
from app.schemas.watering import UpcomingCareRead, UpcomingCareSectionRead, WateringHeatmapRead
from app.services.watering_service import APP_TIMEZONE, WateringService


def test_upcoming_care_route_returns_owned_plants_grouped_by_requested_days(test_engine):
    today = datetime.now(APP_TIMEZONE).date()
    yesterday = today - timedelta(days=1)
    one_week_ago = today - timedelta(days=7)
    ten_days_ago = today - timedelta(days=10)

    with Session(test_engine) as session:
        unrecorded = _create_plant(session, "owner-a", "未記録のポトス")
        due_today = _create_plant(
            session,
            "owner-a",
            "今日予定のモンステラ",
            last_watered_at=_at_utc_midday(one_week_ago),
            watering_cycle_days=7,
        )
        overdue = _create_plant(
            session,
            "owner-a",
            "期限超過のフィカス",
            last_watered_at=_at_utc_midday(ten_days_ago),
            watering_cycle_days=7,
        )
        tomorrow = _create_plant(
            session,
            "owner-a",
            "明日予定のサンスベリア",
            last_watered_at=_at_utc_midday(yesterday),
            watering_cycle_days=2,
        )
        day_after_tomorrow = _create_plant(
            session,
            "owner-a",
            "明後日予定のホヤ",
            last_watered_at=_at_utc_midday(yesterday),
            watering_cycle_days=3,
        )
        other_owner = _create_plant(session, "owner-b", "Bの未記録")
        due_plant_ids = [unrecorded.id, due_today.id, overdue.id]
        tomorrow_id = tomorrow.id
        day_after_tomorrow_id = day_after_tomorrow.id
        other_owner_id = other_owner.id

    response = _client(test_engine, user_id="owner-a").get("/care/upcoming", params={"days": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["startDate"] == today.isoformat()
    assert payload["days"] == 3
    assert [(section["date"], section["kind"]) for section in payload["sections"]] == [
        (today.isoformat(), "today"),
        ((today + timedelta(days=1)).isoformat(), "tomorrow"),
        ((today + timedelta(days=2)).isoformat(), "day_after_tomorrow"),
    ]
    assert [item["plantId"] for item in payload["sections"][0]["items"]] == due_plant_ids
    assert [item["plantId"] for item in payload["sections"][1]["items"]] == [tomorrow_id]
    assert [item["plantId"] for item in payload["sections"][2]["items"]] == [
        day_after_tomorrow_id
    ]
    all_item_ids = [
        item["plantId"]
        for section in payload["sections"]
        for item in section["items"]
    ]
    assert other_owner_id not in all_item_ids

    assert payload["sections"][0]["items"][0]["dueStatus"] == "unrecorded"
    assert payload["sections"][0]["items"][0]["lastWateredAt"] is None
    assert payload["sections"][0]["items"][0]["nextWateringDate"] is None
    assert payload["sections"][0]["items"][0]["plant"]["name"] == "未記録のポトス"

    assert payload["sections"][0]["items"][1]["dueStatus"] == "due_today"
    assert payload["sections"][0]["items"][1]["nextWateringDate"] == today.isoformat()
    assert payload["sections"][0]["items"][2]["dueStatus"] == "overdue"
    assert payload["sections"][0]["items"][2]["nextWateringDate"] == (
        ten_days_ago + timedelta(days=7)
    ).isoformat()
    assert_no_owner_fields(payload)


def test_upcoming_care_route_defaults_to_today_only(test_engine):
    with Session(test_engine) as session:
        _create_user(session, "owner-a")

    response = _client(test_engine, user_id="owner-a").get("/care/upcoming")

    assert response.status_code == 200
    assert response.json() == {
        "startDate": datetime.now(APP_TIMEZONE).date().isoformat(),
        "days": 1,
        "sections": [
            {
                "date": datetime.now(APP_TIMEZONE).date().isoformat(),
                "kind": "today",
                "items": [],
            }
        ],
    }


def test_upcoming_care_route_keeps_empty_future_sections(test_engine):
    today = datetime.now(APP_TIMEZONE).date()

    with Session(test_engine) as session:
        unrecorded = _create_plant(session, "owner-a", "初回待ちのポトス")
        unrecorded_id = unrecorded.id

    response = _client(test_engine, user_id="owner-a").get("/care/upcoming", params={"days": 3})

    assert response.status_code == 200
    payload = response.json()
    assert [section["date"] for section in payload["sections"]] == [
        today.isoformat(),
        (today + timedelta(days=1)).isoformat(),
        (today + timedelta(days=2)).isoformat(),
    ]
    assert [item["plantId"] for item in payload["sections"][0]["items"]] == [unrecorded_id]
    assert payload["sections"][1]["items"] == []
    assert payload["sections"][2]["items"] == []


def test_upcoming_care_route_rejects_days_outside_mvp_range(test_engine):
    for invalid_days in (0, 15):
        response = _client(test_engine, user_id="owner-a").get(
            "/care/upcoming",
            params={"days": invalid_days},
        )

        assert response.status_code == 422


def test_today_care_route_is_removed(test_engine):
    response = _client(test_engine, user_id="owner-a").get("/care/today")

    assert response.status_code == 404


def test_upcoming_care_route_requires_authentication_before_service_runs(test_engine):
    calls: list[str] = []

    class FailingWateringService:
        def get_upcoming_care(self, owner_user_id: str, days: int = 1):
            calls.append(owner_user_id)
            raise AssertionError("Watering service must not run without auth")

    app = _care_app(test_engine)
    app.dependency_overrides[get_watering_service] = lambda: FailingWateringService()

    with TestClient(app) as client:
        response = client.get("/care/upcoming")

    assert response.status_code == 401
    assert calls == []


def test_upcoming_care_route_uses_internal_current_user_id(test_engine):
    calls: list[str] = []

    class SpyWateringService:
        def get_upcoming_care(self, owner_user_id: str, days: int = 1) -> UpcomingCareRead:
            calls.append(f"{owner_user_id}:{days}")
            return UpcomingCareRead(
                start_date=date(2026, 5, 30),
                days=days,
                sections=[
                    UpcomingCareSectionRead(
                        date=date(2026, 5, 30),
                        kind="today",
                        items=[],
                    )
                ],
            )

    app = _care_app(test_engine, user_id="internal-user-id")
    app.dependency_overrides[get_watering_service] = lambda: SpyWateringService()

    with TestClient(app) as client:
        response = client.get("/care/upcoming", params={"days": 3})

    assert response.status_code == 200
    assert response.json() == {
        "startDate": "2026-05-30",
        "days": 3,
        "sections": [{"date": "2026-05-30", "kind": "today", "items": []}],
    }
    assert calls == ["internal-user-id:3"]


def test_watering_heatmap_route_returns_owned_records_for_requested_range(test_engine):
    watered_on = date(2026, 5, 28)
    empty_day = date(2026, 5, 29)
    range_end = date(2026, 5, 30)

    with Session(test_engine) as session:
        monstera = _create_plant(session, "owner-a", "古いモンステラ名")
        pothos = _create_plant(session, "owner-a", "ポトス")
        other_owner_plant = _create_plant(session, "owner-b", "Bのフィカス")
        monstera_id = monstera.id
        pothos_id = pothos.id

        _create_watering_record(session, "owner-a", monstera_id, watered_on, hour=8)
        _create_watering_record(session, "owner-a", monstera_id, watered_on, hour=10)
        _create_watering_record(session, "owner-a", pothos_id, watered_on, hour=9)
        _create_watering_record(session, "owner-b", other_owner_plant.id, watered_on)
        _create_watering_record(
            session,
            "owner-a",
            monstera_id,
            watered_on - timedelta(days=1),
        )
        _create_watering_record(
            session,
            "owner-a",
            pothos_id,
            range_end + timedelta(days=1),
        )

        monstera.name = "現在のモンステラ名"
        session.add(monstera)
        session.commit()

    response = _client(test_engine, user_id="owner-a").get(
        "/care/watering-heatmap",
        params={"from": watered_on.isoformat(), "to": range_end.isoformat()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["startDate"] == watered_on.isoformat()
    assert payload["endDate"] == range_end.isoformat()
    assert [day["date"] for day in payload["days"]] == [
        watered_on.isoformat(),
        empty_day.isoformat(),
        range_end.isoformat(),
    ]

    active_day = payload["days"][0]
    assert active_day["plantCount"] == 2
    assert active_day["level"] == 2
    assert active_day["plants"] == [
        {"plantId": monstera_id, "name": "現在のモンステラ名"},
        {"plantId": pothos_id, "name": "ポトス"},
    ]
    assert payload["days"][1] == {
        "date": empty_day.isoformat(),
        "plantCount": 0,
        "level": 0,
        "plants": [],
    }
    assert payload["days"][2]["plantCount"] == 0
    assert_no_owner_fields(payload)


def test_watering_heatmap_route_returns_empty_days_without_records(test_engine):
    start = date(2026, 5, 1)
    end = date(2026, 5, 3)

    with Session(test_engine) as session:
        _create_user(session, "owner-a")

    response = _client(test_engine, user_id="owner-a").get(
        "/care/watering-heatmap",
        params={"from": start.isoformat(), "to": end.isoformat()},
    )

    assert response.status_code == 200
    assert response.json() == {
        "startDate": "2026-05-01",
        "endDate": "2026-05-03",
        "days": [
            {"date": "2026-05-01", "plantCount": 0, "level": 0, "plants": []},
            {"date": "2026-05-02", "plantCount": 0, "level": 0, "plants": []},
            {"date": "2026-05-03", "plantCount": 0, "level": 0, "plants": []},
        ],
    }


def test_watering_heatmap_route_uses_default_recent_range(test_engine):
    fixed_today = date(2026, 5, 31)

    app = _care_app(test_engine, user_id="owner-a")

    def fixed_service():
        with Session(test_engine) as session:
            yield WateringService(
                PlantRepository(session),
                WateringRepository(session),
                today_provider=lambda: fixed_today,
            )

    app.dependency_overrides[get_watering_service] = fixed_service

    with Session(test_engine) as session:
        _create_user(session, "owner-a")

    with TestClient(app) as client:
        response = client.get("/care/watering-heatmap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["startDate"] == "2026-03-02"
    assert payload["endDate"] == "2026-05-31"
    assert len(payload["days"]) == 91
    assert payload["days"][0]["date"] == "2026-03-02"
    assert payload["days"][-1]["date"] == "2026-05-31"


def test_watering_heatmap_route_requires_authentication_before_service_runs(test_engine):
    calls: list[str] = []

    class FailingWateringService:
        def get_watering_heatmap(self, owner_user_id: str, **kwargs):
            calls.append(owner_user_id)
            raise AssertionError("Watering service must not run without auth")

    app = _care_app(test_engine)
    app.dependency_overrides[get_watering_service] = lambda: FailingWateringService()

    with TestClient(app) as client:
        response = client.get("/care/watering-heatmap")

    assert response.status_code == 401
    assert calls == []


def test_watering_heatmap_route_rejects_inactive_user_before_service_runs(test_engine):
    calls: list[str] = []

    class FailingWateringService:
        def get_watering_heatmap(self, owner_user_id: str, **kwargs):
            calls.append(owner_user_id)
            raise AssertionError("Watering service must not run for inactive users")

    app = _care_app(test_engine, user_id="inactive-user")
    app.dependency_overrides[get_current_user] = _forbidden_current_user
    app.dependency_overrides[get_watering_service] = lambda: FailingWateringService()

    with TestClient(app) as client:
        response = client.get("/care/watering-heatmap")

    assert response.status_code == 403
    assert calls == []


def test_watering_heatmap_route_uses_internal_current_user_id(test_engine):
    calls: list[tuple[str, date | None, date | None]] = []

    class SpyWateringService:
        def get_watering_heatmap(
            self,
            owner_user_id: str,
            start_date: date | None = None,
            end_date: date | None = None,
        ) -> WateringHeatmapRead:
            calls.append((owner_user_id, start_date, end_date))
            return WateringHeatmapRead(
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 1),
                days=[],
            )

    app = _care_app(test_engine, user_id="internal-user-id")
    app.dependency_overrides[get_watering_service] = lambda: SpyWateringService()

    with TestClient(app) as client:
        response = client.get(
            "/care/watering-heatmap",
            params={"from": "2026-05-01", "to": "2026-05-02"},
        )

    assert response.status_code == 200
    assert calls == [("internal-user-id", date(2026, 5, 1), date(2026, 5, 2))]


def test_watering_heatmap_route_rejects_invalid_range(test_engine):
    reversed_range = _client(test_engine, user_id="owner-a").get(
        "/care/watering-heatmap",
        params={"from": "2026-05-31", "to": "2026-05-30"},
    )
    too_long_range = _client(test_engine, user_id="owner-a").get(
        "/care/watering-heatmap",
        params={"from": "2025-01-01", "to": "2026-01-02"},
    )

    assert reversed_range.status_code == 422
    assert (
        "start date must be on or before end date"
        in reversed_range.json()["detail"]
    )
    assert too_long_range.status_code == 422
    assert "366 days or fewer" in too_long_range.json()["detail"]


def _care_app(test_engine, *, user_id: str | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    def override_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    if user_id is not None:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id=user_id,
            clerk_user_id=f"clerk-{user_id}",
            status="active",
        )
    return app


def _client(test_engine, *, user_id: str) -> TestClient:
    return TestClient(_care_app(test_engine, user_id=user_id))


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


def _create_watering_record(
    session: Session,
    owner_user_id: str,
    plant_id: int,
    watered_on: date,
    *,
    hour: int = 12,
) -> WateringRecord:
    record = WateringRecord(
        owner_user_id=owner_user_id,
        plant_id=plant_id,
        watered_at=datetime(
            watered_on.year,
            watered_on.month,
            watered_on.day,
            hour,
            0,
            tzinfo=timezone.utc,
        ),
        created_at=datetime(
            watered_on.year,
            watered_on.month,
            watered_on.day,
            hour,
            1,
            tzinfo=timezone.utc,
        ),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def _forbidden_current_user() -> CurrentUser:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _at_utc_midday(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, 12, 0, tzinfo=timezone.utc)


def assert_no_owner_fields(value) -> None:
    if isinstance(value, dict):
        assert "ownerUserId" not in value
        assert "owner_user_id" not in value
        assert "owner" not in value
        for child in value.values():
            assert_no_owner_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_owner_fields(child)
