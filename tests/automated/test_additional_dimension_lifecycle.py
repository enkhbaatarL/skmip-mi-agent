from __future__ import annotations

# ruff: noqa: CPY001, S101
import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apps.agents.scenario_group_agent.constants import (
    ADDITIONAL_DIMENSION_API_VERSION,
    API_IDENTIFIER_ADD_DIMENSION,
)
from apps.agents.scenario_group_agent.flows.add_dimension.flow import (
    ADDITIONAL_DIMENSION_CANDIDATES_INVALID,
    _additional_dimension_attempt_span,
    _record_attempt_result,
    get_additional_dimensions,
    run_additional_dimension_generation,
)
from apps.agents.scenario_group_agent.flows.add_dimension.nodes import (
    AdditionalDimensionCandidateRejection,
    AdditionalDimensionHydrationResult,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosSyncIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation import (
    run_v4_create_operation,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4EventImpactAnalysisResult,
    V4ReadableAdditionalDimensionDesignDraft,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync import (
    create_v4_scenarios_sync,
)
from apps.agents.scenario_group_agent.runtime import AdditionalDimensionTaskRunner
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext
from apps.common.values.error_codes import ErrorCode


def _uncertainty(uncertainty_id: str) -> dict[str, Any]:
    return {
        "uncertainty_id": uncertainty_id,
        "impact_path_ids": [f"path-{uncertainty_id}"],
        "axis_type": "duration",
        "subject": f"{uncertainty_id} 질문",
        "affected_lever_code": "supply",
        "reason": f"{uncertainty_id} 질문",
        "materiality": "high",
        "semantic_key": f"path-{uncertainty_id}:duration:supply",
    }


def _group(
    *,
    api_version: str = "v4",
    status: str = "creating",
    stage: str = "scenario_created",
    diagnostics: dict[str, Any] | None = None,
    definitions: list[dict[str, Any]] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_id=10,
        api_version=api_version,
        generation_strategy="multi_event_model_lever_dimensions",
        status=status,
        stage=stage,
        generation_diagnostics=diagnostics
        or {
            "path_uncertainties": [_uncertainty("u1")],
            "interaction_uncertainties": [],
        },
        dimension_definitions=definitions or [],
        dimension_selected=[str(item.get("dimension_id") or item.get("dimensionId")) for item in (definitions or [])],
        mod_dtm=datetime(2026, 8, 19, tzinfo=UTC),
    )


def _hydration_result(
    *,
    input_count: int,
    valid_candidates: list[Any] | None = None,
    reason_code: str | None = None,
) -> AdditionalDimensionHydrationResult:
    rejected = (
        []
        if reason_code is None
        else [
            AdditionalDimensionCandidateRejection.model_validate(
                {
                    "candidate_index": 1,
                    "source_aliases": ["U1"],
                    "reason_code": reason_code,
                    "detail": "candidate validation failed",
                },
            ),
        ]
    )
    return AdditionalDimensionHydrationResult.model_construct(
        input_candidate_count=input_count,
        valid_candidates=valid_candidates or [],
        rejected_candidates=rejected,
    )


def _candidate() -> dict[str, Any]:
    return {
        "dimension_id": "ad_1",
        "label": "지속성",
        "description": "공급 확대는 얼마나 지속되는가?",
        "rationale": "공급 분기 기준",
        "source_event_ids": [101],
        "source_impact_path_ids": ["p1"],
        "source_uncertainty_ids": ["u1"],
        "primary_lever_code": "supply",
        "primary_impact_lever_id": 1,
        "dimension_type": "duration",
        "value_kind": "temporal",
        "model_support_status": "full",
        "values": [
            {
                "value_id": "ad_1_v1",
                "label": "단기",
                "assumption_rationale": "단기 종료 가정",
                "pressure_contribution": "balanced",
                "lever_states": [],
            },
        ],
    }


@contextmanager
def _service_fixture(
    group: SimpleNamespace,
) -> Iterator[tuple[Mock, Mock]]:
    session = Mock()
    repository = Mock()
    repository.fetch_by_id.return_value = group

    def update_group(target: SimpleNamespace, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            setattr(target, key, value)

    repository.update_group.side_effect = update_group
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=repository,
        ),
    ):
        yield session, repository


def test_additional_generation_lifecycle_is_idempotent_and_persists_candidates() -> None:
    group = _group()
    service = ScenarioGroupService()
    candidates = [{"dimension_id": "ad_1", "source_uncertainty_ids": ["u1"]}]

    with _service_fixture(group) as (session, repository):
        queued = service.queue_additional_dimension_generation(10, user_id=7)
        queued_again = service.queue_additional_dimension_generation(10, user_id=7)
        started = service.start_additional_dimension_generation(10, run_id="run-1")
        completed = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=queued["source_fingerprint"],
            run_id="run-1",
            candidates=candidates,
        )
        completed_again = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=queued["source_fingerprint"],
            run_id="run-1",
            candidates=[{"dimension_id": "must_not_overwrite"}],
        )

    assert queued["status"] == "queued"
    assert queued_again == queued
    assert started is not None
    assert group.generation_diagnostics["additional_dimension_generation"]["status"] == "ready"
    assert group.generation_diagnostics["additional_dimension_candidates"] == candidates
    assert completed is True
    assert completed_again is True
    assert repository.update_group.call_count == 3
    assert session.commit.call_count == 3


def test_additional_generation_without_unused_questions_is_ready_without_start() -> None:
    group = _group(
        definitions=[{"dimension_id": "d1", "source_uncertainty_ids": ["u1"]}],
    )
    service = ScenarioGroupService()

    with _service_fixture(group) as (_session, _repository):
        generation = service.queue_additional_dimension_generation(10, user_id=7)
        started = service.start_additional_dimension_generation(10, run_id="run-1")

    assert generation["status"] == "ready"
    assert generation["source_uncertainty_ids"] == []
    assert started is None
    assert group.generation_diagnostics["additional_dimension_candidates"] == []


