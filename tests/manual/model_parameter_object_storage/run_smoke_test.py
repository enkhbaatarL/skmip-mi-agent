from __future__ import annotations

# ruff: noqa: S101, S106, S107
import asyncio
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

from pydantic import SecretStr


ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from apps.agents.model_parameter_agent.utils.lut import ReferenceLoadPolicy  # noqa: E402
from apps.agents.model_parameter_agent.utils.resource_bootstrap import (  # noqa: E402
    resolve_model_parameter_resources,
)


MANIFEST_PATH = Path(__file__).with_name("model_parameter_resources.yaml")


def _storage(local_root: Path, *, secret: str = "minio-test-secret") -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        endpoint_url="http://127.0.0.1:19000",
        region_name="us-east-1",
        signature_version="s3v4",
        bucket="sk-mi-d-osb-ss-skgas",
        access_key_id=SecretStr("minio-test-access"),
        secret_access_key=SecretStr(secret),
        manifest_path=str(MANIFEST_PATH),
        local_root=str(local_root),
        connect_timeout_seconds=2,
        read_timeout_seconds=10,
        max_attempts=1,
        bootstrap_timeout_seconds=120,
        lock_timeout_seconds=10,
        download_chunk_size_bytes=1024 * 1024,
    )


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="model-parameter-minio-") as tmpdir:
        root = Path(tmpdir)
        active = await resolve_model_parameter_resources(
            _storage(root / "success"),
            lut_enabled=True,
            lut_policy=ReferenceLoadPolicy(),
        )
        reused = await resolve_model_parameter_resources(
            _storage(root / "success"),
            lut_enabled=True,
            lut_policy=ReferenceLoadPolicy(),
        )
        fallback = await resolve_model_parameter_resources(
            _storage(root / "fallback", secret="wrong-secret"),
            lut_enabled=True,
            lut_policy=ReferenceLoadPolicy(),
        )

        assert active.source == "object_storage"
        assert active.root == reused.root
        assert fallback.source == "packaged"
        assert fallback.fallback_reason
        assert (root / "success" / "current").resolve() == active.root
        assert (root / "fallback" / "current").resolve() == fallback.root


if __name__ == "__main__":
    asyncio.run(main())
