from __future__ import annotations

# ruff: noqa: CPY001, S101, SLF001
from copy import deepcopy
from decimal import Decimal
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest

from apps.agents.scenario_group_agent.flows.add_dimension.flow import get_additional_dimensions
from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
    dimension_definition_fingerprint,
    scenario_fingerprint,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import ScenarioService
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario_group_operation.schema import (
    ValidationGeneratedFieldsPayload,
    ValidationOperationResultPayload,
    ValidationResultPayload,
    ValidationScenarioChangeSetPayload,
    ValidationScenarioUpsertPayload,
)


FORMAL_DEFINITION = {
    "dimension_id": "d1",
    "label": "공급 규모",
    "description": "공급 규모는 어떻게 변하는가?",
    "rationale": "초기 분기",
    "source_uncertainty_ids": ["u1"],
    "values": [
        {"value_id": "d1_v1", "label": "낮음", "pressure_contribution": "bullish"},
        {"value_id": "d1_v2", "label": "높음", "pressure_contribution": "bearish"},
    ],
}

CANDIDATE_DEFINITION = {
    "dimension_id": "ad_duration",
    "label": "공급 지속성",
    "description": "공급 변화는 얼마나 지속되는가?",
    "rationale": "기간 분기",
    "source_uncertainty_ids": ["u2"],
    "values": [
        {
            "value_id": "ad_duration_v1",
            "label": "단기",
            "pressure_contribution": "balanced",
        },
        {
            "value_id": "ad_duration_v2",
            "label": "장기",
            "pressure_contribution": "bullish",
        },
    ],
}


def _uncertainty(
    subject: str = "공급 변화는 얼마나 지속되는가?",
    *,
    uncertainty_id: str = "u2",
) -> dict[str, Any]:
    return {
        "uncertainty_id": uncertainty_id,
        "impact_path_ids": [f"p-{uncertainty_id}"],
        "axis_type": "duration",
        "subject": subject,
        "affected_lever_code": "supply",
        "reason": subject,
        "materiality": "high",
        "semantic_key": f"p-{uncertainty_id}:duration:supply",
    }


def _scenario_dict(target: SimpleNamespace) -> dict[str, Any]:
    return {
        "scenario_id": target.scenario_id,
        "scenario_group_id": target.scenario_group_id,
        "display_order": target.display_order,
        "title": target.title,
        "narrative": target.narrative,
        "dimension_values": deepcopy(target.dimension_values),
        "probability_score": target.probability_score,
        "probability_delta": target.probability_delta,
        "baseline_yn": target.baseline_yn,
        "global_pressure_band": target.global_pressure_band,
        "scenario_role": target.scenario_role,
        "global_pressure_rationale": target.global_pressure_rationale,
        "related_markets": deepcopy(target.related_markets),
    }