def test_manual_requeue_requires_v4_ready_empty_candidates_and_unused_questions() -> None:
    group = _group()
    service = ScenarioGroupService()

    with _service_fixture(group) as (session, repository):
        ready = service.queue_additional_dimension_generation(10, user_id=7)
        assert service.start_additional_dimension_generation(10, run_id="run-1") is not None
        service.complete_additional_dimension_generation(
            10,
            source_fingerprint=ready["source_fingerprint"],
            run_id="run-1",
            candidates=[],
        )
        requeued = service.requeue_empty_ready_additional_dimension_generation(10)
        with pytest.raises(MIBaseError):
            service.requeue_empty_ready_additional_dimension_generation(10)

    assert requeued["status"] == "queued"
    assert requeued["source_uncertainty_ids"] == ["u1"]
    assert group.status == "creating"
    assert group.stage == "scenario_created"
    assert group.dimension_definitions == []
    assert repository.update_group.call_count == 4
    assert session.commit.call_count == 4


def test_additional_shutdown_interrupt_is_idempotent() -> None:
    group = _group()
    service = ScenarioGroupService()

    with _service_fixture(group):
        service.queue_additional_dimension_generation(10, user_id=7)
        assert service.start_additional_dimension_generation(10, run_id="run-1") is not None
        service.interrupt_additional_dimension_generation(10, run_id="run-1")
        service.interrupt_additional_dimension_generation(10, run_id="run-1")

    generation = group.generation_diagnostics["additional_dimension_generation"]
    assert generation["status"] == "interrupted"
    assert generation["error_code"] == "SERVER_SHUTDOWN"


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (lambda group: setattr(group, "stage", "scenario_validated"), "GROUP_NOT_ELIGIBLE"),
        (
            lambda group: group.generation_diagnostics["path_uncertainties"].append(
                _uncertainty("u2"),
            ),
            "SOURCE_FINGERPRINT_CHANGED",
        ),
    ],
)
def test_additional_result_is_discarded_when_locked_source_is_stale(
    mutation: Callable[[SimpleNamespace], None],
    expected_error: str,
) -> None:
    group = _group()
    service = ScenarioGroupService()

    with _service_fixture(group):
        queued = service.queue_additional_dimension_generation(10, user_id=7)
        assert service.start_additional_dimension_generation(10, run_id="run-1") is not None
        mutation(group)
        stored = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=queued["source_fingerprint"],
            run_id="run-1",
            candidates=[{"dimension_id": "ad_stale"}],
        )

    generation = group.generation_diagnostics["additional_dimension_generation"]
    assert stored is False
    assert generation["status"] == "discarded"
    assert generation["error_code"] == expected_error
    assert group.generation_diagnostics["additional_dimension_candidates"] == []


def test_additional_generation_rejects_wrong_version_and_stage() -> None:
    service = ScenarioGroupService()
    with _service_fixture(_group(api_version="v3")):
        with pytest.raises(MIBaseError) as wrong_version:
            service.queue_additional_dimension_generation(10, user_id=7)
        with pytest.raises(MIBaseError) as wrong_version_get:
            service.load_additional_dimensions(10)
    with _service_fixture(_group(stage="scenario_validated")), pytest.raises(MIBaseError) as wrong_stage:
        service.queue_additional_dimension_generation(10, user_id=7)

    assert wrong_version.value.error_code is ErrorCode.INVALID_REQUEST
    assert wrong_version.value.status_code == 400
    assert wrong_version_get.value.error_code is ErrorCode.INVALID_REQUEST
    assert wrong_version_get.value.status_code == 400
    assert wrong_stage.value.error_code is ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT
    assert wrong_stage.value.status_code == 409


def test_additional_get_is_read_only_and_hides_internal_lineage() -> None:
    candidate = {
        "dimension_id": "ad_1",
        "label": "지속성",
        "description": "공급 확대는 얼마나 지속되는가?",
        "rationale": "공급 분기 기준",
        "source_event_ids": [101],
        "source_impact_path_ids": ["p1"],
        "source_uncertainty_ids": ["u1"],
        "primary_lever_code": "supply",
        "primary_impact_lever_id": 1,
        "dimension_type": "duration",
        "value_kind": "temporal",
        "model_support_status": "full",
        "values": [
            {
                "value_id": "ad_1_v1",
                "label": "단기",
                "assumption_rationale": "단기 종료 가정",
                "pressure_contribution": "balanced",
                "lever_states": [],
            },
        ],
    }
    group = _group(
        stage="scenario_validated",
        diagnostics={
            "additional_dimension_generation": {
                "status": "ready",
                "source_fingerprint": "sha256:ready",
            },
            "additional_dimension_candidates": [candidate],
        },
    )
    service = ScenarioGroupService()

    with _service_fixture(group) as (session, repository):
        loaded = service.load_additional_dimensions(10)

    session.commit.assert_not_called()
    repository.update_group.assert_not_called()
    assert loaded["candidates"] == [candidate]

    with patch(
        "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
        return_value=loaded,
    ):
        output = get_additional_dimensions(10).model_dump(mode="json", by_alias=True)

    item = output["data"]["dimensionDefinitions"]["items"][0]
    assert item["sourceEventIds"] == [101]
    assert "sourceImpactPathIds" not in item
    assert "sourceUncertaintyIds" not in item
    assert "primaryLeverCode" not in item
    assert "primaryImpactLeverId" not in item
    assert "dimensionType" not in item
    assert "valueKind" not in item


@pytest.mark.parametrize("status", ["queued", "running"])
@pytest.mark.parametrize(
    ("age_seconds", "expected_status", "expected_definition_status", "expected_error"),
    [
        (239.999, None, "pending", None),
        (240.0, "interrupted", "unavailable", "STALE_TIMEOUT"),
        (300.0, "interrupted", "unavailable", "STALE_TIMEOUT"),
    ],
)
def test_additional_get_projects_stale_active_generation_at_configured_boundary(
    status: str,
    age_seconds: float,
    expected_status: str | None,
    expected_definition_status: str,
    expected_error: str | None,
) -> None:
    now = datetime(2026, 8, 21, 0, 10, tzinfo=UTC)
    timestamp_key = "queued_at" if status == "queued" else "started_at"
    generation = {
        "status": status,
        timestamp_key: (now - timedelta(seconds=age_seconds)).isoformat(),
    }
    payload = {
        "generation": generation,
        "candidates": [],
        "dimension_selected": [],
        "dimension_definitions": [],
        "updated_at": None,
    }
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
            return_value=payload,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._get_additional_dimension_stale_after_seconds",
            return_value=240,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._utc_now",
            return_value=now,
        ),
    ):
        output = get_additional_dimensions(10)

    assert output.status == "success"
    assert output.data is not None
    assert output.data.generation_status == (expected_status or status)
    assert output.data.dimension_definitions.status == expected_definition_status
    assert output.data.dimension_definitions.items == []
    assert output.data.error_code == expected_error
    assert generation["status"] == status


def test_additional_get_running_stale_falls_back_to_queued_at_when_started_at_is_missing() -> None:
    now = datetime(2026, 8, 21, 0, 10, tzinfo=UTC)
    payload = {
        "generation": {
            "status": "running",
            "queuedAt": (now - timedelta(seconds=240)).isoformat(),
        },
        "candidates": [],
        "dimension_selected": [],
        "dimension_definitions": [],
        "updated_at": None,
    }
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
            return_value=payload,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._get_additional_dimension_stale_after_seconds",
            return_value=240,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._utc_now",
            return_value=now,
        ),
    ):
        output = get_additional_dimensions(10)

    assert output.data is not None
    assert output.data.generation_status == "interrupted"
    assert output.data.error_code == "STALE_TIMEOUT"


@pytest.mark.parametrize(
    "generation",
    [
        {"status": "queued"},
        {"status": "queued", "queued_at": "not-a-timestamp"},
        {"status": "running"},
        {
            "status": "running",
            "started_at": "not-a-timestamp",
            "queued_at": "2020-01-01T00:00:00+00:00",
        },
    ],
)
def test_additional_get_preserves_active_status_when_timestamp_is_missing_or_invalid(
    generation: dict[str, Any],
) -> None:
    payload = {
        "generation": generation,
        "candidates": [],
        "dimension_selected": [],
        "dimension_definitions": [],
        "updated_at": None,
    }
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
            return_value=payload,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._get_additional_dimension_stale_after_seconds",
            return_value=240,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._utc_now",
            return_value=datetime(2026, 8, 21, 0, 10, tzinfo=UTC),
        ),
    ):
        output = get_additional_dimensions(10)

    assert output.data is not None
    assert output.data.generation_status == generation["status"]
    assert output.data.dimension_definitions.status == "pending"
    assert output.data.error_code is None


def test_additional_get_does_not_project_old_ready_generation_as_stale() -> None:
    payload = {
        "generation": {
            "status": "ready",
            "queued_at": "2020-01-01T00:00:00+00:00",
            "started_at": "2020-01-01T00:01:00+00:00",
        },
        "candidates": [_candidate()],
        "dimension_selected": [],
        "dimension_definitions": [],
        "updated_at": None,
    }
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
            return_value=payload,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._get_additional_dimension_stale_after_seconds",
            return_value=240,
        ),
    ):
        output = get_additional_dimensions(10)

    assert output.data is not None
    assert output.data.generation_status == "ready"
    assert output.data.dimension_definitions.status == "ready"
    assert output.data.available_count == 1
    assert output.data.dimension_definitions.items[0].dimension_id == "ad_1"


def test_stale_running_get_can_be_followed_by_same_run_completion() -> None:
    group = _group()
    service = ScenarioGroupService()
    now = datetime(2026, 8, 21, 0, 10, tzinfo=UTC)

    with (
        _service_fixture(group) as (session, repository),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._get_additional_dimension_stale_after_seconds",
            return_value=240,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._utc_now",
            return_value=now,
        ),
    ):
        queued = service.queue_additional_dimension_generation(10, user_id=7)
        assert service.start_additional_dimension_generation(10, run_id="run-slow") is not None
        generation = group.generation_diagnostics["additional_dimension_generation"]
        generation["started_at"] = (now - timedelta(seconds=240)).isoformat()
        original_generation = deepcopy(generation)
        update_count = repository.update_group.call_count
        commit_count = session.commit.call_count

        stale_output = get_additional_dimensions(10)

        assert generation == original_generation
        assert repository.update_group.call_count == update_count
        assert session.commit.call_count == commit_count
        completed = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=queued["source_fingerprint"],
            run_id="run-slow",
            candidates=[_candidate()],
        )
        ready_output = get_additional_dimensions(10)

    assert stale_output.data is not None
    assert stale_output.data.generation_status == "interrupted"
    assert stale_output.data.dimension_definitions.status == "unavailable"
    assert stale_output.data.error_code == "STALE_TIMEOUT"
    assert completed is True
    assert ready_output.data is not None
    assert ready_output.data.generation_status == "ready"
    assert ready_output.data.available_count == 1
    assert ready_output.data.dimension_definitions.items[0].dimension_id == "ad_1"


