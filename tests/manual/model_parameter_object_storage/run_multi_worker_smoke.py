from __future__ import annotations

# ruff: noqa: S101
import asyncio
from multiprocessing import get_context
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from apps.agents.model_parameter_agent.utils.lut import ReferenceLoadPolicy  # noqa: E402
from apps.agents.model_parameter_agent.utils.resource_bootstrap import (  # noqa: E402
    ObjectStorageReader,
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
from apps.connectors.object_storage import (  # noqa: E402
    DownloadedObject,
    ObjectMetadata,
    S3ObjectStorageClient,
)


SETTINGS = get_settings()
RESOURCE_MANIFEST = load_model_parameter_resource_manifest(
    SETTINGS.model_parameter_resources,
    source_path=CONFIG_FILE_PATH,
)


def _storage(local_root: Path) -> ModelParameterResourceStorageConfig:
    return SETTINGS.model_parameter_resource_storage.model_copy(
        update={
            "local_root": str(local_root),
            "connect_timeout_seconds": 2,
            "read_timeout_seconds": 10,
            "max_attempts": 1,
            "bootstrap_timeout_seconds": 120,
            "lock_timeout_seconds": 180,
        },
    )


class _CountingObjectStorageClient(ObjectStorageReader):
    def __init__(self, delegate: S3ObjectStorageClient, marker_path: Path) -> None:
        self._delegate = delegate
        self._marker_path = marker_path

    async def head_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
    ) -> ObjectMetadata:
        return await self._delegate.head_object(
            bucket=bucket,
            object_key=object_key,
            logical_name=logical_name,
        )

    async def download_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
        destination: Path,
        chunk_size_bytes: int,
        deadline: float,
    ) -> DownloadedObject:
        with self._marker_path.open("a", encoding="utf-8") as marker:
            marker.write(f"download:{logical_name}\n")
        return await self._delegate.download_object(
            bucket=bucket,
            object_key=object_key,
            logical_name=logical_name,
            destination=destination,
            chunk_size_bytes=chunk_size_bytes,
            deadline=deadline,
        )

    async def close(self) -> None:
        await self._delegate.close()


def _client_factory(storage: Any, marker_path: Path) -> ObjectStorageReader:
    with marker_path.open("a", encoding="utf-8") as marker:
        marker.write("client-created\n")
    return _CountingObjectStorageClient(
        S3ObjectStorageClient(
            endpoint_url=storage.endpoint_url,
            region_name=storage.region_name,
            signature_version=storage.signature_version,
            access_key_id=storage.access_key_id.get_secret_value(),
            secret_access_key=storage.secret_access_key.get_secret_value(),
            connect_timeout_seconds=storage.connect_timeout_seconds,
            read_timeout_seconds=storage.read_timeout_seconds,
        ),
        marker_path,
    )


def _worker(local_root: str, marker_path: str, result_queue: Any) -> None:  # noqa: ANN401
    storage = _storage(Path(local_root))

    async def run() -> None:
        paths = await resolve_model_parameter_resources(
            storage,
            manifest=RESOURCE_MANIFEST,
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
        marker_lines = marker_path.read_text(encoding="utf-8").splitlines()
        assert marker_lines.count("client-created") == 1
        download_markers = [line.removeprefix("download:") for line in marker_lines if line.startswith("download:")]
        assert sorted(download_markers) == sorted(
            resource.logical_name
            for resource in RESOURCE_MANIFEST.selected_files(lut_enabled=True)
        )


if __name__ == "__main__":
    main()
