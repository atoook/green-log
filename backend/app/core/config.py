from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./green_log.db", alias="DATABASE_URL")
    turso_database_url: str | None = Field(default=None, alias="TURSO_DATABASE_URL")
    turso_auth_token: SecretStr | None = Field(default=None, alias="TURSO_AUTH_TOKEN")
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
    )
    clerk_secret_key: SecretStr | None = Field(default=None, alias="CLERK_SECRET_KEY")
    clerk_authorized_parties: str = Field(default="", alias="CLERK_AUTHORIZED_PARTIES")
    clerk_webhook_secret: SecretStr | None = Field(default=None, alias="CLERK_WEBHOOK_SECRET")
    legacy_owner_backfill_user_id: str | None = Field(
        default=None,
        alias="LEGACY_OWNER_BACKFILL_USER_ID",
    )
    storage_access_key_id: SecretStr | None = Field(
        default=None,
        alias="STORAGE_ACCESS_KEY_ID",
    )
    storage_secret_access_key: SecretStr | None = Field(
        default=None,
        alias="STORAGE_SECRET_ACCESS_KEY",
    )
    storage_region: str = Field(default="ap-northeast-1", alias="STORAGE_REGION")
    storage_bucket_name: str | None = Field(default=None, alias="STORAGE_BUCKET_NAME")
    storage_endpoint_url: str | None = Field(default=None, alias="STORAGE_ENDPOINT_URL")
    storage_public_base_url: str | None = Field(
        default=None,
        alias="STORAGE_PUBLIC_BASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_database_url(self) -> str:
        return self.turso_database_url or self.database_url

    @property
    def turso_auth_token_value(self) -> str | None:
        return self.turso_auth_token.get_secret_value() if self.turso_auth_token else None

    @property
    def storage_access_key_id_value(self) -> str | None:
        return (
            self.storage_access_key_id.get_secret_value()
            if self.storage_access_key_id
            else None
        )

    @property
    def storage_secret_access_key_value(self) -> str | None:
        return (
            self.storage_secret_access_key.get_secret_value()
            if self.storage_secret_access_key
            else None
        )

    @property
    def storage_upload_configured(self) -> bool:
        return bool(
            self.storage_access_key_id_value
            and self.storage_secret_access_key_value
            and self.storage_region
            and self.storage_bucket_name
        )

    @property
    def storage_resolved_public_base_url(self) -> str | None:
        if self.storage_public_base_url:
            return self.storage_public_base_url.rstrip("/")
        return None

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    @property
    def clerk_authorized_party_list(self) -> list[str]:
        return [
            party.strip()
            for party in self.clerk_authorized_parties.split(",")
            if party.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
