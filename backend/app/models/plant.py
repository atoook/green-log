from datetime import date, datetime, timezone

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Plant(SQLModel, table=True):
    __tablename__ = "plants"
    __table_args__ = (
        sa.Index("ix_plants_owner_user_id_id", "owner_user_id", "id"),
        sa.Index(
            "ix_plants_owner_user_id_last_watered_at",
            "owner_user_id",
            "last_watered_at",
        ),
        sa.Index("ix_plants_cover_photo_id", "cover_photo_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: str = Field(
        sa_column=sa.Column(
            sa.Text(),
            sa.ForeignKey("users.id"),
            nullable=False,
        )
    )
    name: str = Field(index=True, nullable=False)
    acquired_date: date | None = Field(default=None)
    memo: str | None = Field(default=None)
    cover_photo_id: int | None = Field(default=None, nullable=True)
    watering_cycle_days: int = Field(nullable=False)
    last_watered_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
