from __future__ import annotations

# ruff: noqa: CPY001, S101
import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
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
        started = service.start_additional_dimension_generation(10)
        completed = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=queued["source_fingerprint"],
            candidates=candidates,
        )
        completed_again = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=queued["source_fingerprint"],
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
        started = service.start_additional_dimension_generation(10)

    assert generation["status"] == "ready"
    assert generation["source_uncertainty_ids"] == []
    assert started is None
    assert group.generation_diagnostics["additional_dimension_candidates"] == []


def test_manual_requeue_requires_v4_ready_empty_candidates_and_unused_questions() -> None:
    group = _group()
    service = ScenarioGroupService()

    with _service_fixture(group) as (session, repository):
        ready = service.queue_additional_dimension_generation(10, user_id=7)
        assert service.start_additional_dimension_generation(10) is not None
        service.complete_additional_dimension_generation(
            10,
            source_fingerprint=ready["source_fingerprint"],
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
        assert service.start_additional_dimension_generation(10) is not None
        service.interrupt_additional_dimension_generation(10)
        service.interrupt_additional_dimension_generation(10)

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
        assert service.start_additional_dimension_generation(10) is not None
        mutation(group)
        stored = service.complete_additional_dimension_generation(
            10,
            source_fingerprint=queued["source_fingerprint"],
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
    with _service_fixture(_group(stage="scenario_validated")):
        with pytest.raises(MIBaseError) as wrong_stage:
            service.queue_additional_dimension_generation(10, user_id=7)
        with pytest.raises(MIBaseError) as wrong_stage_get:
            service.load_additional_dimensions(10)

    assert wrong_version.value.error_code is ErrorCode.INVALID_REQUEST
    assert wrong_version.value.status_code == 400
    assert wrong_version_get.value.error_code is ErrorCode.INVALID_REQUEST
    assert wrong_version_get.value.status_code == 400
    assert wrong_stage.value.error_code is ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT
    assert wrong_stage.value.status_code == 409
    assert wrong_stage_get.value.error_code is ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT
    assert wrong_stage_get.value.status_code == 409


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
        asyncio.run(run_additional_dimension_generation(10))
        asyncio.run(run_additional_dimension_generation(10))

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


def test_additional_flow_preserves_partial_success_without_retry() -> None:
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
            return_value="batch prompt",
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
        asyncio.run(run_additional_dimension_generation(10))

    invoke.assert_awaited_once()
    service.complete_additional_dimension_generation.assert_called_once_with(
        10,
        source_fingerprint="sha256:source",
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
        asyncio.run(run_additional_dimension_generation(10))

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
        asyncio.run(run_additional_dimension_generation(10))

    assert invoke.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [1.0, 2.0]
    service.complete_additional_dimension_generation.assert_not_called()
    service.fail_additional_dimension_generation.assert_called_once_with(
        10,
        source_fingerprint="sha256:source",
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
            task = asyncio.create_task(run_additional_dimension_generation(10))
            await asyncio.wait_for(entered.wait(), timeout=1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(exercise())

    service.fail_additional_dimension_generation.assert_called_once_with(
        10,
        source_fingerprint="sha256:source",
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


def test_additional_runner_performs_bounded_startup_recovery() -> None:
    runner = AdditionalDimensionTaskRunner()
    with (
        patch.object(
            ScenarioGroupService,
            "list_recoverable_additional_dimension_group_ids",
            return_value=[10, 11],
        ) as recover,
        patch.object(runner, "submit") as submit,
    ):
        asyncio.run(runner.start(recovery_limit=2))

    recover.assert_called_once_with(limit=2)
    assert [call.args[0] for call in submit.call_args_list] == [10, 11]


def test_additional_runner_shutdown_finalizes_registered_jobs() -> None:
    runner = AdditionalDimensionTaskRunner()
    entered = asyncio.Event()

    async def running_job(_scenario_group_id: int) -> None:
        entered.set()
        await asyncio.Event().wait()

    with (
        patch.object(
            ScenarioGroupService,
            "list_recoverable_additional_dimension_group_ids",
            return_value=[],
        ),
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
            runner.submit(10)
            await asyncio.wait_for(entered.wait(), timeout=1)
            await runner.shutdown()

        asyncio.run(exercise())

    interrupt.assert_called_once_with(10)


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

    assert order == ["event:phase_started", "queue", "event:completed", "submit"]
