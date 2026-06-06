from datetime import datetime, timezone
from unittest.mock import ANY

import pytest

from app.routers.photo_dependencies import get_plant_photo_service
from app.routers.photos import _read_limited_upload_file
from app.schemas.plant_photo import (
    PlantPhotoGalleryRead,
    PlantPhotoQuotaRead,
    PlantPhotoRead,
    PlantPhotoUploadRead,
)
from app.services.plant_photo_service import (
    PlantPhotoNotFoundError,
    PlantPhotoQuotaExceededError,
    PlantPhotoValidationError,
    PlantPhotoService,
)
from app.domain.plant_photo_constraints import MAX_PHOTO_UPLOAD_BYTES
from app.storage.s3 import StorageOperationError
from app.models.plant_photo import PlantPhoto
from app.models.user import User
from app.repositories.plant_photo_repository import PlantPhotoRepository
from app.repositories.user_repository import UserRepository
from sqlmodel import Session


class FakePlantPhotoService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.error: Exception | None = None

    def upload_photo(self, **kwargs) -> str:
        self.calls.append(("upload_photo", kwargs))
        self._raise_if_needed()
        return "plants/1/photo-id.webp"

    def get_gallery(self, owner_user_id: str, plant_id: int) -> PlantPhotoGalleryRead:
        self.calls.append(
            ("get_gallery", {"owner_user_id": owner_user_id, "plant_id": plant_id})
        )
        self._raise_if_needed()
        return _gallery()

    def register_photo(self, **kwargs) -> PlantPhotoRead:
        self.calls.append(("register_photo", kwargs))
        self._raise_if_needed()
        return _photo()

    def set_cover_photo(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> PlantPhotoGalleryRead:
        self.calls.append(
            (
                "set_cover_photo",
                {
                    "owner_user_id": owner_user_id,
                    "plant_id": plant_id,
                    "photo_id": photo_id,
                },
            )
        )
        self._raise_if_needed()
        return _gallery(cover_photo_id=photo_id)

    def delete_photo(
        self,
        owner_user_id: str,
        plant_id: int,
        photo_id: str,
    ) -> PlantPhotoRead:
        self.calls.append(
            (
                "delete_photo",
                {
                    "owner_user_id": owner_user_id,
                    "plant_id": plant_id,
                    "photo_id": photo_id,
                },
            )
        )
        self._raise_if_needed()
        return _photo(photo_id=photo_id)

    def _raise_if_needed(self) -> None:
        if self.error is not None:
            raise self.error


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[str] = []
        self.deletes: list[str] = []

    def upload_object(self, *, object_key: str, body: bytes, content_type: str) -> None:
        self.uploads.append(object_key)

    def delete_object(self, object_key: str) -> None:
        self.deletes.append(object_key)


class FakeUrlResolver:
    def public_url(self, object_key: str) -> str:
        return f"https://cdn.example.invalid/{object_key}"


class FakeUploadFile:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.body[:size]


def test_photo_api_routes_are_protected_and_call_owner_scoped_service(
    protected_client,
    app_dependency_override,
):
    client = protected_client("owner-a")
    fake_service = FakePlantPhotoService()
    app_dependency_override(get_plant_photo_service, lambda: fake_service)

    upload = client.post(
        "/photos/upload",
        data={"plantId": "1"},
        files={"file": ("photo.webp", b"image-bytes", "image/webp")},
    )
    gallery = client.get("/plants/1/photos")
    created = client.post(
        "/plants/1/photos",
        json={"objectKey": "plants/1/photo-id.webp", "comment": "葉が増えた"},
    )
    cover = client.put(
        "/plants/1/cover-photo",
        json={"photoId": "4bb385d0-eef0-4985-b50f-1e3da1fdf54f"},
    )
    deleted = client.delete(
        "/plants/1/photos/4bb385d0-eef0-4985-b50f-1e3da1fdf54f"
    )

    assert upload.status_code == 201
    assert upload.json() == {"objectKey": "plants/1/photo-id.webp"}
    assert gallery.status_code == 200
    assert gallery.json()["quota"] == {
        "currentCount": 1,
        "maxCount": 5,
        "unlimited": False,
    }
    assert created.status_code == 201
    assert created.json()["imageUrl"] == "https://cdn.example.invalid/photo.webp"
    assert cover.status_code == 200
    assert cover.json()["coverPhotoId"] == "4bb385d0-eef0-4985-b50f-1e3da1fdf54f"
    assert deleted.status_code == 200
    assert deleted.json()["id"] == "4bb385d0-eef0-4985-b50f-1e3da1fdf54f"
    assert ("upload_photo", ANY) in fake_service.calls
    assert fake_service.calls[0][1]["owner_user_id"] == "owner-a"
    assert fake_service.calls[0][1]["plant_id"] == 1
    assert fake_service.calls[0][1]["filename"] == "photo.webp"
    assert fake_service.calls[0][1]["content_type"] == "image/webp"
    assert fake_service.calls[0][1]["body"] == b"image-bytes"


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (PlantPhotoValidationError("bad photo"), 422),
        (PlantPhotoQuotaExceededError("Photo limit reached"), 409),
        (PlantPhotoNotFoundError("Plant not found"), 404),
        (StorageOperationError("storage failed"), 503),
    ],
)
def test_photo_api_maps_service_errors(
    protected_client,
    app_dependency_override,
    error,
    expected_status,
):
    client = protected_client("owner-a")
    fake_service = FakePlantPhotoService()
    fake_service.error = error
    app_dependency_override(get_plant_photo_service, lambda: fake_service)

    response = client.post(
        "/photos/upload",
        data={"plantId": "1"},
        files={"file": ("photo.webp", b"image-bytes", "image/webp")},
    )

    assert response.status_code == expected_status
    assert "owner-a" not in response.text
    assert "image-bytes" not in response.text


