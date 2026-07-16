from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.agents.model_parameter_agent.utils.lut.adapters import (
    ADAPTER_SCHEMA_VERSION,
    FileSnapshot,
)
from apps.agents.model_parameter_agent.utils.lut.catalog import LutCatalog, build_lut_catalog
from apps.agents.model_parameter_agent.utils.lut.models import ReferenceLoadPolicy, domain_error
from apps.agents.model_parameter_agent.utils.lut.registry import (
    DEFAULT_LUT_CONFIG_PATH,
    DEFAULT_LUT_ROOT,
    ParameterSpecRegistry,
    load_parameter_spec_registry,
)
from apps.agents.model_parameter_agent.utils.runtime_cache import (
    RuntimeLruCache,
    file_mtime_size_signature,
)


_SNAPSHOT_CACHE: RuntimeLruCache[FileSnapshot] = RuntimeLruCache(max_entries=64)
_REGISTRY_CACHE: RuntimeLruCache[ParameterSpecRegistry] = RuntimeLruCache(max_entries=16)
_CATALOG_CACHE: RuntimeLruCache[LutCatalog] = RuntimeLruCache(max_entries=16)


def _read_snapshot(path: Path) -> FileSnapshot:
    resolved = path.resolve()
    try:
        signature = file_mtime_size_signature(resolved)
    except OSError as exc:
        msg = f"required LUT file is not accessible: {resolved}: {exc}"
        raise domain_error(msg) from exc

    def build() -> FileSnapshot:
        try:
            content = resolved.read_bytes()
        except OSError as exc:
            msg = f"failed to read required LUT file: {resolved}: {exc}"
            raise domain_error(msg) from exc
        return FileSnapshot(
            path=str(resolved),
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
        )

    return _SNAPSHOT_CACHE.get_or_build(
        (
            "lut-file-snapshot-v1",
            resolved,
            signature.mtime_ns,
            signature.size,
        ),
        builder=build,
    )


def get_parameter_spec_registry(
    config_path: Path | str | None = None,
    *,
    lut_root: Path | str | None = None,
) -> ParameterSpecRegistry:
    if config_path is None:
        # Model Parameter app 기동 후에는 검증된 registry를 process memory에서 재사용한다.
        from apps.agents.model_parameter_agent.utils.resource_runtime import (
            get_registered_model_parameter_resource_paths,
        )

        resource_paths = get_registered_model_parameter_resource_paths()
        if resource_paths is not None:
            return resource_paths.lut_registry
        config_path = DEFAULT_LUT_CONFIG_PATH

    config = Path(config_path).expanduser().resolve()
    root = (
        Path(lut_root).expanduser().resolve()
        if lut_root is not None
        else (DEFAULT_LUT_ROOT if config == DEFAULT_LUT_CONFIG_PATH.resolve() else config.parent.parent).resolve()
    )
    yaml_snapshot = _read_snapshot(config)

    def build() -> ParameterSpecRegistry:
        registry = load_parameter_spec_registry(
            config,
            lut_root=root,
            yaml_bytes=yaml_snapshot.content,
        )
        return registry

    return _REGISTRY_CACHE.get_or_build(
        ("lut-registry-v1", config, root, yaml_snapshot.sha256),
        builder=build,
    )


def _catalog_version(
    registry: ParameterSpecRegistry,
    policy: ReferenceLoadPolicy,
    snapshots: dict[str, FileSnapshot],
) -> str:
    digest = hashlib.sha256()
    digest.update(ADAPTER_SCHEMA_VERSION.encode("utf-8"))
    digest.update(registry.canonical_yaml)
    digest.update(
        json.dumps(
            {
                "start_year": policy.start_year,
                "end_year": policy.end_year,
                "value_max_decimal_places": policy.value_max_decimal_places,
                "value_precision_mode": policy.value_precision_mode,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    )
    for relative_path, snapshot in sorted(snapshots.items()):
        digest.update(relative_path.encode("utf-8"))
        digest.update(snapshot.sha256.encode("ascii"))
    return digest.hexdigest()


def get_lut_catalog(
    policy: ReferenceLoadPolicy,
    *,
    registry: ParameterSpecRegistry | None = None,
    config_path: Path | str | None = None,
    lut_root: Path | str | None = None,
) -> LutCatalog:
    active_registry = registry or get_parameter_spec_registry(
        config_path,
        lut_root=lut_root,
    )
    snapshots: dict[str, FileSnapshot] = {}
    for spec in active_registry.specs.values():
        for file_spec in spec.files.values():
            snapshots.setdefault(
                file_spec.relative_path,
                _read_snapshot(file_spec.resolved_path),
            )
    file_identity = tuple(
        (relative_path, snapshot.sha256)
        for relative_path, snapshot in sorted(snapshots.items())
    )
    cache_key = (
        "lut-catalog-v2",
        active_registry.config_path,
        active_registry.lut_root,
        active_registry.schema_hash,
        policy.start_year,
        policy.end_year,
        policy.value_max_decimal_places,
        policy.value_precision_mode,
        file_identity,
    )

    def build() -> LutCatalog:
        return build_lut_catalog(
            active_registry,
            policy,
            snapshots,
            version=_catalog_version(active_registry, policy, snapshots),
        )

    return _CATALOG_CACHE.get_or_build(
        cache_key,
        builder=build,
    )


def validate_lut_startup(
    enabled: bool,  # noqa: FBT001
    policy: ReferenceLoadPolicy,
    *,
    registry: ParameterSpecRegistry | None = None,
    config_path: Path | str | None = None,
    lut_root: Path | str | None = None,
) -> tuple[ParameterSpecRegistry, LutCatalog | None]:
    active_registry = registry or get_parameter_spec_registry(config_path, lut_root=lut_root)
    if not enabled:
        return active_registry, None
    return active_registry, get_lut_catalog(policy, registry=active_registry)


def clear_lut_runtime_cache() -> None:
    _CATALOG_CACHE.clear()
    _REGISTRY_CACHE.clear()
    _SNAPSHOT_CACHE.clear()