def test_additional_flow_uses_one_batch_call_and_empty_pool_skips_llm() -> None:
    service = Mock()
    service.start_additional_dimension_generation.return_value = {
        "source_fingerprint": "sha256:source",
        "generation_diagnostics": {},
        "dimension_definitions": [],
    }
    one_question = V4EventImpactAnalysisResult.model_validate(
        {
            "impactPaths": [
                {
                    "impactPathId": "p1",
                    "eventId": 101,
                    "sourceFactIds": ["f1"],
                    "mechanism": "공급 경로",
                    "leverSteps": [
                        {
                            "impactLeverId": 1,
                            "leverCode": "supply",
                            "pathRole": "primary",
                            "stateDirection": "increase",
                            "scope": "시장",
                            "timing": "단기",
                        },
                    ],
                    "materiality": "high",
                },
            ],
            "pathUncertainties": [_uncertainty("u1")],
        },
    )
    invoke = AsyncMock(return_value=V4ReadableAdditionalDimensionDesignDraft(dimensions=[]))
    catalog_service = Mock()
    catalog_service.load_active_catalog.return_value = ([], "v1", "checksum")
    logger = Mock()
    trace_contexts: list[TraceContext] = []
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )

    @contextmanager
    def capture_mlflow_context(trace_context: TraceContext) -> Iterator[None]:
        trace_contexts.append(trace_context)
        yield

    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService",
            return_value=service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_unused_impact_analysis",
            side_effect=[one_question, V4EventImpactAnalysisResult()],
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ModelImpactLeverService",
            return_value=catalog_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_v4_additional_dimension_user_prompt",
            return_value="batch prompt",
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.invoke_stage_structured_output",
            invoke,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.mlflow_trace_context",
            side_effect=capture_mlflow_context,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.new_transaction_id",
            side_effect=["trace-add-1", "trace-add-2"],
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.logger",
            logger,
        ),
    ):
        asyncio.run(run_additional_dimension_generation(10, run_id="run-1"))
        asyncio.run(run_additional_dimension_generation(10, run_id="run-2"))

    invoke.assert_awaited_once()
    llm_trace_context = invoke.await_args.kwargs["trace_context"]
    assert isinstance(llm_trace_context, TraceContext)
    assert llm_trace_context.transaction_id == "trace-add-1"
    assert llm_trace_context.api_identifier == API_IDENTIFIER_ADD_DIMENSION
    assert llm_trace_context.tags["api_version"] == ADDITIONAL_DIMENSION_API_VERSION
    assert trace_contexts[0] is llm_trace_context
    info_templates = [call.args[0] for call in logger.info.call_args_list]
    assert any("generation started" in template for template in info_templates)
    assert any("generation completed" in template for template in info_templates)
    assert service.complete_additional_dimension_generation.call_count == 2
    assert all(
        call.kwargs["candidates"] == [] for call in service.complete_additional_dimension_generation.call_args_list
    )


def test_additional_flow_retries_partial_success_and_saves_valid_candidates_after_last_attempt() -> None:
    service = Mock()
    service.start_additional_dimension_generation.return_value = {
        "source_fingerprint": "sha256:source",
        "generation_diagnostics": {},
        "dimension_definitions": [],
    }
    one_question = V4EventImpactAnalysisResult.model_validate(
        {
            "impactPaths": [
                {
                    "impactPathId": "p1",
                    "eventId": 101,
                    "sourceFactIds": ["f1"],
                    "mechanism": "공급 경로",
                    "leverSteps": [
                        {
                            "impactLeverId": 1,
                            "leverCode": "supply",
                            "pathRole": "primary",
                            "stateDirection": "increase",
                            "scope": "시장",
                            "timing": "단기",
                        },
                    ],
                    "materiality": "high",
                },
            ],
            "pathUncertainties": [_uncertainty("u1")],
        },
    )
    candidate = Mock()
    candidate.model_dump.return_value = {"dimension_id": "ad_valid"}
    hydration = _hydration_result(
        input_count=2,
        valid_candidates=[candidate],
        reason_code="INVALID_STATE_FORMAT",
    )
    invoke = AsyncMock(return_value=V4ReadableAdditionalDimensionDesignDraft(dimensions=[]))
    sleep = AsyncMock()
    prompt_builder = Mock(return_value="batch prompt")
    logger = Mock()
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )

    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService",
            return_value=service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_unused_impact_analysis",
            return_value=one_question,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ModelImpactLeverService",
        ) as catalog_service,
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_v4_additional_dimension_user_prompt",
            prompt_builder,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.invoke_stage_structured_output",
            invoke,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.hydrate_additional_dimension_candidates",
            return_value=hydration,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.asyncio.sleep",
            sleep,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.new_transaction_id",
            return_value="trace-partial",
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.logger",
            logger,
        ),
    ):
        catalog_service.return_value.load_active_catalog.return_value = ([], "v1", "checksum")
        asyncio.run(run_additional_dimension_generation(10, run_id="run-1"))

    assert invoke.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [1.0, 2.0]
    assert "INVALID_STATE_FORMAT" in prompt_builder.call_args_list[1].kwargs["validation_feedback"]
    service.complete_additional_dimension_generation.assert_called_once_with(
        10,
        source_fingerprint="sha256:source",
        run_id="run-1",
        candidates=[{"dimension_id": "ad_valid"}],
    )
    service.fail_additional_dimension_generation.assert_not_called()
    assert any("candidates rejected" in call.args[0] for call in logger.warning.call_args_list)


def test_additional_flow_retries_all_invalid_batch_then_saves_valid_second_response() -> None:
    service = Mock()
    service.start_additional_dimension_generation.return_value = {
        "source_fingerprint": "sha256:source",
        "generation_diagnostics": {},
        "dimension_definitions": [],
    }
    one_question = V4EventImpactAnalysisResult.model_validate(
        {
            "impactPaths": [
                {
                    "impactPathId": "p1",
                    "eventId": 101,
                    "sourceFactIds": ["f1"],
                    "mechanism": "공급 경로",
                    "leverSteps": [
                        {
                            "impactLeverId": 1,
                            "leverCode": "supply",
                            "pathRole": "primary",
                            "stateDirection": "increase",
                            "scope": "시장",
                            "timing": "단기",
                        },
                    ],
                    "materiality": "high",
                },
            ],
            "pathUncertainties": [_uncertainty("u1")],
        },
    )
    candidate = Mock()
    candidate.model_dump.return_value = {"dimension_id": "ad_valid"}
    invalid = _hydration_result(input_count=1, reason_code="INVALID_STATE_FORMAT")
    valid = _hydration_result(input_count=1, valid_candidates=[candidate])
    invoke = AsyncMock(return_value=V4ReadableAdditionalDimensionDesignDraft(dimensions=[]))
    sleep = AsyncMock()
    prompt_builder = Mock(return_value="batch prompt")
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )

    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService",
            return_value=service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_unused_impact_analysis",
            return_value=one_question,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ModelImpactLeverService",
        ) as catalog_service,
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_v4_additional_dimension_user_prompt",
            prompt_builder,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.invoke_stage_structured_output",
            invoke,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.hydrate_additional_dimension_candidates",
            side_effect=[invalid, valid],
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.asyncio.sleep",
            sleep,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.new_transaction_id",
            return_value="trace-retry",
        ),
    ):
        catalog_service.return_value.load_active_catalog.return_value = ([], "v1", "checksum")
        asyncio.run(run_additional_dimension_generation(10, run_id="run-1"))

    assert invoke.await_count == 2
    sleep.assert_awaited_once_with(1.0)
    assert "INVALID_STATE_FORMAT" in prompt_builder.call_args_list[1].kwargs["validation_feedback"]
    service.complete_additional_dimension_generation.assert_called_once()
    service.fail_additional_dimension_generation.assert_not_called()


