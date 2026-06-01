from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.db.session import get_session
from app.repositories.plant_repository import PlantRepository
from app.schemas.plant import PlantCreate, PlantRead, PlantUpdate
from app.services.plant_service import PlantNotFoundError, PlantService, PlantValidationError

router = APIRouter(prefix="/plants", tags=["plants"])


def get_plant_service(session: Annotated[Session, Depends(get_session)]) -> PlantService:
    return PlantService(PlantRepository(session))


@router.get("", response_model=list[PlantRead])
def list_plants(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantService, Depends(get_plant_service)],
) -> list[PlantRead]:
    return service.list_plants(current_user.id)


@router.post("", response_model=PlantRead, status_code=status.HTTP_201_CREATED)
def create_plant(
    payload: PlantCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantService, Depends(get_plant_service)],
) -> PlantRead:
    try:
        return service.create_plant(current_user.id, payload)
    except PlantValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{plant_id}", response_model=PlantRead)
def get_plant(
    plant_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantService, Depends(get_plant_service)],
) -> PlantRead:
    try:
        return service.get_plant(current_user.id, plant_id)
    except PlantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{plant_id}", response_model=PlantRead)
def update_plant(
    plant_id: int,
    payload: PlantUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantService, Depends(get_plant_service)],
) -> PlantRead:
    try:
        return service.update_plant(current_user.id, plant_id, payload)
    except PlantValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PlantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
