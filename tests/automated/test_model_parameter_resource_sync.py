from __future__ import annotations

# ruff: noqa: ASYNC240, S101, S106
import asyncio
from datetime import UTC, datetime
import hashlib
from io import BytesIO
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, patch

from botocore.response import StreamingBody
from botocore.session import get_session
from botocore.stub import Stubber
from pydantic import SecretStr
import pytest
import yaml

from apps.agents.model_parameter_agent.utils.lut import LutLoadPolicy
from apps.agents.model_parameter_agent.utils.resource_bootstrap import (
    ObjectStorageReader,
    ensure_model_parameter_resource_runtime,
    resolve_model_parameter_resources,
)
from apps.agents.model_parameter_agent.utils.resource_manifest import (
    DEFAULT_RESOURCE_MANIFEST_PATH,
    RemoteResourceConfigError,
    load_model_parameter_resource_manifest,
    resource_config_fingerprint,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    clear_model_parameter_resource_runtime,
    get_model_parameter_resource_paths,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.connectors.object_storage import DownloadedObject, ObjectMetadata, S3ObjectStorageClient


def _manifest_document() -> dict[str, object]:
    document = yaml.safe_load(DEFAULT_RESOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _write_manifest_with_object_paths(path: Path, *, prefix: str) -> None:
    document = _manifest_document()
    basecase = document["basecase"]
    assert isinstance(basecase, dict)
    for role, raw_file in basecase.items():
        assert isinstance(raw_file, dict)
        raw_file["object_storage_path"] = f"{prefix}/remote-{role}.binary"
    lut = document["lut"]
    assert isinstance(lut, dict)
    for parameter_name, raw_spec in lut.items():
        assert isinstance(raw_spec, dict)
        files = raw_spec["files"]
        assert isinstance(files, dict)
        for role, raw_file in files.items():
            assert isinstance(raw_file, dict)
            raw_file["object_storage_path"] = f"{prefix}/remote-{parameter_name}-{role}.data"
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _storage_config(tmp_path: Path, manifest_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        endpoint_url="http://mip-minio:9000",
        region_name="us-east-1",
        signature_version="s3v4",
        bucket="model-parameter-test",
        access_key_id=SecretStr("minio-test-access"),
        secret_access_key=SecretStr("minio-test-secret"),
        manifest_path=str(manifest_path),
        local_root=str(tmp_path / "runtime"),
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        max_attempts=2,
        bootstrap_timeout_seconds=30,
        lock_timeout_seconds=5,
        download_chunk_size_bytes=64 * 1024,
    )


def test_integrated_manifest_declares_expected_resources() -> None:
    integrated = load_model_parameter_resource_manifest()
    assert set(integrated.basecase_files) == {"demand", "supply", "trade"}
    assert set(integrated.lut_registry.specs) == {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "LiqUtilAdjustment",
    }


def test_object_location_changes_only_resource_config_fingerprint(tmp_path: Path) -> None:
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    _write_manifest_with_object_paths(first_path, prefix="first")
    _write_manifest_with_object_paths(second_path, prefix="second")
    first = load_model_parameter_resource_manifest(first_path)
    second = load_model_parameter_resource_manifest(second_path)
    first_fingerprint, first_plan = resource_config_fingerprint(
        first,
        endpoint_url="https://example.invalid",
        region_name="region",
        signature_version="s3v4",
        default_bucket="bucket",
        lut_enabled=True,
    )
    second_fingerprint, second_plan = resource_config_fingerprint(
        second,
        endpoint_url="https://example.invalid",
        region_name="region",
        signature_version="s3v4",
        default_bucket="bucket",
        lut_enabled=True,
    )
    assert first.semantic_schema_hash == second.semantic_schema_hash
    assert first_fingerprint != second_fingerprint
    assert {item.relative_path for item in first_plan} == {item.relative_path for item in second_plan}


def test_missing_object_storage_path_is_remote_fallback_error(tmp_path: Path) -> None:
    document = _manifest_document()
    basecase = document["basecase"]
    assert isinstance(basecase, dict)
    demand = basecase["demand"]
    assert isinstance(demand, dict)
    demand["object_storage_path"] = ""
    manifest_path = tmp_path / "missing-object-key.yaml"
    manifest_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    manifest = load_model_parameter_resource_manifest(manifest_path)
    with pytest.raises(RemoteResourceConfigError):
        manifest.download_plan(default_bucket="bucket", lut_enabled=False)


def test_manifest_rejects_local_path_traversal(tmp_path: Path) -> None:
    document = _manifest_document()
    basecase = document["basecase"]
    assert isinstance(basecase, dict)
    demand = basecase["demand"]
    assert isinstance(demand, dict)
    demand["path"] = "../escaped.xlsm"
    manifest_path = tmp_path / "invalid.yaml"
    manifest_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    with pytest.raises(MIBaseError, match="escapes the resource directory"):
        load_model_parameter_resource_manifest(manifest_path)


def test_storage_disabled_requires_no_network_or_writable_runtime(tmp_path: Path) -> None:
    local_root = tmp_path / "must-not-be-created"
    storage = SimpleNamespace(
        enabled=False,
        manifest_path=str(DEFAULT_RESOURCE_MANIFEST_PATH),
        local_root=str(local_root),
    )

    async def exercise() -> None:
        paths = await resolve_model_parameter_resources(
            storage,
            lut_enabled=True,
            lut_policy=LutLoadPolicy(),
            client_factory=lambda _: pytest.fail("network client must not be created"),
        )
        assert paths.source == "packaged"
        assert paths.basecase_dir.is_dir()
        assert paths.lut_root.is_dir()

    asyncio.run(exercise())
    assert not local_root.exists()


def test_storage_disabled_runtime_uses_packaged_without_local_root(tmp_path: Path) -> None:
    local_root = tmp_path / "must-not-be-created"
    storage = SimpleNamespace(
        enabled=False,
        manifest_path=str(DEFAULT_RESOURCE_MANIFEST_PATH),
        local_root=str(local_root),
    )
    clear_model_parameter_resource_runtime()

    async def exercise() -> None:
        paths = await ensure_model_parameter_resource_runtime(
            storage,
            lut_enabled=True,
            lut_policy=LutLoadPolicy(),
            client_factory=lambda _: pytest.fail("network client must not be created"),
        )
        assert paths.source == "packaged"
        assert get_model_parameter_resource_paths() == paths

    try:
        asyncio.run(exercise())
    finally:
        clear_model_parameter_resource_runtime()
    assert not local_root.exists()


def test_s3_connector_uses_exact_head_and_streaming_get(tmp_path: Path) -> None:
    body_bytes = b"remote-content"
    last_modified = datetime(2026, 7, 15, tzinfo=UTC)
    client = get_session().create_client(
        "s3",
        endpoint_url="http://127.0.0.1:9000",
        region_name="us-east-1",
        aws_access_key_id="test-access",
        aws_secret_access_key="test-secret",
    )
    stubber = Stubber(client)
    response_metadata = {
        "ETag": '"etag"',
        "ContentLength": len(body_bytes),
        "LastModified": last_modified,
    }
    stubber.add_response(
        "head_object",
        response_metadata,
        {"Bucket": "bucket", "Key": "vendor/remote-name"},
    )
    stubber.add_response(
        "get_object",
        {
            **response_metadata,
            "Body": StreamingBody(BytesIO(body_bytes), len(body_bytes)),
        },
        {"Bucket": "bucket", "Key": "vendor/remote-name"},
    )
    connector = S3ObjectStorageClient(
        endpoint_url="http://127.0.0.1:9000",
        region_name="us-east-1",
        signature_version="s3v4",
        access_key_id="unused",
        secret_access_key="unused",
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        client=client,
    )

    async def exercise() -> None:
        metadata = await connector.head_object(
            bucket="bucket",
            object_key="vendor/remote-name",
            logical_name="basecase.demand",
        )
        downloaded = await connector.download_object(
            bucket="bucket",
            object_key="vendor/remote-name",
            logical_name="basecase.demand",
            destination=tmp_path / "local-name.xlsm.tmp",
            chunk_size_bytes=4,
            deadline=9999999999.0,
        )
        assert metadata == downloaded.metadata
        assert downloaded.sha256 == hashlib.sha256(body_bytes).hexdigest()
        assert downloaded.path.read_bytes() == body_bytes
        await connector.close()

    with stubber:
        asyncio.run(exercise())
        stubber.assert_no_pending_responses()


def test_s3_connector_normalizes_error_without_object_key_or_secret() -> None:
    client = get_session().create_client(
        "s3",
        endpoint_url="http://127.0.0.1:9000",
        region_name="us-east-1",
        aws_access_key_id="test-access",
        aws_secret_access_key="test-secret",
    )
    stubber = Stubber(client)
    stubber.add_client_error(
        "head_object",
        service_error_code="AccessDenied",
        service_message="secret-value-must-not-escape",
        http_status_code=403,
        expected_params={"Bucket": "bucket", "Key": "private/object-key"},
    )
    connector = S3ObjectStorageClient(
        endpoint_url="http://127.0.0.1:9000",
        region_name="us-east-1",
        signature_version="s3v4",
        access_key_id="unused",
        secret_access_key="unused",
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        client=client,
    )

    async def exercise() -> None:
        with pytest.raises(MIBaseError) as error:
            await connector.head_object(
                bucket="bucket",
                object_key="private/object-key",
                logical_name="basecase.demand",
            )
        rendered = str(error.value)
        assert "private/object-key" not in rendered
        assert "secret-value-must-not-escape" not in rendered
        await connector.close()

    with stubber:
        asyncio.run(exercise())


class _FakeObjectStorageClient(ObjectStorageReader):
    def __init__(self, objects: dict[tuple[str, str], bytes], *, fail: bool = False) -> None:
        self.objects = MappingProxyType(objects)
        self.fail = fail
        self.head_calls: list[tuple[str, str]] = []
        self.download_calls: list[tuple[str, str]] = []
        self.closed = False

    def _metadata(self, content: bytes) -> ObjectMetadata:
        return ObjectMetadata(
            etag=hashlib.md5(content, usedforsecurity=False).hexdigest(),
            content_length=len(content),
            last_modified="2026-07-15T00:00:00+00:00",
        )

    async def head_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
    ) -> ObjectMetadata:
        del logical_name
        self.head_calls.append((bucket, object_key))
        if self.fail:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail="fake remote failure",
            )
        return self._metadata(self.objects[(bucket, object_key)])

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
        del logical_name, chunk_size_bytes, deadline
        self.download_calls.append((bucket, object_key))
        content = self.objects[(bucket, object_key)]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return DownloadedObject(
            path=destination,
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            metadata=self._metadata(content),
        )

    async def close(self) -> None:
        self.closed = True