def test_additional_flow_marks_failed_after_three_all_invalid_batches() -> None:
    service = Mock()
    service.start_additional_dimension_generation.return_value = {
        "source_fingerprint": "sha256:source",
        "generation_diagnostics": {},
        "dimension_definitions": [],
    }
    one_question = V4EventImpactAnalysisResult.model_validate(
        {
            "impactPaths": [
                {
                    "impactPathId": "p1",
                    "eventId": 101,
                    "sourceFactIds": ["f1"],
                    "mechanism": "공급 경로",
                    "leverSteps": [
                        {
                            "impactLeverId": 1,
                            "leverCode": "supply",
                            "pathRole": "primary",
                            "stateDirection": "increase",
                            "scope": "시장",
                            "timing": "단기",
                        },
                    ],
                    "materiality": "high",
                },
            ],
            "pathUncertainties": [_uncertainty("u1")],
        },
    )
    invalid = _hydration_result(input_count=1, reason_code="INVALID_STATE_FORMAT")
    invoke = AsyncMock(return_value=V4ReadableAdditionalDimensionDesignDraft(dimensions=[]))
    sleep = AsyncMock()
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )

    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService",
            return_value=service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_unused_impact_analysis",
            return_value=one_question,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ModelImpactLeverService",
        ) as catalog_service,
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_v4_additional_dimension_user_prompt",
            return_value="batch prompt",
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.invoke_stage_structured_output",
            invoke,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.hydrate_additional_dimension_candidates",
            return_value=invalid,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.asyncio.sleep",
            sleep,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.new_transaction_id",
            return_value="trace-invalid",
        ),
    ):
        catalog_service.return_value.load_active_catalog.return_value = ([], "v1", "checksum")
        asyncio.run(run_additional_dimension_generation(10, run_id="run-1"))

    assert invoke.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [1.0, 2.0]
    service.complete_additional_dimension_generation.assert_not_called()
    service.fail_additional_dimension_generation.assert_called_once_with(
        10,
        source_fingerprint="sha256:source",
        run_id="run-1",
        error_code=ADDITIONAL_DIMENSION_CANDIDATES_INVALID,
    )

    with patch(
        "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
        return_value={
            "generation": {"status": "failed", "error_code": ADDITIONAL_DIMENSION_CANDIDATES_INVALID},
            "candidates": [],
            "dimension_selected": [],
            "dimension_definitions": [],
            "updated_at": None,
        },
    ):
        output = get_additional_dimensions(10)
    assert output.data is not None
    assert output.data.dimension_definitions.status == "unavailable"
    assert output.data.error_code == ADDITIONAL_DIMENSION_CANDIDATES_INVALID


def test_additional_attempt_span_records_attempt_counts_and_rejection_reason_codes() -> None:
    captured: dict[str, Any] = {}

    class FakeSpan:
        def set_attributes(self, attributes: dict[str, Any]) -> None:
            captured["result_attributes"] = attributes

    class FakeManager:
        def __enter__(self) -> FakeSpan:
            return FakeSpan()

        def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
            return None

    def start_span(**kwargs: Any) -> FakeManager:  # noqa: ANN401
        captured["start_kwargs"] = kwargs
        return FakeManager()

    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(is_mlflow_tracing_enabled=lambda **_kwargs: True),
    )
    mlflow_module = ModuleType("mlflow")
    mlflow_module.start_span = start_span  # type: ignore[attr-defined]
    result = _hydration_result(input_count=1, reason_code="INVALID_STATE_FORMAT")

    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.config": settings_module, "mlflow": mlflow_module},
        ),
        _additional_dimension_attempt_span(attempt=2) as span,
    ):
        _record_attempt_result(span, result)

    assert captured["start_kwargs"] == {
        "name": "additional_dimension_design_attempt",
        "span_type": "CHAIN",
        "attributes": {"attempt": 2},
    }
    assert captured["result_attributes"] == {
        "input_candidate_count": 1,
        "valid_candidate_count": 0,
        "rejected_candidate_count": 1,
        "rejection_reason_codes": "INVALID_STATE_FORMAT",
    }


