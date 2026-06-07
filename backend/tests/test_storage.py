from botocore.exceptions import ClientError

from app.core.config import Settings
from app.storage.object_storage import (
    ObjectStorageClient,
    StorageConfigurationError,
    StorageOperationError,
    StorageUrlResolver,
)


class FakeObjectStorageClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.put_calls: list[dict[str, object]] = []
        self.delete_calls: list[dict[str, object]] = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        if self.fail:
            raise ClientError(
                {
                    "Error": {
                        "Code": "AccessDenied",
                        "Message": "raw secret bucket plants/1/photo.webp",
                    }
                },
                "PutObject",
            )

    def delete_object(self, **kwargs):
        self.delete_calls.append(kwargs)
        if self.fail:
            raise ClientError(
                {
                    "Error": {
                        "Code": "AccessDenied",
                        "Message": "raw secret bucket plants/1/photo.webp",
                    }
                },
                "DeleteObject",
            )


def test_storage_url_resolver_builds_public_url_from_object_key():
    resolver = StorageUrlResolver(
        Settings(
            storage_region="ap-northeast-1",
            storage_bucket_name="green-mate-photos",
            storage_public_base_url=(
                "https://green-mate-photos.s3.ap-northeast-1.amazonaws.com"
            ),
        )
    )

    assert resolver.public_url("plants/1/photo id.webp") == (
        "https://green-mate-photos.s3.ap-northeast-1.amazonaws.com/"
        "plants/1/photo%20id.webp"
    )


def test_storage_url_resolver_trims_configured_public_base_url():
    resolver = StorageUrlResolver(
        Settings(
            storage_bucket_name="green-mate-photos",
            storage_public_base_url="https://photos.green-mate.example.com/",
        )
    )

    assert resolver.public_url("plants/1/photo id.webp") == (
        "https://photos.green-mate.example.com/plants/1/photo%20id.webp"
    )


def test_object_storage_client_uploads_without_acl_and_deletes_by_object_key():
    fake_storage = FakeObjectStorageClient()
    storage = ObjectStorageClient(
        Settings(
            storage_access_key_id="dummy-access-key",
            storage_secret_access_key="dummy-secret-key",
            storage_region="ap-northeast-1",
            storage_bucket_name="green-mate-photos",
        ),
        client=fake_storage,
    )

    storage.upload_object(
        object_key="plants/1/photo.webp",
        body=b"image-bytes",
        content_type="image/webp",
    )
    storage.delete_object("plants/1/photo.webp")

    assert fake_storage.put_calls == [
        {
            "Bucket": "green-mate-photos",
            "Key": "plants/1/photo.webp",
            "Body": b"image-bytes",
            "ContentType": "image/webp",
        }
    ]
    assert "ACL" not in fake_storage.put_calls[0]
    assert fake_storage.delete_calls == [
        {"Bucket": "green-mate-photos", "Key": "plants/1/photo.webp"}
    ]


def test_object_storage_client_uses_generic_storage_configuration(monkeypatch):
    captured = {}

    def fake_boto3_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured["kwargs"] = kwargs
        return FakeObjectStorageClient()

    monkeypatch.setattr("app.storage.object_storage.boto3.client", fake_boto3_client)

    storage = ObjectStorageClient(
        Settings(
            storage_access_key_id="r2-access-key",
            storage_secret_access_key="r2-secret-key",
            storage_region="auto",
            storage_bucket_name="green-mate-photos",
            storage_endpoint_url="https://example-account.r2.cloudflarestorage.com",
        )
    )

    storage.upload_object(
        object_key="plants/1/photo.webp",
        body=b"image-bytes",
        content_type="image/webp",
    )

    assert captured == {
        "service_name": "s3",
        "kwargs": {
            "region_name": "auto",
            "aws_access_key_id": "r2-access-key",
            "aws_secret_access_key": "r2-secret-key",
            "endpoint_url": "https://example-account.r2.cloudflarestorage.com",
        },
    }


def test_object_storage_client_requires_upload_configuration():
    storage = ObjectStorageClient(Settings(_env_file=None), client=FakeObjectStorageClient())

    try:
        storage.upload_object(
            object_key="plants/1/photo.webp",
            body=b"image-bytes",
            content_type="image/webp",
        )
    except StorageConfigurationError as exc:
        assert str(exc) == "Image storage is not configured"
    else:
        raise AssertionError("storage must reject missing object storage configuration")


def test_object_storage_client_sanitizes_provider_failures():
    storage = ObjectStorageClient(
        Settings(
            storage_access_key_id="dummy-access-key",
            storage_secret_access_key="raw secret",
            storage_region="ap-northeast-1",
            storage_bucket_name="bucket",
        ),
        client=FakeObjectStorageClient(fail=True),
    )

    try:
        storage.delete_object("plants/1/photo.webp")
    except StorageOperationError as exc:
        rendered = str(exc)
        assert rendered == "Image storage operation failed"
        assert "raw secret" not in rendered
        assert "bucket" not in rendered
        assert "plants/1/photo.webp" not in rendered
    else:
        raise AssertionError("storage must wrap S3 provider failures")
