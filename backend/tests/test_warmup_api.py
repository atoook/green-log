from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app as main_app
from app.routers.warmup import router as warmup_router


def make_client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(warmup_router)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_warmup_accepts_valid_key():
    client = make_client(Settings(warmup_key="dummy-warmup-key"))

    response = client.get("/warmup", headers={"X-Warmup-Key": "dummy-warmup-key"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_warmup_rejects_missing_header_without_secret_details():
    client = make_client(Settings(warmup_key="dummy-warmup-key"))

    response = client.get("/warmup")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
    assert "dummy-warmup-key" not in response.text


def test_warmup_rejects_invalid_key_without_secret_details():
    client = make_client(Settings(warmup_key="dummy-warmup-key"))

    response = client.get("/warmup", headers={"X-Warmup-Key": "wrong-key"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
    assert "dummy-warmup-key" not in response.text
    assert "wrong-key" not in response.text


def test_warmup_fails_closed_when_key_unconfigured():
    client = make_client(Settings(warmup_key=None))

    response = client.get("/warmup", headers={"X-Warmup-Key": "dummy-warmup-key"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Warmup is not configured"}


def test_warmup_fails_closed_when_key_is_blank():
    client = make_client(Settings(warmup_key="  "))

    response = client.get("/warmup", headers={"X-Warmup-Key": "dummy-warmup-key"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Warmup is not configured"}


def test_warmup_route_is_registered_on_application():
    main_app.dependency_overrides[get_settings] = lambda: Settings(
        warmup_key="dummy-warmup-key"
    )
    client = TestClient(main_app)

    try:
        response = client.get(
            "/warmup",
            headers={"X-Warmup-Key": "dummy-warmup-key"},
        )
    finally:
        main_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_warmup_does_not_require_authenticated_user_or_database():
    def fail_dependency():
        raise AssertionError("warmup must not resolve protected dependencies")

    main_app.dependency_overrides[get_settings] = lambda: Settings(
        warmup_key="dummy-warmup-key"
    )
    main_app.dependency_overrides[get_current_user] = fail_dependency
    main_app.dependency_overrides[get_session] = fail_dependency
    client = TestClient(main_app)

    try:
        response = client.get(
            "/warmup",
            headers={"X-Warmup-Key": "dummy-warmup-key"},
        )
    finally:
        main_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
