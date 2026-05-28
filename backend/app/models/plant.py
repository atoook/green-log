from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Plant(SQLModel, table=True):
    __tablename__ = "plants"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False)
    acquired_date: date | None = Field(default=None)
    memo: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    watering_cycle_days: int = Field(nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
