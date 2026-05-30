from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import app


def test_settings_reads_auth_runtime_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("CLERK_SECRET_KEY", "dummy-clerk-key")
    monkeypatch.setenv(
        "CLERK_AUTHORIZED_PARTIES",
        " https://green-mate.example.com, https://preview.green-mate.example.com ,,",
    )
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "dummy-webhook-key")
    monkeypatch.setenv("LEGACY_OWNER_BACKFILL_USER_ID", "user-backfill-id")

    settings = Settings()

    assert isinstance(settings.clerk_secret_key, SecretStr)
    assert settings.clerk_secret_key.get_secret_value() == "dummy-clerk-key"
    assert settings.clerk_authorized_party_list == [
        "https://green-mate.example.com",
        "https://preview.green-mate.example.com",
    ]
    assert isinstance(settings.clerk_webhook_secret, SecretStr)
    assert settings.clerk_webhook_secret.get_secret_value() == "dummy-webhook-key"
    assert settings.legacy_owner_backfill_user_id == "user-backfill-id"


def test_settings_repr_masks_secret_values():
    settings = Settings(
        clerk_secret_key="dummy-clerk-key",
        clerk_webhook_secret="dummy-webhook-key",
    )

    rendered = repr(settings)

    assert "dummy-clerk-key" not in rendered
    assert "dummy-webhook-key" not in rendered
    assert "**********" in rendered


def test_cors_preflight_allows_authorization_header():
    client = TestClient(app)

    response = client.options(
        "/plants",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
