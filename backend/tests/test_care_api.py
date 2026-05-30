from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.db.session import get_session
from app.models import Plant, User
from app.routers.care import get_watering_service, router
from app.schemas.watering import TodayCareRead


def test_today_care_route_returns_only_owned_due_plants(test_engine):
    today = datetime.now(timezone.utc).date()
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
        not_due = _create_plant(
            session,
            "owner-a",
            "まだ不要なサンスベリア",
            last_watered_at=_at_utc_midday(yesterday),
            watering_cycle_days=7,
        )
        other_owner = _create_plant(session, "owner-b", "Bの未記録")
        due_plant_ids = [unrecorded.id, due_today.id, overdue.id]
        not_due_id = not_due.id
        other_owner_id = other_owner.id

    response = _client(test_engine, user_id="owner-a").get("/care/today")

    assert response.status_code == 200
    payload = response.json()
    assert payload["today"] == today.isoformat()
    assert [item["plantId"] for item in payload["items"]] == due_plant_ids
    assert not_due_id not in [item["plantId"] for item in payload["items"]]
    assert other_owner_id not in [item["plantId"] for item in payload["items"]]

    assert payload["items"][0]["dueStatus"] == "unrecorded"
    assert payload["items"][0]["lastWateredAt"] is None
    assert payload["items"][0]["nextWateringDate"] is None
    assert payload["items"][0]["plant"]["name"] == "未記録のポトス"

    assert payload["items"][1]["dueStatus"] == "due_today"
    assert payload["items"][1]["nextWateringDate"] == today.isoformat()
    assert payload["items"][2]["dueStatus"] == "overdue"
    assert payload["items"][2]["nextWateringDate"] == (
        ten_days_ago + timedelta(days=7)
    ).isoformat()
    assert_no_owner_fields(payload)


def test_today_care_route_returns_empty_items_and_today(test_engine):
    with Session(test_engine) as session:
        _create_user(session, "owner-a")

    response = _client(test_engine, user_id="owner-a").get("/care/today")

    assert response.status_code == 200
    assert response.json() == {
        "today": datetime.now(timezone.utc).date().isoformat(),
        "items": [],
    }


def test_today_care_route_requires_authentication_before_service_runs(test_engine):
    calls: list[str] = []

    class FailingWateringService:
        def get_today_care(self, owner_user_id: str):
            calls.append(owner_user_id)
            raise AssertionError("Watering service must not run without auth")

    app = _care_app(test_engine)
    app.dependency_overrides[get_watering_service] = lambda: FailingWateringService()

    with TestClient(app) as client:
        response = client.get("/care/today")

    assert response.status_code == 401
    assert calls == []


def test_today_care_route_uses_internal_current_user_id(test_engine):
    calls: list[str] = []

    class SpyWateringService:
        def get_today_care(self, owner_user_id: str) -> TodayCareRead:
            calls.append(owner_user_id)
            return TodayCareRead(today=date(2026, 5, 30), items=[])

    app = _care_app(test_engine, user_id="internal-user-id")
    app.dependency_overrides[get_watering_service] = lambda: SpyWateringService()

    with TestClient(app) as client:
        response = client.get("/care/today")

    assert response.status_code == 200
    assert response.json() == {"today": "2026-05-30", "items": []}
    assert calls == ["internal-user-id"]


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
