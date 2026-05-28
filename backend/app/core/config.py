from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./green_log.db", alias="DATABASE_URL")
    turso_database_url: str | None = Field(default=None, alias="TURSO_DATABASE_URL")
    turso_auth_token: str | None = Field(default=None, alias="TURSO_AUTH_TOKEN")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_database_url(self) -> str:
        return self.turso_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
