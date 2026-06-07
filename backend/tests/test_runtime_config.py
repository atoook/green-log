from pathlib import Path

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


def test_settings_reads_storage_runtime_configuration_for_s3(monkeypatch):
    monkeypatch.setenv("STORAGE_ACCESS_KEY_ID", "dummy-access-key")
    monkeypatch.setenv("STORAGE_SECRET_ACCESS_KEY", "dummy-secret-key")
    monkeypatch.setenv("STORAGE_REGION", "ap-northeast-1")
    monkeypatch.setenv("STORAGE_BUCKET_NAME", "green-mate-photos")
    monkeypatch.setenv(
        "STORAGE_PUBLIC_BASE_URL",
        "https://green-mate-photos.s3.ap-northeast-1.amazonaws.com",
    )

    settings = Settings()

    assert isinstance(settings.storage_access_key_id, SecretStr)
    assert settings.storage_access_key_id_value == "dummy-access-key"
    assert isinstance(settings.storage_secret_access_key, SecretStr)
    assert settings.storage_secret_access_key_value == "dummy-secret-key"
    assert settings.storage_region == "ap-northeast-1"
    assert settings.storage_bucket_name == "green-mate-photos"
    assert settings.storage_resolved_public_base_url == (
        "https://green-mate-photos.s3.ap-northeast-1.amazonaws.com"
    )
    assert settings.storage_upload_configured is True


def test_settings_reads_storage_runtime_configuration_for_r2(monkeypatch):
    monkeypatch.setenv("STORAGE_ACCESS_KEY_ID", "r2-access-key")
    monkeypatch.setenv("STORAGE_SECRET_ACCESS_KEY", "r2-secret-key")
    monkeypatch.setenv("STORAGE_REGION", "auto")
    monkeypatch.setenv("STORAGE_BUCKET_NAME", "green-mate-photos")
    monkeypatch.setenv(
        "STORAGE_ENDPOINT_URL",
        "https://example-account.r2.cloudflarestorage.com",
    )
    monkeypatch.setenv(
        "STORAGE_PUBLIC_BASE_URL",
        "https://photos.green-mate.example.com/",
    )

    settings = Settings()

    assert settings.storage_access_key_id_value == "r2-access-key"
    assert settings.storage_secret_access_key_value == "r2-secret-key"
    assert settings.storage_region == "auto"
    assert settings.storage_bucket_name == "green-mate-photos"
    assert settings.storage_endpoint_url == "https://example-account.r2.cloudflarestorage.com"
    assert settings.storage_resolved_public_base_url == (
        "https://photos.green-mate.example.com"
    )
    assert settings.storage_upload_configured is True


def test_settings_repr_masks_secret_values():
    settings = Settings(
        clerk_secret_key="dummy-clerk-key",
        clerk_webhook_secret="dummy-webhook-key",
        storage_access_key_id="dummy-access-key",
        storage_secret_access_key="dummy-secret-key",
    )

    rendered = repr(settings)

    assert "dummy-clerk-key" not in rendered
    assert "dummy-webhook-key" not in rendered
    assert "dummy-access-key" not in rendered
    assert "dummy-secret-key" not in rendered
    assert "**********" in rendered


def test_photo_upload_runtime_dependencies_are_available():
    import boto3
    import python_multipart

    assert boto3.__version__
    assert python_multipart.__version__


def test_env_example_documents_storage_runtime_configuration():
    env_example = (Path(__file__).resolve().parents[1] / ".env.example").read_text()

    assert "STORAGE_ACCESS_KEY_ID=" in env_example
    assert "STORAGE_SECRET_ACCESS_KEY=" in env_example
    assert "STORAGE_REGION=ap-northeast-1" in env_example
    assert "STORAGE_BUCKET_NAME=" in env_example
    assert "STORAGE_ENDPOINT_URL=" in env_example
    assert "STORAGE_PUBLIC_BASE_URL=" in env_example
    assert "AWS_ACCESS_KEY_ID=" not in env_example
    assert "AWS_SECRET_ACCESS_KEY=" not in env_example
    assert "AWS_REGION=" not in env_example
    assert "S3_BUCKET_NAME=" not in env_example


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
