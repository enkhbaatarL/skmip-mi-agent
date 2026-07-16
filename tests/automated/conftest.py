from __future__ import annotations

from collections.abc import Iterator

import pytest

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
from apps.common.configs.config import CONFIG_FILE_PATH, get_settings


@pytest.fixture(autouse=True)
def packaged_model_parameter_resource_runtime(request: pytest.FixtureRequest) -> Iterator[None]:
    """Lifespan 밖에서 node를 직접 호출하는 기존 단위 테스트용 runtime."""
    if "model_parameter" not in request.path.name:
        yield
        return

    manifest = load_model_parameter_resource_manifest(
        get_settings().model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
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
