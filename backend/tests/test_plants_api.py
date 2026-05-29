from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.config import Settings
from app.db.session import get_session
from app.main import app
from app.models.plant import Plant


def make_client() -> TestClient:
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
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_create_and_read_plant():
    client = make_client()

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
    assert "nextWateringDate" not in created

    list_response = client.get("/plants")
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "リビングのモンステラ"

    detail_response = client.get(f"/plants/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created["id"]


def test_create_plant_rejects_blank_name():
    client = make_client()

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
    client = make_client()

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
    client = make_client()

    response = client.get("/plants/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Plant not found"


def test_repository_timestamp_and_optional_fields_round_trip():
    client = make_client()

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
        cors_allow_origins=" http://localhost:5173, https://green-log.example.com ,,"
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "https://green-log.example.com",
    ]


def test_settings_reads_cors_origins_from_environment(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://green-log.example.com,https://preview.green-log.example.com",
    )

    settings = Settings()

    assert settings.cors_origin_list == [
        "https://green-log.example.com",
        "https://preview.green-log.example.com",
    ]
