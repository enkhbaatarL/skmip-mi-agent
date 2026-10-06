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
from apps.common.configs.config import ModelParameterResourceStorageConfig
from apps.common.exceptions.custom import MIBaseError
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
            return_value=SimpleNamespace(model_parameter_resource_storage=storage),
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


def test_incomplete_scnrcase_workbooks_use_configured_fallback(
    tmp_path: Path,
) -> None:
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
            return_value=SimpleNamespace(model_parameter_resource_storage=storage),
        ),
    ):
        selection = asyncio.run(
            resolve_mi_base_resources(
                snapshot,
                client_factory=client_factory,
            ),
        )

    assert selection.source == "configured_fallback"
    assert selection.case_id == 15
    assert selection.basecase_dir == configured_paths.basecase_dir
    client_factory.assert_not_called()


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
