# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: S101, S105, S106
import asyncio
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, patch

from botocore.response import StreamingBody
from botocore.session import get_session
from botocore.stub import Stubber
from pydantic import SecretStr
import pytest
import yaml

from apps.agents.model_parameter_agent.utils.lut import (
    ReferenceLoadPolicy,
    get_parameter_spec_registry,
)
from apps.agents.model_parameter_agent.utils.resource_bootstrap import (
    ObjectStorageReader,
    ensure_model_parameter_resource_runtime,
    resolve_model_parameter_resources,
)
from apps.agents.model_parameter_agent.utils.resource_manifest import (
    ModelParameterResourceManifest,
    RemoteResourceConfigError,
    load_model_parameter_resource_manifest,
    resource_config_fingerprint,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    clear_model_parameter_resource_runtime,
    get_model_parameter_resource_paths,
)
from apps.common.configs.config import CONFIG_FILE_PATH, get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.connectors.object_storage import DownloadedObject, ObjectMetadata, S3ObjectStorageClient
from model_param import _config_debug_json


ENABLED_LUT_PARAMETERS = {
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "Population",
    "HurricaneIntensity",
    "LiqProdAdjustment",
    "LiqUtilAdjustment",
    "PipelineAdjustment",
    "SupplyDisruption",
}
DISABLED_LUT_PARAMETERS = {"Coal Futures Price", "Gas Futures Price"}
STAGING_RESOURCE_PATH = "apps/agents/model_parameter_agent/new_resources/"


def _manifest_document() -> dict[str, object]:
    document = deepcopy(get_settings().model_parameter_resources)
    assert isinstance(document, dict)
    return document


def _manifest_with_object_paths(*, prefix: str) -> ModelParameterResourceManifest:
    document = _manifest_document()
    basecase = document["basecase"]
    assert isinstance(basecase, dict)
    for role, raw_file in basecase.items():
        assert isinstance(raw_file, dict)
        raw_file["object_storage_path"] = f"{prefix}/remote-{role}.binary"
    lut = document["lut"]
    assert isinstance(lut, dict)
    for raw_spec in lut.values():
        assert isinstance(raw_spec, dict)
        files = raw_spec["files"]
        assert isinstance(files, dict)
        for raw_file in files.values():
            assert isinstance(raw_file, dict)
            raw_file["object_storage_path"] = f"{prefix}/{raw_file['path']}"
    references = document["references"]
    assert isinstance(references, dict)
    for raw_file in references.values():
        assert isinstance(raw_file, dict)
        raw_file["object_storage_path"] = f"{prefix}/{raw_file['path']}"
    return load_model_parameter_resource_manifest(
        document,
        source_path=CONFIG_FILE_PATH,
    )


def _storage_config(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        endpoint_url="http://mip-minio:9000",
        region_name="us-east-1",
        signature_version="s3v4",
        bucket="model-parameter-test",
        access_key_id=SecretStr("minio-test-access"),
        secret_access_key=SecretStr("minio-test-secret"),
        local_root=str(tmp_path / "runtime"),
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        max_attempts=2,
        bootstrap_timeout_seconds=30,
        lock_timeout_seconds=5,
        download_chunk_size_bytes=64 * 1024,
    )


def test_integrated_manifest_declares_expected_resources() -> None:
    integrated = load_model_parameter_resource_manifest(
        get_settings().model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )
    assert integrated.schema_version == 7
    assert integrated.workbook_contract.release_id == "new-bc-v7"
    assert integrated.workbook_contract.public_api_unchanged is True
    assert integrated.workbook_contract_path.name == "model-parameter-workbook-contract-v7.json"
    assert len(integrated.workbook_contract_schema_hash) == 64
    assert integrated.proposal_capability_contract.release_id == "extend16-v7"
    assert {item.model_param_id for item in integrated.proposal_capability_contract.parameters} == {
        4,
        6,
        7,
        8,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        20,
        22,
        23,
        24,
    }
    assert len(integrated.proposal_capability_contract_sha256) == 64
    assert len(integrated.semantic_schema_hash) == 64
    assert set(integrated.basecase_files) == {"demand", "supply", "trade"}
    assert {role: resource.object_storage_path for role, resource in integrated.basecase_files.items()} == {
        "demand": "fundamental_model_artifact/input_template/복호화_(Base) Demand Model_Input.xlsm",
        "supply": "fundamental_model_artifact/input_template/복호화_(Base) Supply Model_Input.xlsm",
        "trade": "fundamental_model_artifact/input_template/복호화_(Base) Trade Model_Input.xlsm",
    }
    assert set(integrated.lut_registry.specs) == ENABLED_LUT_PARAMETERS | DISABLED_LUT_PARAMETERS
    assert set(integrated.lut_registry.enabled_specs) == ENABLED_LUT_PARAMETERS
    assert {
        parameter_name for parameter_name, spec in integrated.lut_registry.specs.items() if not spec.enabled
    } == DISABLED_LUT_PARAMETERS
    assert set(integrated.lut_registry.references) == {"demand_general_country_list"}


