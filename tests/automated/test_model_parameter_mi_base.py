# Copyright (c) 2026 SK Innovation E&S.

# ruff: noqa: ASYNC240, S101, S106, SLF001

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from apps.agents.model_parameter_agent.flows.propose_parameters import flow
from apps.agents.model_parameter_agent.utils import mi_base_resources
from apps.agents.model_parameter_agent.utils.mi_base_resources import (
    resolve_mi_base_resources,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    ModelParameterResourcePaths,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    PACKAGE_RESOURCE_DIR,
    load_workbook_contract,
)
from apps.common.configs.config import (
    ModelParameterMiBaseFallbackConfig,
    ModelParameterResourceStorageConfig,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.connectors.object_storage import DownloadedObject, ObjectMetadata
from apps.persistence.mi_base.repository import MiBaseRepository
from apps.persistence.mi_base.schema import MiBaseFilePayload, MiBaseSnapshot
from apps.persistence.mi_base.service import MiBaseService
from apps.persistence.model_parameter.repository import ModelParameterRepository


def _file(
    *,
    file_no: int,
    relation_code: str,
    destination_no: int,
    name: str | None,
    path: str | None,
    size: int | None = None,
) -> MiBaseFilePayload:
    return MiBaseFilePayload(
        file_no=file_no,
        org_file_nm=name,
        strg_file_nm=f"stored-{file_no}.xlsm",
        strg_path_nm=path,
        file_size=size,
        filex_nm="xlsm",
        mime_type_nm="application/vnd.ms-excel.sheet.macroEnabled.12",
        file_rel_obj_spt_cd=relation_code,
        file_rel_obj_dstg_no=destination_no,
    )


def test_active_mi_base_selection_allows_zero_or_one_and_rejects_multiple() -> None:
    empty_repository = SimpleNamespace(fetch_active_candidates=list)
    one_repository = SimpleNamespace(
        fetch_active_candidates=lambda: [{"case_id": 15, "last_run_id": "run-15"}],
    )
    duplicate_repository = SimpleNamespace(
        fetch_active_candidates=lambda: [
            {"case_id": 16, "last_run_id": "run-16"},
            {"case_id": 15, "last_run_id": "run-15"},
        ],
    )

    assert MiBaseService._load_active_case_id(empty_repository) is None
    assert MiBaseService._load_active_case_id(one_repository) == 15
    with pytest.raises(MIBaseError, match="Multiple active MI Base"):
        MiBaseService._load_active_case_id(duplicate_repository)


def test_mi_base_snapshot_uses_last_run_id_and_run_seq_for_linked_files() -> None:
    repository = Mock()
    repository.fetch_by_case_id.return_value = {
        "case_id": 15,
        "last_run_id": "20260727_103605_7740",
    }
    repository.fetch_run_seq.return_value = 71
    repository.fetch_linked_files.return_value = []

    snapshot = MiBaseService._load_snapshot(repository, case_id=15)

    assert snapshot.case_id == 15
    assert snapshot.run_seq == 71
    repository.fetch_run_seq.assert_called_once_with("20260727_103605_7740")
    repository.fetch_linked_files.assert_called_once_with(case_id=15, run_seq=71)


def test_linked_file_query_uses_case_id_and_latest_run_seq() -> None:
    class EmptyRows:
        def mappings(self) -> EmptyRows:
            return self

        @staticmethod
        def all() -> list[object]:
            return []

    class FakeSession:
        def __init__(self) -> None:
            self.statement = ""
            self.parameters: dict[str, int | None] = {}

        def execute(
            self,
            statement: object,
            parameters: dict[str, int | None],
        ) -> EmptyRows:
            self.statement = str(statement)
            self.parameters = parameters
            return EmptyRows()

    session = FakeSession()
    files = MiBaseRepository(session=session).fetch_linked_files(
        case_id=15,
        run_seq=71,
    )

    assert files == []
    assert session.parameters == {"case_id": 15, "run_seq": 71}
    assert "file_rel_obj_spt_cd = 'SCNRCASE'" in session.statement
    assert "file_rel_obj_dstg_no = :case_id" in session.statement
    assert "'SCNRCASEH', 'SCNRCASEHI', 'SCNRCASEHTF'" in session.statement
    assert "file_rel_obj_dstg_no = :run_seq" in session.statement


class _FakeStorageClient:
    def __init__(self, objects: dict[tuple[str, str], bytes]) -> None:
        self.objects = objects
        self.head_calls: list[tuple[str, str]] = []
        self.download_calls: list[tuple[str, str]] = []
        self.closed = False

    @staticmethod
    def _metadata(content: bytes) -> ObjectMetadata:
        return ObjectMetadata(
            etag=hashlib.md5(content, usedforsecurity=False).hexdigest(),
            content_length=len(content),
            last_modified="2026-10-06T00:00:00+00:00",
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


class _UnavailableStorageClient:
    def __init__(self) -> None:
        self.download_calls: list[tuple[str, str]] = []
        self.closed = False

    async def head_object(
        self,
        *,
        bucket: str,
        object_key: str,
        logical_name: str,
    ) -> ObjectMetadata:
        del bucket, object_key, logical_name
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail="Object Storage unavailable",
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
        del logical_name, destination, chunk_size_bytes, deadline
        self.download_calls.append((bucket, object_key))
        message = "download must not be attempted"
        raise AssertionError(message)

    async def close(self) -> None:
        self.closed = True


class _DownloadUnavailableStorageClient(_FakeStorageClient):
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
        del logical_name, destination, chunk_size_bytes, deadline
        self.download_calls.append((bucket, object_key))
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail="Object Storage download unavailable",
        )


def _settings(
    storage: ModelParameterResourceStorageConfig,
    *,
    no_active_case_mode: str = "fail",
    active_case_unavailable_mode: str = "verified_cache",
) -> SimpleNamespace:
    return SimpleNamespace(
        model_parameter_resource_storage=storage,
        model_parameter_mi_base_fallback=ModelParameterMiBaseFallbackConfig(
            no_active_case_mode=no_active_case_mode,
            active_case_unavailable_mode=active_case_unavailable_mode,
        ),
    )


def _configured_resource_paths() -> ModelParameterResourcePaths:
    return ModelParameterResourcePaths(
        source="packaged",
        root=PACKAGE_RESOURCE_DIR,
        basecase_dir=PACKAGE_RESOURCE_DIR / "basecase",
        lut_root=PACKAGE_RESOURCE_DIR / "lut",
        resource_config_path=PACKAGE_RESOURCE_DIR / "model-parameter-resources.yaml",
        lut_registry=Mock(),
        semantic_schema_hash="test",
        workbook_contract=load_workbook_contract(),
    )


def _complete_snapshot(
    *,
    bucket: str,
    objects: dict[tuple[str, str], bytes],
    case_id: int = 15,
    run_seq: int = 71,
) -> MiBaseSnapshot:
    files = [
        _file(
            file_no=index,
            relation_code="SCNRCASE",
            destination_no=case_id,
            name=f"(Base) {role.title()} Model_Input.xlsm",
            path=f"https://storage.example/{bucket}/SCNRCASE/{role}.xlsm",
            size=len(objects[(bucket, f"SCNRCASE/{role}.xlsm")]),
        )
        for index, role in enumerate(("demand", "supply", "trade"), start=1)
    ]
    return MiBaseSnapshot(
        case_id=case_id,
        last_run_id=f"run-{run_seq}",
        run_seq=run_seq,
        files=files,
    )


def _storage_config(
    tmp_path: Path,
    *,
    bucket: str = "mi-bucket",
    enabled: bool = True,
) -> ModelParameterResourceStorageConfig:
    return ModelParameterResourceStorageConfig(
        enabled=enabled,
        endpoint_url="https://storage.example",
        bucket=bucket,
        access_key_id="test-access",
        secret_access_key="test-secret",
        local_root=str(tmp_path),
        max_attempts=1,
    )


def test_scnrcase_workbooks_are_classified_by_role_token_only() -> None:
    snapshot = MiBaseSnapshot(
        case_id=219,
        files=[
            _file(
                file_no=1,
                relation_code="SCNRCASE",
                destination_no=219,
                name="복호화_Trade_v11_플랫폼입력_최종_v8_플랫폼전달.xlsm",
                path="https://storage.example/mi-bucket/SCNRCASE/trade.xlsm",
            ),
            _file(
                file_no=2,
                relation_code="SCNRCASE",
                destination_no=219,
                name="Demand_v5_플랫폼입력_최종_v8_플랫폼전달.xlsm",
                path="https://storage.example/mi-bucket/SCNRCASE/demand.xlsm",
            ),
            _file(
                file_no=3,
                relation_code="SCNRCASE",
                destination_no=219,
                name="Output_v3_플랫폼입력_최종_v8_플랫폼전달.xlsm",
                path="https://storage.example/mi-bucket/SCNRCASE/output.xlsm",
            ),
            _file(
                file_no=4,
                relation_code="SCNRCASE",
                destination_no=219,
                name="Supply_v14_플랫폼입력_최종_v6_플랫폼전달.xlsm",
                path="https://storage.example/mi-bucket/SCNRCASE/supply.xlsm",
            ),
            _file(
                file_no=5,
                relation_code="SCNRCASE",
                destination_no=219,
                name="result_trade.csv",
                path="https://storage.example/mi-bucket/SCNRCASE/result_trade.csv",
            ),
        ],
    )

    selected = mi_base_resources._classify_inputs(snapshot, bucket="mi-bucket")

    assert [(item.role, item.file.file_no) for item in selected] == [
        ("demand", 2),
        ("supply", 4),
        ("trade", 1),
    ]


def test_scnrcase_workbook_role_tokens_must_be_unambiguous() -> None:
    snapshot = MiBaseSnapshot(
        case_id=219,
        files=[
            _file(
                file_no=1,
                relation_code="SCNRCASE",
                destination_no=219,
                name="Demand_Supply_v1_플랫폼입력.xlsm",
                path="https://storage.example/mi-bucket/SCNRCASE/ambiguous.xlsm",
            ),
        ],
    )

    with pytest.raises(
        mi_base_resources.MiBaseResourceFallbackError,
        match="Ambiguous SCNRCASE workbook role",
    ):
        mi_base_resources._classify_inputs(snapshot, bucket="mi-bucket")


def test_only_scnrcase_workbooks_are_downloaded_for_calculation(
    tmp_path: Path,
) -> None:
    bucket = "mi-bucket"
    objects = {
        (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
        (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
        (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
    }
    client = _FakeStorageClient(objects)
    snapshot = MiBaseSnapshot(
        case_id=15,
        last_run_id="run-15",
        run_seq=71,
        files=[
            _file(
                file_no=1,
                relation_code="SCNRCASE",
                destination_no=15,
                name="(Base) Demand Model_Input.xlsm",
                path=f"https://storage.example/{bucket}/SCNRCASE/demand.xlsm",
                size=len(objects[(bucket, "SCNRCASE/demand.xlsm")]),
            ),
            _file(
                file_no=2,
                relation_code="SCNRCASE",
                destination_no=15,
                name="(Base) Supply Model_Input.xlsm",
                path=f"https://storage.example/{bucket}/SCNRCASE/supply.xlsm",
                size=len(objects[(bucket, "SCNRCASE/supply.xlsm")]),
            ),
            _file(
                file_no=3,
                relation_code="SCNRCASE",
                destination_no=15,
                name="(Base) Trade Model_Input.xlsm",
                path=f"https://storage.example/{bucket}/SCNRCASE/trade.xlsm",
                size=len(objects[(bucket, "SCNRCASE/trade.xlsm")]),
            ),
            _file(
                file_no=4,
                relation_code="SCNRCASEH",
                destination_no=71,
                name=None,
                path=None,
            ),
        ],
    )
    contract = load_workbook_contract()
    configured_paths = ModelParameterResourcePaths(
        source="packaged",
        root=PACKAGE_RESOURCE_DIR,
        basecase_dir=PACKAGE_RESOURCE_DIR / "basecase",
        lut_root=PACKAGE_RESOURCE_DIR / "lut",
        resource_config_path=PACKAGE_RESOURCE_DIR / "model-parameter-resources.yaml",
        lut_registry=Mock(),
        semantic_schema_hash="test",
        workbook_contract=contract,
    )
    storage = ModelParameterResourceStorageConfig(
        enabled=True,
        endpoint_url="https://storage.example",
        bucket=bucket,
        access_key_id="test-access",
        secret_access_key="test-secret",
        local_root=str(tmp_path),
        max_attempts=1,
    )

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(
            mi_base_resources,
            "get_settings",
            return_value=_settings(storage),
        ),
        patch.object(mi_base_resources, "extract_workbook_references"),
    ):
        selection = asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=lambda _storage: client,
            ),
        )

    assert selection.source == "mi_base"
    assert selection.case_id == 15
    assert selection.run_seq == 71
    assert selection.linked_file_counts == {
        "SCNRCASE": 3,
        "SCNRCASEH": 1,
        "SCNRCASEHI": 0,
        "SCNRCASEHTF": 0,
    }
    assert client.download_calls == [
        (bucket, "SCNRCASE/demand.xlsm"),
        (bucket, "SCNRCASE/supply.xlsm"),
        (bucket, "SCNRCASE/trade.xlsm"),
    ]
    assert client.closed is True
    assert (selection.basecase_dir / "Demand Model_Input.xlsm").is_file()


def test_incomplete_scnrcase_workbooks_fail_without_cross_case_fallback(
    tmp_path: Path,
) -> None:
    contract = load_workbook_contract()
    configured_release_root = tmp_path / "configured-release"
    configured_release_root.mkdir()
    configured_paths = ModelParameterResourcePaths(
        source="packaged",
        root=configured_release_root,
        basecase_dir=PACKAGE_RESOURCE_DIR / "basecase",
        lut_root=PACKAGE_RESOURCE_DIR / "lut",
        resource_config_path=PACKAGE_RESOURCE_DIR / "model-parameter-resources.yaml",
        lut_registry=Mock(),
        semantic_schema_hash="test",
        workbook_contract=contract,
    )
    storage = ModelParameterResourceStorageConfig(
        enabled=True,
        endpoint_url="https://storage.example",
        bucket="mi-bucket",
        access_key_id="test-access",
        secret_access_key="test-secret",
        local_root=str(tmp_path),
        max_attempts=1,
    )
    snapshot = MiBaseSnapshot(
        case_id=15,
        files=[
            _file(
                file_no=1,
                relation_code="SCNRCASE",
                destination_no=15,
                name="(Base) Demand Model_Input.xlsm",
                path="https://storage.example/mi-bucket/SCNRCASE/demand.xlsm",
            ),
            _file(
                file_no=2,
                relation_code="SCNRCASE",
                destination_no=15,
                name="(Base) Supply Model_Input.xlsm",
                path="https://storage.example/mi-bucket/SCNRCASE/supply.xlsm",
            ),
        ],
    )
    client_factory = Mock(side_effect=AssertionError("client must not be created"))

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(
            mi_base_resources,
            "get_settings",
            return_value=_settings(storage),
        ),
        pytest.raises(MIBaseError) as error,
    ):
        asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=client_factory,
            ),
        )

    assert error.value.error_code is ErrorCode.DATA_RETRIEVAL_FAILED
    client_factory.assert_not_called()


