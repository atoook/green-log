from app.models.plant import Plant, utc_now
from app.repositories.plant_repository import PlantRepository
from app.schemas.plant import PlantCreate, PlantRead


class PlantValidationError(ValueError):
    pass


class PlantNotFoundError(LookupError):
    pass


class PlantService:
    def __init__(self, repository: PlantRepository) -> None:
        self.repository = repository

    def create_plant(self, owner_user_id: str, payload: PlantCreate) -> PlantRead:
        name = payload.name.strip()
        if not name:
            raise PlantValidationError("植物名が必要です")

        if payload.watering_cycle_days < 1:
            raise PlantValidationError("水やり周期は1日以上で入力してください")

        now = utc_now()
        plant = Plant(
            owner_user_id=owner_user_id,
            name=name,
            acquired_date=payload.acquired_date,
            memo=payload.memo,
            image_url=payload.image_url,
            watering_cycle_days=payload.watering_cycle_days,
            created_at=now,
            updated_at=now,
        )
        return PlantRead.model_validate(self.repository.create(plant))

    def list_plants(self, owner_user_id: str) -> list[PlantRead]:
        return [
            PlantRead.model_validate(plant)
            for plant in self.repository.list(owner_user_id)
        ]

    def get_plant(self, owner_user_id: str, plant_id: int) -> PlantRead:
        plant = self.repository.get_by_id(owner_user_id, plant_id)
        if plant is None:
            raise PlantNotFoundError("Plant not found")
        return PlantRead.model_validate(plant)