def test_k8s_single_config_file_uses_same_resource_mapping() -> None:
    configmap_path = CONFIG_FILE_PATH.parents[1] / "devops" / "k8s" / "configmap.yaml"
    configmap = yaml.safe_load(configmap_path.read_text(encoding="utf-8"))
    embedded_config = yaml.safe_load(configmap["data"]["config.yaml"])

    assert embedded_config["model_parameter_resources"] == get_settings().model_parameter_resources
    for setting_name in (
        "model_parameter_max_total_selected_slots",
        "model_parameter_max_step2_prompt_bytes",
        "model_parameter_max_step3_prompt_bytes",
    ):
        assert embedded_config[setting_name] == getattr(get_settings(), setting_name)


@pytest.mark.parametrize("dockerfile_name", ["Dockerfile", "Dockerfile.model_param"])
def test_docker_build_context_excludes_incoming_staging(dockerfile_name: str) -> None:
    repository_root = CONFIG_FILE_PATH.parents[1]
    dockerfile_specific_ignore = repository_root / f"{dockerfile_name}.dockerignore"
    effective_ignore = (
        dockerfile_specific_ignore if dockerfile_specific_ignore.is_file() else repository_root / ".dockerignore"
    )
    patterns = {
        line.strip()
        for line in effective_ignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert STAGING_RESOURCE_PATH in patterns


def test_every_packaged_lut_csv_has_exactly_one_active_pending_or_reference_class() -> None:
    integrated = load_model_parameter_resource_manifest(
        get_settings().model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )
    active_paths = {
        file_spec.relative_path
        for parameter_name in ENABLED_LUT_PARAMETERS
        for file_spec in integrated.lut_registry.specs[parameter_name].files.values()
    }
    pending_paths = {
        file_spec.relative_path
        for parameter_name in DISABLED_LUT_PARAMETERS
        for file_spec in integrated.lut_registry.specs[parameter_name].files.values()
    }
    reference_paths = {file_spec.relative_path for file_spec in integrated.lut_registry.references.values()}
    packaged_paths = {path.name for path in integrated.lut_registry.lut_root.glob("*.csv") if path.is_file()}

    assert active_paths.isdisjoint(pending_paths)
    assert active_paths.isdisjoint(reference_paths)
    assert pending_paths.isdisjoint(reference_paths)
    assert active_paths | pending_paths | reference_paths == packaged_paths
    assert len(packaged_paths) == 14

    selected_targets = {
        resource_file.relative_path
        for resource_file in integrated.selected_files(lut_enabled=True)
        if resource_file.area == "lut"
    }
    assert selected_targets == packaged_paths


def test_debug_config_snapshot_includes_all_settings_and_redacts_secrets() -> None:
    cfg = get_settings()
    payload = json.loads(_config_debug_json(cfg, source_path=CONFIG_FILE_PATH))

    assert payload["source_path"] == str(CONFIG_FILE_PATH)
    assert payload["settings"]["METADATA_DB_HOST"] == cfg.METADATA_DB_HOST
    assert payload["settings"]["METADATA_DB_PASSWORD"] == "**********"
    assert payload["settings"]["model_api_key"] == "**********"
    assert payload["settings"]["callback_oauth2_token_url"] == cfg.callback_oauth2_token_url
    assert payload["settings"]["model_parameter_resource_storage"]["access_key_id"] == "**********"
    assert payload["settings"]["model_parameter_resource_storage"]["secret_access_key"] == "**********"
    assert payload["settings"]["model_parameter_resources"] == cfg.model_parameter_resources


def test_resource_config_rejects_operator_managed_schema_version() -> None:
    document = _manifest_document()
    document["schema_version"] = 1

    with pytest.raises(MIBaseError, match="unknown fields"):
        load_model_parameter_resource_manifest(
            document,
            source_path=CONFIG_FILE_PATH,
        )


def test_object_location_changes_only_resource_config_fingerprint() -> None:
    first = _manifest_with_object_paths(prefix="first")
    second = _manifest_with_object_paths(prefix="second")
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


def test_missing_object_storage_path_is_remote_fallback_error() -> None:
    document = _manifest_document()
    basecase = document["basecase"]
    assert isinstance(basecase, dict)
    demand = basecase["demand"]
    assert isinstance(demand, dict)
    demand["object_storage_path"] = ""
    manifest = load_model_parameter_resource_manifest(
        document,
        source_path=CONFIG_FILE_PATH,
    )
    with pytest.raises(RemoteResourceConfigError):
        manifest.download_plan(default_bucket="bucket", lut_enabled=False)


def test_manifest_rejects_local_path_traversal() -> None:
    document = _manifest_document()
    basecase = document["basecase"]
    assert isinstance(basecase, dict)
    demand = basecase["demand"]
    assert isinstance(demand, dict)
    demand["path"] = "../escaped.xlsm"
    with pytest.raises(MIBaseError, match="escapes the resource directory"):
        load_model_parameter_resource_manifest(
            document,
            source_path=CONFIG_FILE_PATH,
        )


def test_storage_disabled_requires_no_network_or_writable_runtime(tmp_path: Path) -> None:
    local_root = tmp_path / "must-not-be-created"
    storage = SimpleNamespace(
        enabled=False,
        local_root=str(local_root),
    )
    manifest = load_model_parameter_resource_manifest(
        get_settings().model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )

    async def exercise() -> None:
        paths = await resolve_model_parameter_resources(
            storage,
            manifest=manifest,
            lut_enabled=True,
            lut_policy=ReferenceLoadPolicy(),
            client_factory=lambda _: pytest.fail("network client must not be created"),
        )
        assert paths.source == "packaged"
        assert paths.basecase_dir.is_dir()
        assert paths.lut_root.is_dir()
        assert paths.workbook_contract == manifest.workbook_contract
        assert paths.workbook_contract_path == manifest.workbook_contract_path

    asyncio.run(exercise())
    assert not local_root.exists()


def test_resource_startup_rejects_horizon_outside_workbook_contract(
    tmp_path: Path,
) -> None:
    storage = SimpleNamespace(
        enabled=False,
        local_root=str(tmp_path / "must-not-be-created"),
    )
    manifest = load_model_parameter_resource_manifest(
        get_settings().model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )

    async def exercise() -> None:
        with pytest.raises(
            MIBaseError,
            match="LUT horizon must match the active versioned workbook contract",
        ):
            await resolve_model_parameter_resources(
                storage,
                manifest=manifest,
                lut_enabled=True,
                lut_policy=ReferenceLoadPolicy(start_year=2027, end_year=2030),
            )

    asyncio.run(exercise())


def test_storage_disabled_runtime_uses_packaged_without_local_root(tmp_path: Path) -> None:
    local_root = tmp_path / "must-not-be-created"
    storage = SimpleNamespace(
        enabled=False,
        local_root=str(local_root),
    )
    manifest = load_model_parameter_resource_manifest(
        get_settings().model_parameter_resources,
        source_path=CONFIG_FILE_PATH,
    )
    clear_model_parameter_resource_runtime()

    async def exercise() -> None:
        paths = await ensure_model_parameter_resource_runtime(
            storage,
            manifest=manifest,
            lut_enabled=True,
            lut_policy=ReferenceLoadPolicy(),
            client_factory=lambda _: pytest.fail("network client must not be created"),
        )
        assert paths.source == "packaged"
        assert get_model_parameter_resource_paths() == paths
        with patch.object(Path, "read_bytes", side_effect=AssertionError("config must not be reread")):
            assert get_parameter_spec_registry() is paths.lut_registry

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
        destination.write_bytes(content)  # noqa: ASYNC240
        return DownloadedObject(
            path=destination,
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            metadata=self._metadata(content),
        )

    async def close(self) -> None:
        self.closed = True


def _basecase_objects(
    manifest: ModelParameterResourceManifest,
    *,
    bucket: str,
) -> dict[tuple[str, str], bytes]:
    plan = manifest.download_plan(default_bucket=bucket, lut_enabled=False)
    return {(item.location.bucket, item.location.object_key): f"content-{item.logical_name}".encode() for item in plan}


def test_remote_bootstrap_activates_current_and_reuses_it(tmp_path: Path) -> None:
    manifest = _manifest_with_object_paths(prefix="vendor")
    storage = _storage_config(tmp_path)
    first_client = _FakeObjectStorageClient(
        _basecase_objects(manifest, bucket=storage.bucket),
    )

    clear_model_parameter_resource_runtime()

    async def exercise() -> None:
        with patch(
            "apps.agents.model_parameter_agent.utils.resource_bootstrap._validate_resource_set",
            new=AsyncMock(),
        ):
            first = await resolve_model_parameter_resources(
                storage,
                manifest=manifest,
                lut_enabled=False,
                lut_policy=ReferenceLoadPolicy(),
                client_factory=lambda _: first_client,
            )
            second_client = _FakeObjectStorageClient({}, fail=True)
            second = await ensure_model_parameter_resource_runtime(
                storage,
                manifest=manifest,
                lut_enabled=False,
                lut_policy=ReferenceLoadPolicy(),
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
    manifest = _manifest_with_object_paths(prefix="vendor")
    storage = _storage_config(tmp_path)
    client = _FakeObjectStorageClient({}, fail=True)

    async def exercise() -> None:
        with patch(
            "apps.agents.model_parameter_agent.utils.resource_bootstrap._validate_resource_set",
            new=AsyncMock(),
        ):
            paths = await resolve_model_parameter_resources(
                storage,
                manifest=manifest,
                lut_enabled=False,
                lut_policy=ReferenceLoadPolicy(),
                client_factory=lambda _: client,
            )
        assert paths.source == "packaged"
        assert paths.fallback_reason is not None
        assert (paths.root / "basecase").is_symlink()
        assert paths.basecase_dir.name == "basecase"

    asyncio.run(exercise())