def test_no_active_mi_base_fails_closed_by_default(tmp_path: Path) -> None:
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(
            mi_base_resources,
            "get_settings",
            return_value=_settings(storage),
        ),
        pytest.raises(MIBaseError) as error,
    ):
        asyncio.run(resolve_mi_base_resources(None))

    assert error.value.error_code is ErrorCode.DATA_RETRIEVAL_FAILED


def test_no_active_mi_base_uses_configured_fallback_only_when_enabled(
    tmp_path: Path,
) -> None:
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(
            mi_base_resources,
            "get_settings",
            return_value=_settings(storage, no_active_case_mode="configured_fallback"),
        ),
    ):
        selection = asyncio.run(resolve_mi_base_resources(None))

    assert selection.source == "configured_fallback"
    assert selection.case_id is None
    assert selection.basecase_dir == configured_paths.basecase_dir
    assert selection.workbook_resource_root == PACKAGE_RESOURCE_DIR


def test_object_storage_outage_uses_only_verified_same_file_cache(
    tmp_path: Path,
) -> None:
    bucket = "mi-bucket"
    objects = {
        (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
        (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
        (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
    }
    snapshot = _complete_snapshot(bucket=bucket, objects=objects)
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path, bucket=bucket)
    settings = _settings(storage)
    initial_client = _FakeStorageClient(objects)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(mi_base_resources, "get_settings", return_value=settings),
        patch.object(mi_base_resources, "extract_workbook_references"),
    ):
        initial = asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=lambda _storage: initial_client,
            ),
        )
        unavailable_client = _UnavailableStorageClient()
        cached = asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=lambda _storage: unavailable_client,
            ),
        )

    assert initial.source == "mi_base"
    assert cached.source == "verified_cache"
    assert cached.case_id == snapshot.case_id
    assert cached.run_seq == snapshot.run_seq
    assert cached.workbook_resource_root == initial.workbook_resource_root
    assert cached.fallback_reason is not None
    assert unavailable_client.download_calls == []
    assert unavailable_client.closed is True


