"""S3-compatible object storage for uploaded voice messages and photos.

Object keys are always generated server-side, so a user-supplied file name can
never influence the storage path.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Literal

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from onedrop.ai.providers.base import ALLOWED_AUDIO_MIME, ALLOWED_IMAGE_MIME
from onedrop.config import Settings, get_settings
from onedrop.errors import ProviderError, UnsupportedMediaError, ValidationError
from onedrop.logging import get_logger

logger = get_logger(__name__)

EXTENSION_BY_MIME: dict[str, str] = {
    "audio/ogg": "ogg",
    "audio/oga": "oga",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MediaKind = Literal["audio", "image"]


def validate_media(
    *, mime_type: str, size_bytes: int, kind: MediaKind, settings: Settings | None = None
) -> None:
    """Reject unsupported types and oversized uploads before any AI work."""
    active = settings or get_settings()
    allowed = ALLOWED_AUDIO_MIME if kind == "audio" else ALLOWED_IMAGE_MIME
    if mime_type not in allowed:
        raise UnsupportedMediaError(f"unsupported {kind} type: {mime_type}")
    if size_bytes <= 0:
        raise ValidationError("uploaded file is empty")
    if size_bytes > active.max_upload_bytes:
        raise ValidationError(
            "uploaded file is too large",
            details={"max_bytes": active.max_upload_bytes},
        )


def build_object_key(user_id: uuid.UUID, mime_type: str) -> str:
    """Generated, collision-free key: `{user_id}/{uuid4}.{ext}`."""
    extension = EXTENSION_BY_MIME.get(mime_type, "bin")
    return f"{user_id}/{uuid.uuid4().hex}.{extension}"


class ObjectStorage:
    """Thin async wrapper over the synchronous S3 client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _client(self) -> Any:
        return boto3.client(
            "s3",
            endpoint_url=self._settings.s3_endpoint_url,
            aws_access_key_id=self._settings.s3_access_key,
            aws_secret_access_key=self._settings.s3_secret_key,
            region_name=self._settings.s3_region,
            config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    async def ensure_bucket(self) -> None:
        """Create the bucket when it is missing (development convenience)."""

        def _ensure() -> None:
            client = self._client()
            bucket = self._settings.s3_bucket
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError:
                client.create_bucket(Bucket=bucket)

        try:
            await asyncio.to_thread(_ensure)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("storage.ensure_bucket_failed", error_type=type(exc).__name__)
            raise ProviderError("object storage is unavailable") from exc

    async def put(self, key: str, data: bytes, mime_type: str) -> str:
        def _put() -> None:
            self._client().put_object(
                Bucket=self._settings.s3_bucket,
                Key=key,
                Body=data,
                ContentType=mime_type,
            )

        try:
            await asyncio.to_thread(_put)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("storage.put_failed", error_type=type(exc).__name__)
            raise ProviderError("could not store the uploaded file") from exc
        return key

    async def get(self, key: str) -> bytes:
        def _get() -> bytes:
            response = self._client().get_object(Bucket=self._settings.s3_bucket, Key=key)
            body: bytes = response["Body"].read()
            return body

        try:
            return await asyncio.to_thread(_get)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("storage.get_failed", error_type=type(exc).__name__)
            raise ProviderError("could not read the stored file") from exc

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            self._client().delete_object(Bucket=self._settings.s3_bucket, Key=key)

        try:
            await asyncio.to_thread(_delete)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("storage.delete_failed", error_type=type(exc).__name__)

    async def delete_prefix(self, prefix: str) -> int:
        """Delete every object under a prefix. Used by account deletion."""

        def _delete_prefix() -> int:
            client = self._client()
            bucket = self._settings.s3_bucket
            deleted = 0
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    client.delete_object(Bucket=bucket, Key=item["Key"])
                    deleted += 1
            return deleted

        try:
            return await asyncio.to_thread(_delete_prefix)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("storage.delete_prefix_failed", error_type=type(exc).__name__)
            return 0

    async def delete_older_than(self, cutoff: datetime) -> int:
        """Media retention sweep executed by the scheduler."""

        def _sweep() -> int:
            client = self._client()
            bucket = self._settings.s3_bucket
            deleted = 0
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket):
                for item in page.get("Contents", []):
                    if item["LastModified"] < cutoff:
                        client.delete_object(Bucket=bucket, Key=item["Key"])
                        deleted += 1
            return deleted

        try:
            return await asyncio.to_thread(_sweep)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("storage.sweep_failed", error_type=type(exc).__name__)
            return 0

    async def presigned_url(self, key: str, *, expires_seconds: int = 300) -> str:
        def _sign() -> str:
            url: str = self._client().generate_presigned_url(
                "get_object",
                Params={"Bucket": self._settings.s3_bucket, "Key": key},
                ExpiresIn=expires_seconds,
            )
            return url

        try:
            return await asyncio.to_thread(_sign)
        except (BotoCoreError, ClientError) as exc:
            raise ProviderError("could not sign the media URL") from exc
