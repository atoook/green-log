from app.models.plant import Plant, utc_now
from app.repositories.plant_repository import PlantReadRow, PlantRepository
from app.schemas.plant import PlantCreate, PlantRead, PlantUpdate


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
            watering_cycle_days=payload.watering_cycle_days,
            created_at=now,
            updated_at=now,
        )
        return _plant_to_read(self.repository.create(plant), image_url=None)

    def list_plants(self, owner_user_id: str) -> list[PlantRead]:
        return [
            _row_to_read(row)
            for row in self.repository.list_with_cover_image(owner_user_id)
        ]

    def get_plant(self, owner_user_id: str, plant_id: int) -> PlantRead:
        plant = self.repository.get_by_id_with_cover_image(owner_user_id, plant_id)
        if plant is None:
            raise PlantNotFoundError("Plant not found")
        return _row_to_read(plant)

    @staticmethod
    def normalize_update_payload(payload: PlantUpdate) -> PlantUpdate:
        normalized: dict[str, str | int | object | None] = {}
        supplied_fields = payload.model_fields_set

        if "name" in supplied_fields:
            if payload.name is None:
                raise PlantValidationError("植物名が必要です")
            name = payload.name.strip()
            if not name:
                raise PlantValidationError("植物名が必要です")
            normalized["name"] = name

        if "acquired_date" in supplied_fields:
            normalized["acquired_date"] = payload.acquired_date

        if "memo" in supplied_fields:
            normalized["memo"] = _normalize_optional_text(payload.memo)

        if "watering_cycle_days" in supplied_fields:
            if payload.watering_cycle_days is None or payload.watering_cycle_days < 1:
                raise PlantValidationError("水やり周期は1日以上で入力してください")
            normalized["watering_cycle_days"] = payload.watering_cycle_days

        return PlantUpdate.model_validate(normalized)


def _row_to_read(row: PlantReadRow) -> PlantRead:
    return _plant_to_read(row.plant, image_url=row.cover_image_url)


def _plant_to_read(plant: Plant, image_url: str | None) -> PlantRead:
    return PlantRead.model_validate(
        {
            "id": plant.id,
            "name": plant.name,
            "acquired_date": plant.acquired_date,
            "memo": plant.memo,
            "image_url": image_url,
            "watering_cycle_days": plant.watering_cycle_days,
            "created_at": plant.created_at,
            "updated_at": plant.updated_at,
        }
    )


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized
