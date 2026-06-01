from datetime import date, datetime, timezone

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import Settings
from app.main import app
from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto
from app.routers.plants import get_plant_service
from app.schemas.plant import PlantRead, PlantUpdate
from app.services.plant_service import PlantService, PlantValidationError


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
    assert created["imageUrl"] is None
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


def test_owner_separation_flow_hides_owner_and_preserves_other_user_row(
    api_client,
    override_current_user,
    test_engine,
):
    client = api_client

    override_current_user("user-a")
    first_a_response = client.post(
        "/plants",
        json={
            "name": "Aのモンステラ",
            "wateringCycleDays": 7,
            "ownerUserId": "user-b",
        },
    )
    second_a_response = client.post(
        "/plants",
        json={"name": "Aのポトス", "wateringCycleDays": 10},
    )
    assert first_a_response.status_code == 201
    assert second_a_response.status_code == 201
    first_a = first_a_response.json()
    second_a = second_a_response.json()
    assert_no_owner_fields(first_a)
    assert_no_owner_fields(second_a)

    override_current_user("user-b")
    first_b_response = client.post(
        "/plants",
        json={
            "name": "Bのパキラ",
            "wateringCycleDays": 14,
            "owner_user_id": "user-a",
        },
    )
    assert first_b_response.status_code == 201
    first_b = first_b_response.json()
    assert_no_owner_fields(first_b)

    list_b_response = client.get("/plants")
    detail_b_response = client.get(f"/plants/{first_b['id']}")
    forbidden_detail_response = client.get(f"/plants/{first_a['id']}")

    assert list_b_response.status_code == 200
    assert [plant["id"] for plant in list_b_response.json()] == [first_b["id"]]
    for plant in list_b_response.json():
        assert_no_owner_fields(plant)
    assert detail_b_response.status_code == 200
    assert detail_b_response.json()["id"] == first_b["id"]
    assert_no_owner_fields(detail_b_response.json())
    assert forbidden_detail_response.status_code == 404
    assert forbidden_detail_response.json()["detail"] == "Plant not found"

    with Session(test_engine) as session:
        plant_before = session.get(Plant, first_a["id"])
        assert plant_before is not None
        assert not hasattr(plant_before, "image_url")
        before_snapshot = {
            "owner_user_id": plant_before.owner_user_id,
            "name": plant_before.name,
            "watering_cycle_days": plant_before.watering_cycle_days,
            "updated_at": plant_before.updated_at,
        }
        row_count_before = len(session.exec(select(Plant)).all())

    repeat_forbidden_detail_response = client.get(f"/plants/{first_a['id']}")
    assert repeat_forbidden_detail_response.status_code == 404

    with Session(test_engine) as session:
        plant_after = session.get(Plant, first_a["id"])
        assert plant_after is not None
        assert {
            "owner_user_id": plant_after.owner_user_id,
            "name": plant_after.name,
            "watering_cycle_days": plant_after.watering_cycle_days,
            "updated_at": plant_after.updated_at,
        } == before_snapshot
        assert plant_after.owner_user_id == "user-a"
        assert len(session.exec(select(Plant)).all()) == row_count_before

    override_current_user("user-a")
    list_a_response = client.get("/plants")
    detail_first_a_response = client.get(f"/plants/{first_a['id']}")
    detail_second_a_response = client.get(f"/plants/{second_a['id']}")
    detail_b_as_a_response = client.get(f"/plants/{first_b['id']}")

    assert list_a_response.status_code == 200
    assert [plant["id"] for plant in list_a_response.json()] == [
        first_a["id"],
        second_a["id"],
    ]
    for plant in list_a_response.json():
        assert_no_owner_fields(plant)
    assert detail_first_a_response.status_code == 200
    assert detail_first_a_response.json()["id"] == first_a["id"]
    assert_no_owner_fields(detail_first_a_response.json())
    assert detail_second_a_response.status_code == 200
    assert detail_second_a_response.json()["id"] == second_a["id"]
    assert_no_owner_fields(detail_second_a_response.json())
    assert detail_b_as_a_response.status_code == 404


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