def test_object_storage_outage_uses_configured_fallback_only_when_explicitly_enabled(
    tmp_path: Path,
) -> None:
    bucket = "mi-bucket"
    snapshot = _complete_snapshot(
        bucket=bucket,
        objects={
            (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
            (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
            (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
        },
    )
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path, bucket=bucket)
    unavailable_client = _UnavailableStorageClient()

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(
            mi_base_resources,
            "get_settings",
            return_value=_settings(
                storage,
                active_case_unavailable_mode="configured_fallback",
            ),
        ),
    ):
        selection = asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=lambda _storage: unavailable_client,
            ),
        )

    assert selection.source == "configured_fallback"
    assert selection.case_id == snapshot.case_id
    assert selection.run_seq == snapshot.run_seq
    assert selection.basecase_dir == configured_paths.basecase_dir
    assert selection.workbook_resource_root == PACKAGE_RESOURCE_DIR
    assert selection.fallback_reason is not None
    assert unavailable_client.download_calls == []
    assert unavailable_client.closed is True


def test_verified_cache_rejects_corrupted_workbook(tmp_path: Path) -> None:
    bucket = "mi-bucket"
    objects = {
        (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
        (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
        (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
    }
    snapshot = _complete_snapshot(bucket=bucket, objects=objects)
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path, bucket=bucket)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(mi_base_resources, "get_settings", return_value=_settings(storage)),
        patch.object(mi_base_resources, "extract_workbook_references"),
    ):
        initial = asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=lambda _storage: _FakeStorageClient(objects),
            ),
        )
        (initial.basecase_dir / "Demand Model_Input.xlsm").write_bytes(b"corrupted")
        with pytest.raises(MIBaseError) as error:
            asyncio.run(
                resolve_mi_base_resources(
                    snapshot,
                    client_factory=lambda _storage: _UnavailableStorageClient(),
                ),
            )

    assert error.value.error_code is ErrorCode.DATA_RETRIEVAL_FAILED


