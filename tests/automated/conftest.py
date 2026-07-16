from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path

import pytest
import yaml

from apps.agents.model_parameter_agent.utils.resource_manifest import (
    PACKAGE_BASECASE_DIR,
    PACKAGE_LUT_ROOT,
    load_model_parameter_resource_manifest,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    ModelParameterResourcePaths,
    clear_model_parameter_resource_runtime,
    register_model_parameter_resource_paths,
)
from apps.common.utils.yaml_utils import normalize_yaml_text


DEFAULT_CONFIG_FILE = Path(__file__).resolve().parents[2] / "envs" / "config.yaml"


def _load_model_parameter_resources() -> tuple[Path, dict[str, object]]:
    config_path = (
        Path(
            os.getenv("APP_CONFIG", str(DEFAULT_CONFIG_FILE)),
        )
        .expanduser()
        .resolve()
    )
    raw_document = yaml.safe_load(
        normalize_yaml_text(config_path.read_text(encoding="utf-8")),
    )
    if not isinstance(raw_document, dict):
        msg = f"APP_CONFIG must contain a YAML mapping: {config_path}"
        raise TypeError(msg)
    resources = raw_document.get("model_parameter_resources")
    if not isinstance(resources, dict):
        msg = f"APP_CONFIG model_parameter_resources must be a mapping: {config_path}"
        raise TypeError(msg)
    return config_path, resources


@pytest.fixture(autouse=True)
def packaged_model_parameter_resource_runtime(request: pytest.FixtureRequest) -> Iterator[None]:
    """Lifespan 밖에서 node를 직접 호출하는 기존 단위 테스트용 runtime."""
    if "model_parameter" not in request.path.name:
        yield
        return

    config_path, resource_document = _load_model_parameter_resources()
    manifest = load_model_parameter_resource_manifest(
        resource_document,
        source_path=config_path,
    )
    clear_model_parameter_resource_runtime()
    register_model_parameter_resource_paths(
        ModelParameterResourcePaths(
            source="packaged",
            root=PACKAGE_BASECASE_DIR.parent,
            basecase_dir=PACKAGE_BASECASE_DIR,
            lut_root=PACKAGE_LUT_ROOT,
            resource_config_path=manifest.source_path,
            lut_registry=manifest.lut_registry,
            semantic_schema_hash=manifest.semantic_schema_hash,
        ),
    )
    try:
        yield
    finally:
        clear_model_parameter_resource_runtime()
