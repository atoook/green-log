from typing import Annotated

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.schemas.watering import UpcomingCareRead, WateringHeatmapRead
from app.services.watering_service import (
    UpcomingCareDaysError,
    WateringHeatmapRangeError,
    WateringService,
)
from app.storage.object_storage import StorageUrlResolver

router = APIRouter(prefix="/care", tags=["care"])


def get_watering_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WateringService:
    return WateringService(
        PlantRepository(session),
        WateringRepository(session),
        image_url_resolver=StorageUrlResolver(settings),
    )


@router.get("/upcoming", response_model=UpcomingCareRead)
def get_upcoming_care(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WateringService, Depends(get_watering_service)],
    days: Annotated[int, Query(ge=1, le=14)] = 1,
) -> UpcomingCareRead:
    try:
        return service.get_upcoming_care(current_user.id, days=days)
    except UpcomingCareDaysError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


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
