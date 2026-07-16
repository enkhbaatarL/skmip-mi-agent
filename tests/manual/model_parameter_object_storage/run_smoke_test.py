from __future__ import annotations

# ruff: noqa: S101, S106, S107
import asyncio
from pathlib import Path
import sys
import tempfile

from pydantic import SecretStr


ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from apps.agents.model_parameter_agent.utils.lut import LutLoadPolicy  # noqa: E402
from apps.agents.model_parameter_agent.utils.resource_bootstrap import (  # noqa: E402
    resolve_model_parameter_resources,
)
from apps.agents.model_parameter_agent.utils.resource_manifest import (  # noqa: E402
    load_model_parameter_resource_manifest,
)
from apps.common.configs.config import (  # noqa: E402
    CONFIG_FILE_PATH,
    ModelParameterResourceStorageConfig,
    get_settings,
)


SETTINGS = get_settings()
RESOURCE_MANIFEST = load_model_parameter_resource_manifest(
    SETTINGS.model_parameter_resources,
    source_path=CONFIG_FILE_PATH,
)


def _storage(
    local_root: Path,
    *,
    secret: str = "minio-test-secret",
) -> ModelParameterResourceStorageConfig:
    return SETTINGS.model_parameter_resource_storage.model_copy(
        update={
            "secret_access_key": SecretStr(secret),
            "local_root": str(local_root),
            "connect_timeout_seconds": 2,
            "read_timeout_seconds": 10,
            "max_attempts": 1,
            "bootstrap_timeout_seconds": 120,
            "lock_timeout_seconds": 10,
        },
    )


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="model-parameter-minio-") as tmpdir:
        root = Path(tmpdir)
        active = await resolve_model_parameter_resources(
            _storage(root / "success"),
            manifest=RESOURCE_MANIFEST,
            lut_enabled=True,
            lut_policy=LutLoadPolicy(),
        )
        reused = await resolve_model_parameter_resources(
            _storage(root / "success"),
            manifest=RESOURCE_MANIFEST,
            lut_enabled=True,
            lut_policy=LutLoadPolicy(),
        )
        fallback = await resolve_model_parameter_resources(
            _storage(root / "fallback", secret="wrong-secret"),
            manifest=RESOURCE_MANIFEST,
            lut_enabled=True,
            lut_policy=LutLoadPolicy(),
        )

        assert active.source == "object_storage"
        assert active.root == reused.root
        assert fallback.source == "packaged"
        assert fallback.fallback_reason
        assert (root / "success" / "current").resolve() == active.root
        assert (root / "fallback" / "current").resolve() == fallback.root


if __name__ == "__main__":
    asyncio.run(main())
