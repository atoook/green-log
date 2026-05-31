from typing import Annotated

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.db.session import get_session
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.schemas.watering import TodayCareRead, WateringHeatmapRead
from app.services.watering_service import WateringHeatmapRangeError, WateringService

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


@router.get("/watering-heatmap", response_model=WateringHeatmapRead)
def get_watering_heatmap(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WateringService, Depends(get_watering_service)],
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> WateringHeatmapRead:
    try:
        return service.get_watering_heatmap(
            current_user.id,
            start_date=from_date,
            end_date=to_date,
        )
    except WateringHeatmapRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