def _fixture() -> tuple[
    ValidationOperationResultPayload,
    SimpleNamespace,
    SimpleNamespace,
    SimpleNamespace,
    Mock,
    Mock,
    Mock,
    Mock,
    Mock,
]:
    scenario = SimpleNamespace(
        scenario_id=1,
        scenario_group_id=10,
        display_order=1,
        title="기존 Scenario",
        narrative="기존 narrative",
        dimension_values={"d1": "d1_v1"},
        probability_score=Decimal("100"),
        probability_delta=Decimal("0"),
        baseline_yn="Y",
        global_pressure_band="bullish",
        scenario_role="ceiling",
        global_pressure_rationale="기존 근거",
        related_markets=[],
        status="creating",
    )
    diagnostics = {
        "path_uncertainties": [_uncertainty()],
        "interaction_uncertainties": [],
        "additional_dimension_candidates": [deepcopy(CANDIDATE_DEFINITION)],
    }
    group = SimpleNamespace(
        scenario_group_id=10,
        api_version="v4",
        generation_strategy="multi_event_model_lever_dimensions",
        status="creating",
        stage="scenario_created",
        request_usr_id=7,
        dimension_selected=["d1"],
        dimension_definitions=[deepcopy(FORMAL_DEFINITION)],
        generation_diagnostics=diagnostics,
    )
    _unused, source_fingerprint = ScenarioGroupService._additional_dimension_source(group)
    diagnostics["additional_dimension_generation"] = {
        "status": "ready",
        "source_fingerprint": source_fingerprint,
    }
    target_definitions = [deepcopy(FORMAL_DEFINITION), deepcopy(CANDIDATE_DEFINITION)]
    result = ValidationOperationResultPayload(
        mode="changed",
        base_scenario_fingerprint=scenario_fingerprint([_scenario_dict(scenario)]),
        base_dimension_definition_fingerprint=dimension_definition_fingerprint(
            [FORMAL_DEFINITION],
        ),
        dimension_definition_fingerprint=dimension_definition_fingerprint(target_definitions),
        requested_dimension_ids=["d1", "ad_duration"],
        requested_dimension_definitions=[
            deepcopy(FORMAL_DEFINITION),
            {**deepcopy(CANDIDATE_DEFINITION), "label": "operation payload 변조값"},
        ],
        promoted_dimension_ids=["ad_duration"],
        candidate_source_fingerprint=source_fingerprint,
        validation_result=ValidationResultPayload(
            verdict="PASS",
            is_valid=True,
            can_proceed=True,
            reason_markdown="승격 가능",
        ),
        scenario_change_set=ValidationScenarioChangeSetPayload(
            upserts=[
                ValidationScenarioUpsertPayload(
                    scenario_id=1,
                    client_row_key="scenario:1",
                    change_type="COMBINATION_CHANGED",
                    display_order=1,
                    title="기존 Scenario",
                    dimension_values={"d1": "d1_v1", "ad_duration": "ad_duration_v2"},
                    generated_fields=ValidationGeneratedFieldsPayload(
                        narrative="후보 Dimension을 반영한 narrative",
                        probability_score=100,
                        probability_delta=0,
                        pressure_band="bullish",
                        pressure_rationale="장기 공급 변화",
                        related_markets=[],
                    ),
                ),
            ],
        ),
    )
    operation = SimpleNamespace(
        operation_id="validation-op",
        operation_type="validation",
        status="running",
        result_payload=None,
    )
    session = Mock()
    operation_repository = Mock()
    operation_repository.fetch_by_id.return_value = operation
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "creating",
        "stage": "scenario_validated",
    }

    def update_group(target: SimpleNamespace, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            setattr(target, key, value)

    group_repository.update_group.side_effect = update_group
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.side_effect = [[scenario], [scenario]]
    scenario_repository.model_to_dict.side_effect = _scenario_dict

    def update_scenario(target: SimpleNamespace, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            setattr(target, key, value)

    scenario_repository.update_from_payload.side_effect = update_scenario
    signpost_repository = Mock()
    return (
        result,
        group,
        scenario,
        operation,
        session,
        operation_repository,
        group_repository,
        scenario_repository,
        signpost_repository,
    )


def _connection_module(session: Mock) -> ModuleType:
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    return connection_module


def test_validation_atomically_promotes_locked_candidate_definition() -> None:
    (
        result,
        group,
        scenario,
        operation,
        session,
        operation_repository,
        group_repository,
        scenario_repository,
        signpost_repository,
    ) = _fixture()
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": _connection_module(
                    session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "SignpostRepository",
            return_value=signpost_repository,
        ),
        patch.object(ScenarioService, "_apply_v4_baseline_and_roles"),
    ):
        ScenarioGroupOperationService().complete_validation(
            scenario_group_id=10,
            operation_id="validation-op",
            result_payload=result,
            user_id=7,
        )

    assert group.dimension_selected == ["d1", "ad_duration"]
    assert group.dimension_definitions[1] == CANDIDATE_DEFINITION
    assert group.dimension_definitions[1]["label"] != "operation payload 변조값"
    assert scenario.dimension_values == {"d1": "d1_v1", "ad_duration": "ad_duration_v2"}
    assert group.generation_diagnostics["additional_dimension_candidates"] == []
    _unused, current_fingerprint = ScenarioGroupService._additional_dimension_source(group)
    assert group.generation_diagnostics["additional_dimension_generation"]["source_fingerprint"] == current_fingerprint
    assert group.generation_diagnostics["additional_dimension_generation"]["source_uncertainty_ids"] == []
    stored = ValidationOperationResultPayload.model_validate(operation.result_payload)
    assert stored.application is not None
    assert stored.requested_dimension_definitions[1] == CANDIDATE_DEFINITION
    group_repository.fetch_by_id.assert_called_once_with(10, for_update=True)
    assert scenario_repository.fetch_models_by_group_id.call_args_list[0].kwargs == {
        "for_update": True,
    }
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_two_candidates_from_distinct_sources_can_be_promoted_sequentially() -> None:
    (
        first_result,
        group,
        scenario,
        _operation,
        session,
        operation_repository,
        group_repository,
        scenario_repository,
        signpost_repository,
    ) = _fixture()
    second_candidate = deepcopy(CANDIDATE_DEFINITION)
    second_candidate.update(
        dimension_id="ad_scope",
        label="공급 영향 범위",
        description="공급 영향은 어디까지 확산되는가?",
        rationale="범위 분기",
        source_uncertainty_ids=["u3"],
    )
    second_candidate["values"] = [
        {**item, "value_id": str(item["value_id"]).replace("ad_duration", "ad_scope")}
        for item in second_candidate["values"]
    ]
    group.generation_diagnostics["path_uncertainties"].append(
        _uncertainty("공급 영향은 어디까지 확산되는가?", uncertainty_id="u3"),
    )
    group.generation_diagnostics["additional_dimension_candidates"].append(second_candidate)
    _unused, initial_fingerprint = ScenarioGroupService._additional_dimension_source(group)
    group.generation_diagnostics["additional_dimension_generation"]["source_fingerprint"] = initial_fingerprint
    first_result.candidate_source_fingerprint = initial_fingerprint

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": _connection_module(
                    session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "SignpostRepository",
            return_value=signpost_repository,
        ),
        patch.object(ScenarioService, "_apply_v4_baseline_and_roles"),
    ):
        service = ScenarioGroupOperationService()
        service.complete_validation(
            scenario_group_id=10,
            operation_id="validation-op",
            result_payload=first_result,
            user_id=7,
        )

        generation = group.generation_diagnostics["additional_dimension_generation"]
        assert generation["source_uncertainty_ids"] == ["u3"]
        assert group.generation_diagnostics["additional_dimension_candidates"] == [second_candidate]
        with patch.object(
            ScenarioGroupService,
            "load_additional_dimensions",
            return_value={
                "generation": generation,
                "candidates": group.generation_diagnostics["additional_dimension_candidates"],
                "dimension_selected": group.dimension_selected,
                "dimension_definitions": group.dimension_definitions,
                "updated_at": None,
            },
        ):
            get_result = get_additional_dimensions(10)
        assert get_result.data is not None
        assert [item.dimension_id for item in get_result.data.dimension_definitions.items] == ["ad_scope"]

        second_target_definitions = [*deepcopy(group.dimension_definitions), deepcopy(second_candidate)]
        second_result = ValidationOperationResultPayload(
            mode="changed",
            base_scenario_fingerprint=scenario_fingerprint([_scenario_dict(scenario)]),
            base_dimension_definition_fingerprint=dimension_definition_fingerprint(group.dimension_definitions),
            dimension_definition_fingerprint=dimension_definition_fingerprint(second_target_definitions),
            requested_dimension_ids=["d1", "ad_duration", "ad_scope"],
            requested_dimension_definitions=deepcopy(second_target_definitions),
            promoted_dimension_ids=["ad_scope"],
            candidate_source_fingerprint=generation["source_fingerprint"],
            validation_result=ValidationResultPayload(
                verdict="PASS",
                is_valid=True,
                can_proceed=True,
                reason_markdown="두 번째 승격 가능",
            ),
            scenario_change_set=ValidationScenarioChangeSetPayload(
                upserts=[
                    ValidationScenarioUpsertPayload(
                        scenario_id=1,
                        client_row_key="scenario:1",
                        change_type="COMBINATION_CHANGED",
                        display_order=1,
                        title="기존 Scenario",
                        dimension_values={
                            "d1": "d1_v1",
                            "ad_duration": "ad_duration_v2",
                            "ad_scope": "ad_scope_v1",
                        },
                        generated_fields=ValidationGeneratedFieldsPayload(
                            narrative="두 후보 Dimension을 반영한 narrative",
                            probability_score=100,
                            probability_delta=0,
                            pressure_band="bullish",
                            pressure_rationale="장기 공급 변화와 영향 범위",
                            related_markets=[],
                        ),
                    ),
                ],
            ),
        )
        operation_repository.fetch_by_id.return_value = SimpleNamespace(
            operation_id="validation-op-2",
            operation_type="validation",
            status="running",
            result_payload=None,
        )
        scenario_repository.fetch_models_by_group_id.side_effect = [[scenario], [scenario]]
        service.complete_validation(
            scenario_group_id=10,
            operation_id="validation-op-2",
            result_payload=second_result,
            user_id=7,
        )

    assert group.dimension_selected == ["d1", "ad_duration", "ad_scope"]
    assert group.generation_diagnostics["additional_dimension_candidates"] == []
    assert group.generation_diagnostics["additional_dimension_generation"]["source_uncertainty_ids"] == []
    assert session.commit.call_count == 2
    session.rollback.assert_not_called()


def test_validation_stale_candidate_source_rolls_back_without_writes() -> None:
    (
        result,
        group,
        _scenario,
        _operation,
        session,
        operation_repository,
        group_repository,
        scenario_repository,
        signpost_repository,
    ) = _fixture()
    group.generation_diagnostics["path_uncertainties"][0]["subject"] = "동시에 변경된 질문"
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": _connection_module(
                    session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "SignpostRepository",
            return_value=signpost_repository,
        ),
        pytest.raises(MIBaseError) as error,
    ):
        ScenarioGroupOperationService().complete_validation(
            scenario_group_id=10,
            operation_id="validation-op",
            result_payload=result,
            user_id=7,
        )

    assert error.value.error_code is ErrorCode.SCENARIO_DIMENSION_CANDIDATE_STALE
    scenario_repository.update_from_payload.assert_not_called()
    group_repository.update_group.assert_not_called()
    operation_repository.append_event.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
