import sqlalchemy as sa
from sqlmodel import Session, select

from app.models.plant import Plant
from app.models.plant_photo import PlantPhoto


class PlantPhotoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_plant(self, owner_user_id: str, plant_id: int) -> list[PlantPhoto]:
        statement = (
            self._owner_scoped_photo_select(owner_user_id, plant_id)
            .order_by(
                sa.case((PlantPhoto.taken_date.is_(None), 1), else_=0),
                PlantPhoto.taken_date,
                PlantPhoto.created_at,
                PlantPhoto.id,
            )
        )
        return list(self.session.exec(statement).all())

    def count_for_plant(self, owner_user_id: str, plant_id: int) -> int:
        statement = (
            select(sa.func.count(PlantPhoto.id))
            .join(Plant, PlantPhoto.plant_id == Plant.id)
            .where(
                Plant.owner_user_id == owner_user_id,
                Plant.id == plant_id,
                PlantPhoto.owner_user_id == owner_user_id,
            )
        )
        return int(self.session.exec(statement).one())

    def has_owner_plant(self, owner_user_id: str, plant_id: int) -> bool:
        return self.get_owner_plant(owner_user_id, plant_id) is not None

    def get_owner_plant(self, owner_user_id: str, plant_id: int) -> Plant | None:
        return self._get_owner_plant(owner_user_id, plant_id)

    def get_for_plant(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> PlantPhoto | None:
        statement = self._owner_scoped_photo_select(owner_user_id, plant_id).where(
            PlantPhoto.id == photo_id,
        )
        return self.session.exec(statement).first()

    def create(self, photo: PlantPhoto) -> PlantPhoto:
        self.session.add(photo)
        self.session.commit()
        self.session.refresh(photo)
        return photo

    def set_cover_photo(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> Plant | None:
        plant = self._get_owner_plant(owner_user_id, plant_id)
        if plant is None:
            return None
        photo = self.get_for_plant(owner_user_id, plant_id, photo_id)
        if photo is None:
            return None

        plant.cover_photo_id = photo.id
        self.session.add(plant)
        self.session.commit()
        self.session.refresh(plant)
        return plant

    def clear_cover_photo(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> Plant | None:
        plant = self._get_owner_plant(owner_user_id, plant_id)
        if plant is None or plant.cover_photo_id != photo_id:
            return plant

        plant.cover_photo_id = None
        self.session.add(plant)
        self.session.commit()
        self.session.refresh(plant)
        return plant

    def delete_photo(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> PlantPhoto | None:
        photo = self.get_for_plant(owner_user_id, plant_id, photo_id)
        if photo is None:
            return None

        plant = self._get_owner_plant(owner_user_id, plant_id)
        if plant is not None and plant.cover_photo_id == photo.id:
            plant.cover_photo_id = None
            self.session.add(plant)
        self.session.delete(photo)
        self.session.commit()
        return photo

    def _owner_scoped_photo_select(self, owner_user_id: str, plant_id: int):
        return (
            select(PlantPhoto)
            .join(Plant, PlantPhoto.plant_id == Plant.id)
            .where(
                Plant.owner_user_id == owner_user_id,
                Plant.id == plant_id,
                PlantPhoto.owner_user_id == owner_user_id,
            )
        )

    def _get_owner_plant(self, owner_user_id: str, plant_id: int) -> Plant | None:
        statement = select(Plant).where(
            Plant.owner_user_id == owner_user_id,
            Plant.id == plant_id,
        )
        return self.session.exec(statement).first()