def test_create_plant_ignores_legacy_image_url_input(protected_client, test_engine):
    client = protected_client()

    response = client.post(
        "/plants",
        json={
            "name": "画像入力を無視するポトス",
            "imageUrl": "https://example.com/legacy.jpg",
            "wateringCycleDays": 7,
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["imageUrl"] is None

    with Session(test_engine) as session:
        plant = session.get(Plant, created["id"])

    assert plant is not None
    assert plant.cover_photo_id is None
    assert not hasattr(plant, "image_url")


def test_plant_update_contract_normalizes_existing_editable_fields_only():
    payload = PlantUpdate.model_validate(
        {
            "name": "  窓辺のポトス  ",
            "acquiredDate": "2026-05-28",
            "memo": "   ",
            "wateringCycleDays": 10,
        }
    )

    normalized = PlantService.normalize_update_payload(payload)

    assert normalized.name == "窓辺のポトス"
    assert normalized.acquired_date == date(2026, 5, 28)
    assert normalized.memo is None
    assert normalized.watering_cycle_days == 10
    assert set(normalized.model_fields_set) == {
        "name",
        "acquired_date",
        "memo",
        "watering_cycle_days",
    }
    assert not hasattr(normalized, "owner_user_id")
    assert not hasattr(normalized, "species")


def test_plant_update_contract_supports_partial_patch_fields():
    payload = PlantUpdate.model_validate({"name": "  棚のポトス  "})

    normalized = PlantService.normalize_update_payload(payload)

    assert normalized.name == "棚のポトス"
    assert set(normalized.model_fields_set) == {"name"}
    assert normalized.acquired_date is None
    assert normalized.memo is None
    assert normalized.watering_cycle_days is None


def test_plant_update_contract_preserves_explicit_null_clear_fields():
    payload = PlantUpdate.model_validate(
        {
            "memo": None,
            "acquiredDate": None,
        }
    )

    normalized = PlantService.normalize_update_payload(payload)

    assert normalized.memo is None
    assert normalized.acquired_date is None
    assert set(normalized.model_fields_set) == {"memo", "acquired_date"}
    assert "name" not in normalized.model_fields_set
    assert "watering_cycle_days" not in normalized.model_fields_set


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "name": "  ",
                "acquiredDate": None,
                "memo": None,
                "wateringCycleDays": 7,
            },
            "植物名",
        ),
        (
            {
                "name": None,
            },
            "植物名",
        ),
        (
            {
                "wateringCycleDays": 0,
            },
            "水やり周期",
        ),
        (
            {
                "wateringCycleDays": None,
            },
            "水やり周期",
        ),
    ],
)
def test_plant_update_service_rejects_invalid_domain_values(payload, message):
    update = PlantUpdate.model_validate(payload)

    with pytest.raises(PlantValidationError, match=message):
        PlantService.normalize_update_payload(update)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": "ポトス",
            "acquiredDate": "not-a-date",
            "memo": None,
            "wateringCycleDays": 7,
        },
        {
            "name": "ポトス",
            "acquiredDate": None,
            "memo": None,
            "wateringCycleDays": "毎週",
        },
        {
            "name": "ポトス",
            "acquiredDate": None,
            "memo": None,
            "wateringCycleDays": 7,
            "ownerUserId": "attacker",
        },
        {
            "name": "ポトス",
            "acquiredDate": None,
            "memo": None,
            "wateringCycleDays": 7,
            "species": "Epipremnum aureum",
        },
    ],
)
def test_plant_update_contract_rejects_invalid_or_out_of_scope_fields(payload):
    with pytest.raises(ValueError):
        PlantUpdate.model_validate(payload)