def test_additional_flow_records_interrupted_on_cancellation() -> None:
    service = Mock()
    service.start_additional_dimension_generation.return_value = {
        "source_fingerprint": "sha256:source",
        "generation_diagnostics": {},
        "dimension_definitions": [],
    }
    one_question = V4EventImpactAnalysisResult.model_validate(
        {
            "impactPaths": [
                {
                    "impactPathId": "p1",
                    "eventId": 101,
                    "sourceFactIds": ["f1"],
                    "mechanism": "공급 경로",
                    "leverSteps": [
                        {
                            "impactLeverId": 1,
                            "leverCode": "supply",
                            "pathRole": "primary",
                            "stateDirection": "increase",
                            "scope": "시장",
                            "timing": "단기",
                        },
                    ],
                    "materiality": "high",
                },
            ],
            "pathUncertainties": [_uncertainty("u1")],
        },
    )
    entered = asyncio.Event()

    async def wait_forever(**_kwargs: object) -> None:
        entered.set()
        await asyncio.Event().wait()

    catalog_service = Mock()
    catalog_service.load_active_catalog.return_value = ([], "v1", "checksum")
    logger = Mock()
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )
    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService",
            return_value=service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_unused_impact_analysis",
            return_value=one_question,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ModelImpactLeverService",
            return_value=catalog_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.build_v4_additional_dimension_user_prompt",
            return_value="batch prompt",
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.invoke_stage_structured_output",
            side_effect=wait_forever,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.new_transaction_id",
            return_value="trace-cancelled",
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.logger",
            logger,
        ),
    ):

        async def exercise() -> None:
            task = asyncio.create_task(run_additional_dimension_generation(10, run_id="run-1"))
            await asyncio.wait_for(entered.wait(), timeout=1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(exercise())

    service.fail_additional_dimension_generation.assert_called_once_with(
        10,
        source_fingerprint="sha256:source",
        run_id="run-1",
        error_code="SERVER_SHUTDOWN",
        interrupted=True,
    )
    assert any("generation interrupted" in call.args[0] for call in logger.error.call_args_list)


def test_v4_sync_queues_and_submits_additional_dimension_generation() -> None:
    order: list[str] = []
    group_service = Mock()
    group_service.queue_additional_dimension_generation.side_effect = lambda *_args, **_kwargs: (
        order.append("queue")
        or {
            "status": "queued",
            "source_fingerprint": "sha256:source",
            "source_uncertainty_ids": ["u1"],
        }
    )
    runner = Mock()
    runner.submit.side_effect = lambda _scenario_group_id: order.append("submit")
    output = SimpleNamespace(
        data=SimpleNamespace(
            generation_diagnostics=SimpleNamespace(additional_dimension_generation=None),
            usage=None,
        ),
    )
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )
    prepared = {
        "scenario_group": SimpleNamespace(scenario_group_id=10),
        "user_id": 7,
    }
    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync."
            "prepare_v4_multi_event_scenarios",
            return_value=prepared,
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync."
            "run_v4_multi_event_scenarios_inline",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync.ScenarioGroupService",
            return_value=group_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.runtime.get_additional_dimension_task_runner",
            return_value=runner,
        ),
    ):
        result = asyncio.run(
            create_v4_scenarios_sync(
                V4MultiEventCreateScenariosSyncIn(mi_event_ids=[101], user_id=7),
            ),
        )

    assert result is output
    assert order == ["queue", "submit"]
    generation = output.data.generation_diagnostics.additional_dimension_generation
    assert generation.status == "queued"
    assert generation.source_uncertainty_ids == ["u1"]


def test_v4_sync_keeps_main_result_successful_when_additional_enqueue_fails() -> None:
    group_service = Mock()
    group_service.queue_additional_dimension_generation.side_effect = RuntimeError("queue database failure")
    group_service.fail_additional_dimension_enqueue.return_value = {
        "status": "failed",
        "source_fingerprint": "sha256:source",
        "source_uncertainty_ids": ["u1"],
        "error_code": "ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
    }
    output = SimpleNamespace(
        data=SimpleNamespace(
            generation_diagnostics=SimpleNamespace(additional_dimension_generation=None),
            usage=None,
        ),
    )
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )
    prepared = {
        "scenario_group": SimpleNamespace(scenario_group_id=10),
        "user_id": 7,
    }
    runner = Mock()
    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync."
            "prepare_v4_multi_event_scenarios",
            return_value=prepared,
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync."
            "run_v4_multi_event_scenarios_inline",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync.ScenarioGroupService",
            return_value=group_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.runtime.get_additional_dimension_task_runner",
            return_value=runner,
        ),
    ):
        result = asyncio.run(
            create_v4_scenarios_sync(
                V4MultiEventCreateScenariosSyncIn(mi_event_ids=[101], user_id=7),
            ),
        )

    assert result is output
    assert result.data.generation_diagnostics.additional_dimension_generation.status == "failed"
    assert (
        result.data.generation_diagnostics.additional_dimension_generation.error_code
        == "ADDITIONAL_DIMENSION_ENQUEUE_FAILED"
    )
    group_service.fail_additional_dimension_enqueue.assert_called_once_with(
        10,
        user_id=7,
        error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
    )
    runner.submit.assert_not_called()


def test_v4_sync_keeps_main_result_successful_when_task_submit_fails() -> None:
    group_service = Mock()
    group_service.queue_additional_dimension_generation.return_value = {
        "status": "queued",
        "source_fingerprint": "sha256:source",
        "source_uncertainty_ids": ["u1"],
    }
    group_service.fail_additional_dimension_enqueue.return_value = {
        "status": "failed",
        "source_fingerprint": "sha256:source",
        "source_uncertainty_ids": ["u1"],
        "error_code": "ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
    }
    output = SimpleNamespace(
        data=SimpleNamespace(
            generation_diagnostics=SimpleNamespace(additional_dimension_generation=None),
            usage=None,
        ),
    )
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )
    prepared = {
        "scenario_group": SimpleNamespace(scenario_group_id=10),
        "user_id": 7,
    }
    runner = Mock()
    runner.submit.side_effect = RuntimeError("event loop unavailable")
    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync."
            "prepare_v4_multi_event_scenarios",
            return_value=prepared,
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync."
            "run_v4_multi_event_scenarios_inline",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync.ScenarioGroupService",
            return_value=group_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.runtime.get_additional_dimension_task_runner",
            return_value=runner,
        ),
    ):
        result = asyncio.run(
            create_v4_scenarios_sync(
                V4MultiEventCreateScenariosSyncIn(mi_event_ids=[101], user_id=7),
            ),
        )

    assert result is output
    generation = result.data.generation_diagnostics.additional_dimension_generation
    assert generation.status == "failed"
    assert generation.error_code == "ADDITIONAL_DIMENSION_ENQUEUE_FAILED"
    group_service.fail_additional_dimension_enqueue.assert_called_once_with(
        10,
        user_id=7,
        error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
    )


