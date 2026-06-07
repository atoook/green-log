from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.repositories.plant_photo_repository import PlantPhotoRepository
from app.repositories.user_repository import UserRepository
from app.services.plant_photo_service import PlantPhotoService
from app.storage.object_storage import ObjectStorageClient, StorageUrlResolver


def get_plant_photo_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PlantPhotoService:
    return PlantPhotoService(
        photo_repository=PlantPhotoRepository(session),
        user_repository=UserRepository(session),
        storage=ObjectStorageClient(settings),
        url_resolver=StorageUrlResolver(settings),
    )