def test_photo_api_routes_require_auth(api_client, app_dependency_override):
    fake_service = FakePlantPhotoService()
    app_dependency_override(get_plant_photo_service, lambda: fake_service)

    response = api_client.get("/plants/1/photos")

    assert response.status_code == 401
    assert fake_service.calls == []


@pytest.mark.anyio
async def test_upload_file_reader_rejects_oversized_file_without_unbounded_read():
    upload_file = FakeUploadFile(b"x" * (MAX_PHOTO_UPLOAD_BYTES + 2))

    with pytest.raises(PlantPhotoValidationError):
        await _read_limited_upload_file(upload_file)

    assert upload_file.read_sizes == [MAX_PHOTO_UPLOAD_BYTES + 1]


def test_photo_api_integration_happy_path_uses_owner_scoped_domain_service(
    protected_client,
    app_dependency_override,
    test_engine,
):
    storage = FakeStorage()
    app_dependency_override(
        get_plant_photo_service,
        _real_photo_service_override(test_engine, storage),
    )
    client = protected_client("owner-a")
    plant_id = client.post(
        "/plants",
        json={"name": "画像つきポトス", "wateringCycleDays": 7},
    ).json()["id"]

    upload = client.post(
        "/photos/upload",
        data={"plantId": str(plant_id)},
        files={"file": ("photo.webp", b"image-bytes", "image/webp")},
    )
    assert upload.status_code == 201
    object_key = upload.json()["objectKey"]
    assert object_key.startswith(f"plants/{plant_id}/")
    assert "owner-a" not in object_key

    created = client.post(
        f"/plants/{plant_id}/photos",
        json={"objectKey": object_key, "takenDate": "2026-06-01"},
    )
    assert created.status_code == 201
    photo_id = created.json()["id"]
    assert created.json()["imageUrl"] == f"https://cdn.example.invalid/{object_key}"

    gallery = client.get(f"/plants/{plant_id}/photos")
    assert gallery.status_code == 200
    assert gallery.json()["quota"] == {
        "currentCount": 1,
        "maxCount": 5,
        "unlimited": False,
    }

    cover = client.put(f"/plants/{plant_id}/cover-photo", json={"photoId": photo_id})
    assert cover.status_code == 200
    assert cover.json()["coverPhotoId"] == photo_id

    deleted = client.delete(f"/plants/{plant_id}/photos/{photo_id}")
    assert deleted.status_code == 200
    assert storage.uploads == [object_key]
    assert storage.deletes == [object_key]


def test_photo_api_integration_hides_other_owner_photo_and_plant(
    protected_client,
    app_dependency_override,
    test_engine,
):
    storage = FakeStorage()
    app_dependency_override(
        get_plant_photo_service,
        _real_photo_service_override(test_engine, storage),
    )
    owner_a_client = protected_client("owner-a")
    plant_id = owner_a_client.post(
        "/plants",
        json={"name": "Aのポトス", "wateringCycleDays": 7},
    ).json()["id"]
    upload = owner_a_client.post(
        "/photos/upload",
        data={"plantId": str(plant_id)},
        files={"file": ("photo.webp", b"image-bytes", "image/webp")},
    )
    photo = owner_a_client.post(
        f"/plants/{plant_id}/photos",
        json={"objectKey": upload.json()["objectKey"]},
    )
    photo_id = photo.json()["id"]

    owner_b_client = protected_client("owner-b")

    responses = [
        owner_b_client.get(f"/plants/{plant_id}/photos"),
        owner_b_client.post(
            "/photos/upload",
            data={"plantId": str(plant_id)},
            files={"file": ("photo.webp", b"image-bytes", "image/webp")},
        ),
        owner_b_client.post(
            f"/plants/{plant_id}/photos",
            json={"objectKey": f"plants/{plant_id}/other.webp"},
        ),
        owner_b_client.put(f"/plants/{plant_id}/cover-photo", json={"photoId": photo_id}),
        owner_b_client.delete(f"/plants/{plant_id}/photos/{photo_id}"),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404, 404, 404]


