from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.plant_photo_constraints import (
    ALLOWED_PHOTO_CONTENT_TYPES,
    ALLOWED_PHOTO_EXTENSIONS,
    MAX_PHOTO_UPLOAD_BYTES,
    MAX_PHOTOS_PER_PLANT,
)
from app.schemas.plant_photo import (
    PlantPhotoCreate,
    PlantPhotoGalleryRead,
    PlantPhotoQuotaRead,
    PlantPhotoRead,
    PlantPhotoUploadRead,
    PlantCoverPhotoUpdate,
)


def test_photo_constraints_are_shared_for_upload_and_quota_rules():
    assert MAX_PHOTOS_PER_PLANT == 5
    assert MAX_PHOTO_UPLOAD_BYTES > 0
    assert ALLOWED_PHOTO_CONTENT_TYPES == frozenset(
        {"image/jpeg", "image/png", "image/webp"}
    )
    assert ALLOWED_PHOTO_EXTENSIONS == frozenset({"jpg", "jpeg", "png", "webp"})


def test_photo_read_schema_serializes_gallery_fields_without_internal_fields():
    photo = PlantPhotoRead(
        id="4bb385d0-eef0-4985-b50f-1e3da1fdf54f",
        plant_id=1,
        image_url="https://green-mate-photos.s3.ap-northeast-1.amazonaws.com/plants/1/photo.webp",
        taken_date=date(2026, 6, 1),
        comment="新芽が出た",
        is_cover=True,
        created_at=datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc),
    )

    payload = photo.model_dump(mode="json", by_alias=True)

    assert payload == {
        "id": "4bb385d0-eef0-4985-b50f-1e3da1fdf54f",
        "plantId": 1,
        "imageUrl": "https://green-mate-photos.s3.ap-northeast-1.amazonaws.com/plants/1/photo.webp",
        "takenDate": "2026-06-01",
        "comment": "新芽が出た",
        "isCover": True,
        "createdAt": "2026-06-01T09:30:00Z",
    }
    dumped_text = str(payload)
    assert "storageKey" not in dumped_text
    assert "storage_key" not in dumped_text
    assert "ownerUserId" not in dumped_text
    assert "owner_user_id" not in dumped_text


def test_photo_gallery_schema_represents_limited_and_unlimited_quotas():
    photo = PlantPhotoRead(
        id="f8ad1d63-45e3-4594-a180-333d56954348",
        plant_id=1,
        image_url="https://example.invalid/photo.jpg",
        taken_date=None,
        comment=None,
        is_cover=False,
        created_at=datetime(2026, 6, 1, 9, 30),
    )

    limited = PlantPhotoGalleryRead(
        photos=[photo],
        quota=PlantPhotoQuotaRead(current_count=1, max_count=5, unlimited=False),
        cover_photo_id=None,
    )
    unlimited = PlantPhotoGalleryRead(
        photos=[],
        quota=PlantPhotoQuotaRead(current_count=0, max_count=None, unlimited=True),
        cover_photo_id=None,
    )

    assert limited.model_dump(mode="json", by_alias=True)["quota"] == {
        "currentCount": 1,
        "maxCount": 5,
        "unlimited": False,
    }
    assert unlimited.model_dump(mode="json", by_alias=True)["quota"] == {
        "currentCount": 0,
        "maxCount": None,
        "unlimited": True,
    }


def test_upload_and_register_flow_schemas_allow_object_key_only_at_boundary():
    upload = PlantPhotoUploadRead(object_key="plants/1/photo-id.webp")
    create = PlantPhotoCreate.model_validate(
        {
            "objectKey": "plants/1/photo-id.webp",
            "takenDate": "2026-06-01",
            "comment": "葉が増えた",
        }
    )
    cover = PlantCoverPhotoUpdate.model_validate(
        {"photoId": "4bb385d0-eef0-4985-b50f-1e3da1fdf54f"}
    )

    assert upload.model_dump(mode="json", by_alias=True) == {
        "objectKey": "plants/1/photo-id.webp"
    }
    assert create.object_key == "plants/1/photo-id.webp"
    assert create.taken_date == date(2026, 6, 1)
    assert create.comment == "葉が増えた"
    assert cover.photo_id == "4bb385d0-eef0-4985-b50f-1e3da1fdf54f"


def test_photo_create_schema_rejects_internal_fields():
    with pytest.raises(ValidationError):
        PlantPhotoCreate.model_validate(
            {
                "objectKey": "plants/1/photo-id.webp",
                "ownerUserId": "internal-owner",
            }
        )
