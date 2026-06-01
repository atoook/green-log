from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlmodel import Session, select

from app.models.plant import Plant
from app.models.watering_record import WateringRecord


DEFAULT_WATERING_HISTORY_LIMIT = 20


@dataclass(frozen=True)
class WateringHeatmapRecordRow:
    watered_on: date
    plant_id: int
    plant_name: str
    watered_at: datetime


class WateringRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, record: WateringRecord) -> WateringRecord | None:
        if not self._plant_is_owned(record.owner_user_id, record.plant_id):
            return None

        self.session.add(record)
        self.session.flush()
        self.session.refresh(record)
        return record

    def list_for_plant(
        self,
        owner_user_id: str,
        plant_id: int,
        *,
        limit: int | None = DEFAULT_WATERING_HISTORY_LIMIT,
    ) -> list[WateringRecord]:
        if not self._plant_is_owned(owner_user_id, plant_id):
            return []

        statement = (
            select(WateringRecord)
            .where(
                WateringRecord.owner_user_id == owner_user_id,
                WateringRecord.plant_id == plant_id,
            )
            .order_by(WateringRecord.watered_at.desc(), WateringRecord.id.desc())
        )
        if limit is not None:
            statement = statement.limit(max(limit, 0))

        return list(self.session.exec(statement).all())

    def exists_for_plant_between(
        self,
        owner_user_id: str,
        plant_id: int,
        start_at: datetime,
        end_exclusive: datetime,
    ) -> bool:
        if not self._plant_is_owned(owner_user_id, plant_id):
            return False

        statement = (
            select(WateringRecord.id)
            .where(
                WateringRecord.owner_user_id == owner_user_id,
                WateringRecord.plant_id == plant_id,
                WateringRecord.watered_at >= start_at,
                WateringRecord.watered_at < end_exclusive,
            )
            .limit(1)
        )
        return self.session.exec(statement).first() is not None

    def list_for_heatmap(
        self,
        owner_user_id: str,
        start_at: datetime,
        end_exclusive: datetime,
    ) -> list[WateringHeatmapRecordRow]:
        statement = (
            select(WateringRecord, Plant.name)
            .join(Plant, Plant.id == WateringRecord.plant_id)
            .where(
                WateringRecord.owner_user_id == owner_user_id,
                Plant.owner_user_id == owner_user_id,
                WateringRecord.watered_at >= start_at,
                WateringRecord.watered_at < end_exclusive,
            )
            .order_by(WateringRecord.watered_at, WateringRecord.id)
        )

        return [
            WateringHeatmapRecordRow(
                watered_on=_as_utc(record.watered_at).date(),
                plant_id=record.plant_id,
                plant_name=plant_name,
                watered_at=_as_utc(record.watered_at),
            )
            for record, plant_name in self.session.exec(statement).all()
        ]

    def _plant_is_owned(self, owner_user_id: str, plant_id: int) -> bool:
        statement = select(Plant.id).where(
            Plant.id == plant_id,
            Plant.owner_user_id == owner_user_id,
        )
        return self.session.exec(statement).first() is not None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