def test_verified_cache_is_not_used_after_current_remote_identity_is_observed(
    tmp_path: Path,
) -> None:
    bucket = "mi-bucket"
    cached_objects = {
        (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
        (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
        (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
    }
    current_objects = {key: value.replace(b"current", b"currenT") for key, value in cached_objects.items()}
    snapshot = _complete_snapshot(bucket=bucket, objects=cached_objects)
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path, bucket=bucket)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(mi_base_resources, "get_settings", return_value=_settings(storage)),
        patch.object(mi_base_resources, "extract_workbook_references"),
    ):
        asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=lambda _storage: _FakeStorageClient(cached_objects),
            ),
        )
        current_client = _DownloadUnavailableStorageClient(current_objects)
        with pytest.raises(MIBaseError) as error:
            asyncio.run(
                resolve_mi_base_resources(
                    snapshot,
                    client_factory=lambda _storage: current_client,
                ),
            )

    assert error.value.error_code is ErrorCode.DATA_RETRIEVAL_FAILED
    assert current_client.download_calls == [(bucket, "SCNRCASE/demand.xlsm")]


def test_configured_fallback_is_not_used_after_current_remote_identity_is_observed(
    tmp_path: Path,
) -> None:
    bucket = "mi-bucket"
    objects = {
        (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
        (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
        (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
    }
    snapshot = _complete_snapshot(bucket=bucket, objects=objects)
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path, bucket=bucket)
    client = _DownloadUnavailableStorageClient(objects)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(
            mi_base_resources,
            "get_settings",
            return_value=_settings(
                storage,
                active_case_unavailable_mode="configured_fallback",
            ),
        ),
        pytest.raises(MIBaseError) as error,
    ):
        asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=lambda _storage: client,
            ),
        )

    assert error.value.error_code is ErrorCode.DATA_RETRIEVAL_FAILED
    assert client.download_calls == [(bucket, "SCNRCASE/demand.xlsm")]


