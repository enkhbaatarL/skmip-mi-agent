from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from threading import RLock

from apps.agents.model_parameter_agent.utils.lut.adapters import (
    ADAPTER_SCHEMA_VERSION,
    FileSnapshot,
)
from apps.agents.model_parameter_agent.utils.lut.catalog import LutCatalog, build_lut_catalog
from apps.agents.model_parameter_agent.utils.lut.models import LutLoadPolicy, domain_error
from apps.agents.model_parameter_agent.utils.lut.registry import (
    DEFAULT_LUT_CONFIG_PATH,
    DEFAULT_LUT_ROOT,
    ParameterSpecRegistry,
    load_parameter_spec_registry,
)


@dataclass(frozen=True, slots=True)
class _SnapshotEntry:
    signature: tuple[int, int]
    snapshot: FileSnapshot


_RUNTIME_LOCK = RLock()
_SNAPSHOT_CACHE: dict[Path, _SnapshotEntry] = {}
_REGISTRY_CACHE: dict[tuple[Path, Path, str], ParameterSpecRegistry] = {}
_CATALOG_CACHE: dict[
    tuple[Path, Path, str, int, int, tuple[tuple[str, str], ...]],
    LutCatalog,
] = {}


def _read_snapshot(path: Path) -> FileSnapshot:
    resolved = path.resolve()
    try:
        stat = resolved.stat()
    except OSError as exc:
        msg = f"required LUT file is not accessible: {resolved}: {exc}"
        raise domain_error(msg) from exc
    signature = (stat.st_mtime_ns, stat.st_size)
    cached = _SNAPSHOT_CACHE.get(resolved)
    if cached is not None and cached.signature == signature:
        return cached.snapshot
    try:
        content = resolved.read_bytes()
    except OSError as exc:
        msg = f"failed to read required LUT file: {resolved}: {exc}"
        raise domain_error(msg) from exc
    snapshot = FileSnapshot(
        path=str(resolved),
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )
    _SNAPSHOT_CACHE[resolved] = _SnapshotEntry(signature=signature, snapshot=snapshot)
    return snapshot


def get_parameter_spec_registry(
    config_path: Path | str = DEFAULT_LUT_CONFIG_PATH,
    *,
    lut_root: Path | str | None = None,
) -> ParameterSpecRegistry:
    config = Path(config_path).expanduser().resolve()
    root = (
        Path(lut_root).expanduser().resolve()
        if lut_root is not None
        else (DEFAULT_LUT_ROOT if config == DEFAULT_LUT_CONFIG_PATH.resolve() else config.parent.parent).resolve()
    )
    with _RUNTIME_LOCK:
        yaml_snapshot = _read_snapshot(config)
        cache_key = (config, root, yaml_snapshot.sha256)
        cached = _REGISTRY_CACHE.get(cache_key)
        if cached is not None:
            return cached
        registry = load_parameter_spec_registry(
            config,
            lut_root=root,
            yaml_bytes=yaml_snapshot.content,
        )
        _REGISTRY_CACHE[cache_key] = registry
        return registry


def _catalog_version(
    registry: ParameterSpecRegistry,
    policy: LutLoadPolicy,
    snapshots: dict[str, FileSnapshot],
) -> str:
    digest = hashlib.sha256()
    digest.update(ADAPTER_SCHEMA_VERSION.encode("utf-8"))
    digest.update(registry.canonical_yaml)
    digest.update(
        json.dumps(
            {"start_year": policy.start_year, "end_year": policy.end_year},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    )
    for relative_path, snapshot in sorted(snapshots.items()):
        digest.update(relative_path.encode("utf-8"))
        digest.update(snapshot.sha256.encode("ascii"))
    return digest.hexdigest()


def get_lut_catalog(
    policy: LutLoadPolicy,
    *,
    registry: ParameterSpecRegistry | None = None,
    config_path: Path | str = DEFAULT_LUT_CONFIG_PATH,
    lut_root: Path | str | None = None,
) -> LutCatalog:
    with _RUNTIME_LOCK:
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
        file_identity = tuple((relative_path, snapshot.sha256) for relative_path, snapshot in sorted(snapshots.items()))
        cache_key = (
            active_registry.config_path,
            active_registry.lut_root,
            active_registry.schema_hash,
            policy.start_year,
            policy.end_year,
            file_identity,
        )
        cached = _CATALOG_CACHE.get(cache_key)
        if cached is not None:
            return cached
        catalog = build_lut_catalog(
            active_registry,
            policy,
            snapshots,
            version=_catalog_version(active_registry, policy, snapshots),
        )
        _CATALOG_CACHE[cache_key] = catalog
        return catalog


def validate_lut_startup(
    enabled: bool,  # noqa: FBT001
    policy: LutLoadPolicy,
    *,
    config_path: Path | str = DEFAULT_LUT_CONFIG_PATH,
    lut_root: Path | str | None = None,
) -> tuple[ParameterSpecRegistry, LutCatalog | None]:
    registry = get_parameter_spec_registry(config_path, lut_root=lut_root)
    if not enabled:
        return registry, None
    return registry, get_lut_catalog(policy, registry=registry)


def clear_lut_runtime_cache() -> None:
    with _RUNTIME_LOCK:
        _CATALOG_CACHE.clear()
        _REGISTRY_CACHE.clear()
        _SNAPSHOT_CACHE.clear()
