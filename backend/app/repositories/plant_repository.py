from sqlmodel import Session, select

from app.models.plant import Plant


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

    def get_by_id(self, owner_user_id: str, plant_id: int) -> Plant | None:
        statement = select(Plant).where(
            Plant.id == plant_id,
            Plant.owner_user_id == owner_user_id,
        )
        return self.session.exec(statement).first()