def test_additional_runner_start_only_enables_task_acceptance() -> None:
    runner = AdditionalDimensionTaskRunner()

    with (
        patch("apps.agents.scenario_group_agent.runtime.asyncio.create_task") as create_task,
        patch("apps.agents.scenario_group_agent.runtime.asyncio.to_thread", new=AsyncMock()) as to_thread,
    ):
        asyncio.run(runner.start())

    assert not hasattr(runner, "_heartbeat_tasks")
    assert not hasattr(runner, "_reaper_task")
    create_task.assert_not_called()
    to_thread.assert_not_awaited()


def test_additional_runner_shutdown_finalizes_registered_jobs() -> None:
    runner = AdditionalDimensionTaskRunner()
    entered = asyncio.Event()

    async def running_job(_scenario_group_id: int, *, run_id: str) -> None:
        assert run_id
        entered.set()
        await asyncio.Event().wait()

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.run_additional_dimension_generation",
            side_effect=running_job,
        ),
        patch.object(
            ScenarioGroupService,
            "interrupt_additional_dimension_generation",
        ) as interrupt,
    ):

        async def exercise() -> None:
            await runner.start()
            submitted_run_id = runner.submit(10)
            await asyncio.wait_for(entered.wait(), timeout=1)
            await runner.shutdown()
            assert submitted_run_id

        asyncio.run(exercise())

    assert interrupt.call_count == 1
    assert interrupt.call_args.args == (10,)
    assert interrupt.call_args.kwargs["run_id"]


def test_graceful_shutdown_stops_owner_before_fenced_interrupt() -> None:
    order: list[str] = []
    runner = AdditionalDimensionTaskRunner()
    entered = asyncio.Event()

    async def running_job(_scenario_group_id: int, *, run_id: str) -> None:
        assert run_id
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            order.append("owner_stopped")

    def interrupt(_scenario_group_id: int, *, run_id: str) -> None:
        assert run_id
        order.append("db_interrupted")

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.run_additional_dimension_generation",
            side_effect=running_job,
        ),
        patch.object(
            ScenarioGroupService,
            "interrupt_additional_dimension_generation",
            side_effect=interrupt,
        ),
    ):

        async def exercise() -> None:
            runner.submit(10)
            await asyncio.wait_for(entered.wait(), timeout=1)
            await runner.shutdown()

        asyncio.run(exercise())

    assert order == ["owner_stopped", "db_interrupted"]


def test_claim_is_single_owner_and_records_run_id() -> None:
    group = _group()
    service = ScenarioGroupService()

    with _service_fixture(group) as (session, repository):
        queued = service.queue_additional_dimension_generation(10, user_id=7)
        first = service.start_additional_dimension_generation(10, run_id="run-1")
        second = service.start_additional_dimension_generation(10, run_id="run-2")

    generation = group.generation_diagnostics["additional_dimension_generation"]
    assert first is not None
    assert first["run_id"] == "run-1"
    assert second is None
    assert generation["status"] == "running"
    assert generation["source_fingerprint"] == queued["source_fingerprint"]
    assert generation["run_id"] == "run-1"
    assert generation["started_at"]
    assert "heartbeat_at" not in generation
    assert repository.update_group.call_count == 2
    assert session.commit.call_count == 2


def test_old_run_cannot_overwrite_replacement_with_same_source_fingerprint() -> None:
    group = _group()
    service = ScenarioGroupService()

    with _service_fixture(group):
        old = service.queue_additional_dimension_generation(10, user_id=7)
        assert service.start_additional_dimension_generation(10, run_id="run-old") is not None
        generation = group.generation_diagnostics["additional_dimension_generation"]
        generation["run_id"] = "run-new"

        late_complete = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=old["source_fingerprint"],
            run_id="run-old",
            candidates=[{"dimension_id": "late"}],
        )
        service.fail_additional_dimension_generation(
            10,
            source_fingerprint=old["source_fingerprint"],
            run_id="run-old",
            error_code="LATE_FAILURE",
        )

    generation = group.generation_diagnostics["additional_dimension_generation"]
    assert late_complete is False
    assert generation["status"] == "running"
    assert generation["run_id"] == "run-new"
    assert group.generation_diagnostics["additional_dimension_candidates"] == []


def test_additional_flow_claim_failure_is_contained_and_marks_auxiliary_failed() -> None:
    service = Mock()
    service.start_additional_dimension_generation.side_effect = RuntimeError("database unavailable")

    with patch(
        "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService",
        return_value=service,
    ):
        asyncio.run(run_additional_dimension_generation(10, run_id="run-1"))

    service.fail_additional_dimension_claim.assert_called_once_with(
        10,
        run_id="run-1",
        error_code="ADDITIONAL_DIMENSION_CLAIM_FAILED",
    )
    service.complete_additional_dimension_generation.assert_not_called()
    service.fail_additional_dimension_generation.assert_not_called()


def test_claim_and_failure_status_errors_leave_job_for_stale_get_projection_without_llm() -> None:
    failed_service = Mock()
    failed_service.start_additional_dimension_generation.side_effect = RuntimeError("claim failed")
    failed_service.fail_additional_dimension_claim.side_effect = RuntimeError("status failed")
    invoke = AsyncMock()

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService",
            return_value=failed_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow.invoke_stage_structured_output",
            invoke,
        ),
    ):
        asyncio.run(run_additional_dimension_generation(10, run_id="run-failed-claim"))

    invoke.assert_not_awaited()
    group = _group(
        diagnostics={
            "additional_dimension_generation": {
                "status": "queued",
                "source_fingerprint": "sha256:source",
                "queued_at": "2026-08-21T00:00:00+00:00",
            },
        },
    )
    original = deepcopy(group.generation_diagnostics)
    with (
        _service_fixture(group) as (session, repository),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._get_additional_dimension_stale_after_seconds",
            return_value=240,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.add_dimension.flow._utc_now",
            return_value=datetime(2026, 8, 21, 0, 4, tzinfo=UTC),
        ),
    ):
        output = get_additional_dimensions(10)

    assert output.data is not None
    assert output.data.generation_status == "interrupted"
    assert output.data.error_code == "STALE_TIMEOUT"
    assert group.generation_diagnostics == original
    repository.update_group.assert_not_called()
    session.commit.assert_not_called()


