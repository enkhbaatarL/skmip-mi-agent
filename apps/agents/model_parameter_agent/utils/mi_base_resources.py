# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import time
from typing import Literal, Protocol
from urllib.parse import unquote, urlsplit
import uuid

from botocore.exceptions import BotoCoreError

from apps.agents.model_parameter_agent.utils.resource_runtime import (
    ModelParameterResourcePaths,
    get_model_parameter_resource_paths,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    PACKAGE_RESOURCE_DIR,
    ModelParameterWorkbookContract,
    load_workbook_contract,
    workbook_sha256,
)
from apps.agents.model_parameter_agent.utils.workbook_reference import (
    extract_workbook_references,
)
from apps.common.configs.config import (
    ModelParameterMiBaseFallbackConfig,
    ModelParameterResourceStorageConfig,
    get_settings,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.object_storage import DownloadedObject, ObjectMetadata, S3ObjectStorageClient
from apps.persistence.mi_base.schema import MiBaseFilePayload, MiBaseSnapshot


MI_BASE_RELATION_CODE = "SCNRCASE"
_ROLE_TOKEN_PATTERN = re.compile(r"\b(demand|supply|trade)\b", re.IGNORECASE)
_COMPLETE_FILE_NAME = ".complete.json"
_LOCK_FILE_NAME = ".mi-base.lock"
_CACHE_MARKER_SCHEMA_VERSION = 2


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


@dataclass(frozen=True, slots=True)
class _ObjectLocation:
    bucket: str
    object_key: str


@dataclass(frozen=True, slots=True)
class _SelectedInput:
    role: Literal["demand", "supply", "trade"]
    file: MiBaseFilePayload
    location: _ObjectLocation


@dataclass(frozen=True, slots=True)
class MiBaseResourceSelection:
    source: Literal["mi_base", "verified_cache", "configured_fallback"]
    basecase_dir: Path
    workbook_resource_root: Path
    workbook_contract: ModelParameterWorkbookContract
    case_id: int | None
    linked_file_counts: Mapping[str, int]
    fallback_reason: str | None = None


class MiBaseResourceFallbackError(RuntimeError):
    """A selected MI Base cannot safely replace the configured resources."""


class _ProcessFileLock(AbstractAsyncContextManager[None]):
    def __init__(self, path: Path, *, timeout_seconds: float) -> None:
        self._path = path
        self._timeout_seconds = timeout_seconds
        self._descriptor: int | None = None

    async def __aenter__(self) -> None:
        self._descriptor = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o600)
        deadline = time.monotonic() + self._timeout_seconds
        while True:
            try:
                fcntl.flock(self._descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(self._descriptor)
                    self._descriptor = None
                    message = "MI Base resource lock timeout"
                    raise MiBaseResourceFallbackError(message) from None
                await asyncio.sleep(0.1)
            else:
                return

    async def __aexit__(self, *exc_info: object) -> None:
        if self._descriptor is None:
            return
        try:
            fcntl.flock(self._descriptor, fcntl.LOCK_UN)
        finally:
            os.close(self._descriptor)
            self._descriptor = None


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
        message = "Object Storage client initialization failed"
        raise MiBaseResourceFallbackError(message) from exc


def _linked_file_counts(snapshot: MiBaseSnapshot | None) -> dict[str, int]:
    return {
        MI_BASE_RELATION_CODE: (
            len(snapshot.files_for(MI_BASE_RELATION_CODE)) if snapshot is not None else 0
        ),
    }


def _fallback_selection(
    *,
    snapshot: MiBaseSnapshot | None,
    reason: str,
    resource_paths: ModelParameterResourcePaths,
) -> MiBaseResourceSelection:
    contract = resource_paths.workbook_contract or load_workbook_contract()
    return MiBaseResourceSelection(
        source="configured_fallback",
        basecase_dir=resource_paths.basecase_dir,
        # The configured release root owns the legacy Basecase/LUT runtime,
        # while versioned v4 workbooks are immutable package artifacts.  A
        # remote or packaged wrapper release does not contain basecase_v4/.
        workbook_resource_root=PACKAGE_RESOURCE_DIR,
        workbook_contract=contract,
        case_id=snapshot.case_id if snapshot is not None else None,
        linked_file_counts=_linked_file_counts(snapshot),
        fallback_reason=reason,
    )


def _classify_inputs(
    snapshot: MiBaseSnapshot,
    *,
    bucket: str,
) -> tuple[_SelectedInput, ...]:
    selected: dict[str, _SelectedInput] = {}
    for file in snapshot.files_for(MI_BASE_RELATION_CODE):
        original_name = str(file.org_file_nm or "").strip()
        if Path(original_name).suffix.lower() != ".xlsm":
            continue
        normalized_name = original_name.replace("_", " ")
        roles = {match.group(1).lower() for match in _ROLE_TOKEN_PATTERN.finditer(normalized_name)}
        if not roles:
            continue
        if len(roles) > 1:
            message = f"Ambiguous SCNRCASE workbook role: file_no={file.file_no} roles={sorted(roles)}"
            raise MiBaseResourceFallbackError(message)
        role = next(iter(roles))
        if role in selected:
            message = f"Duplicate SCNRCASE workbook role: role={role}"
            raise MiBaseResourceFallbackError(message)
        selected[role] = _SelectedInput(
            role=role,  # type: ignore[arg-type]
            file=file,
            location=_parse_object_location(
                str(file.strg_path_nm or ""),
                configured_bucket=bucket,
                file_no=file.file_no,
            ),
        )
    expected = {"demand", "supply", "trade"}
    if set(selected) != expected:
        message = (
            f"SCNRCASE input workbook set must contain exactly Demand, Supply, and Trade: actual={sorted(selected)}"
        )
        raise MiBaseResourceFallbackError(message)
    return tuple(selected[role] for role in ("demand", "supply", "trade"))


def _parse_object_location(
    value: str,
    *,
    configured_bucket: str,
    file_no: int,
) -> _ObjectLocation:
    raw_value = value.strip()
    if not raw_value or not configured_bucket.strip():
        message = f"Object Storage location is incomplete: file_no={file_no}"
        raise MiBaseResourceFallbackError(message)
    parsed = urlsplit(raw_value)
    raw_path = parsed.path if parsed.scheme or parsed.netloc else raw_value
    parts = tuple(part for part in PurePosixPath(unquote(raw_path).lstrip("/")).parts if part not in {"", "."})
    if ".." in parts:
        message = f"Object Storage key is unsafe: file_no={file_no}"
        raise MiBaseResourceFallbackError(message)
    bucket = configured_bucket.strip()
    if parts and parts[0] == bucket:
        key_parts = parts[1:]
    elif not parsed.scheme and not parsed.netloc:
        key_parts = parts
    else:
        message = f"Linked file bucket differs from configured bucket: file_no={file_no}"
        raise MiBaseResourceFallbackError(message)
    if not key_parts:
        message = f"Object Storage key is empty: file_no={file_no}"
        raise MiBaseResourceFallbackError(message)
    return _ObjectLocation(bucket=bucket, object_key=PurePosixPath(*key_parts).as_posix())


def _metadata_fingerprint(
    snapshot: MiBaseSnapshot,
    inputs: tuple[_SelectedInput, ...],
    metadata: Mapping[str, ObjectMetadata],
) -> str:
    payload = {
        "case_id": snapshot.case_id,
        "files": [
            {
                "role": item.role,
                "file_no": item.file.file_no,
                "bucket": item.location.bucket,
                "object_key": item.location.object_key,
                "etag": metadata[item.role].etag,
                "content_length": metadata[item.role].content_length,
                "last_modified": metadata[item.role].last_modified,
                "version_id": metadata[item.role].version_id,
            }
            for item in inputs
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()


def _linked_file_fingerprint(
    snapshot: MiBaseSnapshot,
    inputs: tuple[_SelectedInput, ...],
) -> str:
    """Build an Object-Storage-independent identity for the selected input set."""
    payload = {
        "case_id": snapshot.case_id,
        "files": [
            {
                "role": item.role,
                "file_no": item.file.file_no,
                "file_rel_obj_spt_cd": item.file.file_rel_obj_spt_cd,
                "file_rel_obj_dstg_no": item.file.file_rel_obj_dstg_no,
                "org_file_nm": item.file.org_file_nm,
                "strg_file_nm": item.file.strg_file_nm,
                "strg_path_nm": item.file.strg_path_nm,
                "file_size": item.file.file_size,
                "filex_nm": item.file.filex_nm,
                "mime_type_nm": item.file.mime_type_nm,
                "bucket": item.location.bucket,
                "object_key": item.location.object_key,
            }
            for item in inputs
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()


def _contract_with_hashes(
    contract: ModelParameterWorkbookContract,
    *,
    hashes: Mapping[str, str],
) -> ModelParameterWorkbookContract:
    workbooks = {
        role: artifact.model_copy(update={"sha256": hashes[role]}) for role, artifact in contract.workbooks.items()
    }
    return contract.model_copy(update={"workbooks": workbooks})


def _remove_cache_path(path: Path, *, cache_root: Path) -> None:
    resolved = path.resolve(strict=False)
    if resolved == cache_root or not resolved.is_relative_to(cache_root):
        message = "Refusing to remove an unsafe MI Base cache path"
        raise MiBaseResourceFallbackError(message)
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def _stage_auxiliary_sources(
    *,
    contract: ModelParameterWorkbookContract,
    configured_root: Path,
    staging_root: Path,
) -> None:
    auxiliary_paths = {
        source.path
        for parameter in contract.parameters.values()
        for source in parameter.reference_source.auxiliary_sources.values()
    }
    for relative_path in auxiliary_paths:
        source = (configured_root / relative_path).resolve(strict=True)
        destination = staging_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source)


def _link_legacy_basecase_files(
    *,
    contract: ModelParameterWorkbookContract,
    staging_root: Path,
) -> Path:
    v4_directory = staging_root / contract.resource_directory
    legacy_directory = staging_root / "basecase"
    legacy_directory.mkdir(parents=True, exist_ok=True)
    for artifact in contract.workbooks.values():
        source = v4_directory / artifact.filename
        destination = legacy_directory / artifact.filename
        try:
            os.link(source, destination)
        except OSError:
            shutil.copy2(source, destination)
    return legacy_directory


async def _head_inputs(
    client: ObjectStorageReader,
    inputs: tuple[_SelectedInput, ...],
) -> dict[str, ObjectMetadata]:
    metadata: dict[str, ObjectMetadata] = {}
    for item in inputs:
        head = await client.head_object(
            bucket=item.location.bucket,
            object_key=item.location.object_key,
            logical_name=f"MI Base {item.role} workbook",
        )
        if head.content_length <= 0:
            message = f"MI Base workbook is empty: role={item.role}"
            raise MiBaseResourceFallbackError(message)
        if item.file.file_size is not None and head.content_length != item.file.file_size:
            message = f"MI Base workbook size differs from file metadata: role={item.role}"
            raise MiBaseResourceFallbackError(message)
        metadata[item.role] = head
    return metadata


def _matching_cache_payload(
    *,
    marker: Path,
    snapshot: MiBaseSnapshot,
    linked_file_fingerprint: str,
    remote_metadata_fingerprint: str | None,
) -> dict[str, object] | None:
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != _CACHE_MARKER_SCHEMA_VERSION:
        return None
    if payload.get("case_id") != snapshot.case_id:
        return None
    if payload.get("linked_file_fingerprint") != linked_file_fingerprint:
        return None
    if (
        remote_metadata_fingerprint is not None
        and payload.get("remote_metadata_fingerprint") != remote_metadata_fingerprint
    ):
        return None
    return payload


def _cached_selection(
    *,
    release_root: Path,
    snapshot: MiBaseSnapshot,
    configured_paths: ModelParameterResourcePaths,
    linked_file_fingerprint: str,
    remote_metadata_fingerprint: str | None,
    source: Literal["mi_base", "verified_cache"],
    fallback_reason: str | None = None,
) -> MiBaseResourceSelection | None:
    marker = release_root / _COMPLETE_FILE_NAME
    if not marker.is_file():
        return None
    payload = _matching_cache_payload(
        marker=marker,
        snapshot=snapshot,
        linked_file_fingerprint=linked_file_fingerprint,
        remote_metadata_fingerprint=remote_metadata_fingerprint,
    )
    if payload is None:
        return None
    try:
        hashes = payload["workbook_sha256"]
        contract_template = configured_paths.workbook_contract or load_workbook_contract()
        if not isinstance(hashes, dict) or set(hashes) != set(contract_template.workbooks):
            return None
        contract = _contract_with_hashes(
            contract_template,
            hashes={str(key): str(value) for key, value in hashes.items()},
        )
        for artifact in contract.workbooks.values():
            workbook_path = release_root / contract.resource_directory / artifact.filename
            if workbook_sha256(workbook_path) != artifact.sha256:
                return None
        extract_workbook_references(
            contract,
            resource_root=release_root,
            use_cache=False,
        )
    except (KeyError, OSError, ValueError, MIBaseError):
        return None
    return MiBaseResourceSelection(
        source=source,
        basecase_dir=release_root / "basecase",
        workbook_resource_root=release_root,
        workbook_contract=contract,
        case_id=snapshot.case_id,
        linked_file_counts=_linked_file_counts(snapshot),
        fallback_reason=fallback_reason,
    )


def _verified_cached_selection(
    *,
    releases_root: Path,
    snapshot: MiBaseSnapshot,
    configured_paths: ModelParameterResourcePaths,
    linked_file_fingerprint: str,
    fallback_reason: str,
) -> MiBaseResourceSelection | None:
    candidates: list[MiBaseResourceSelection] = []
    for release_root in sorted(releases_root.glob(f"case-{snapshot.case_id}-*")):
        candidate = _cached_selection(
            release_root=release_root,
            snapshot=snapshot,
            configured_paths=configured_paths,
            linked_file_fingerprint=linked_file_fingerprint,
            remote_metadata_fingerprint=None,
            source="verified_cache",
            fallback_reason=fallback_reason,
        )
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return None

    workbook_hash_sets = {
        tuple(
            sorted((role, artifact.sha256) for role, artifact in candidate.workbook_contract.workbooks.items()),
        )
        for candidate in candidates
    }
    if len(workbook_hash_sets) != 1:
        message = (
            "Multiple MI Base cache contents match the same linked-file identity: "
            f"case_id={snapshot.case_id}"
        )
        raise MiBaseResourceFallbackError(message)
    return candidates[-1]


async def _download_release(
    *,
    snapshot: MiBaseSnapshot,
    inputs: tuple[_SelectedInput, ...],
    first_metadata: Mapping[str, ObjectMetadata],
    release_root: Path,
    cache_root: Path,
    configured_paths: ModelParameterResourcePaths,
    storage: ModelParameterResourceStorageConfig,
    client: ObjectStorageReader,
    deadline: float,
    linked_file_fingerprint: str,
    remote_metadata_fingerprint: str,
) -> MiBaseResourceSelection:
    staging_root = cache_root / f"staging-{uuid.uuid4().hex}"
    contract = configured_paths.workbook_contract or load_workbook_contract()
    try:
        workbook_hashes: dict[str, str] = {}
        for item in inputs:
            artifact = contract.workbooks[item.role]
            destination = staging_root / contract.resource_directory / artifact.filename
            temporary_destination = destination.with_name(f"{destination.name}.tmp")
            downloaded = await client.download_object(
                bucket=item.location.bucket,
                object_key=item.location.object_key,
                logical_name=f"MI Base {item.role} workbook",
                destination=temporary_destination,
                chunk_size_bytes=storage.download_chunk_size_bytes,
                deadline=deadline,
            )
            expected = first_metadata[item.role]
            if downloaded.size != expected.content_length or downloaded.metadata != expected:
                message = f"MI Base workbook changed while downloading: role={item.role}"
                raise MiBaseResourceFallbackError(message)  # noqa: TRY301
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary_destination.replace(destination)
            workbook_hashes[item.role] = downloaded.sha256

        final_metadata = await _head_inputs(client, inputs)
        if final_metadata != dict(first_metadata):
            message = "MI Base workbook metadata changed while preparing the request"
            raise MiBaseResourceFallbackError(message)  # noqa: TRY301
        _link_legacy_basecase_files(contract=contract, staging_root=staging_root)
        _stage_auxiliary_sources(
            contract=contract,
            configured_root=configured_paths.root,
            staging_root=staging_root,
        )
        dynamic_contract = _contract_with_hashes(contract, hashes=workbook_hashes)
        try:
            extract_workbook_references(
                dynamic_contract,
                resource_root=staging_root,
                use_cache=False,
            )
        except MIBaseError as exc:
            message = "MI Base workbook contract validation failed"
            raise MiBaseResourceFallbackError(message) from exc
        marker = staging_root / _COMPLETE_FILE_NAME
        marker.write_text(
            json.dumps(
                {
                    "schema_version": _CACHE_MARKER_SCHEMA_VERSION,
                    "case_id": snapshot.case_id,
                    "linked_file_fingerprint": linked_file_fingerprint,
                    "remote_metadata_fingerprint": remote_metadata_fingerprint,
                    "workbook_sha256": workbook_hashes,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        release_root.parent.mkdir(parents=True, exist_ok=True)
        staging_root.replace(release_root)
        return MiBaseResourceSelection(
            source="mi_base",
            basecase_dir=release_root / "basecase",
            workbook_resource_root=release_root,
            workbook_contract=dynamic_contract,
            case_id=snapshot.case_id,
            linked_file_counts=_linked_file_counts(snapshot),
        )
    except Exception:
        _remove_cache_path(staging_root, cache_root=cache_root)
        raise


async def _prepare_mi_base_release(  # noqa: C901
    snapshot: MiBaseSnapshot,
    *,
    configured_paths: ModelParameterResourcePaths,
    storage: ModelParameterResourceStorageConfig,
    fallback_policy: ModelParameterMiBaseFallbackConfig,
    client_factory: Callable[[ModelParameterResourceStorageConfig], ObjectStorageReader],
) -> MiBaseResourceSelection:
    inputs = _classify_inputs(snapshot, bucket=storage.bucket)
    cache_root, releases_root = await asyncio.to_thread(
        _prepare_cache_directories,
        storage.local_root,
    )
    linked_fingerprint = _linked_file_fingerprint(snapshot, inputs)

    async def unavailable_fallback(reason: str) -> MiBaseResourceSelection | None:
        mode = fallback_policy.active_case_unavailable_mode
        if mode == "configured_fallback":
            return _fallback_selection(
                snapshot=snapshot,
                reason=reason,
                resource_paths=configured_paths,
            )
        if mode != "verified_cache":
            return None
        async with _ProcessFileLock(
            cache_root / _LOCK_FILE_NAME,
            timeout_seconds=storage.lock_timeout_seconds,
        ):
            return _verified_cached_selection(
                releases_root=releases_root,
                snapshot=snapshot,
                configured_paths=configured_paths,
                linked_file_fingerprint=linked_fingerprint,
                fallback_reason=reason,
            )

    if not storage.enabled:
        message = "Object Storage resource loading is disabled"
        fallback = await unavailable_fallback(message)
        if fallback is not None:
            return fallback
        raise MiBaseResourceFallbackError(message)

    deadline = time.monotonic() + storage.bootstrap_timeout_seconds
    try:
        client = client_factory(storage)
    except (MiBaseResourceFallbackError, MIBaseError, OSError, ValueError) as exc:
        reason = _safe_reason(exc)
        fallback = await unavailable_fallback(reason)
        if fallback is not None:
            return fallback
        raise MiBaseResourceFallbackError(str(exc)) from exc

    remote_identity_observed = False
    try:
        last_error: Exception | None = None
        for _attempt in range(1, storage.max_attempts + 1):
            try:
                first_metadata = await _head_inputs(client, inputs)
                fingerprint = _metadata_fingerprint(snapshot, inputs, first_metadata)
                remote_identity_observed = True
                release_root = releases_root / f"case-{snapshot.case_id}-{fingerprint[:16]}"
                async with _ProcessFileLock(
                    cache_root / _LOCK_FILE_NAME,
                    timeout_seconds=storage.lock_timeout_seconds,
                ):
                    cached = _cached_selection(
                        release_root=release_root,
                        snapshot=snapshot,
                        configured_paths=configured_paths,
                        linked_file_fingerprint=linked_fingerprint,
                        remote_metadata_fingerprint=fingerprint,
                        source="mi_base",
                    )
                    if cached is not None:
                        return cached
                    if release_root.exists() or release_root.is_symlink():
                        _remove_cache_path(release_root, cache_root=cache_root)
                    return await _download_release(
                        snapshot=snapshot,
                        inputs=inputs,
                        first_metadata=first_metadata,
                        release_root=release_root,
                        cache_root=cache_root,
                        configured_paths=configured_paths,
                        storage=storage,
                        client=client,
                        deadline=deadline,
                        linked_file_fingerprint=linked_fingerprint,
                        remote_metadata_fingerprint=fingerprint,
                    )
            except MiBaseResourceFallbackError:
                raise
            except (MIBaseError, OSError, ValueError) as exc:
                last_error = exc
                if time.monotonic() >= deadline:
                    break
        message = str(last_error or "MI Base resource preparation failed")
        if not remote_identity_observed:
            fallback = await unavailable_fallback(
                _safe_reason(last_error or MiBaseResourceFallbackError(message)),
            )
            if fallback is not None:
                return fallback
        raise MiBaseResourceFallbackError(message) from last_error
    finally:
        await client.close()


def _prepare_cache_directories(local_root: str) -> tuple[Path, Path]:
    cache_root = Path(local_root).expanduser().resolve() / "mi-base"
    cache_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    releases_root = cache_root / "releases"
    releases_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return cache_root, releases_root


def _safe_reason(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:500]


def mi_base_resource_identity(
    selection: MiBaseResourceSelection,
) -> dict[str, object]:
    """Return a path-free identity suitable for graph and campaign evidence."""
    return {
        "source": selection.source,
        "case_id": selection.case_id,
        "workbook_sha256": {
            role: selection.workbook_contract.workbooks[role].sha256
            for role in sorted(selection.workbook_contract.workbooks)
        },
    }


async def resolve_mi_base_resources(
    snapshot: MiBaseSnapshot | None,
    *,
    client_factory: Callable[[ModelParameterResourceStorageConfig], ObjectStorageReader] = _create_client,
) -> MiBaseResourceSelection:
    """Resolve request-local MI Base inputs under the configured fallback boundary."""
    configured_paths = get_model_parameter_resource_paths()
    settings = get_settings()
    fallback_policy = settings.model_parameter_mi_base_fallback
    if snapshot is None:
        if fallback_policy.no_active_case_mode == "configured_fallback":
            return _fallback_selection(
                snapshot=None,
                reason="No active MI Base; using explicitly enabled configured Basecase fallback",
                resource_paths=configured_paths,
            )
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail="No active MI Base is available for the model parameter proposal",
        )
    try:
        selection = await _prepare_mi_base_release(
            snapshot,
            configured_paths=configured_paths,
            storage=settings.model_parameter_resource_storage,
            fallback_policy=fallback_policy,
            client_factory=client_factory,
        )
    except (MiBaseResourceFallbackError, MIBaseError, OSError, ValueError) as exc:
        reason = _safe_reason(exc)
        logger.error(
            "[model-parameter] MI Base input unavailable | case_id={} reason={}",
            snapshot.case_id,
            reason,
        )
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=(
                "Selected MI Base input workbooks are unavailable: "
                f"case_id={snapshot.case_id}"
            ),
        ) from exc
    if selection.source == "verified_cache":
        logger.warning(
            "[model-parameter] verified MI Base cache fallback active | case_id={} reason={}",
            snapshot.case_id,
            selection.fallback_reason,
        )
    elif selection.source == "configured_fallback":
        logger.warning(
            "[model-parameter] configured Basecase fallback active | case_id={} reason={}",
            snapshot.case_id,
            selection.fallback_reason,
        )
    logger.info(
        "[model-parameter] MI Base inputs ready | case_id={} source={} linked_file_counts={}",
        snapshot.case_id,
        selection.source,
        dict(selection.linked_file_counts),
    )
    return selection


__all__ = [
    "MI_BASE_RELATION_CODE",
    "MiBaseResourceSelection",
    "mi_base_resource_identity",
    "resolve_mi_base_resources",
]
