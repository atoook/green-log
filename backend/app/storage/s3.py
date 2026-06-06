from typing import Protocol
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings


class StorageConfigurationError(RuntimeError):
    pass


class StorageOperationError(RuntimeError):
    pass


class S3ClientProtocol(Protocol):
    def put_object(self, **kwargs): ...

    def delete_object(self, **kwargs): ...


class StorageUrlResolver:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def public_url(self, object_key: str) -> str:
        base_url = self.settings.s3_public_base_url
        if base_url is None:
            raise StorageConfigurationError("Image storage is not configured")
        return f"{base_url}/{quote(object_key, safe='/')}"


class S3StorageClient:
    def __init__(
        self,
        settings: Settings,
        client: S3ClientProtocol | None = None,
    ) -> None:
        self.settings = settings
        self._client = client

    def upload_object(
        self,
        *,
        object_key: str,
        body: bytes,
        content_type: str,
    ) -> None:
        try:
            self._configured_client().put_object(
                Bucket=self._bucket_name(),
                Key=object_key,
                Body=body,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageOperationError("Image storage operation failed") from exc

    def delete_object(self, object_key: str) -> None:
        try:
            self._configured_client().delete_object(
                Bucket=self._bucket_name(),
                Key=object_key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageOperationError("Image storage operation failed") from exc

    def _configured_client(self) -> S3ClientProtocol:
        self._ensure_configured()
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=self.settings.aws_region,
                aws_access_key_id=self.settings.aws_access_key_id_value,
                aws_secret_access_key=self.settings.aws_secret_access_key_value,
            )
        return self._client

    def _ensure_configured(self) -> None:
        if not self.settings.s3_upload_configured:
            raise StorageConfigurationError("Image storage is not configured")

    def _bucket_name(self) -> str:
        self._ensure_configured()
        if self.settings.s3_bucket_name is None:
            raise StorageConfigurationError("Image storage is not configured")
        return self.settings.s3_bucket_name
