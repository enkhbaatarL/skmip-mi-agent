from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal

import yaml

from apps.agents.model_parameter_agent.utils.lut.registry import (
    ParameterSpecRegistry,
    load_parameter_spec_registry,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.utils.yaml_utils import normalize_yaml_text
from apps.common.values.error_codes import ErrorCode


PACKAGE_DIR = Path(__file__).resolve().parents[1]
PACKAGE_RESOURCE_DIR = PACKAGE_DIR / "resources"
PACKAGE_BASECASE_DIR = PACKAGE_RESOURCE_DIR / "basecase"
PACKAGE_LUT_ROOT = PACKAGE_RESOURCE_DIR / "lut"
DEFAULT_RESOURCE_MANIFEST_PATH = PACKAGE_RESOURCE_DIR / "config" / "model_parameter_resources.yaml"
REQUIRED_BASECASE_ROLES = frozenset({"demand", "supply", "trade"})


class RemoteResourceConfigError(ValueError):
    """원격 object location 설정 오류. packaged fallback 대상으로 분류한다."""


@dataclass(frozen=True, slots=True)
class ObjectStorageLocation:
    bucket: str
    object_key: str


@dataclass(frozen=True, slots=True)
class ManifestResourceFile:
    area: Literal["basecase", "lut"]
    logical_name: str
    relative_path: str
    object_storage_path: object

    @property
    def target_relative_path(self) -> str:
        return f"{self.area}/{self.relative_path}"


@dataclass(frozen=True, slots=True)
class PlannedResourceDownload:
    area: Literal["basecase", "lut"]
    logical_name: str
    relative_path: str
    target_relative_path: str
    location: ObjectStorageLocation


@dataclass(frozen=True, slots=True)
class ModelParameterResourceManifest:
    path: Path
    schema_version: int
    basecase_files: Mapping[str, ManifestResourceFile]
    lut_files: tuple[ManifestResourceFile, ...]
    lut_registry: ParameterSpecRegistry
    semantic_schema_hash: str

    def selected_files(self, *, lut_enabled: bool) -> tuple[ManifestResourceFile, ...]:
        selected = [*self.basecase_files.values()]
        if lut_enabled:
            selected.extend(self.lut_files)
        return tuple(selected)

    def download_plan(
        self,
        *,
        default_bucket: str,
        lut_enabled: bool,
    ) -> tuple[PlannedResourceDownload, ...]:
        plan_by_target: dict[str, PlannedResourceDownload] = {}
        for resource_file in self.selected_files(lut_enabled=lut_enabled):
            location = _parse_object_storage_location(
                resource_file.object_storage_path,
                default_bucket=default_bucket,
                logical_name=resource_file.logical_name,
            )
            planned = PlannedResourceDownload(
                area=resource_file.area,
                logical_name=resource_file.logical_name,
                relative_path=resource_file.relative_path,
                target_relative_path=resource_file.target_relative_path,
                location=location,
            )
            previous = plan_by_target.get(planned.target_relative_path)
            if previous is not None and previous.location != planned.location:
                msg = f"서로 다른 원격 객체가 동일한 local target을 사용합니다: {planned.target_relative_path}"
                raise RemoteResourceConfigError(
                    msg,
                )
            plan_by_target[planned.target_relative_path] = planned
        return tuple(plan_by_target[key] for key in sorted(plan_by_target))


def _manifest_error(detail: str) -> MIBaseError:
    return MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def _safe_relative_path(raw_path: object, *, label: str) -> str:
    text = str(raw_path or "")
    if not text or text != text.strip() or "\\" in text:
        msg = f"{label} path must be a non-empty POSIX relative path"
        raise _manifest_error(msg)
    path = PurePosixPath(text)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        msg = f"{label} path escapes the resource directory: {text}"
        raise _manifest_error(msg)
    return path.as_posix()


def _contains_placeholder(value: str) -> bool:
    return value.startswith("${") and value.endswith("}")


def _valid_storage_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if not value or value != value.strip() or _contains_placeholder(value):
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    return value


def _parse_object_storage_location(
    raw_path: object,
    *,
    default_bucket: str,
    logical_name: str,
) -> ObjectStorageLocation:
    bucket = _valid_storage_text(default_bucket)
    object_key = _valid_storage_text(raw_path)
    if bucket is None:
        msg = f"유효한 bucket 설정이 필요합니다: {logical_name}"
        raise RemoteResourceConfigError(msg)
    if object_key is None:
        msg = f"유효한 object_storage_path 설정이 필요합니다: {logical_name}"
        raise RemoteResourceConfigError(msg)
    return ObjectStorageLocation(bucket=bucket, object_key=object_key)


def _basecase_files(raw_basecase: object) -> Mapping[str, ManifestResourceFile]:
    if not isinstance(raw_basecase, dict):
        msg = "manifest basecase must be a mapping"
        raise _manifest_error(msg)
    roles = set(raw_basecase)
    if roles != REQUIRED_BASECASE_ROLES:
        missing = sorted(REQUIRED_BASECASE_ROLES - roles)
        unknown = sorted(roles - REQUIRED_BASECASE_ROLES)
        msg = f"manifest basecase roles are invalid: missing={missing}, unknown={unknown}"
        raise _manifest_error(
            msg,
        )

    files: dict[str, ManifestResourceFile] = {}
    targets: set[str] = set()
    for role in sorted(REQUIRED_BASECASE_ROLES):
        raw_file = raw_basecase[role]
        if not isinstance(raw_file, dict):
            msg = f"basecase.{role} must be a mapping"
            raise _manifest_error(msg)
        unknown_fields = sorted(set(raw_file) - {"path", "object_storage_path"})
        if unknown_fields:
            msg = f"basecase.{role} contains unknown fields: {unknown_fields}"
            raise _manifest_error(msg)
        relative_path = _safe_relative_path(raw_file.get("path"), label=f"basecase.{role}")
        if relative_path in targets:
            msg = f"basecase local target is duplicated: {relative_path}"
            raise _manifest_error(msg)
        targets.add(relative_path)
        files[role] = ManifestResourceFile(
            area="basecase",
            logical_name=f"basecase.{role}",
            relative_path=relative_path,
            object_storage_path=raw_file.get("object_storage_path"),
        )
    return MappingProxyType(files)


def _lut_files(
    raw_lut: object,
    *,
    registry: ParameterSpecRegistry,
) -> tuple[ManifestResourceFile, ...]:
    if not isinstance(raw_lut, dict):
        msg = "manifest lut must be a mapping"
        raise _manifest_error(msg)
    files: list[ManifestResourceFile] = []
    for parameter_name, parameter_spec in registry.specs.items():
        raw_parameter_spec = raw_lut.get(parameter_name)
        raw_files = raw_parameter_spec.get("files") if isinstance(raw_parameter_spec, dict) else None
        if not isinstance(raw_files, dict):
            msg = f"lut.{parameter_name}.files must be a mapping"
            raise _manifest_error(msg)
        for role, file_spec in parameter_spec.files.items():
            raw_file = raw_files.get(role)
            if not isinstance(raw_file, dict):
                msg = f"lut.{parameter_name}.files.{role} must be a mapping"
                raise _manifest_error(msg)
            files.append(
                ManifestResourceFile(
                    area="lut",
                    logical_name=f"lut.{parameter_name}.{role}",
                    relative_path=file_spec.relative_path,
                    object_storage_path=raw_file.get("object_storage_path"),
                ),
            )
    return tuple(files)


def _semantic_schema_hash(
    *,
    schema_version: int,
    basecase_files: Mapping[str, ManifestResourceFile],
    registry: ParameterSpecRegistry,
) -> str:
    payload = {
        "schema_version": schema_version,
        "basecase": {role: resource_file.relative_path for role, resource_file in sorted(basecase_files.items())},
        "lut_schema_hash": registry.schema_hash,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_model_parameter_resource_manifest(
    manifest_path: Path | str = DEFAULT_RESOURCE_MANIFEST_PATH,
    *,
    lut_root: Path | str = PACKAGE_LUT_ROOT,
) -> ModelParameterResourceManifest:
    path = Path(manifest_path).expanduser().resolve()
    root = Path(lut_root).expanduser().resolve()
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        msg = f"failed to read model parameter resource manifest {path}: {exc}"
        raise _manifest_error(msg) from exc
    try:
        normalized_text = normalize_yaml_text(raw_bytes.decode("utf-8"))
        normalized_bytes = normalized_text.encode("utf-8")
        raw_document = yaml.safe_load(normalized_text)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        msg = f"invalid model parameter resource manifest {path}: {exc}"
        raise _manifest_error(msg) from exc
    if not isinstance(raw_document, dict):
        msg = "model parameter resource manifest must be a mapping"
        raise _manifest_error(msg)
    unknown_fields = sorted(set(raw_document) - {"schema_version", "basecase", "lut"})
    if unknown_fields:
        msg = f"manifest contains unknown fields: {unknown_fields}"
        raise _manifest_error(msg)
    if raw_document.get("schema_version") != 1:
        msg = "manifest schema_version must be 1"
        raise _manifest_error(msg)

    basecase_files = _basecase_files(raw_document.get("basecase"))
    registry = load_parameter_spec_registry(path, lut_root=root, yaml_bytes=normalized_bytes)
    lut_files = _lut_files(raw_document.get("lut"), registry=registry)
    return ModelParameterResourceManifest(
        path=path,
        schema_version=1,
        basecase_files=basecase_files,
        lut_files=lut_files,
        lut_registry=registry,
        semantic_schema_hash=_semantic_schema_hash(
            schema_version=1,
            basecase_files=basecase_files,
            registry=registry,
        ),
    )


def resource_config_fingerprint(
    manifest: ModelParameterResourceManifest,
    *,
    endpoint_url: str,
    region_name: str,
    signature_version: str,
    default_bucket: str,
    lut_enabled: bool,
) -> tuple[str, tuple[PlannedResourceDownload, ...]]:
    plan = manifest.download_plan(default_bucket=default_bucket, lut_enabled=lut_enabled)
    payload = {
        "endpoint_url": endpoint_url,
        "region_name": region_name,
        "signature_version": signature_version,
        "lut_enabled": lut_enabled,
        "schema_version": manifest.schema_version,
        "files": [
            {
                "bucket": item.location.bucket,
                "object_key": item.location.object_key,
                "target": item.target_relative_path,
            }
            for item in plan
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), plan