def test_list_and_detail_return_only_owned_cover_photo_url(
    api_client,
    override_current_user,
    test_engine,
):
    override_current_user("owner-a")
    client = api_client

    create_response = client.post(
        "/plants",
        json={"name": "代表写真のポトス", "wateringCycleDays": 7},
    )
    assert create_response.status_code == 201
    plant_id = create_response.json()["id"]

    with Session(test_engine) as session:
        plant = session.get(Plant, plant_id)
        assert plant is not None
        session.add(
            PlantPhoto(
                owner_user_id="owner-b",
                plant_id=plant_id,
                image_url="https://example.com/other-owner.jpg",
            )
        )
        same_owner_cover = PlantPhoto(
            owner_user_id="owner-a",
            plant_id=plant_id,
            image_url="https://example.com/cover.jpg",
        )
        empty_cover = PlantPhoto(
            owner_user_id="owner-a",
            plant_id=plant_id,
            image_url=None,
        )
        session.add(same_owner_cover)
        session.add(empty_cover)
        session.commit()
        session.refresh(same_owner_cover)
        session.refresh(empty_cover)

        plant.cover_photo_id = same_owner_cover.id
        session.add(plant)
        session.commit()

    list_response = client.get("/plants")
    detail_response = client.get(f"/plants/{plant_id}")

    assert list_response.status_code == 200
    assert list_response.json()[0]["imageUrl"] == "https://example.com/cover.jpg"
    assert detail_response.status_code == 200
    assert detail_response.json()["imageUrl"] == "https://example.com/cover.jpg"
    assert_no_owner_fields(detail_response.json())

    with Session(test_engine) as session:
        plant = session.get(Plant, plant_id)
        assert plant is not None
        other_owner_cover = session.exec(
            select(PlantPhoto).where(PlantPhoto.owner_user_id == "owner-b")
        ).one()
        plant.cover_photo_id = other_owner_cover.id
        session.add(plant)
        session.commit()

    mismatched_detail_response = client.get(f"/plants/{plant_id}")
    assert mismatched_detail_response.status_code == 200
    assert mismatched_detail_response.json()["imageUrl"] is None

    with Session(test_engine) as session:
        plant = session.get(Plant, plant_id)
        assert plant is not None
        empty_cover = session.exec(
            select(PlantPhoto).where(
                PlantPhoto.owner_user_id == "owner-a",
                PlantPhoto.image_url.is_(None),
            )
        ).one()
        plant.cover_photo_id = empty_cover.id
        session.add(plant)
        session.commit()

    empty_url_detail_response = client.get(f"/plants/{plant_id}")
    assert empty_url_detail_response.status_code == 200
    assert empty_url_detail_response.json()["imageUrl"] is None


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
                image_url=None,
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
    app_routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    watering_mvp_routes = {
        ("GET", "/care/upcoming"),
        ("GET", "/care/watering-heatmap"),
        ("GET", "/plants/{plant_id}/watering"),
        ("POST", "/plants/{plant_id}/watering-records"),
    }
    watering_route_surface = {
        (method, path)
        for method, path in app_routes
        if path.startswith("/care") or "watering" in path
    }
    app_paths = {path for _, path in app_routes}

    assert plant_routes == {
        ("GET", "/plants"),
        ("POST", "/plants"),
        ("GET", "/plants/{plant_id}"),
    }
    assert watering_route_surface == watering_mvp_routes
    assert not any(
        forbidden in path
        for path in app_paths
        for forbidden in (
            "notification",
            "permission",
            "skip",
            "defer",
            "growth",
            "photo",
            "share",
            "care-type",
            "fertilizer",
            "pruning",
            "repotting",
            "streak",
            "ranking",
            "calendar",
            "weekly",
            "monthly",
            "summary",
            "recommend",
        )
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


def assert_no_owner_fields(payload: dict) -> None:
    assert "ownerUserId" not in payload
    assert "owner_user_id" not in payload
    assert "owner" not in payload
