from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_user
from app.auth.types import CurrentUser
from app.routers.photo_dependencies import get_plant_photo_service
from app.schemas.plant_photo import PlantPhotoUploadRead
from app.services.plant_photo_service import (
    PlantPhotoNotFoundError,
    PlantPhotoQuotaExceededError,
    PlantPhotoService,
    PlantPhotoValidationError,
)
from app.storage.s3 import StorageConfigurationError, StorageOperationError

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post(
    "/upload",
    response_model=PlantPhotoUploadRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    plant_id: Annotated[int, Form(alias="plantId")],
    file: Annotated[UploadFile, File()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[PlantPhotoService, Depends(get_plant_photo_service)],
) -> PlantPhotoUploadRead:
    try:
        object_key = service.upload_photo(
            owner_user_id=current_user.id,
            plant_id=plant_id,
            filename=file.filename or "",
            content_type=file.content_type or "",
            body=await file.read(),
        )
        return PlantPhotoUploadRead(object_key=object_key)
    except PlantPhotoValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PlantPhotoQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PlantPhotoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (StorageConfigurationError, StorageOperationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image storage is unavailable",
        ) from exc
