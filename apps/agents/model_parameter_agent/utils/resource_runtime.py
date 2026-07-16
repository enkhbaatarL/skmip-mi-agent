from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Literal

from apps.agents.model_parameter_agent.utils.lut.registry import ParameterSpecRegistry
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


@dataclass(frozen=True, slots=True)
class ModelParameterResourcePaths:
    source: Literal["object_storage", "packaged"]
    root: Path
    basecase_dir: Path
    lut_root: Path
    resource_config_path: Path
    lut_registry: ParameterSpecRegistry
    semantic_schema_hash: str
    resource_config_fingerprint: str | None = None
    resource_fingerprint: str | None = None
    fallback_reason: str | None = None


_RUNTIME_LOCK = threading.Lock()
_ACTIVE_RESOURCE_PATHS: ModelParameterResourcePaths | None = None


def get_registered_model_parameter_resource_paths() -> ModelParameterResourcePaths | None:
    """현재 process에 고정된 리소스 경로를 반환하고 미등록이면 None을 반환한다."""
    with _RUNTIME_LOCK:
        return _ACTIVE_RESOURCE_PATHS


def register_model_parameter_resource_paths(paths: ModelParameterResourcePaths) -> None:
    """기동 중 확정한 실제 경로를 process-local runtime에 한 번 등록한다."""
    global _ACTIVE_RESOURCE_PATHS

    resolved = ModelParameterResourcePaths(
        source=paths.source,
        root=paths.root.resolve(strict=True),
        basecase_dir=paths.basecase_dir.resolve(strict=True),
        lut_root=paths.lut_root.resolve(strict=True),
        resource_config_path=paths.resource_config_path.resolve(strict=True),
        lut_registry=paths.lut_registry,
        semantic_schema_hash=paths.semantic_schema_hash,
        resource_config_fingerprint=paths.resource_config_fingerprint,
        resource_fingerprint=paths.resource_fingerprint,
        fallback_reason=paths.fallback_reason,
    )
    with _RUNTIME_LOCK:
        if _ACTIVE_RESOURCE_PATHS is not None and resolved != _ACTIVE_RESOURCE_PATHS:
            raise MIBaseError(
                ErrorCode.RUNTIME_REGISTRY_NOT_READY,
                detail="model parameter resource runtime is already registered",
            )
        _ACTIVE_RESOURCE_PATHS = resolved


def get_model_parameter_resource_paths() -> ModelParameterResourcePaths:
    paths = get_registered_model_parameter_resource_paths()
    if paths is None:
        raise MIBaseError(
            ErrorCode.RUNTIME_REGISTRY_NOT_READY,
            detail="model parameter resource runtime has not been registered",
        )
    return paths


def clear_model_parameter_resource_runtime() -> None:
    """테스트와 lifespan 종료 시 process-local 등록을 비운다."""
    global _ACTIVE_RESOURCE_PATHS

    with _RUNTIME_LOCK:
        _ACTIVE_RESOURCE_PATHS = None