def test_photo_api_integration_rejects_object_key_for_different_plant(
    protected_client,
    app_dependency_override,
    test_engine,
):
    storage = FakeStorage()
    app_dependency_override(
        get_plant_photo_service,
        _real_photo_service_override(test_engine, storage),
    )
    client = protected_client("owner-a")
    plant_id = client.post(
        "/plants",
        json={"name": "Aのポトス", "wateringCycleDays": 7},
    ).json()["id"]
    other_plant_id = client.post(
        "/plants",
        json={"name": "Aの別植物", "wateringCycleDays": 7},
    ).json()["id"]

    response = client.post(
        f"/plants/{plant_id}/photos",
        json={
            "objectKey": (
                f"plants/{other_plant_id}/4bb385d0-eef0-4985-b50f-1e3da1fdf54f.webp"
            )
        },
    )

    assert response.status_code == 422
    assert "owner-a" not in response.text
    with Session(test_engine) as session:
        assert PlantPhotoRepository(session).count_for_plant("owner-a", plant_id) == 0


def test_photo_api_integration_enforces_quota_and_unlimited_flag(
    protected_client,
    app_dependency_override,
    test_engine,
):
    storage = FakeStorage()
    app_dependency_override(
        get_plant_photo_service,
        _real_photo_service_override(test_engine, storage),
    )
    client = protected_client("owner-a")
    plant_id = client.post(
        "/plants",
        json={"name": "上限確認ポトス", "wateringCycleDays": 7},
    ).json()["id"]
    with Session(test_engine) as session:
        for index in range(5):
            session.add(
                PlantPhoto(
                    owner_user_id="owner-a",
                    plant_id=plant_id,
                    storage_key=f"plants/{plant_id}/{index}.webp",
                )
            )
        session.commit()

    limited = client.post(
        "/photos/upload",
        data={"plantId": str(plant_id)},
        files={"file": ("extra.webp", b"image-bytes", "image/webp")},
    )
    assert limited.status_code == 409

    with Session(test_engine) as session:
        user = session.get(User, "owner-a")
        assert user is not None
        user.photo_upload_unlimited = True
        session.add(user)
        session.commit()

    unlimited = client.post(
        "/photos/upload",
        data={"plantId": str(plant_id)},
        files={"file": ("extra.webp", b"image-bytes", "image/webp")},
    )
    assert unlimited.status_code == 201


def test_photo_openapi_exposes_photo_routes_without_internal_gallery_fields():
    from app.main import app

    openapi = app.openapi()

    assert "/photos/upload" in openapi["paths"]
    assert "/plants/{plant_id}/photos" in openapi["paths"]
    assert "/plants/{plant_id}/cover-photo" in openapi["paths"]
    assert "/plants/{plant_id}/photos/{photo_id}" in openapi["paths"]

    component_text = str(openapi.get("components", {}))
    assert "ownerUserId" not in component_text
    assert "owner_user_id" not in component_text
    assert "storageKey" not in component_text
    assert "storage_key" not in component_text


def _photo(photo_id: str = "4bb385d0-eef0-4985-b50f-1e3da1fdf54f") -> PlantPhotoRead:
    return PlantPhotoRead(
        id=photo_id,
        plant_id=1,
        image_url="https://cdn.example.invalid/photo.webp",
        taken_date=None,
        comment="葉が増えた",
        is_cover=False,
        created_at=datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc),
    )


def _gallery(
    cover_photo_id: str | None = None,
) -> PlantPhotoGalleryRead:
    return PlantPhotoGalleryRead(
        photos=[_photo()],
        quota=PlantPhotoQuotaRead(current_count=1, max_count=5, unlimited=False),
        cover_photo_id=cover_photo_id,
    )


def _real_photo_service_override(test_engine, storage: FakeStorage):
    def override():
        with Session(test_engine) as session:
            yield PlantPhotoService(
                photo_repository=PlantPhotoRepository(session),
                user_repository=UserRepository(session),
                storage=storage,
                url_resolver=FakeUrlResolver(),
            )

    return override
