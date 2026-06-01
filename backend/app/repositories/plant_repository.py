from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Session, select

from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto
from app.schemas.plant import PlantUpdate


@dataclass(frozen=True)
class PlantReadRow:
    plant: Plant
    cover_image_url: str | None


class PlantRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, plant: Plant) -> Plant:
        self.session.add(plant)
        self.session.commit()
        self.session.refresh(plant)
        return plant

    def list(self, owner_user_id: str) -> list[Plant]:
        statement = (
            select(Plant)
            .where(Plant.owner_user_id == owner_user_id)
            .order_by(Plant.id)
        )
        return list(self.session.exec(statement).all())

    def list_with_cover_image(self, owner_user_id: str) -> list[PlantReadRow]:
        statement = (
            self._select_with_cover_image_url(owner_user_id)
            .where(Plant.owner_user_id == owner_user_id)
            .order_by(Plant.id)
        )
        return [
            PlantReadRow(plant=plant, cover_image_url=cover_image_url)
            for plant, cover_image_url in self.session.exec(statement).all()
        ]

    def get_by_id(self, owner_user_id: str, plant_id: int) -> Plant | None:
        statement = select(Plant).where(
            Plant.id == plant_id,
            Plant.owner_user_id == owner_user_id,
        )
        return self.session.exec(statement).first()

    def get_by_id_with_cover_image(
        self,
        owner_user_id: str,
        plant_id: int,
    ) -> PlantReadRow | None:
        statement = self._select_with_cover_image_url(owner_user_id).where(
            Plant.id == plant_id,
            Plant.owner_user_id == owner_user_id,
        )
        row = self.session.exec(statement).first()
        if row is None:
            return None
        plant, cover_image_url = row
        return PlantReadRow(plant=plant, cover_image_url=cover_image_url)

    def update_last_watered_at(
        self,
        owner_user_id: str,
        plant_id: int,
        watered_at: datetime,
    ) -> Plant | None:
        plant = self.get_by_id(owner_user_id, plant_id)
        if plant is None:
            return None

        plant.last_watered_at = watered_at
        self.session.add(plant)
        self.session.flush()
        return plant

    def update_profile(
        self,
        owner_user_id: str,
        plant_id: int,
        payload: PlantUpdate,
        updated_at: datetime,
    ) -> PlantReadRow | None:
        plant = self.get_by_id(owner_user_id, plant_id)
        if plant is None:
            return None

        if "name" in payload.model_fields_set:
            if payload.name is None:
                raise ValueError("Normalized plant update name must not be null")
            plant.name = payload.name
        if "acquired_date" in payload.model_fields_set:
            plant.acquired_date = payload.acquired_date
        if "memo" in payload.model_fields_set:
            plant.memo = payload.memo
        if "watering_cycle_days" in payload.model_fields_set:
            if payload.watering_cycle_days is None:
                raise ValueError("Normalized plant update watering cycle must not be null")
            plant.watering_cycle_days = payload.watering_cycle_days
        plant.updated_at = updated_at

        self.session.add(plant)
        self.session.commit()
        return self.get_by_id_with_cover_image(owner_user_id, plant_id)

    def _select_with_cover_image_url(self, owner_user_id: str):
        cover_join = sa.and_(
            Plant.cover_photo_id == PlantPhoto.id,
            PlantPhoto.owner_user_id == owner_user_id,
            PlantPhoto.plant_id == Plant.id,
        )
        return select(Plant, PlantPhoto.image_url).outerjoin(PlantPhoto, cover_join)
