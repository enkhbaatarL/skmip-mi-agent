from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
import hashlib
import os
from pathlib import Path
import time
from typing import Any

from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from botocore.session import get_session

from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.decorators import log_connector
from apps.common.values.error_codes import ErrorCode
from apps.connectors.object_storage.schemas import DownloadedObject, ObjectMetadata


def _metadata(response: Mapping[str, Any]) -> ObjectMetadata:
    last_modified = response.get("LastModified")
    return ObjectMetadata(
        etag=str(response.get("ETag") or ""),
        content_length=int(response.get("ContentLength") or 0),
        last_modified=(last_modified.isoformat() if isinstance(last_modified, datetime) else str(last_modified or "")),
        version_id=str(response["VersionId"]) if response.get("VersionId") else None,
    )


class S3ObjectStorageClient:
    """S3-compatible Object Storage의 exact Head/Get 전용 connector."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        region_name: str,
        signature_version: str,
        access_key_id: str,
        secret_access_key: str,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        client: BaseClient | None = None,
    ) -> None:
        self._client = client or get_session().create_client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(
                signature_version=signature_version,
                connect_timeout=connect_timeout_seconds,
                read_timeout=read_timeout_seconds,
                retries={"max_attempts": 1, "mode": "standard"},
                s3={"addressing_style": "path"},
            ),
        )

    @log_connector(connector_type="S3", log_input=False, log_output=False)
    async def head_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
    ) -> ObjectMetadata:
        try:
            return await asyncio.to_thread(
                self._head_object_sync,
                bucket=bucket,
                object_key=object_key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"Object Storage metadata 조회 실패: {logical_name}",
            ) from exc

    def _head_object_sync(self, *, bucket: str, object_key: str) -> ObjectMetadata:
        return _metadata(self._client.head_object(Bucket=bucket, Key=object_key))

    @log_connector(connector_type="S3", log_input=False, log_output=False)
    async def download_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
        destination: Path,
        chunk_size_bytes: int,
        deadline: float,
    ) -> DownloadedObject:
        try:
            return await asyncio.to_thread(
                self._download_object_sync,
                bucket=bucket,
                object_key=object_key,
                destination=destination,
                chunk_size_bytes=chunk_size_bytes,
                deadline=deadline,
            )
        except (BotoCoreError, ClientError) as exc:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"Object Storage 다운로드 실패: {logical_name}",
            ) from exc

    def _download_object_sync(
        self,
        *,
        bucket: str,
        object_key: str,
        destination: Path,
        chunk_size_bytes: int,
        deadline: float,
    ) -> DownloadedObject:
        response = self._client.get_object(Bucket=bucket, Key=object_key)
        body = response["Body"]
        digest = hashlib.sha256()
        size = 0
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                while True:
                    if time.monotonic() > deadline:
                        raise MIBaseError(
                            ErrorCode.DATA_RETRIEVAL_FAILED,
                            detail="Object Storage bootstrap timeout",
                        )
                    chunk = body.read(chunk_size_bytes)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                output.flush()
                os.fsync(output.fileno())
        finally:
            body.close()

        return DownloadedObject(
            path=destination,
            size=size,
            sha256=digest.hexdigest(),
            metadata=_metadata(response),
        )

    async def close(self) -> None:
        await asyncio.to_thread(self._client.close)
