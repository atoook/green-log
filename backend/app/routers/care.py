from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.db.session import get_session
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.schemas.watering import TodayCareRead
from app.services.watering_service import WateringService

router = APIRouter(prefix="/care", tags=["care"])


def get_watering_service(
    session: Annotated[Session, Depends(get_session)],
) -> WateringService:
    return WateringService(
        PlantRepository(session),
        WateringRepository(session),
    )


@router.get("/today", response_model=TodayCareRead)
def get_today_care(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WateringService, Depends(get_watering_service)],
) -> TodayCareRead:
    return service.get_today_care(current_user.id)
