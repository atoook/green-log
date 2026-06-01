from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.db.session import get_session
from app.models import Plant, User, WateringRecord
from app.routers.watering import get_watering_service, router
from app.schemas.watering import (
    PlantWateringDetailRead,
    WateringRecordCreateResult,
    WateringRecordRead,
)
from app.services.watering_service import APP_TIMEZONE


def test_get_plant_watering_route_returns_latest_next_date_and_history(test_engine):
    today = datetime.now(APP_TIMEZONE).date()
    latest_watered_at = _at_utc_midday(today - timedelta(days=7))
    older_watered_at = _at_utc_midday(today - timedelta(days=10))

    with Session(test_engine) as session:
        plant = _create_plant(
            session,
            "owner-a",
            "水やり詳細のモンステラ",
            image_url="https://example.com/monstera.jpg",
            last_watered_at=latest_watered_at,
            watering_cycle_days=7,
        )
        older_record = _create_watering_record(
            session,
            "owner-a",
            plant.id,
            watered_at=older_watered_at,
        )
        latest_record = _create_watering_record(
            session,
            "owner-a",
            plant.id,
            watered_at=latest_watered_at,
        )
        plant_id = plant.id
        latest_record_id = latest_record.id
        older_record_id = older_record.id

    response = _client(test_engine, user_id="owner-a").get(
        f"/plants/{plant_id}/watering"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["plantId"] == plant_id
    assert payload["lastWateredAt"] == _as_api_datetime(latest_watered_at)
    assert payload["nextWateringDate"] == today.isoformat()
    assert payload["isDueToday"] is True
    assert payload["hasWateredToday"] is False
    assert payload["dueStatus"] == "due_today"
    assert [record["id"] for record in payload["history"]] == [
        latest_record_id,
        older_record_id,
    ]
    assert payload["history"][0]["plantId"] == plant_id
    assert payload["history"][0]["wateredAt"] == _as_api_datetime(latest_watered_at)
    assert payload["history"][1]["wateredAt"] == _as_api_datetime(older_watered_at)
    assert_no_owner_fields(payload)


def test_get_plant_watering_route_returns_unrecorded_state_and_empty_history(
    test_engine,
):
    with Session(test_engine) as session:
        plant = _create_plant(session, "owner-a", "未記録のポトス")
        plant_id = plant.id

    response = _client(test_engine, user_id="owner-a").get(
        f"/plants/{plant_id}/watering"
    )

    assert response.status_code == 200
    assert response.json() == {
        "plantId": plant_id,
        "lastWateredAt": None,
        "nextWateringDate": None,
        "isDueToday": True,
        "hasWateredToday": False,
        "dueStatus": "unrecorded",
        "history": [],
    }


def test_record_watering_route_creates_record_and_retrieved_state_matches(
    test_engine,
):
    with Session(test_engine) as session:
        plant = _create_plant(
            session,
            "owner-a",
            "記録するフィカス",
            watering_cycle_days=10,
        )
        plant_id = plant.id

    client = _client(test_engine, user_id="owner-a")

    create_response = client.post(f"/plants/{plant_id}/watering-records", json={})

    assert create_response.status_code == 201
    created = create_response.json()
    record = created["record"]
    state = created["state"]
    assert record["plantId"] == plant_id
    assert state["plantId"] == plant_id
    assert state["lastWateredAt"] == record["wateredAt"]
    assert state["hasWateredToday"] is True
    assert state["history"][0]["id"] == record["id"]
    assert state["history"][0]["wateredAt"] == record["wateredAt"]
    assert state["nextWateringDate"] == (
        _parse_api_datetime(record["wateredAt"]).astimezone(APP_TIMEZONE).date()
        + timedelta(days=10)
    ).isoformat()
    assert_no_owner_fields(created)

    detail_response = client.get(f"/plants/{plant_id}/watering")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["lastWateredAt"] == record["wateredAt"]
    assert detail["history"][0]["id"] == record["id"]
    assert detail["history"][0]["wateredAt"] == record["wateredAt"]

    with Session(test_engine) as session:
        records = session.exec(select(WateringRecord)).all()
        plant = session.get(Plant, plant_id)

    assert len(records) == 1
    assert plant is not None
    assert _as_api_datetime(plant.last_watered_at) == record["wateredAt"]


def test_app_watering_flow_keeps_upcoming_detail_record_and_storage_consistent(
    api_client,
    override_current_user,
    test_engine,
):
    override_current_user("owner-a")

    create_plant_response = api_client.post(
        "/plants",
        json={
            "name": "今日お世話するポトス",
            "wateringCycleDays": 10,
        },
    )
    assert create_plant_response.status_code == 201
    plant_id = create_plant_response.json()["id"]

    today_before_response = api_client.get("/care/upcoming")
    detail_before_response = api_client.get(f"/plants/{plant_id}/watering")

    assert today_before_response.status_code == 200
    assert detail_before_response.status_code == 200
    today_before = today_before_response.json()
    detail_before = detail_before_response.json()
    assert [item["plantId"] for item in today_before["sections"][0]["items"]] == [plant_id]
    assert today_before["sections"][0]["items"][0]["dueStatus"] == "unrecorded"
    assert today_before["sections"][0]["items"][0]["lastWateredAt"] is None
    assert today_before["sections"][0]["items"][0]["hasWateredToday"] is False
    assert today_before["sections"][0]["items"][0]["nextWateringDate"] is None
    assert detail_before == {
        "plantId": plant_id,
        "lastWateredAt": None,
        "nextWateringDate": None,
        "isDueToday": True,
        "hasWateredToday": False,
        "dueStatus": "unrecorded",
        "history": [],
    }

    create_record_response = api_client.post(
        f"/plants/{plant_id}/watering-records",
        json={},
    )

    assert create_record_response.status_code == 201
    created = create_record_response.json()
    record = created["record"]
    state = created["state"]
    expected_next_date = (
        _parse_api_datetime(record["wateredAt"]).astimezone(APP_TIMEZONE).date()
        + timedelta(days=10)
    ).isoformat()
    assert state["plantId"] == plant_id
    assert state["lastWateredAt"] == record["wateredAt"]
    assert state["nextWateringDate"] == expected_next_date
    assert state["isDueToday"] is False
    assert state["hasWateredToday"] is True
    assert state["dueStatus"] is None
    assert state["history"] == [record]
    assert_no_owner_fields(created)

    detail_after_response = api_client.get(f"/plants/{plant_id}/watering")
    today_after_response = api_client.get("/care/upcoming")

    assert detail_after_response.status_code == 200
    assert today_after_response.status_code == 200
    detail_after = detail_after_response.json()
    today_after = today_after_response.json()
    assert detail_after == state
    assert plant_id not in [
        item["plantId"]
        for section in today_after["sections"]
        for item in section["items"]
    ]

    with Session(test_engine) as session:
        plant = session.get(Plant, plant_id)
        records = session.exec(select(WateringRecord)).all()

    assert plant is not None
    assert _as_api_datetime(plant.last_watered_at) == record["wateredAt"]
    assert [(item.plant_id, _as_api_datetime(item.watered_at)) for item in records] == [
        (plant_id, record["wateredAt"])
    ]


def test_record_watering_route_rejects_duplicate_same_day_records(test_engine):
    with Session(test_engine) as session:
        plant = _create_plant(
            session,
            "owner-a",
            "重複防止するポトス",
            watering_cycle_days=10,
        )
        plant_id = plant.id

    client = _client(test_engine, user_id="owner-a")

    first_response = client.post(f"/plants/{plant_id}/watering-records", json={})
    second_response = client.post(f"/plants/{plant_id}/watering-records", json={})

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Watering already recorded today"}

    with Session(test_engine) as session:
        records = session.exec(select(WateringRecord)).all()

    assert len(records) == 1


def test_watering_routes_hide_missing_and_other_owner_plants_with_404(
    test_engine,
):
    with Session(test_engine) as session:
        other_owner_plant = _create_plant(session, "owner-b", "Bのパキラ")
        other_owner_plant_id = other_owner_plant.id

    client = _client(test_engine, user_id="owner-a")

    responses = [
        client.get("/plants/999/watering"),
        client.post("/plants/999/watering-records", json={}),
        client.get(f"/plants/{other_owner_plant_id}/watering"),
        client.post(f"/plants/{other_owner_plant_id}/watering-records", json={}),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404, 404]
    assert {response.json()["detail"] for response in responses} == {"Plant not found"}
    with Session(test_engine) as session:
        assert session.exec(select(WateringRecord)).all() == []


def test_watering_routes_require_authentication_before_service_runs(test_engine):
    calls: list[str] = []

    class FailingWateringService:
        def get_plant_watering(self, owner_user_id: str, plant_id: int):
            calls.append(f"get:{owner_user_id}:{plant_id}")
            raise AssertionError("Watering service must not run without auth")

        def record_watering(self, owner_user_id: str, plant_id: int):
            calls.append(f"post:{owner_user_id}:{plant_id}")
            raise AssertionError("Watering service must not run without auth")

    app = _watering_app(test_engine)
    app.dependency_overrides[get_watering_service] = lambda: FailingWateringService()

    with TestClient(app) as client:
        responses = [
            client.get("/plants/1/watering"),
            client.post("/plants/1/watering-records", json={}),
        ]

    assert [response.status_code for response in responses] == [401, 401]
    assert calls == []


def test_watering_routes_use_internal_current_user_id(test_engine):
    calls: list[tuple[str, str, int]] = []
    now = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)

    class SpyWateringService:
        def get_plant_watering(
            self,
            owner_user_id: str,
            plant_id: int,
        ) -> PlantWateringDetailRead:
            calls.append(("get", owner_user_id, plant_id))
            return PlantWateringDetailRead(
                plant_id=plant_id,
                last_watered_at=now,
                next_watering_date=date(2026, 6, 6),
                is_due_today=False,
                has_watered_today=True,
                due_status=None,
                history=[],
            )

        def record_watering(
            self,
            owner_user_id: str,
            plant_id: int,
        ) -> WateringRecordCreateResult:
            calls.append(("post", owner_user_id, plant_id))
            record = WateringRecordRead(
                id=12,
                plant_id=plant_id,
                watered_at=now,
                created_at=now,
            )
            return WateringRecordCreateResult(
                record=record,
                state=PlantWateringDetailRead(
                    plant_id=plant_id,
                    last_watered_at=now,
                    next_watering_date=date(2026, 6, 6),
                    is_due_today=False,
                    has_watered_today=True,
                    due_status=None,
                    history=[record],
                ),
            )

    app = _watering_app(test_engine, user_id="internal-user-id")
    app.dependency_overrides[get_watering_service] = lambda: SpyWateringService()

    with TestClient(app) as client:
        get_response = client.get("/plants/42/watering")
        post_response = client.post("/plants/42/watering-records", json={})

    assert get_response.status_code == 200
    assert post_response.status_code == 201
    assert calls == [
        ("get", "internal-user-id", 42),
        ("post", "internal-user-id", 42),
    ]


