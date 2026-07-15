from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import urlsplit
import uuid

from botocore.exceptions import BotoCoreError
from openpyxl import load_workbook

from apps.agents.model_parameter_agent.utils.basecase import (
    clear_parameter_mapping_runtime_cache,
)
from apps.agents.model_parameter_agent.utils.lut import (
    LutLoadPolicy,
    clear_lut_runtime_cache,
    validate_lut_startup,
)
from apps.agents.model_parameter_agent.utils.resource_manifest import (
    PACKAGE_BASECASE_DIR,
    PACKAGE_LUT_ROOT,
    ModelParameterResourceManifest,
    PlannedResourceDownload,
    RemoteResourceConfigError,
    load_model_parameter_resource_manifest,
    resource_config_fingerprint,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    ModelParameterResourcePaths,
    get_model_parameter_resource_paths,
    get_registered_model_parameter_resource_paths,
    register_model_parameter_resource_paths,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.object_storage import DownloadedObject, ObjectMetadata, S3ObjectStorageClient


if TYPE_CHECKING:
    from apps.common.configs.config import ModelParameterResourceStorageConfig


COMPLETE_FILE_NAME = ".complete.json"
CURRENT_LINK_NAME = "current"
LOCK_FILE_NAME = ".bootstrap.lock"


class ObjectStorageReader(Protocol):
    async def head_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
    ) -> ObjectMetadata: ...

    async def download_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
        destination: Path,
        chunk_size_bytes: int,
        deadline: float,
    ) -> DownloadedObject: ...

    async def close(self) -> None: ...


class RemoteResourceSyncError(RuntimeError):
    """원격 파일 세트 동기화/검증 실패. packaged fallback 대상이다."""


