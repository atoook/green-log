from datetime import date, datetime, timezone

from pydantic import AliasGenerator, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel
from sqlmodel import SQLModel


alias_config = ConfigDict(
    alias_generator=AliasGenerator(validation_alias=to_camel, serialization_alias=to_camel),
    populate_by_name=True,
)


class PlantCreate(SQLModel):
    model_config = alias_config

    name: str
    acquired_date: date | None = None
    memo: str | None = None
    watering_cycle_days: int


class PlantRead(PlantCreate):
    id: int
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_utc_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
