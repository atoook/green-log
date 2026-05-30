from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.core.config import Settings
from app.db.session import get_session
from app.main import app
from app.models.plant import Plant
from app.models.user import User


def make_client(current_user: CurrentUser | None = None) -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    if current_user is not None:
        with Session(engine) as session:
            session.add(
                User(
                    id=current_user.id,
                    clerk_user_id=current_user.clerk_user_id,
                    status=current_user.status,
                )
            )
            session.commit()

        app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def make_current_user(user_id: str = "test-user") -> CurrentUser:
    return CurrentUser(id=user_id, clerk_user_id=f"clerk-{user_id}", status="active")


def teardown_function():
    app.dependency_overrides.clear()


def test_create_and_read_plant():
    client = make_client(make_current_user())

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


def test_create_plant_rejects_blank_name():
    client = make_client(make_current_user())

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


def test_create_plant_rejects_invalid_watering_cycle():
    client = make_client(make_current_user())

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


def test_get_missing_plant_returns_404():
    client = make_client(make_current_user())

    response = client.get("/plants/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Plant not found"


def test_repository_timestamp_and_optional_fields_round_trip():
    client = make_client(make_current_user())

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


def test_plant_routes_require_authentication():
    client = make_client()

    assert client.get("/plants").status_code == 401
    assert client.post(
        "/plants",
        json={"name": "ポトス", "wateringCycleDays": 7},
    ).status_code == 401
    assert client.get("/plants/1").status_code == 401


def test_plant_list_and_detail_are_scoped_to_current_user():
    current_user = make_current_user("user-a")
    client = make_client(current_user)

    create_response = client.post(
        "/plants",
        json={"name": "ユーザーAの植物", "wateringCycleDays": 7},
    )
    assert create_response.status_code == 201

    app.dependency_overrides[get_current_user] = lambda: make_current_user("user-b")
    list_response = client.get("/plants")
    detail_response = client.get(f"/plants/{create_response.json()['id']}")

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert detail_response.status_code == 404


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