def _basecase_objects(manifest_path: Path, *, bucket: str) -> dict[tuple[str, str], bytes]:
    manifest = load_model_parameter_resource_manifest(manifest_path)
    plan = manifest.download_plan(default_bucket=bucket, lut_enabled=False)
    return {(item.location.bucket, item.location.object_key): f"content-{item.logical_name}".encode() for item in plan}


def test_remote_bootstrap_activates_current_and_reuses_it(tmp_path: Path) -> None:
    manifest_path = tmp_path / "resources.yaml"
    _write_manifest_with_object_paths(manifest_path, prefix="vendor")
    storage = _storage_config(tmp_path, manifest_path)
    first_client = _FakeObjectStorageClient(
        _basecase_objects(manifest_path, bucket=storage.bucket),
    )

    clear_model_parameter_resource_runtime()

    async def exercise() -> None:
        with patch(
            "apps.agents.model_parameter_agent.utils.resource_bootstrap._validate_resource_set",
            new=AsyncMock(),
        ):
            first = await resolve_model_parameter_resources(
                storage,
                lut_enabled=False,
                lut_policy=LutLoadPolicy(),
                client_factory=lambda _: first_client,
            )
            second_client = _FakeObjectStorageClient({}, fail=True)
            second = await ensure_model_parameter_resource_runtime(
                storage,
                lut_enabled=False,
                lut_policy=LutLoadPolicy(),
                client_factory=lambda _: second_client,
            )
        assert first.source == "object_storage"
        assert second.root == first.root
        assert get_model_parameter_resource_paths() == second
        assert second_client.head_calls == []
        assert (Path(storage.local_root) / "current").is_symlink()
        assert sorted(path.name for path in first.basecase_dir.iterdir()) == [
            "Demand Model_Input.xlsm",
            "Supply Model_Input.xlsm",
            "Trade Model_Input.xlsm",
        ]

    try:
        asyncio.run(exercise())
    finally:
        clear_model_parameter_resource_runtime()


def test_remote_failure_activates_packaged_wrapper(tmp_path: Path) -> None:
    manifest_path = tmp_path / "resources.yaml"
    _write_manifest_with_object_paths(manifest_path, prefix="vendor")
    storage = _storage_config(tmp_path, manifest_path)
    client = _FakeObjectStorageClient({}, fail=True)

    async def exercise() -> None:
        with patch(
            "apps.agents.model_parameter_agent.utils.resource_bootstrap._validate_resource_set",
            new=AsyncMock(),
        ):
            paths = await resolve_model_parameter_resources(
                storage,
                lut_enabled=False,
                lut_policy=LutLoadPolicy(),
                client_factory=lambda _: client,
            )
        assert paths.source == "packaged"
        assert paths.fallback_reason is not None
        assert (paths.root / "basecase").is_symlink()
        assert paths.basecase_dir.name == "basecase"

    asyncio.run(exercise())
