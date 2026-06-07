from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.routers.photo_dependencies import get_plant_photo_service
from app.schemas.plant_photo import (
    PlantCoverPhotoUpdate,
    PlantPhotoCreate,
    PlantPhotoGalleryRead,
    PlantPhotoRead,
)
from app.services.plant_photo_service import (
    PlantPhotoNotFoundError,
    PlantPhotoQuotaExceededError,
    PlantPhotoService,
    PlantPhotoValidationError,
)
from app.storage.s3 import StorageConfigurationError, StorageOperationError

router = APIRouter(prefix="/plants", tags=["photos"])


@router.get("/{plant_id}/photos", response_model=PlantPhotoGalleryRead)
def get_plant_photos(
    plant_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantPhotoService, Depends(get_plant_photo_service)],
) -> PlantPhotoGalleryRead:
    try:
        return service.get_gallery(current_user.id, plant_id)
    except PlantPhotoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{plant_id}/photos",
    response_model=PlantPhotoRead,
    status_code=status.HTTP_201_CREATED,
)
def register_plant_photo(
    plant_id: int,
    payload: PlantPhotoCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantPhotoService, Depends(get_plant_photo_service)],
) -> PlantPhotoRead:
    try:
        return service.register_photo(
            owner_user_id=current_user.id,
            plant_id=plant_id,
            payload=payload,
        )
    except PlantPhotoValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PlantPhotoQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PlantPhotoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{plant_id}/cover-photo", response_model=PlantPhotoGalleryRead)
def set_plant_cover_photo(
    plant_id: int,
    payload: PlantCoverPhotoUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantPhotoService, Depends(get_plant_photo_service)],
) -> PlantPhotoGalleryRead:
    try:
        if payload.photo_id is None:
            raise PlantPhotoValidationError("Photo id is required")
        return service.set_cover_photo(current_user.id, plant_id, payload.photo_id)
    except PlantPhotoValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PlantPhotoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{plant_id}/photos/{photo_id}", response_model=PlantPhotoRead)
def delete_plant_photo(
    plant_id: int,
    photo_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantPhotoService, Depends(get_plant_photo_service)],
) -> PlantPhotoRead:
    try:
        return service.delete_photo(current_user.id, plant_id, photo_id)
    except PlantPhotoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (StorageConfigurationError, StorageOperationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image storage is unavailable",
        ) from exc
