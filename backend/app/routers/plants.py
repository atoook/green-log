from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.repositories.plant_repository import PlantRepository
from app.schemas.plant import PlantCreate, PlantRead
from app.services.plant_service import PlantNotFoundError, PlantService, PlantValidationError

router = APIRouter(prefix="/plants", tags=["plants"])


def get_plant_service(session: Annotated[Session, Depends(get_session)]) -> PlantService:
    return PlantService(PlantRepository(session))


@router.get("", response_model=list[PlantRead])
def list_plants(service: Annotated[PlantService, Depends(get_plant_service)]) -> list[PlantRead]:
    return service.list_plants()


@router.post("", response_model=PlantRead, status_code=status.HTTP_201_CREATED)
def create_plant(
    payload: PlantCreate,
    service: Annotated[PlantService, Depends(get_plant_service)],
) -> PlantRead:
    try:
        return service.create_plant(payload)
    except PlantValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{plant_id}", response_model=PlantRead)
def get_plant(
    plant_id: int,
    service: Annotated[PlantService, Depends(get_plant_service)],
) -> PlantRead:
    try:
        return service.get_plant(plant_id)
    except PlantNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
