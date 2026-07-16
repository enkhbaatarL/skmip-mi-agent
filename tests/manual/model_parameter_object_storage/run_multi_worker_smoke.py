from __future__ import annotations

# ruff: noqa: S101
import asyncio
from multiprocessing import get_context
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from typing import Any

from pydantic import SecretStr


ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from apps.agents.model_parameter_agent.utils.lut import ReferenceLoadPolicy  # noqa: E402
from apps.agents.model_parameter_agent.utils.resource_bootstrap import (  # noqa: E402
    resolve_model_parameter_resources,
)
from apps.connectors.object_storage import S3ObjectStorageClient  # noqa: E402


MANIFEST_PATH = Path(__file__).with_name("model_parameter_resources.yaml")


def _storage(local_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        endpoint_url="http://127.0.0.1:19000",
        region_name="us-east-1",
        signature_version="s3v4",
        bucket="sk-mi-d-osb-ss-skgas",
        access_key_id=SecretStr("minio-test-access"),
        secret_access_key=SecretStr("minio-test-secret"),
        manifest_path=str(MANIFEST_PATH),
        local_root=str(local_root),
        connect_timeout_seconds=2,
        read_timeout_seconds=10,
        max_attempts=1,
        bootstrap_timeout_seconds=120,
        lock_timeout_seconds=180,
        download_chunk_size_bytes=1024 * 1024,
    )


def _client_factory(storage: SimpleNamespace, marker_path: Path) -> S3ObjectStorageClient:
    with marker_path.open("a", encoding="utf-8") as marker:
        marker.write("remote-bootstrap\n")
    return S3ObjectStorageClient(
        endpoint_url=storage.endpoint_url,
        region_name=storage.region_name,
        signature_version=storage.signature_version,
        access_key_id=storage.access_key_id.get_secret_value(),
        secret_access_key=storage.secret_access_key.get_secret_value(),
        connect_timeout_seconds=storage.connect_timeout_seconds,
        read_timeout_seconds=storage.read_timeout_seconds,
    )


def _worker(local_root: str, marker_path: str, result_queue: Any) -> None:  # noqa: ANN401
    storage = _storage(Path(local_root))

    async def run() -> None:
        paths = await resolve_model_parameter_resources(
            storage,
            lut_enabled=True,
            lut_policy=ReferenceLoadPolicy(),
            client_factory=lambda config: _client_factory(config, Path(marker_path)),
        )
        result_queue.put((paths.source, str(paths.root), paths.resource_fingerprint))

    asyncio.run(run())


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="model-parameter-minio-workers-") as tmpdir:
        root = Path(tmpdir)
        marker_path = root / "remote-bootstrap-count.txt"
        context = get_context("spawn")
        result_queue = context.Queue()
        workers = [
            context.Process(
                target=_worker,
                args=(str(root / "runtime"), str(marker_path), result_queue),
            )
            for _ in range(3)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=240)
            assert worker.exitcode == 0, f"worker failed: exitcode={worker.exitcode}"

        results = [result_queue.get(timeout=5) for _ in workers]
        assert {result[0] for result in results} == {"object_storage"}
        assert len({result[1] for result in results}) == 1
        assert len({result[2] for result in results}) == 1
        assert marker_path.read_text(encoding="utf-8").splitlines() == ["remote-bootstrap"]


if __name__ == "__main__":
    main()
