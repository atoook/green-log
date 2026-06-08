from datetime import date, datetime

from pydantic import field_serializer
from sqlmodel import SQLModel

from app.schemas.plant import alias_config, update_alias_config
from app.schemas.watering import serialize_utc_datetime


class PlantPhotoSchema(SQLModel):
    model_config = alias_config


class PlantPhotoCreate(SQLModel):
    model_config = update_alias_config

    object_key: str
    taken_date: date | None = None
    comment: str | None = None


class PlantPhotoUpdate(SQLModel):
    model_config = update_alias_config

    taken_date: date | None = None
    comment: str | None = None


class PlantPhotoUploadRead(PlantPhotoSchema):
    object_key: str


class PlantCoverPhotoUpdate(SQLModel):
    model_config = update_alias_config

    photo_id: str | None


class PlantPhotoRead(PlantPhotoSchema):
    id: str
    plant_id: int
    image_url: str
    taken_date: date | None = None
    comment: str | None = None
    is_cover: bool
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_datetime(value)


class PlantPhotoQuotaRead(PlantPhotoSchema):
    current_count: int
    max_count: int | None
    unlimited: bool


class PlantPhotoGalleryRead(PlantPhotoSchema):
    photos: list[PlantPhotoRead]
    quota: PlantPhotoQuotaRead
    cover_photo_id: str | None = None
