from datetime import date, datetime, timezone
from typing import Literal

from pydantic import field_serializer
from sqlmodel import SQLModel

from app.schemas.plant import alias_config


DueStatus = Literal["unrecorded", "due_today", "overdue"]
UpcomingCareSectionKind = Literal["today", "tomorrow", "day_after_tomorrow", "future"]
WateringHeatmapLevel = Literal[0, 1, 2, 3, 4]


def serialize_utc_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class WateringSchema(SQLModel):
    model_config = alias_config


class WateringPlantSummaryRead(WateringSchema):
    id: int
    name: str
    image_url: str | None = None
    watering_cycle_days: int


class PlantWateringStateRead(WateringSchema):
    plant_id: int
    last_watered_at: datetime | None = None
    next_watering_date: date | None = None
    is_due_today: bool
    due_status: DueStatus | None = None

    @field_serializer("last_watered_at")
    def serialize_last_watered_at(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return serialize_utc_datetime(value)


class WateringRecordRead(WateringSchema):
    id: int
    plant_id: int
    watered_at: datetime
    created_at: datetime

    @field_serializer("watered_at", "created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return serialize_utc_datetime(value)


class UpcomingCareItemRead(PlantWateringStateRead):
    plant: WateringPlantSummaryRead


class UpcomingCareSectionRead(WateringSchema):
    date: date
    kind: UpcomingCareSectionKind
    items: list[UpcomingCareItemRead]


class UpcomingCareRead(WateringSchema):
    start_date: date
    days: int
    sections: list[UpcomingCareSectionRead]


class PlantWateringDetailRead(PlantWateringStateRead):
    history: list[WateringRecordRead]


class WateringRecordCreateResult(WateringSchema):
    record: WateringRecordRead
    state: PlantWateringDetailRead


class WateringHeatmapPlantRead(WateringSchema):
    plant_id: int
    name: str


class WateringHeatmapDayRead(WateringSchema):
    date: date
    plant_count: int
    level: WateringHeatmapLevel
    plants: list[WateringHeatmapPlantRead]


class WateringHeatmapRead(WateringSchema):
    start_date: date
    end_date: date
    days: list[WateringHeatmapDayRead]
