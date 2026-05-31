from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models import Plant, WateringRecord
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.schemas.watering import (
    PlantWateringDetailRead,
    PlantWateringStateRead,
    TodayCareItemRead,
    TodayCareRead,
    WateringHeatmapDayRead,
    WateringHeatmapPlantRead,
    WateringHeatmapRead,
    WateringPlantSummaryRead,
    WateringRecordRead,
    WateringRecordCreateResult,
)


DEFAULT_HEATMAP_LOOKBACK_DAYS = 90
MAX_HEATMAP_RANGE_DAYS = 366
APP_TIMEZONE = ZoneInfo("Asia/Tokyo")


class WateringPlantNotFoundError(LookupError):
    pass


class WateringHeatmapRangeError(ValueError):
    pass


def app_today() -> date:
    return datetime.now(APP_TIMEZONE).date()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WateringService:
    def __init__(
        self,
        plant_repository: PlantRepository,
        watering_repository: WateringRepository,
        today_provider: Callable[[], date] = app_today,
        now_provider: Callable[[], datetime] = utc_now,
    ) -> None:
        self.plant_repository = plant_repository
        self.watering_repository = watering_repository
        self.today_provider = today_provider
        self.now_provider = now_provider

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

    def get_watering_heatmap(
        self,
        owner_user_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> WateringHeatmapRead:
        start_date, end_date = self._resolve_heatmap_range(start_date, end_date)
        plants_by_date: dict[date, dict[int, WateringHeatmapPlantRead]] = {
            current_date: {}
            for current_date in _date_range(start_date, end_date)
        }

        start_at, end_exclusive = _app_date_range_to_utc(start_date, end_date)

        for row in self.watering_repository.list_for_heatmap(
            owner_user_id,
            start_at,
            end_exclusive,
        ):
            watered_on = _app_date(row.watered_at)
            if watered_on not in plants_by_date:
                continue
            day_plants = plants_by_date[watered_on]
            if row.plant_id not in day_plants:
                day_plants[row.plant_id] = WateringHeatmapPlantRead(
                    plant_id=row.plant_id,
                    name=row.plant_name,
                )

        days = [
            WateringHeatmapDayRead(
                date=current_date,
                plant_count=len(day_plants),
                level=_heatmap_level(len(day_plants)),
                plants=list(day_plants.values()),
            )
            for current_date, day_plants in plants_by_date.items()
        ]
        return WateringHeatmapRead(
            start_date=start_date,
            end_date=end_date,
            days=days,
        )

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

    def record_watering(
        self,
        owner_user_id: str,
        plant_id: int,
        watered_at: datetime | None = None,
    ) -> WateringRecordCreateResult:
        plant = self.plant_repository.get_by_id(owner_user_id, plant_id)
        if plant is None:
            raise WateringPlantNotFoundError("Plant not found")

        watered_at = _as_utc_datetime(watered_at or self.now_provider())
        record = WateringRecord(
            owner_user_id=owner_user_id,
            plant_id=plant_id,
            watered_at=watered_at,
        )
        session = self.watering_repository.session

        try:
            created_record = self.watering_repository.add(record)
            if created_record is None:
                raise WateringPlantNotFoundError("Plant not found")

            updated_plant = self.plant_repository.update_last_watered_at(
                owner_user_id,
                plant_id,
                watered_at,
            )
            if updated_plant is None:
                raise WateringPlantNotFoundError("Plant not found")

            session.commit()
            session.refresh(created_record)
            session.refresh(updated_plant)
        except Exception:
            session.rollback()
            raise

        return WateringRecordCreateResult(
            record=self._build_record(created_record),
            state=self.get_plant_watering(owner_user_id, plant_id),
        )

    def _resolve_heatmap_range(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date]:
        if end_date is None:
            end_date = self.today_provider()
        if start_date is None:
            start_date = end_date - timedelta(days=DEFAULT_HEATMAP_LOOKBACK_DAYS)

        range_days = (end_date - start_date).days + 1
        if range_days <= 0:
            raise WateringHeatmapRangeError(
                "Heatmap start date must be on or before end date",
            )
        if range_days > MAX_HEATMAP_RANGE_DAYS:
            raise WateringHeatmapRangeError(
                "Heatmap range must be 366 days or fewer",
            )
        return start_date, end_date

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
            next_watering_date = _app_date(last_watered_at) + timedelta(
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


def _app_date(value: datetime) -> date:
    return _as_utc_datetime(value).astimezone(APP_TIMEZONE).date()


def _app_date_range_to_utc(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_at = datetime.combine(start_date, datetime.min.time(), tzinfo=APP_TIMEZONE)
    end_exclusive = datetime.combine(
        end_date + timedelta(days=1),
        datetime.min.time(),
        tzinfo=APP_TIMEZONE,
    )
    return start_at.astimezone(timezone.utc), end_exclusive.astimezone(timezone.utc)


def _date_range(start_date: date, end_date: date) -> list[date]:
    return [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    ]


def _heatmap_level(plant_count: int) -> int:
    return min(plant_count, 4)


def _require_id(value: int | None) -> int:
    if value is None:
        raise ValueError("Persisted watering model is missing an id")
    return value
