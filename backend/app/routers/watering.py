from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.repositories.plant_repository import PlantRepository
from app.repositories.watering_repository import WateringRepository
from app.schemas.watering import PlantWateringDetailRead, WateringRecordCreateResult
from app.services.watering_service import (
    WateringAlreadyRecordedTodayError,
    WateringPlantNotFoundError,
    WateringService,
)
from app.storage.s3 import StorageUrlResolver

router = APIRouter(prefix="/plants", tags=["watering"])


def get_watering_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WateringService:
    return WateringService(
        PlantRepository(session),
        WateringRepository(session),
        image_url_resolver=StorageUrlResolver(settings),
    )


@router.get("/{plant_id}/watering", response_model=PlantWateringDetailRead)
def get_plant_watering(
    plant_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WateringService, Depends(get_watering_service)],
) -> PlantWateringDetailRead:
    try:
        return service.get_plant_watering(current_user.id, plant_id)
    except WateringPlantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{plant_id}/watering-records",
    response_model=WateringRecordCreateResult,
    status_code=status.HTTP_201_CREATED,
)
def record_watering(
    plant_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WateringService, Depends(get_watering_service)],
) -> WateringRecordCreateResult:
    try:
        return service.record_watering(current_user.id, plant_id)
    except WateringAlreadyRecordedTodayError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except WateringPlantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