def test_watering_router_policy_only_exposes_mvp_endpoints():
    watering_routes = {
        (next(iter(route.methods)), route.path)
        for route in router.routes
        if isinstance(route, APIRoute)
    }
    paths = {path for _, path in watering_routes}

    assert watering_routes == {
        ("GET", "/plants/{plant_id}/watering"),
        ("POST", "/plants/{plant_id}/watering-records"),
    }
    assert not any(
        forbidden in path
        for path in paths
        for forbidden in ("csv", "delete", "notification", "skip", "care-type")
    )


def _watering_app(test_engine, *, user_id: str | None = None) -> FastAPI:
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
    return TestClient(_watering_app(test_engine, user_id=user_id))


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
    image_url: str | None = None,
    last_watered_at: datetime | None = None,
    watering_cycle_days: int = 7,
) -> Plant:
    _create_user(session, owner_user_id)
    plant = Plant(
        owner_user_id=owner_user_id,
        name=name,
        image_url=image_url,
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
    plant_id: int | None,
    *,
    watered_at: datetime,
) -> WateringRecord:
    if plant_id is None:
        raise ValueError("plant_id must be persisted before creating watering records")

    record = WateringRecord(
        owner_user_id=owner_user_id,
        plant_id=plant_id,
        watered_at=watered_at,
        created_at=watered_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def _at_utc_midday(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, 12, 0, tzinfo=timezone.utc)


def _as_api_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_api_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
