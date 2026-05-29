from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./green_log.db", alias="DATABASE_URL")
    turso_database_url: str | None = Field(default=None, alias="TURSO_DATABASE_URL")
    turso_auth_token: str | None = Field(default=None, alias="TURSO_AUTH_TOKEN")
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
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
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
