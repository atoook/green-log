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

    def list(self) -> list[Plant]:
        statement = select(Plant).order_by(Plant.id)
        return list(self.session.exec(statement).all())

    def get_by_id(self, plant_id: int) -> Plant | None:
        return self.session.get(Plant, plant_id)