def test_create_operation_records_completed_before_auxiliary_submit() -> None:
    order: list[str] = []
    operation_service = Mock()
    operation_service.append_event.side_effect = lambda _group_id, _operation_id, **kwargs: order.append(
        f"event:{kwargs['event_type']}",
    )
    group_service = Mock()
    group_service.queue_additional_dimension_generation.side_effect = lambda *_args, **_kwargs: (
        order.append("queue")
        or {
            "status": "queued",
            "source_fingerprint": "sha256:source",
            "source_uncertainty_ids": ["u1"],
        }
    )
    runner = Mock()
    runner.submit.side_effect = lambda _group_id: order.append("submit")
    output = SimpleNamespace(
        data=SimpleNamespace(
            table=SimpleNamespace(rows=[object(), object()]),
            model_dump=lambda **_kwargs: {
                "scenarioGroup": {"scenarioGroupId": 10},
                "table": {"headers": [], "rows": []},
                "generationDiagnostics": {},
            },
        ),
    )
    settings = Mock()
    settings.get_agent_config.return_value = SimpleNamespace(aip_app_id="scenario-group-test")
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(return_value=settings)  # type: ignore[attr-defined]

    async def run_generation(*_args: object, **kwargs: object) -> object:
        await kwargs["on_node_start"]("analyze_event_impacts")  # type: ignore[operator]
        return output

    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation."
            "ScenarioGroupOperationService",
            return_value=operation_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.ScenarioGroupService",
            return_value=group_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation."
            "run_v4_multi_event_scenarios_with_progress",
            new=AsyncMock(side_effect=run_generation),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.new_transaction_id",
            return_value="trace-id",
        ),
        patch(
            "apps.agents.scenario_group_agent.runtime.get_additional_dimension_task_runner",
            return_value=runner,
        ),
    ):
        asyncio.run(
            run_v4_create_operation(
                {
                    "scenario_group": SimpleNamespace(scenario_group_id=10),
                    "user_id": 7,
                },
                "operation-id",
            ),
        )

    assert order == ["event:phase_started", "queue", "event:completed", "submit"]


def test_create_operation_keeps_completed_status_when_auxiliary_submit_fails() -> None:
    operation_service = Mock()
    group_service = Mock()
    group_service.queue_additional_dimension_generation.return_value = {
        "status": "queued",
        "source_fingerprint": "sha256:source",
        "source_uncertainty_ids": ["u1"],
    }
    runner = Mock()
    runner.submit.side_effect = RuntimeError("event loop unavailable")
    output = SimpleNamespace(
        data=SimpleNamespace(
            table=SimpleNamespace(rows=[object()]),
            model_dump=lambda **_kwargs: {
                "scenarioGroup": {"scenarioGroupId": 10},
                "table": {"headers": [], "rows": []},
                "generationDiagnostics": {},
            },
        ),
    )
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )

    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation."
            "ScenarioGroupOperationService",
            return_value=operation_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.ScenarioGroupService",
            return_value=group_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation."
            "run_v4_multi_event_scenarios_with_progress",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.new_transaction_id",
            return_value="trace-id",
        ),
        patch(
            "apps.agents.scenario_group_agent.runtime.get_additional_dimension_task_runner",
            return_value=runner,
        ),
    ):
        asyncio.run(
            run_v4_create_operation(
                {
                    "scenario_group": SimpleNamespace(scenario_group_id=10),
                    "user_id": 7,
                },
                "operation-id",
            ),
        )

    completed = operation_service.append_event.call_args.kwargs
    assert completed["event_type"] == "completed"
    assert completed["status"] == "succeeded"
    group_service.fail_additional_dimension_enqueue.assert_called_once_with(
        10,
        user_id=7,
        error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
    )


def test_create_operation_keeps_completed_status_when_additional_enqueue_fails() -> None:
    operation_service = Mock()
    events: list[str] = []
    operation_service.append_event.side_effect = lambda _group_id, _operation_id, **kwargs: events.append(
        str(kwargs["event_type"]),
    )
    group_service = Mock()
    group_service.queue_additional_dimension_generation.side_effect = RuntimeError("queue database failure")
    group_service.fail_additional_dimension_enqueue.return_value = {
        "status": "failed",
        "source_fingerprint": "sha256:source",
        "source_uncertainty_ids": ["u1"],
        "error_code": "ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
    }
    output = SimpleNamespace(
        data=SimpleNamespace(
            table=SimpleNamespace(rows=[object()]),
            model_dump=lambda **_kwargs: {
                "scenarioGroup": {"scenarioGroupId": 10},
                "table": {"headers": [], "rows": []},
                "generationDiagnostics": {},
            },
        ),
    )
    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(
            get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="scenario-group-test"),
        ),
    )

    with (
        patch.dict(sys.modules, {"apps.common.configs.config": settings_module}),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation."
            "ScenarioGroupOperationService",
            return_value=operation_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.ScenarioGroupService",
            return_value=group_service,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation."
            "run_v4_multi_event_scenarios_with_progress",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.mlflow_trace_context",
            return_value=nullcontext(),
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation.new_transaction_id",
            return_value="trace-id",
        ),
    ):
        asyncio.run(
            run_v4_create_operation(
                {
                    "scenario_group": SimpleNamespace(scenario_group_id=10),
                    "user_id": 7,
                },
                "operation-id",
            ),
        )

    assert events == ["completed"]
    completed = operation_service.append_event.call_args.kwargs
    assert completed["status"] == "succeeded"
    assert (
        completed["presentation_snapshot"]["generationDiagnostics"]["additionalDimensionGeneration"]["errorCode"]
        == "ADDITIONAL_DIMENSION_ENQUEUE_FAILED"
    )
    group_service.fail_additional_dimension_enqueue.assert_called_once_with(
        10,
        user_id=7,
        error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
    )