def test_verified_cache_rejects_different_run_identity(tmp_path: Path) -> None:
    bucket = "mi-bucket"
    objects = {
        (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
        (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
        (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
    }
    cached_snapshot = _complete_snapshot(bucket=bucket, objects=objects, run_seq=71)
    current_snapshot = _complete_snapshot(bucket=bucket, objects=objects, run_seq=72)
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path, bucket=bucket)
    settings = _settings(storage)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(mi_base_resources, "get_settings", return_value=settings),
        patch.object(mi_base_resources, "extract_workbook_references"),
    ):
        asyncio.run(
            resolve_mi_base_resources(
                cached_snapshot,
                client_factory=lambda _storage: _FakeStorageClient(objects),
            ),
        )
        with pytest.raises(MIBaseError) as error:
            asyncio.run(
                resolve_mi_base_resources(
                    current_snapshot,
                    client_factory=lambda _storage: _UnavailableStorageClient(),
                ),
            )

    assert error.value.error_code is ErrorCode.DATA_RETRIEVAL_FAILED


def test_verified_cache_can_be_disabled_by_policy(tmp_path: Path) -> None:
    bucket = "mi-bucket"
    objects = {
        (bucket, "SCNRCASE/demand.xlsm"): b"demand-current-base",
        (bucket, "SCNRCASE/supply.xlsm"): b"supply-current-base",
        (bucket, "SCNRCASE/trade.xlsm"): b"trade-current-base",
    }
    snapshot = _complete_snapshot(bucket=bucket, objects=objects)
    configured_paths = _configured_resource_paths()
    storage = _storage_config(tmp_path, bucket=bucket)

    with (
        patch.object(
            mi_base_resources,
            "get_model_parameter_resource_paths",
            return_value=configured_paths,
        ),
        patch.object(mi_base_resources, "extract_workbook_references"),
    ):
        with patch.object(
            mi_base_resources,
            "get_settings",
            return_value=_settings(storage),
        ):
            asyncio.run(
                resolve_mi_base_resources(
                    snapshot,
                    client_factory=lambda _storage: _FakeStorageClient(objects),
                ),
            )
        with (
            patch.object(
                mi_base_resources,
                "get_settings",
                return_value=_settings(storage, active_case_unavailable_mode="fail"),
            ),
            pytest.raises(MIBaseError) as error,
        ):
            asyncio.run(
                resolve_mi_base_resources(
                    snapshot,
                    client_factory=lambda _storage: _UnavailableStorageClient(),
                ),
            )

    assert error.value.error_code is ErrorCode.DATA_RETRIEVAL_FAILED


def test_async_admission_pins_active_mi_base_case_id() -> None:
    class FakeService:
        saved_context: dict[str, object] | None = None

        @staticmethod
        def load_context(scenario_id: int) -> dict[str, object]:
            return {
                "scenario": {
                    "scenario_id": scenario_id,
                    "scenario_group_id": 20,
                },
                "scenario_group": {
                    "scenario_group_id": 20,
                    "generation_strategy": "multi_event_model_lever_dimensions",
                },
            }

        @staticmethod
        def load_active_mi_base_case_id() -> int:
            return 15

        def create_processing_proposal(
            self,
            *,
            scenario_context: dict[str, object],
            user_id: int | None,
        ) -> int:
            del user_id
            self.saved_context = scenario_context
            return 901

    service = FakeService()
    with patch.object(flow, "ModelParameterService", return_value=service):
        result = flow.prepare_propose_parameters_callback(100, user_id=40)

    assert result["model_param_proposal_id"] == 901
    assert service.saved_context is not None
    assert service.saved_context["mi_base_case_id"] == 15


def test_repository_persists_selected_mi_base_case_id() -> None:
    class FakeSession:
        added = None

        def add(self, value: object) -> None:
            self.added = value

        def flush(self) -> None:
            self.added.model_param_proposal_id = 901

    session = FakeSession()
    proposal_id = ModelParameterRepository(
        session=session,
    ).create_processing_model_param_proposal(
        scenario_id=100,
        scenario_group_id=20,
        mi_event_id=30,
        mi_base_case_id=15,
        request_usr_id=40,
    )

    assert proposal_id == 901
    assert session.added.mi_base_case_id == 15
