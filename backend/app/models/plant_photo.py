from datetime import date, datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.models.plant import utc_now


class PlantPhoto(SQLModel, table=True):
    __tablename__ = "plant_photos"
    __table_args__ = (
        sa.Index(
            "ix_plant_photos_owner_user_id_plant_id_created_at",
            "owner_user_id",
            "plant_id",
            "created_at",
        ),
        sa.Index(
            "ix_plant_photos_owner_user_id_plant_id_taken_date",
            "owner_user_id",
            "plant_id",
            "taken_date",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: str = Field(
        sa_column=sa.Column(
            sa.Text(),
            sa.ForeignKey("users.id"),
            nullable=False,
        )
    )
    plant_id: int = Field(
        sa_column=sa.Column(
            sa.Integer(),
            sa.ForeignKey("plants.id"),
            nullable=False,
        )
    )
    image_url: str | None = Field(default=None)
    storage_key: str | None = Field(default=None)
    taken_date: date | None = Field(default=None)
    comment: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
