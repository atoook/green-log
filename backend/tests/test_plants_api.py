from datetime import date, datetime, timezone

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.routers.plants import get_plant_service
from app.schemas.plant import PlantRead


def test_create_and_read_plant(protected_client):
    client = protected_client()

    response = client.post(
        "/plants",
        json={
            "name": "リビングのモンステラ",
            "acquiredDate": "2026-05-28",
            "memo": "窓際に置いている",
            "imageUrl": "https://example.com/monstera.jpg",
            "wateringCycleDays": 7,
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["id"] == 1
    assert created["name"] == "リビングのモンステラ"
    assert created["acquiredDate"] == "2026-05-28"
    assert created["memo"] == "窓際に置いている"
    assert created["imageUrl"] == "https://example.com/monstera.jpg"
    assert created["wateringCycleDays"] == 7
    assert "ownerUserId" not in created
    assert "owner_user_id" not in created
    assert "nextWateringDate" not in created

    list_response = client.get("/plants")
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "リビングのモンステラ"

    detail_response = client.get(f"/plants/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created["id"]


def test_create_plant_rejects_blank_name(protected_client):
    client = protected_client()

    response = client.post(
        "/plants",
        json={
            "name": "  ",
            "acquiredDate": None,
            "memo": None,
            "imageUrl": None,
            "wateringCycleDays": 7,
        },
    )

    assert response.status_code == 422
    assert "植物名" in response.json()["detail"]


def test_create_plant_rejects_invalid_watering_cycle(protected_client):
    client = protected_client()

    response = client.post(
        "/plants",
        json={
            "name": "パキラ",
            "acquiredDate": None,
            "memo": None,
            "imageUrl": None,
            "wateringCycleDays": 0,
        },
    )

    assert response.status_code == 422
    assert "水やり周期" in response.json()["detail"]


def test_get_missing_plant_returns_404(protected_client):
    client = protected_client()

    response = client.get("/plants/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Plant not found"


def test_repository_timestamp_and_optional_fields_round_trip(protected_client):
    client = protected_client()

    response = client.post(
        "/plants",
        json={
            "name": "サンスベリア",
            "acquiredDate": date(2026, 5, 28).isoformat(),
            "wateringCycleDays": 14,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["memo"] is None
    assert payload["imageUrl"] is None
    assert payload["createdAt"].endswith("Z")
    assert payload["updatedAt"].endswith("Z")


def test_plant_routes_require_authentication(api_client):
    client = api_client

    assert client.get("/plants").status_code == 401
    assert client.post(
        "/plants",
        json={"name": "ポトス", "wateringCycleDays": 7},
    ).status_code == 401
    assert client.get("/plants/1").status_code == 401


def test_unauthenticated_plant_routes_do_not_execute_service(api_client):
    calls: list[str] = []

    class FailingPlantService:
        def list_plants(self, owner_user_id: str):
            calls.append(f"list:{owner_user_id}")
            raise AssertionError("Plant service must not run without current user")

        def create_plant(self, owner_user_id: str, payload):
            calls.append(f"create:{owner_user_id}")
            raise AssertionError("Plant service must not run without current user")

        def get_plant(self, owner_user_id: str, plant_id: int):
            calls.append(f"detail:{owner_user_id}:{plant_id}")
            raise AssertionError("Plant service must not run without current user")

    def fail_if_resolved() -> FailingPlantService:
        calls.append("dependency")
        return FailingPlantService()

    app.dependency_overrides[get_plant_service] = fail_if_resolved

    responses = [
        api_client.get("/plants"),
        api_client.post("/plants", json={"name": "ポトス", "wateringCycleDays": 7}),
        api_client.get("/plants/1"),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401]
    assert calls == []


def test_valid_current_user_reaches_plant_service_with_internal_user_id(
    api_client,
    override_current_user,
):
    override_current_user("internal-user-id", clerk_user_id="clerk-user-id")
    calls: list[tuple[str, str, int | None]] = []
    now = datetime(2026, 5, 30, tzinfo=timezone.utc)

    class SpyPlantService:
        def list_plants(self, owner_user_id: str) -> list[PlantRead]:
            calls.append(("list", owner_user_id, None))
            return []

        def create_plant(self, owner_user_id: str, payload) -> PlantRead:
            calls.append(("create", owner_user_id, None))
            return PlantRead(
                id=42,
                name=payload.name,
                acquired_date=payload.acquired_date,
                memo=payload.memo,
                image_url=payload.image_url,
                watering_cycle_days=payload.watering_cycle_days,
                created_at=now,
                updated_at=now,
            )

        def get_plant(self, owner_user_id: str, plant_id: int) -> PlantRead:
            calls.append(("detail", owner_user_id, plant_id))
            return PlantRead(
                id=plant_id,
                name="内部IDで取得した植物",
                acquired_date=None,
                memo=None,
                image_url=None,
                watering_cycle_days=7,
                created_at=now,
                updated_at=now,
            )

    app.dependency_overrides[get_plant_service] = lambda: SpyPlantService()

    assert api_client.get("/plants").status_code == 200
    assert api_client.post(
        "/plants",
        json={"name": "ポトス", "wateringCycleDays": 7},
    ).status_code == 201
    assert api_client.get("/plants/42").status_code == 200

    assert calls == [
        ("list", "internal-user-id", None),
        ("create", "internal-user-id", None),
        ("detail", "internal-user-id", 42),
    ]


def test_plant_route_policy_only_exposes_owned_plant_endpoints():
    plant_routes = {
        (next(iter(route.methods)), route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and "plants" in route.tags
    }
    app_paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    }

    assert plant_routes == {
        ("GET", "/plants"),
        ("POST", "/plants"),
        ("GET", "/plants/{plant_id}"),
    }
    assert not any(
        forbidden in path
        for path in app_paths
        for forbidden in ("watering", "today", "care", "growth", "photo", "share")
    )


def test_plant_list_and_detail_are_scoped_to_current_user(
    api_client,
    override_current_user,
):
    override_current_user("user-a")
    client = api_client

    create_response = client.post(
        "/plants",
        json={"name": "ユーザーAの植物", "wateringCycleDays": 7},
    )
    assert create_response.status_code == 201

    override_current_user("user-b")
    list_response = client.get("/plants")
    detail_response = client.get(f"/plants/{create_response.json()['id']}")

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert detail_response.status_code == 404


@pytest.mark.parametrize("user_status", ["disabled", "deleted"])
def test_inactive_current_user_is_rejected_by_shared_override(
    protected_client,
    user_status,
):
    client = protected_client(f"{user_status}-user", status=user_status)

    response = client.get("/plants")

    assert response.status_code == 403


def test_current_user_override_is_cleaned_between_tests(api_client):
    response = api_client.get("/plants")

    assert response.status_code == 401


def test_cors_allows_configured_frontend_origin():
    client = TestClient(app)

    response = client.options(
        "/plants",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_settings_parses_cors_origins_from_comma_separated_value():
    settings = Settings(
        cors_allow_origins=" http://localhost:5173, https://green-mate.example.com ,,"
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "https://green-mate.example.com",
    ]


def test_settings_reads_cors_origins_from_environment(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://green-mate.example.com,https://preview.green-mate.example.com",
    )

    settings = Settings()

    assert settings.cors_origin_list == [
        "https://green-mate.example.com",
        "https://preview.green-mate.example.com",
    ]
