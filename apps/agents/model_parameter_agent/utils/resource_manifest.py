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
from apps.agents.model_parameter_agent.utils.proposal_capabilities import (
    ProposalCapabilityContract,
    load_proposal_capability_contract,
    proposal_capability_contract_sha256,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    ModelParameterWorkbookContract,
    load_workbook_contract,
    workbook_contract_schema_hash,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


PACKAGE_DIR = Path(__file__).resolve().parents[1]
PACKAGE_RESOURCE_DIR = PACKAGE_DIR / "resources"
PACKAGE_BASECASE_DIR = PACKAGE_RESOURCE_DIR / "basecase"
PACKAGE_LUT_ROOT = PACKAGE_RESOURCE_DIR / "lut"
MODEL_PARAMETER_RESOURCE_SCHEMA_VERSION = 6
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
    source_path: Path
    schema_version: int
    basecase_files: Mapping[str, ManifestResourceFile]
    lut_files: tuple[ManifestResourceFile, ...]
    reference_files: tuple[ManifestResourceFile, ...]
    lut_registry: ParameterSpecRegistry
    workbook_contract_path: Path
    workbook_contract: ModelParameterWorkbookContract
    workbook_contract_schema_hash: str
    proposal_capability_contract_path: Path
    proposal_capability_contract: ProposalCapabilityContract
    proposal_capability_contract_sha256: str
    canonical_yaml: bytes
    semantic_schema_hash: str

    def selected_files(self, *, lut_enabled: bool) -> tuple[ManifestResourceFile, ...]:
        selected = [*self.basecase_files.values()]
        if lut_enabled:
            selected.extend(self.lut_files)
            selected.extend(self.reference_files)
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


def _reference_files(
    raw_references: object,
    *,
    registry: ParameterSpecRegistry,
) -> tuple[ManifestResourceFile, ...]:
    if not isinstance(raw_references, dict):
        msg = "manifest references must be a mapping"
        raise _manifest_error(msg)
    if set(raw_references) != set(registry.references):
        missing = sorted(set(registry.references) - set(raw_references))
        unknown = sorted(set(raw_references) - set(registry.references))
        msg = f"manifest references are invalid: missing={missing}, unknown={unknown}"
        raise _manifest_error(msg)

    files: list[ManifestResourceFile] = []
    for reference_name, file_spec in registry.references.items():
        raw_file = raw_references.get(reference_name)
        if not isinstance(raw_file, dict):
            msg = f"references.{reference_name} must be a mapping"
            raise _manifest_error(msg)
        files.append(
            ManifestResourceFile(
                area="lut",
                logical_name=f"references.{reference_name}",
                relative_path=file_spec.relative_path,
                object_storage_path=raw_file.get("object_storage_path"),
            ),
        )
    return tuple(files)


def _workbook_contract(
    raw_contract: object,
) -> tuple[Path, ModelParameterWorkbookContract]:
    if not isinstance(raw_contract, dict):
        msg = "manifest workbook_contract must be a mapping"
        raise _manifest_error(msg)
    unknown_fields = sorted(set(raw_contract) - {"path"})
    if unknown_fields:
        msg = f"workbook_contract contains unknown fields: {unknown_fields}"
        raise _manifest_error(msg)
    relative_path = _safe_relative_path(
        raw_contract.get("path"),
        label="workbook_contract",
    )
    contract_path = (PACKAGE_RESOURCE_DIR / relative_path).resolve()
    if not contract_path.is_relative_to(PACKAGE_RESOURCE_DIR.resolve()):
        msg = f"workbook contract path escapes package resources: {relative_path}"
        raise _manifest_error(msg)
    return contract_path, load_workbook_contract(contract_path)


def _proposal_capabilities(
    raw_contract: object,
) -> tuple[Path, ProposalCapabilityContract, str]:
    if not isinstance(raw_contract, dict):
        raise _manifest_error("manifest proposal_capabilities must be a mapping")
    unknown_fields = sorted(set(raw_contract) - {"path", "release_id", "sha256"})
    if unknown_fields:
        raise _manifest_error(f"proposal_capabilities contains unknown fields: {unknown_fields}")
    relative_path = _safe_relative_path(raw_contract.get("path"), label="proposal_capabilities")
    contract_path = (PACKAGE_RESOURCE_DIR / relative_path).resolve()
    if not contract_path.is_relative_to(PACKAGE_RESOURCE_DIR.resolve()):
        raise _manifest_error(f"proposal capability path escapes package resources: {relative_path}")
    contract = load_proposal_capability_contract(contract_path)
    configured_release_id = str(raw_contract.get("release_id") or "")
    if configured_release_id != contract.release_id:
        raise _manifest_error(
            "proposal capability release ID differs: "
            f"configured={configured_release_id}, contract={contract.release_id}",
        )
    actual_sha256 = proposal_capability_contract_sha256(contract_path)
    configured_sha256 = str(raw_contract.get("sha256") or "")
    if configured_sha256 != actual_sha256:
        raise _manifest_error(
            "proposal capability fingerprint differs: "
            f"configured={configured_sha256}, actual={actual_sha256}",
        )
    return contract_path, contract, actual_sha256


def _semantic_schema_hash(
    *,
    basecase_files: Mapping[str, ManifestResourceFile],
    registry: ParameterSpecRegistry,
    workbook_contract: ModelParameterWorkbookContract,
    proposal_capability_contract_sha256: str,
) -> str:
    payload = {
        "schema_version": MODEL_PARAMETER_RESOURCE_SCHEMA_VERSION,
        "basecase": {role: resource_file.relative_path for role, resource_file in sorted(basecase_files.items())},
        "lut_schema_hash": registry.schema_hash,
        "workbook_contract_schema_hash": workbook_contract_schema_hash(
            workbook_contract,
        ),
        "proposal_capability_contract_sha256": proposal_capability_contract_sha256,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_model_parameter_resource_manifest(
    raw_document: Mapping[str, object],
    *,
    source_path: Path | str,
    lut_root: Path | str = PACKAGE_LUT_ROOT,
) -> ModelParameterResourceManifest:
    path = Path(source_path).expanduser().resolve()
    root = Path(lut_root).expanduser().resolve()
    if not isinstance(raw_document, Mapping):
        msg = "model_parameter_resources must be a mapping"
        raise _manifest_error(msg)
    document = dict(raw_document)
    unknown_fields = sorted(
        set(document) - {"basecase", "lut", "references", "workbook_contract", "proposal_capabilities"},
    )
    if unknown_fields:
        msg = f"model_parameter_resources contains unknown fields: {unknown_fields}"
        raise _manifest_error(msg)

    canonical_yaml = yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
    ).encode("utf-8")

    basecase_files = _basecase_files(document.get("basecase"))
    registry = load_parameter_spec_registry(path, lut_root=root, yaml_bytes=canonical_yaml)
    lut_files = _lut_files(document.get("lut"), registry=registry)
    reference_files = _reference_files(document.get("references", {}), registry=registry)
    workbook_contract_path, workbook_contract = _workbook_contract(
        document.get("workbook_contract"),
    )
    capability_path, capability_contract, capability_sha256 = _proposal_capabilities(
        document.get("proposal_capabilities"),
    )
    return ModelParameterResourceManifest(
        source_path=path,
        schema_version=MODEL_PARAMETER_RESOURCE_SCHEMA_VERSION,
        basecase_files=basecase_files,
        lut_files=lut_files,
        reference_files=reference_files,
        lut_registry=registry,
        workbook_contract_path=workbook_contract_path,
        workbook_contract=workbook_contract,
        workbook_contract_schema_hash=workbook_contract_schema_hash(
            workbook_contract,
        ),
        proposal_capability_contract_path=capability_path,
        proposal_capability_contract=capability_contract,
        proposal_capability_contract_sha256=capability_sha256,
        canonical_yaml=canonical_yaml,
        semantic_schema_hash=_semantic_schema_hash(
            basecase_files=basecase_files,
            registry=registry,
            workbook_contract=workbook_contract,
            proposal_capability_contract_sha256=capability_sha256,
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
        "schema_version": MODEL_PARAMETER_RESOURCE_SCHEMA_VERSION,
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
