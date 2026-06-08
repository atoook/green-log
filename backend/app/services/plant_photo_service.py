from collections.abc import Callable
from pathlib import PurePath
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.plant_photo_constraints import (
    ALLOWED_PHOTO_CONTENT_TYPES,
    ALLOWED_PHOTO_EXTENSIONS,
    MAX_PHOTO_UPLOAD_BYTES,
    MAX_PHOTOS_PER_PLANT,
)
from app.models.plant import utc_now
from app.models.plant_photo import PlantPhoto
from app.repositories.plant_photo_repository import PlantPhotoRepository
from app.repositories.user_repository import UserRepository
from app.schemas.plant_photo import (
    PlantPhotoCreate,
    PlantPhotoGalleryRead,
    PlantPhotoQuotaRead,
    PlantPhotoRead,
    PlantPhotoUpdate,
)


class PlantPhotoValidationError(ValueError):
    pass


class PlantPhotoNotFoundError(LookupError):
    pass


class PlantPhotoQuotaExceededError(ValueError):
    pass


class PlantPhotoStorage(Protocol):
    def upload_object(
        self,
        *,
        object_key: str,
        body: bytes,
        content_type: str,
    ) -> None: ...

    def delete_object(self, object_key: str) -> None: ...


class PlantPhotoUrlResolver(Protocol):
    def public_url(self, object_key: str) -> str: ...


