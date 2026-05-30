from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WateringRecord(SQLModel, table=True):
    __tablename__ = "watering_records"
    __table_args__ = (
        sa.Index(
            "ix_watering_records_owner_user_id_plant_id_watered_at",
            "owner_user_id",
            "plant_id",
            "watered_at",
        ),
        sa.Index(
            "ix_watering_records_owner_user_id_watered_at",
            "owner_user_id",
            "watered_at",
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
    watered_at: datetime = Field(default_factory=utc_now, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
