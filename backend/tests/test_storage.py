from botocore.exceptions import ClientError

from app.core.config import Settings
from app.storage.s3 import (
    S3StorageClient,
    StorageConfigurationError,
    StorageOperationError,
    StorageUrlResolver,
)


class FakeS3Client:
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


def test_storage_url_resolver_builds_public_s3_url_from_object_key():
    resolver = StorageUrlResolver(
        Settings(
            aws_region="ap-northeast-1",
            s3_bucket_name="green-mate-photos",
        )
    )

    assert resolver.public_url("plants/1/photo id.webp") == (
        "https://green-mate-photos.s3.ap-northeast-1.amazonaws.com/"
        "plants/1/photo%20id.webp"
    )


def test_s3_storage_client_uploads_without_acl_and_deletes_by_object_key():
    fake_s3 = FakeS3Client()
    storage = S3StorageClient(
        Settings(
            aws_access_key_id="dummy-access-key",
            aws_secret_access_key="dummy-secret-key",
            aws_region="ap-northeast-1",
            s3_bucket_name="green-mate-photos",
        ),
        client=fake_s3,
    )

    storage.upload_object(
        object_key="plants/1/photo.webp",
        body=b"image-bytes",
        content_type="image/webp",
    )
    storage.delete_object("plants/1/photo.webp")

    assert fake_s3.put_calls == [
        {
            "Bucket": "green-mate-photos",
            "Key": "plants/1/photo.webp",
            "Body": b"image-bytes",
            "ContentType": "image/webp",
        }
    ]
    assert "ACL" not in fake_s3.put_calls[0]
    assert fake_s3.delete_calls == [
        {"Bucket": "green-mate-photos", "Key": "plants/1/photo.webp"}
    ]


def test_s3_storage_client_requires_upload_configuration():
    storage = S3StorageClient(Settings(_env_file=None), client=FakeS3Client())

    try:
        storage.upload_object(
            object_key="plants/1/photo.webp",
            body=b"image-bytes",
            content_type="image/webp",
        )
    except StorageConfigurationError as exc:
        assert str(exc) == "Image storage is not configured"
    else:
        raise AssertionError("storage must reject missing S3 configuration")


def test_s3_storage_client_sanitizes_provider_failures():
    storage = S3StorageClient(
        Settings(
            aws_access_key_id="dummy-access-key",
            aws_secret_access_key="raw secret",
            aws_region="ap-northeast-1",
            s3_bucket_name="bucket",
        ),
        client=FakeS3Client(fail=True),
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
