from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

from app.models import Plant, WateringRecord
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.schemas.watering import (
    PlantWateringDetailRead,
    PlantWateringStateRead,
    TodayCareItemRead,
    TodayCareRead,
    WateringPlantSummaryRead,
    WateringRecordRead,
)


class WateringPlantNotFoundError(LookupError):
    pass


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


class WateringService:
    def __init__(
        self,
        plant_repository: PlantRepository,
        watering_repository: WateringRepository,
        today_provider: Callable[[], date] = utc_today,
    ) -> None:
        self.plant_repository = plant_repository
        self.watering_repository = watering_repository
        self.today_provider = today_provider

    def get_today_care(self, owner_user_id: str) -> TodayCareRead:
        today = self.today_provider()
        items: list[TodayCareItemRead] = []
        for plant in self.plant_repository.list(owner_user_id):
            state = self._build_state(plant, today)
            if state.is_due_today:
                items.append(self._build_today_care_item(plant, state))
        return TodayCareRead(today=today, items=items)

    def list_today_care(self, owner_user_id: str) -> TodayCareRead:
        return self.get_today_care(owner_user_id)

    def get_plant_watering(
        self,
        owner_user_id: str,
        plant_id: int,
    ) -> PlantWateringDetailRead:
        plant = self.plant_repository.get_by_id(owner_user_id, plant_id)
        if plant is None:
            raise WateringPlantNotFoundError("Plant not found")

        state = self._build_state(plant, self.today_provider())
        history = [
            self._build_record(record)
            for record in self.watering_repository.list_for_plant(
                owner_user_id,
                plant_id,
            )
        ]
        return PlantWateringDetailRead(
            plant_id=state.plant_id,
            last_watered_at=state.last_watered_at,
            next_watering_date=state.next_watering_date,
            is_due_today=state.is_due_today,
            due_status=state.due_status,
            history=history,
        )

    def _build_today_care_item(
        self,
        plant: Plant,
        state: PlantWateringStateRead,
    ) -> TodayCareItemRead:
        return TodayCareItemRead(
            plant_id=state.plant_id,
            last_watered_at=state.last_watered_at,
            next_watering_date=state.next_watering_date,
            is_due_today=state.is_due_today,
            due_status=state.due_status,
            plant=WateringPlantSummaryRead(
                id=_require_id(plant.id),
                name=plant.name,
                image_url=plant.image_url,
                watering_cycle_days=plant.watering_cycle_days,
            ),
        )

    def _build_state(self, plant: Plant, today: date) -> PlantWateringStateRead:
        last_watered_at = _as_utc(plant.last_watered_at)
        next_watering_date: date | None = None
        due_status = None
        is_due_today = False

        if last_watered_at is None:
            due_status = "unrecorded"
            is_due_today = True
        else:
            next_watering_date = last_watered_at.date() + timedelta(
                days=plant.watering_cycle_days,
            )
            if next_watering_date < today:
                due_status = "overdue"
                is_due_today = True
            elif next_watering_date == today:
                due_status = "due_today"
                is_due_today = True

        return PlantWateringStateRead(
            plant_id=_require_id(plant.id),
            last_watered_at=last_watered_at,
            next_watering_date=next_watering_date,
            is_due_today=is_due_today,
            due_status=due_status,
        )

    def _build_record(self, record: WateringRecord) -> WateringRecordRead:
        return WateringRecordRead(
            id=_require_id(record.id),
            plant_id=record.plant_id,
            watered_at=_as_utc_datetime(record.watered_at),
            created_at=_as_utc_datetime(record.created_at),
        )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _as_utc_datetime(value: datetime) -> datetime:
    return _as_utc(value) or value


def _require_id(value: int | None) -> int:
    if value is None:
        raise ValueError("Persisted watering model is missing an id")
    return value