class PlantPhotoService:
    def __init__(
        self,
        *,
        photo_repository: PlantPhotoRepository,
        user_repository: UserRepository,
        storage: PlantPhotoStorage,
        url_resolver: PlantPhotoUrlResolver | None = None,
        photo_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.photo_repository = photo_repository
        self.user_repository = user_repository
        self.storage = storage
        self.url_resolver = url_resolver
        self.photo_id_factory = photo_id_factory or (lambda: str(uuid4()))

    def upload_photo(
        self,
        *,
        owner_user_id: str,
        plant_id: int,
        filename: str,
        content_type: str,
        body: bytes,
    ) -> str:
        if not self.photo_repository.has_owner_plant(owner_user_id, plant_id):
            raise PlantPhotoNotFoundError("Plant not found")

        self._validate_quota(owner_user_id, plant_id)
        extension = self._validate_file(
            filename=filename,
            content_type=content_type,
            body=body,
        )

        object_key = f"plants/{plant_id}/{self.photo_id_factory()}.{extension}"
        self.storage.upload_object(
            object_key=object_key,
            body=body,
            content_type=content_type,
        )
        return object_key

    def register_photo(
        self,
        *,
        owner_user_id: str,
        plant_id: int,
        payload: PlantPhotoCreate,
    ) -> PlantPhotoRead:
        plant = self.photo_repository.get_owner_plant(owner_user_id, plant_id)
        if plant is None:
            raise PlantPhotoNotFoundError("Plant not found")

        self._validate_quota(owner_user_id, plant_id)
        self._validate_object_key(payload.object_key, plant_id)
        now = utc_now()
        photo = self.photo_repository.create(
            PlantPhoto(
                owner_user_id=owner_user_id,
                plant_id=plant_id,
                storage_key=payload.object_key,
                taken_date=payload.taken_date,
                comment=payload.comment,
                created_at=now,
                updated_at=now,
            )
        )
        return self._photo_to_read(photo, cover_photo_id=plant.cover_photo_id)

    def get_gallery(self, owner_user_id: str, plant_id: int) -> PlantPhotoGalleryRead:
        plant = self.photo_repository.get_owner_plant(owner_user_id, plant_id)
        if plant is None:
            raise PlantPhotoNotFoundError("Plant not found")

        photos = self.photo_repository.list_for_plant(owner_user_id, plant_id)
        return PlantPhotoGalleryRead(
            photos=[
                self._photo_to_read(photo, cover_photo_id=plant.cover_photo_id)
                for photo in photos
            ],
            quota=self._quota_read(owner_user_id, plant_id),
            cover_photo_id=plant.cover_photo_id,
        )

    def set_cover_photo(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> PlantPhotoGalleryRead:
        plant = self.photo_repository.set_cover_photo(owner_user_id, plant_id, photo_id)
        if plant is None:
            raise PlantPhotoNotFoundError("Photo not found")
        return self.get_gallery(owner_user_id, plant_id)

    def update_photo_metadata(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
        payload: PlantPhotoUpdate,
    ) -> PlantPhotoRead:
        plant = self.photo_repository.get_owner_plant(owner_user_id, plant_id)
        if plant is None:
            raise PlantPhotoNotFoundError("Photo not found")

        photo = self.photo_repository.update_metadata(
            owner_user_id,
            plant_id,
            photo_id,
            taken_date=payload.taken_date,
            comment=payload.comment,
            updated_at=utc_now(),
        )
        if photo is None:
            raise PlantPhotoNotFoundError("Photo not found")

        return self._photo_to_read(photo, cover_photo_id=plant.cover_photo_id)

    def delete_photo(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> PlantPhotoRead:
        plant = self.photo_repository.get_owner_plant(owner_user_id, plant_id)
        photo = self.photo_repository.get_for_plant(owner_user_id, plant_id, photo_id)
        if plant is None or photo is None:
            raise PlantPhotoNotFoundError("Photo not found")

        deleted_read = self._photo_to_read(photo, cover_photo_id=plant.cover_photo_id)
        self.storage.delete_object(photo.storage_key)
        deleted = self.photo_repository.delete_photo(owner_user_id, plant_id, photo_id)
        if deleted is None:
            raise PlantPhotoNotFoundError("Photo not found")
        return deleted_read

    def _validate_quota(self, owner_user_id: str, plant_id: int) -> None:
        if self._photo_upload_unlimited(owner_user_id):
            return

        current_count = self.photo_repository.count_for_plant(owner_user_id, plant_id)
        if current_count >= MAX_PHOTOS_PER_PLANT:
            raise PlantPhotoQuotaExceededError("Photo limit reached")

    def _quota_read(self, owner_user_id: str, plant_id: int) -> PlantPhotoQuotaRead:
        unlimited = self._photo_upload_unlimited(owner_user_id)
        return PlantPhotoQuotaRead(
            current_count=self.photo_repository.count_for_plant(owner_user_id, plant_id),
            max_count=None if unlimited else MAX_PHOTOS_PER_PLANT,
            unlimited=unlimited,
        )

    def _photo_upload_unlimited(self, owner_user_id: str) -> bool:
        user = self.user_repository.get_by_id(owner_user_id)
        return bool(user and user.photo_upload_unlimited)

    def _validate_file(
        self,
        *,
        filename: str,
        content_type: str,
        body: bytes,
    ) -> str:
        extension = PurePath(filename).suffix.removeprefix(".").lower()
        if extension not in ALLOWED_PHOTO_EXTENSIONS:
            raise PlantPhotoValidationError("Unsupported photo extension")
        if content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
            raise PlantPhotoValidationError("Unsupported photo content type")
        if not body:
            raise PlantPhotoValidationError("Photo file is empty")
        if len(body) > MAX_PHOTO_UPLOAD_BYTES:
            raise PlantPhotoValidationError("Photo file is too large")
        return extension

    def _validate_object_key(self, object_key: str, plant_id: int) -> None:
        parts = object_key.split("/")
        if len(parts) != 3 or parts[0] != "plants":
            raise PlantPhotoValidationError("Invalid photo object key")

        try:
            key_plant_id = int(parts[1])
        except ValueError as exc:
            raise PlantPhotoValidationError("Invalid photo object key") from exc

        if key_plant_id != plant_id:
            raise PlantPhotoValidationError("Invalid photo object key")

        filename = parts[2]
        stem, separator, extension = filename.rpartition(".")
        if not stem or separator != "." or extension.lower() not in ALLOWED_PHOTO_EXTENSIONS:
            raise PlantPhotoValidationError("Invalid photo object key")

        try:
            UUID(stem)
        except ValueError as exc:
            raise PlantPhotoValidationError("Invalid photo object key") from exc

    def _photo_to_read(
        self,
        photo: PlantPhoto,
        *,
        cover_photo_id: str | None,
    ) -> PlantPhotoRead:
        return PlantPhotoRead(
            id=photo.id,
            plant_id=photo.plant_id,
            image_url=self._public_url(photo.storage_key),
            taken_date=photo.taken_date,
            comment=photo.comment,
            is_cover=photo.id == cover_photo_id,
            created_at=photo.created_at,
        )

    def _public_url(self, object_key: str) -> str:
        if self.url_resolver is None:
            raise PlantPhotoValidationError("Photo URL resolver is not configured")
        return self.url_resolver.public_url(object_key)
