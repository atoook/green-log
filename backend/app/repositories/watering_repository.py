from sqlmodel import Session, select

from app.models.plant import Plant
from app.models.watering_record import WateringRecord


DEFAULT_WATERING_HISTORY_LIMIT = 20


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

    def _plant_is_owned(self, owner_user_id: str, plant_id: int) -> bool:
        statement = select(Plant.id).where(
            Plant.id == plant_id,
            Plant.owner_user_id == owner_user_id,
        )
        return self.session.exec(statement).first() is not None