class _ProcessFileLock(AbstractAsyncContextManager[None]):
    def __init__(self, path: Path, *, timeout_seconds: float) -> None:
        self._path = path
        self._timeout_seconds = timeout_seconds
        self._descriptor: int | None = None

    async def __aenter__(self) -> None:
        try:
            self._descriptor = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError as exc:
            msg = f"process lock 생성 실패: {self._path}"
            raise _bootstrap_error(msg) from exc
        deadline = time.monotonic() + self._timeout_seconds
        while True:
            try:
                fcntl.flock(self._descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return  # noqa: TRY300
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(self._descriptor)
                    self._descriptor = None
                    msg = "process lock wait timeout"
                    raise _bootstrap_error(msg) from None
                await asyncio.sleep(0.1)
            except OSError as exc:
                os.close(self._descriptor)
                self._descriptor = None
                msg = "process lock 획득 실패"
                raise _bootstrap_error(msg) from exc

    async def __aexit__(self, *exc_info: object) -> None:
        if self._descriptor is None:
            return
        try:
            fcntl.flock(self._descriptor, fcntl.LOCK_UN)
        finally:
            os.close(self._descriptor)
            self._descriptor = None


def _bootstrap_error(detail: str) -> MIBaseError:
    return MIBaseError(ErrorCode.RUNTIME_REGISTRY_NOT_READY, detail=detail)


def _safe_reason(exc: Exception) -> str:
    reason = f"{type(exc).__name__}: {exc}"
    return reason[:500]


def _fallback_config_fingerprint(
    manifest: ModelParameterResourceManifest,
    *,
    storage: ModelParameterResourceStorageConfig,
    lut_enabled: bool,
) -> str:
    digest = hashlib.sha256()
    digest.update(manifest.path.read_bytes())
    digest.update(
        json.dumps(
            {
                "endpoint_url": storage.endpoint_url,
                "region_name": storage.region_name,
                "signature_version": storage.signature_version,
                "lut_enabled": lut_enabled,
                "invalid_remote_plan": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    )
    return digest.hexdigest()


def _validate_remote_connection_settings(storage: ModelParameterResourceStorageConfig) -> None:
    parsed = urlsplit(storage.endpoint_url)
    if not parsed.hostname:
        msg = "유효한 Object Storage endpoint_url이 필요합니다"
        raise RemoteResourceConfigError(msg)
    if not storage.region_name.strip() or not storage.signature_version.strip():
        msg = "Object Storage region/signature 설정이 필요합니다"
        raise RemoteResourceConfigError(msg)

    access_key = storage.access_key_id.get_secret_value()
    secret_key = storage.secret_access_key.get_secret_value()

    def invalid_secret(value: str) -> bool:
        return not value or (value.startswith("${") and value.endswith("}"))

    if invalid_secret(access_key) or invalid_secret(secret_key):
        msg = "Object Storage credential 설정이 필요합니다"
        raise RemoteResourceConfigError(msg)


def _create_client(storage: ModelParameterResourceStorageConfig) -> S3ObjectStorageClient:
    try:
        return S3ObjectStorageClient(
            endpoint_url=storage.endpoint_url,
            region_name=storage.region_name,
            signature_version=storage.signature_version,
            access_key_id=storage.access_key_id.get_secret_value(),
            secret_access_key=storage.secret_access_key.get_secret_value(),
            connect_timeout_seconds=storage.connect_timeout_seconds,
            read_timeout_seconds=storage.read_timeout_seconds,
        )
    except BotoCoreError as exc:
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail="Object Storage client 초기화 실패",
        ) from exc


def _validate_basecase_workbooks(
    manifest: ModelParameterResourceManifest,
    *,
    basecase_dir: Path,
) -> None:
    for resource_file in manifest.basecase_files.values():
        workbook_path = (basecase_dir / resource_file.relative_path).resolve()
        if not workbook_path.is_file() or workbook_path.stat().st_size <= 0:
            msg = f"Basecase workbook이 없거나 비어 있습니다: {resource_file.logical_name}"
            raise RemoteResourceSyncError(
                msg,
            )
        try:
            workbook = load_workbook(
                workbook_path,
                read_only=True,
                data_only=True,
                keep_vba=False,
            )
        except Exception as exc:
            msg = f"Basecase workbook 검증 실패: {resource_file.logical_name}"
            raise RemoteResourceSyncError(
                msg,
            ) from exc
        workbook.close()


async def _validate_resource_set(
    manifest: ModelParameterResourceManifest,
    *,
    basecase_dir: Path,
    lut_root: Path,
    lut_enabled: bool,
    lut_policy: LutLoadPolicy,
) -> None:
    await asyncio.to_thread(
        _validate_basecase_workbooks,
        manifest,
        basecase_dir=basecase_dir,
    )
    await asyncio.to_thread(
        validate_lut_startup,
        lut_enabled,
        lut_policy,
        config_path=manifest.path,
        lut_root=lut_root,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _selected_file_records(
    manifest: ModelParameterResourceManifest,
    *,
    resource_root: Path,
    lut_enabled: bool,
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for resource_file in manifest.selected_files(lut_enabled=lut_enabled):
        path = resource_root / resource_file.target_relative_path
        size = path.stat().st_size
        records[resource_file.target_relative_path] = {
            "size": size,
            "sha256": _file_sha256(path),
        }
    return records


def _resource_fingerprint(file_records: Mapping[str, Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for relative_path, metadata in sorted(file_records.items()):
        digest.update(relative_path.encode("utf-8"))
        digest.update(str(metadata["sha256"]).encode("ascii"))
    return digest.hexdigest()


def _write_complete_file(release_root: Path, payload: Mapping[str, Any]) -> None:
    complete_path = release_root / COMPLETE_FILE_NAME
    with complete_path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        output.flush()
        os.fsync(output.fileno())


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def _clean_orphan_staging(local_root: Path) -> None:
    for path in local_root.glob("staging-*"):
        _remove_path(path)


def _complete_payload(
    *,
    source: str,
    config_fingerprint: str,
    manifest: ModelParameterResourceManifest,
    resource_fingerprint: str | None,
    fallback_reason: str | None,
    files: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": source,
        "resource_config_fingerprint": config_fingerprint,
        "semantic_schema_hash": manifest.semantic_schema_hash,
        "resource_fingerprint": resource_fingerprint,
        "fallback_reason": fallback_reason,
        "files": dict(files),
    }


def _read_valid_release(  # noqa: C901
    release_root: Path,
    *,
    releases_root: Path,
    manifest: ModelParameterResourceManifest,
    config_fingerprint: str,
    lut_enabled: bool,
) -> dict[str, Any] | None:
    try:
        resolved_release = release_root.resolve(strict=True)
        if not resolved_release.is_relative_to(releases_root.resolve(strict=True)):
            return None
        payload = json.loads((resolved_release / COMPLETE_FILE_NAME).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        if payload.get("schema_version") != 1:
            return None
        if payload.get("resource_config_fingerprint") != config_fingerprint:
            return None
        if payload.get("semantic_schema_hash") != manifest.semantic_schema_hash:
            return None
        if payload.get("source") not in {"object_storage", "packaged"}:
            return None
        files = payload.get("files")
        if not isinstance(files, dict):
            return None
        expected_targets = {
            resource_file.target_relative_path for resource_file in manifest.selected_files(lut_enabled=lut_enabled)
        }
        if set(files) != expected_targets:
            return None
        for relative_path, file_metadata in files.items():
            if not isinstance(file_metadata, dict):
                return None
            resource_path = resolved_release / relative_path
            if not resource_path.is_file() or resource_path.stat().st_size != file_metadata.get("size"):
                return None

        if payload["source"] == "packaged":
            if (resolved_release / "basecase").resolve(strict=True) != PACKAGE_BASECASE_DIR.resolve(strict=True):
                return None
            if (resolved_release / "lut").resolve(strict=True) != PACKAGE_LUT_ROOT.resolve(strict=True):
                return None
        elif (resolved_release / "basecase").is_symlink() or (resolved_release / "lut").is_symlink():
            return None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return payload


def _read_current_release(
    local_root: Path,
    *,
    manifest: ModelParameterResourceManifest,
    config_fingerprint: str,
    lut_enabled: bool,
) -> tuple[Path, dict[str, Any]] | None:
    current = local_root / CURRENT_LINK_NAME
    releases_root = local_root / "releases"
    if not current.is_symlink():
        return None
    payload = _read_valid_release(
        current,
        releases_root=releases_root,
        manifest=manifest,
        config_fingerprint=config_fingerprint,
        lut_enabled=lut_enabled,
    )
    if payload is None:
        return None
    return current.resolve(strict=True), payload


def _activate_release(local_root: Path, release_root: Path) -> None:
    current = local_root / CURRENT_LINK_NAME
    temporary_link = local_root / f".current-{uuid.uuid4().hex}.tmp"
    relative_target = os.path.relpath(release_root, start=local_root)
    try:
        temporary_link.symlink_to(relative_target, target_is_directory=True)
        temporary_link.replace(current)
    except OSError:
        temporary_link.unlink(missing_ok=True)
        raise


def _paths_from_release(
    release_root: Path,
    payload: Mapping[str, Any],
    *,
    manifest: ModelParameterResourceManifest,
) -> ModelParameterResourcePaths:
    resolved_root = release_root.resolve(strict=True)
    return ModelParameterResourcePaths(
        source=str(payload["source"]),  # type: ignore[arg-type]
        root=resolved_root,
        basecase_dir=(resolved_root / "basecase").resolve(strict=True),
        lut_root=(resolved_root / "lut").resolve(strict=True),
        manifest_path=manifest.path,
        semantic_schema_hash=manifest.semantic_schema_hash,
        resource_config_fingerprint=str(payload["resource_config_fingerprint"]),
        resource_fingerprint=(str(payload["resource_fingerprint"]) if payload.get("resource_fingerprint") else None),
        fallback_reason=(str(payload["fallback_reason"]) if payload.get("fallback_reason") else None),
    )


async def _head_plan(
    client: ObjectStorageReader,
    plan: tuple[PlannedResourceDownload, ...],
) -> dict[str, ObjectMetadata]:
    metadata: dict[str, ObjectMetadata] = {}
    for item in plan:
        head = await client.head_object(
            bucket=item.location.bucket,
            object_key=item.location.object_key,
            logical_name=item.logical_name,
        )
        if head.content_length <= 0:
            msg = f"Object Storage 객체가 비어 있습니다: {item.logical_name}"
            raise RemoteResourceSyncError(msg)
        metadata[item.target_relative_path] = head
    return metadata


async def _download_plan_once(
    client: ObjectStorageReader,
    plan: tuple[PlannedResourceDownload, ...],
    *,
    staging_root: Path,
    storage: ModelParameterResourceStorageConfig,
    deadline: float,
) -> tuple[dict[str, dict[str, Any]], int]:
    first_metadata = await _head_plan(client, plan)
    file_records: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    for item in plan:
        destination = staging_root / item.target_relative_path
        temporary_destination = destination.with_name(f"{destination.name}.tmp")
        downloaded = await client.download_object(
            bucket=item.location.bucket,
            object_key=item.location.object_key,
            logical_name=item.logical_name,
            destination=temporary_destination,
            chunk_size_bytes=storage.download_chunk_size_bytes,
            deadline=deadline,
        )
        expected = first_metadata[item.target_relative_path]
        if downloaded.size <= 0 or downloaded.size != expected.content_length:
            msg = f"Object Storage 다운로드 길이 불일치: {item.logical_name}"
            raise RemoteResourceSyncError(msg)
        if downloaded.metadata != expected:
            msg = f"Object Storage GetObject metadata 변경 감지: {item.logical_name}"
            raise RemoteResourceSyncError(msg)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_destination.replace(destination)
        file_records[item.target_relative_path] = {
            "size": downloaded.size,
            "sha256": downloaded.sha256,
        }
        total_bytes += downloaded.size

    final_metadata = await _head_plan(client, plan)
    if final_metadata != first_metadata:
        msg = "Object Storage 다운로드 중 metadata가 변경되었습니다"
        raise RemoteResourceSyncError(msg)
    return file_records, total_bytes


async def _build_remote_release(
    *,
    local_root: Path,
    manifest: ModelParameterResourceManifest,
    config_fingerprint: str,
    plan: tuple[PlannedResourceDownload, ...],
    storage: ModelParameterResourceStorageConfig,
    lut_enabled: bool,
    lut_policy: LutLoadPolicy,
    client_factory: Callable[[ModelParameterResourceStorageConfig], ObjectStorageReader],
) -> tuple[Path, dict[str, Any], int, int]:
    _validate_remote_connection_settings(storage)
    client = client_factory(storage)
    deadline = time.monotonic() + storage.bootstrap_timeout_seconds
    last_error: Exception | None = None
    try:
        for attempt in range(1, storage.max_attempts + 1):
            if time.monotonic() >= deadline:
                raise MIBaseError(
                    ErrorCode.DATA_RETRIEVAL_FAILED,
                    detail="Object Storage bootstrap timeout",
                )
            staging_root = local_root / f"staging-{uuid.uuid4().hex}"
            staging_root.mkdir(mode=0o700)
            (staging_root / "basecase").mkdir(mode=0o700)
            (staging_root / "lut").mkdir(mode=0o700)
            try:
                file_records, total_bytes = await _download_plan_once(
                    client,
                    plan,
                    staging_root=staging_root,
                    storage=storage,
                    deadline=deadline,
                )
                await _validate_resource_set(
                    manifest,
                    basecase_dir=staging_root / "basecase",
                    lut_root=staging_root / "lut",
                    lut_enabled=lut_enabled,
                    lut_policy=lut_policy,
                )
                resource_fingerprint = _resource_fingerprint(file_records)
                payload = _complete_payload(
                    source="object_storage",
                    config_fingerprint=config_fingerprint,
                    manifest=manifest,
                    resource_fingerprint=resource_fingerprint,
                    fallback_reason=None,
                    files=file_records,
                )
                _write_complete_file(staging_root, payload)
                release_root = local_root / "releases" / f"remote-{resource_fingerprint[:12]}"
                if release_root.exists() or release_root.is_symlink():
                    existing = _read_valid_release(
                        release_root,
                        releases_root=local_root / "releases",
                        manifest=manifest,
                        config_fingerprint=config_fingerprint,
                        lut_enabled=lut_enabled,
                    )
                    if existing is not None:
                        _remove_path(staging_root)
                        return release_root, existing, len(plan), total_bytes
                    _remove_path(release_root)
                staging_root.replace(release_root)
                return release_root, payload, len(plan), total_bytes
            except (MIBaseError, RemoteResourceSyncError) as exc:
                last_error = exc
                _remove_path(staging_root)
                clear_lut_runtime_cache()
                clear_parameter_mapping_runtime_cache()
                if attempt < storage.max_attempts:
                    await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
        if last_error is not None:
            raise last_error
        msg = "Object Storage 동기화 시도에 실패했습니다"
        raise RemoteResourceSyncError(msg)
    finally:
        await client.close()


async def _build_packaged_release(
    *,
    local_root: Path,
    manifest: ModelParameterResourceManifest,
    config_fingerprint: str,
    fallback_reason: str,
    lut_enabled: bool,
    lut_policy: LutLoadPolicy,
) -> tuple[Path, dict[str, Any]]:
    clear_lut_runtime_cache()
    clear_parameter_mapping_runtime_cache()
    await _validate_resource_set(
        manifest,
        basecase_dir=PACKAGE_BASECASE_DIR,
        lut_root=PACKAGE_LUT_ROOT,
        lut_enabled=lut_enabled,
        lut_policy=lut_policy,
    )
    release_root = local_root / "releases" / f"packaged-{config_fingerprint[:12]}"
    if release_root.exists() or release_root.is_symlink():
        _remove_path(release_root)
    release_root.mkdir(mode=0o700)
    (release_root / "basecase").symlink_to(PACKAGE_BASECASE_DIR, target_is_directory=True)
    (release_root / "lut").symlink_to(PACKAGE_LUT_ROOT, target_is_directory=True)
    file_records = await asyncio.to_thread(
        _selected_file_records,
        manifest,
        resource_root=release_root,
        lut_enabled=lut_enabled,
    )
    payload = _complete_payload(
        source="packaged",
        config_fingerprint=config_fingerprint,
        manifest=manifest,
        resource_fingerprint=None,
        fallback_reason=fallback_reason,
        files=file_records,
    )
    _write_complete_file(release_root, payload)
    return release_root, payload


async def resolve_model_parameter_resources(
    storage: ModelParameterResourceStorageConfig,
    *,
    lut_enabled: bool,
    lut_policy: LutLoadPolicy,
    client_factory: Callable[[ModelParameterResourceStorageConfig], ObjectStorageReader] = _create_client,
) -> ModelParameterResourcePaths:
    """원격 리소스 세트를 원자적으로 선택하고 worker가 고정해 사용할 경로를 반환한다."""
    manifest = load_model_parameter_resource_manifest(storage.manifest_path, lut_root=PACKAGE_LUT_ROOT)
    if not storage.enabled:
        return ModelParameterResourcePaths(
            source="packaged",
            root=PACKAGE_BASECASE_DIR.parent,
            basecase_dir=PACKAGE_BASECASE_DIR,
            lut_root=PACKAGE_LUT_ROOT,
            manifest_path=manifest.path,
            semantic_schema_hash=manifest.semantic_schema_hash,
        )

    local_root = Path(storage.local_root).expanduser().resolve()  # noqa: ASYNC240
    try:
        local_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        (local_root / "releases").mkdir(mode=0o700, exist_ok=True)
    except OSError as exc:
        msg = f"local_root 생성 실패: {local_root}"
        raise _bootstrap_error(msg) from exc

    remote_config_error: RemoteResourceConfigError | None = None
    try:
        config_fingerprint, plan = resource_config_fingerprint(
            manifest,
            endpoint_url=storage.endpoint_url,
            region_name=storage.region_name,
            signature_version=storage.signature_version,
            default_bucket=storage.bucket,
            lut_enabled=lut_enabled,
        )
    except RemoteResourceConfigError as exc:
        remote_config_error = exc
        config_fingerprint = _fallback_config_fingerprint(
            manifest,
            storage=storage,
            lut_enabled=lut_enabled,
        )
        plan = ()

    async with _ProcessFileLock(
        local_root / LOCK_FILE_NAME,
        timeout_seconds=storage.lock_timeout_seconds,
    ):
        _clean_orphan_staging(local_root)
        current = _read_current_release(
            local_root,
            manifest=manifest,
            config_fingerprint=config_fingerprint,
            lut_enabled=lut_enabled,
        )
        if current is not None:
            release_root, payload = current
            logger.info(
                "Model Parameter resource current reused | source={} fingerprint={}",
                payload["source"],
                payload.get("resource_fingerprint"),
            )
            return _paths_from_release(release_root, payload, manifest=manifest)
        try:
            if remote_config_error is not None:
                raise remote_config_error
            release_root, payload, file_count, total_bytes = await _build_remote_release(
                local_root=local_root,
                manifest=manifest,
                config_fingerprint=config_fingerprint,
                plan=plan,
                storage=storage,
                lut_enabled=lut_enabled,
                lut_policy=lut_policy,
                client_factory=client_factory,
            )
            _activate_release(local_root, release_root)
            logger.info(
                "Model Parameter resource remote sync completed | files={} bytes={} fingerprint={}",
                file_count,
                total_bytes,
                payload.get("resource_fingerprint"),
            )
            return _paths_from_release(release_root, payload, manifest=manifest)
        except (MIBaseError, RemoteResourceConfigError, RemoteResourceSyncError) as remote_error:
            fallback_reason = _safe_reason(remote_error)
            logger.error(
                "Model Parameter resource remote sync failed; packaged fallback will be activated | reason={}",
                fallback_reason,
            )
            release_root, payload = await _build_packaged_release(
                local_root=local_root,
                manifest=manifest,
                config_fingerprint=config_fingerprint,
                fallback_reason=fallback_reason,
                lut_enabled=lut_enabled,
                lut_policy=lut_policy,
            )
            _activate_release(local_root, release_root)
            logger.warning(
                "Model Parameter resource packaged fallback active | reason={}",
                fallback_reason,
            )
            return _paths_from_release(release_root, payload, manifest=manifest)


async def ensure_model_parameter_resource_runtime(
    storage: ModelParameterResourceStorageConfig,
    *,
    lut_enabled: bool,
    lut_policy: LutLoadPolicy,
    client_factory: Callable[[ModelParameterResourceStorageConfig], ObjectStorageReader] = _create_client,
) -> ModelParameterResourcePaths:
    """현재 process에서 사용할 리소스 경로를 한 번 결정하고 고정한다."""
    registered = get_registered_model_parameter_resource_paths()
    if registered is not None:
        return registered

    paths = await resolve_model_parameter_resources(
        storage,
        lut_enabled=lut_enabled,
        lut_policy=lut_policy,
        client_factory=client_factory,
    )
    register_model_parameter_resource_paths(paths)
    return get_model_parameter_resource_paths()
