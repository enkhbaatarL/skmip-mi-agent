from __future__ import annotations

# ruff: noqa: COM812, CPY001, S101
import asyncio
from collections.abc import Callable
from contextlib import nullcontext
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from apps.agents.scenario_group_agent.flows.validate_scenarios.flow import (
    _bg_to_output,
    _validation_table_for_output,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    _invoke_v4_autofill_selections,
    _run_v4_scenario_validation,
    _v4_autofill_selection_span,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.state import ValidateScenariosState
from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
    V4ValidationAnalysis,
    analyze_v4_validation_request,
    apply_v4_additional_dimension_autofill_selections,
    build_v4_additional_dimension_autofill_plan,
    normalize_v4_probability_scores,
    render_reason_markdown,
    scenario_fingerprint,
    validate_v4_pressure_aggregate,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import ScenarioService
from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    V4AdditionalDimensionValueSelection,
    V4AdditionalDimensionValueSelectionOutput,
    V4ValidationGeneratedScenario,
    V4ValidationGeneratedScenariosOutput,
)
from apps.agents.scenario_group_agent.schemas.endpoint import CreateSignpostsIn
from apps.agents.scenario_group_agent.schemas.state import ScenarioTableState
from apps.agents.scenario_group_agent.subgraphs.scenario_review.schema import CheckResult, ReviewReport
from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import ScenarioReviewState
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario.schema import ScenarioPayload, ScenarioTemplateDimension, ScenarioTemplateEnum
from apps.persistence.scenario_group.schema import ScenarioGroupPayload
from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationModel
from apps.persistence.scenario_group_operation.schema import (
    ValidationGeneratedFieldsPayload,
    ValidationOperationResultPayload,
    ValidationResultPayload,
    ValidationScenarioChangeSetPayload,
    ValidationScenarioUpsertPayload,
)


DEFINITIONS = [
    {
        "dimension_id": "demand",
        "label": "수요",
        "display_order": 1,
        "values": [
            {"value_id": "demand_low", "label": "낮은 수요", "pressure_contribution": "bearish"},
            {"value_id": "demand_high", "label": "높은 수요", "pressure_contribution": "bullish"},
        ],
    },
    {
        "dimension_id": "supply",
        "label": "공급",
        "display_order": 2,
        "values": [
            {"value_id": "supply_low", "label": "낮은 공급", "pressure_contribution": "bullish"},
            {"value_id": "supply_high", "label": "높은 공급", "pressure_contribution": "bearish"},
        ],
    },
]


def test_result_payload_has_orm_column_and_optional_reference_migration() -> None:
    assert MiScenarioGroupOperationModel.__table__.c.result_payload.nullable is True

    repository_root = Path(__file__).resolve().parents[2]
    migration = repository_root / "scripts/migrations/20260814_add_scenario_group_operation_result_payload.sql"
    if not migration.exists():
        return
    migration_sql = migration.read_text(encoding="utf-8")
    assert "ALTER TABLE `tmm_mi_scenario_group_operation_m`" in migration_sql
    assert "ADD COLUMN `result_payload` JSON NULL" in migration_sql


def _scenarios() -> list[dict[str, object]]:
    combinations = [
        ("상방", "demand_high", "supply_low", "strong_bullish", 30),
        ("혼합", "demand_high", "supply_high", "balanced", 50),
        ("하방", "demand_low", "supply_high", "strong_bearish", 20),
    ]
    return [
        {
            "scenario_id": index,
            "scenario_group_id": 10,
            "display_order": index,
            "title": title,
            "narrative": f"{title} narrative",
            "dimension_values": {"demand": demand, "supply": supply},
            "probability_score": score,
            "probability_delta": 0,
            "baseline_yn": "Y" if score == 50 else "N",
            "global_pressure_band": band,
            "scenario_role": "ceiling" if index == 1 else "floor" if index == 3 else "mixed",
            "global_pressure_rationale": f"{title} pressure",
            "related_markets": [],
            "status": "creating",
        }
        for index, (title, demand, supply, band, score) in enumerate(combinations, start=1)
    ]


def _table(*, labels: bool = False) -> dict[str, object]:
    value_labels = {
        "demand_low": "낮은 수요",
        "demand_high": "높은 수요",
        "supply_low": "낮은 공급",
        "supply_high": "높은 공급",
    }
    return {
        "headers": [
            {"key": "demand", "label": "수요", "display_order": 1},
            {"key": "supply", "label": "공급", "display_order": 2},
        ],
        "rows": [
            {
                "scenario_id": scenario["scenario_id"],
                "display_order": scenario["display_order"],
                "title": scenario["title"],
                "cells": {
                    key: value_labels[str(value)] if labels else value
                    for key, value in scenario["dimension_values"].items()
                },
            }
            for scenario in _scenarios()
        ],
    }


def _analyze(
    table: dict[str, object],
    diagnostics: dict[str, object] | None = None,
) -> V4ValidationAnalysis:
    return analyze_v4_validation_request(
        request_table=table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=diagnostics or {},
        stored_header_order=["demand", "supply"],
    )


def test_label_and_value_id_normalize_to_unchanged_fast_path() -> None:
    table = _table(labels=True)
    table["rows"][0]["title"] = "상 방!!"
    analysis = _analyze(table)

    assert analysis.unchanged is True
    assert analysis.blocking is False
    assert analysis.changed_rows == []


def test_ready_additional_candidate_extends_effective_validation_catalog() -> None:
    candidate = {
        "dimension_id": "ad_duration",
        "label": "지속 기간",
        "display_order": 3,
        "source_uncertainty_ids": ["u_duration"],
        "values": [
            {"value_id": "duration_short", "label": "단기", "pressure_contribution": "balanced"},
            {"value_id": "duration_long", "label": "장기", "pressure_contribution": "bullish"},
        ],
    }
    table = _table()
    table["headers"].append({"key": "ad_duration", "label": "지속 기간", "display_order": 3})
    for index, row in enumerate(table["rows"]):
        row["cells"]["ad_duration"] = "duration_short" if index == 0 else "duration_long"

    analysis = _analyze(
        table,
        diagnostics={
            "additional_dimension_generation": {
                "status": "ready",
                "source_fingerprint": "sha256:candidate-source",
            },
            "additional_dimension_candidates": [candidate],
        },
    )

    assert analysis.blocking is False
    assert analysis.canonical_headers == ["demand", "supply", "ad_duration"]
    assert analysis.promoted_dimension_ids == ["ad_duration"]
    assert analysis.candidate_source_fingerprint == "sha256:candidate-source"
    assert analysis.requested_dimension_definitions[-1]["dimension_id"] == "ad_duration"
    assert all("ad_duration" in row.dimension_values for row in analysis.canonical_rows)


def _directional_candidate(*, duplicate_bullish: bool = False) -> dict[str, object]:
    values: list[dict[str, object]] = [
        {
            "value_id": "duration_bearish",
            "label": "단기 종료",
            "pressure_contribution": "bearish",
            "lever_states": [{"lever_code": "L1", "direction": "recover"}],
            "assumption_rationale": "충격이 빠르게 해소되는 가정",
        },
        {
            "value_id": "duration_balanced",
            "label": "중립 지속",
            "pressure_contribution": "balanced",
            "lever_states": [{"lever_code": "L1", "direction": "unchanged"}],
            "assumption_rationale": "현재 상태가 유지되는 가정",
        },
        {
            "value_id": "duration_bullish",
            "label": "장기 지속",
            "pressure_contribution": "bullish",
            "lever_states": [{"lever_code": "L1", "direction": "disrupt"}],
            "assumption_rationale": "충격이 장기화되는 가정",
        },
    ]
    if duplicate_bullish:
        values.append(
            {
                "value_id": "duration_bullish_alt",
                "label": "점진 장기화",
                "pressure_contribution": "bullish",
                "lever_states": [{"lever_code": "L1", "direction": "disrupt"}],
                "assumption_rationale": "충격이 점진적으로 장기화되는 가정",
            }
        )
    return {
        "dimension_id": "ad_duration",
        "label": "지속 기간",
        "display_order": 3,
        "source_uncertainty_ids": ["u_duration"],
        "values": values,
    }


def _additional_diagnostics(candidate: dict[str, object]) -> dict[str, object]:
    return {
        "additional_dimension_generation": {
            "status": "ready",
            "source_fingerprint": "sha256:candidate-source",
        },
        "additional_dimension_candidates": [candidate],
    }


def _table_with_null_additional() -> dict[str, object]:
    table = _table()
    table["headers"].append({"key": "ad_duration", "label": "지속 기간", "display_order": 3})
    for row in table["rows"]:
        row["cells"]["ad_duration"] = None
    return table


def test_additional_dimension_nulls_are_deterministically_filled_by_existing_pressure_band() -> None:
    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(_directional_candidate()),
        stored_header_order=["demand", "supply"],
    )

    assert plan.requests == []
    assert plan.checks == []
    assert [row["cells"]["ad_duration"] for row in plan.request_table["rows"]] == [
        "duration_bullish",
        "duration_balanced",
        "duration_bearish",
    ]

    analysis = analyze_v4_validation_request(
        request_table=plan.request_table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(_directional_candidate()),
        stored_header_order=["demand", "supply"],
        autofilled_cells=plan.assignments,
    )
    assert not any(check.check_id == "V4_VALUE_ENUM" for check in analysis.checks)
    assert [row.change_type for row in analysis.canonical_rows] == ["AUTOFILL_ONLY"] * 3


def test_balanced_autofill_optimizes_all_empty_dimensions_as_one_row() -> None:
    base_definition = {
        "dimension_id": "base",
        "values": [{"value_id": "base_up", "label": "상방", "pressure_contribution": "bullish"}],
    }
    additional_definitions = [
        {
            "dimension_id": dimension_id,
            "label": dimension_id,
            "values": [
                {"value_id": f"{dimension_id}_down", "label": "하방", "pressure_contribution": "bearish"},
                {"value_id": f"{dimension_id}_flat", "label": "중립", "pressure_contribution": "balanced"},
            ],
        }
        for dimension_id in ("ad_first", "ad_second")
    ]
    plan = build_v4_additional_dimension_autofill_plan(
        request_table={
            "headers": [{"key": key} for key in ("base", "ad_first", "ad_second")],
            "rows": [
                {
                    "scenario_id": 1,
                    "title": "균형",
                    "cells": {"base": "base_up", "ad_first": None, "ad_second": None},
                }
            ],
        },
        persisted_scenarios=[
            {
                "scenario_id": 1,
                "global_pressure_band": "balanced",
                "dimension_values": {"base": "base_up"},
            }
        ],
        dimension_definitions=[base_definition],
        generation_diagnostics={
            "additional_dimension_generation": {"status": "ready"},
            "additional_dimension_candidates": additional_definitions,
        },
        stored_header_order=["base"],
    )

    assert plan.request_table["rows"][0]["cells"] == {
        "base": "base_up",
        "ad_first": "ad_first_down",
        "ad_second": "ad_second_flat",
    }


def test_balanced_autofill_tie_prefers_more_stored_value_reuse() -> None:
    definitions = [
        {
            "dimension_id": "base",
            "values": [{"value_id": "base_up", "pressure_contribution": "bullish"}],
        },
        *[
            {
                "dimension_id": dimension_id,
                "values": [
                    {"value_id": f"{dimension_id}_down", "pressure_contribution": "bearish"},
                    {"value_id": f"{dimension_id}_flat", "pressure_contribution": "balanced"},
                ],
            }
            for dimension_id in ("ad_first", "ad_second")
        ],
    ]
    plan = build_v4_additional_dimension_autofill_plan(
        request_table={
            "headers": [{"key": key} for key in ("base", "ad_first", "ad_second")],
            "rows": [
                {
                    "scenario_id": 1,
                    "title": "균형",
                    "cells": {"base": "base_up", "ad_first": None, "ad_second": None},
                }
            ],
        },
        persisted_scenarios=[
            {
                "scenario_id": 1,
                "global_pressure_band": "balanced",
                "dimension_values": {
                    "base": "base_up",
                    "ad_first": "ad_first_flat",
                    "ad_second": "ad_second_down",
                },
            }
        ],
        dimension_definitions=definitions,
        generation_diagnostics={},
        stored_header_order=["base", "ad_first", "ad_second"],
    )

    assert plan.request_table["rows"][0]["cells"] == {
        "base": "base_up",
        "ad_first": "ad_first_flat",
        "ad_second": "ad_second_down",
    }
    assert set(plan.restorations) == {("scenario:1", "ad_first"), ("scenario:1", "ad_second")}


def test_formal_but_unselected_new_dimension_nulls_are_autofilled() -> None:
    formal_definitions = [*DEFINITIONS, _directional_candidate()]
    table = _table_with_null_additional()

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=["demand", "supply"],
    )

    assert plan.checks == []
    assert [row["cells"]["ad_duration"] for row in plan.request_table["rows"]] == [
        "duration_bullish",
        "duration_balanced",
        "duration_bearish",
    ]

    analysis = analyze_v4_validation_request(
        request_table=plan.request_table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=["demand", "supply"],
        autofilled_cells=plan.assignments,
    )

    assert analysis.blocking is False
    assert analysis.added_dimension_ids == ["ad_duration"]
    assert analysis.promoted_dimension_ids == []
    assert [row.change_type for row in analysis.canonical_rows] == ["AUTOFILL_ONLY"] * 3


def test_selected_but_unpopulated_formal_dimension_nulls_are_autofilled() -> None:
    formal_definitions = [*DEFINITIONS, _directional_candidate()]
    table = _table_with_null_additional()
    stored_headers = ["demand", "supply", "ad_duration"]

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=stored_headers,
    )
    analysis = analyze_v4_validation_request(
        request_table=plan.request_table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=stored_headers,
        autofilled_cells=plan.assignments,
    )

    assert plan.checks == []
    assert analysis.blocking is False
    assert analysis.added_dimension_ids == []
    assert [row.change_type for row in analysis.canonical_rows] == ["AUTOFILL_ONLY"] * 3


def test_selected_formal_dimension_nulls_restore_persisted_values() -> None:
    formal_definitions = [*DEFINITIONS, _directional_candidate()]
    persisted = deepcopy(_scenarios())
    persisted_values = ["duration_bullish", "duration_balanced", "duration_bearish"]
    for scenario, value_id in zip(persisted, persisted_values, strict=True):
        scenario["dimension_values"]["ad_duration"] = value_id
    table = _table_with_null_additional()

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=table,
        persisted_scenarios=persisted,
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=["demand", "supply", "ad_duration"],
    )
    analysis = analyze_v4_validation_request(
        request_table=plan.request_table,
        persisted_scenarios=persisted,
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=["demand", "supply", "ad_duration"],
    )

    assert plan.assignments == {}
    assert list(plan.restorations.values()) == persisted_values
    assert [row["cells"]["ad_duration"] for row in plan.request_table["rows"]] == persisted_values
    assert analysis.unchanged is True
    assert not any(check.check_id == "V4_VALUE_ENUM" for check in analysis.checks)


def test_explicit_existing_dimension_value_wins_over_persisted_restoration() -> None:
    formal_definitions = [*DEFINITIONS, _directional_candidate()]
    persisted = deepcopy(_scenarios())
    persisted_values = ["duration_bullish", "duration_balanced", "duration_bearish"]
    for scenario, value_id in zip(persisted, persisted_values, strict=True):
        scenario["dimension_values"]["ad_duration"] = value_id
    table = _table_with_null_additional()
    table["rows"][0]["cells"]["ad_duration"] = "duration_balanced"

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=table,
        persisted_scenarios=persisted,
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=["demand", "supply", "ad_duration"],
    )

    assert plan.request_table["rows"][0]["cells"]["ad_duration"] == "duration_balanced"
    assert ("scenario:1", "ad_duration") not in plan.restorations
    assert len(plan.restorations) == 2


def test_existing_dimension_null_retry_returns_persisted_values_in_callback_table() -> None:
    formal_definitions = [*DEFINITIONS, _directional_candidate()]
    persisted = deepcopy(_scenarios())
    persisted_values = ["duration_bullish", "duration_balanced", "duration_bearish"]
    for scenario, value_id in zip(persisted, persisted_values, strict=True):
        scenario["dimension_values"]["ad_duration"] = value_id
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=101,
        operation_id="validation-op",
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            request_usr_id=101,
            dimension_selected=["demand", "supply", "ad_duration"],
            generation_strategy="multi_event_model_lever_dimensions",
            api_version="v4",
            dimension_definitions=formal_definitions,
            generation_diagnostics={},
        ),
        generation_diagnostics={},
        scenarios=[ScenarioPayload.model_validate(item) for item in persisted],
        request_table=_table_with_null_additional(),
    )

    result = asyncio.run(_run_v4_scenario_validation(state, runtime=None))
    operation_result = ValidationOperationResultPayload.model_validate(result["operation_result"])

    assert operation_result.mode == "unchanged"
    assert operation_result.validation_result.verdict == "PASS"
    assert operation_result.validation_result.reason_markdown == "변경된 내용이 없어 바로 진행할 수 있습니다."
    assert (
        sum(
            check.check_id == "V4_EXISTING_DIMENSION_VALUE_RESTORED"
            for check in operation_result.validation_result.checks
        )
        == 3
    )
    assert [row["cells"]["ad_duration"] for row in result["request_table"]["rows"]] == persisted_values


def test_original_dimension_null_is_not_restored_and_remains_blocking() -> None:
    table = _table()
    table["rows"][0]["cells"]["demand"] = None

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics={},
        stored_header_order=["demand", "supply"],
    )
    analysis = analyze_v4_validation_request(
        request_table=plan.request_table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics={},
        stored_header_order=["demand", "supply"],
    )

    assert plan.restorations == {}
    assert plan.request_table["rows"][0]["cells"]["demand"] is None
    assert any(check.check_id == "V4_VALUE_ENUM" and check.blocking for check in analysis.checks)


def test_additional_dimension_stored_value_is_reselected_when_pressure_direction_changed() -> None:
    formal_definitions = [*DEFINITIONS, _directional_candidate()]
    persisted = deepcopy(_scenarios())
    for scenario in persisted:
        scenario["dimension_values"]["ad_duration"] = "duration_balanced"

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=persisted,
        dimension_definitions=formal_definitions,
        generation_diagnostics={},
        stored_header_order=["demand", "supply", "ad_duration"],
    )

    assert plan.request_table["rows"][0]["cells"]["ad_duration"] == "duration_bullish"
    assert plan.assignments[("scenario:1", "ad_duration")] == "duration_bullish"
    assert ("scenario:1", "ad_duration") not in plan.restorations


def test_reason_uses_major_table_changes_instead_of_generated_storage_fields() -> None:
    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(_directional_candidate()),
        stored_header_order=["demand", "supply"],
    )
    analysis = analyze_v4_validation_request(
        request_table=plan.request_table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(_directional_candidate()),
        stored_header_order=["demand", "supply"],
        autofilled_cells=plan.assignments,
    )

    reason = render_reason_markdown([], analysis=analysis)

    assert reason == "[주요 변경] 1개의 분기 추가"
    assert "저장 필드" not in reason


def test_value_enum_reason_uses_scenario_and_dimension_labels_instead_of_ids() -> None:
    table = _table()
    table["rows"][0]["cells"]["demand"] = None
    analysis = _analyze(table)

    reason = render_reason_markdown(analysis.checks, analysis=analysis)

    assert "'상방' 시나리오" in reason
    assert "수요: 값 없음" in reason
    assert "scenario:1" not in reason
    assert "demand=None" not in reason


def test_ambiguous_same_direction_candidates_are_restricted_and_fail_closed() -> None:
    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(_directional_candidate(duplicate_bullish=True)),
        stored_header_order=["demand", "supply"],
    )

    assert [(request.client_row_key, request.dimension_id) for request in plan.requests] == [
        ("scenario:1", "ad_duration")
    ]
    assert {value["value_id"] for value in plan.requests[0].allowed_values} == {
        "duration_bullish",
        "duration_bullish_alt",
    }
    with pytest.raises(ValueError, match="outside allowed values"):
        apply_v4_additional_dimension_autofill_selections(
            plan,
            {("scenario:1", "ad_duration"): "duration_bearish"},
        )
    with pytest.raises(ValueError, match="key mismatch"):
        apply_v4_additional_dimension_autofill_selections(plan, {})


@pytest.mark.parametrize("value_id", ["duration_bearish", None])
def test_constrained_autofill_llm_rejects_out_of_range_or_missing_response(value_id: str | None) -> None:
    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(_directional_candidate(duplicate_bullish=True)),
        stored_header_order=["demand", "supply"],
    )
    items = (
        [
            V4AdditionalDimensionValueSelection(
                client_row_key="scenario:1",
                dimension_id="ad_duration",
                value_id=value_id,
            )
        ]
        if value_id is not None
        else []
    )
    invocation = SimpleNamespace(result=V4AdditionalDimensionValueSelectionOutput(items=items))
    invoke = AsyncMock(return_value=invocation)

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.config": SimpleNamespace(
                    get_settings=lambda: SimpleNamespace(
                        llm_stream_enabled=False,
                        llm_reasoning_effort=None,
                    )
                ),
                "apps.connectors.llm.llm_client": SimpleNamespace(
                    invoke_llm_structured_output=invoke,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes._v4_autofill_selection_span",
            return_value=nullcontext(None),
        ),
        pytest.raises(MIBaseError) as error,
    ):
        asyncio.run(
            _invoke_v4_autofill_selections(
                requests=plan.requests,
                events=[],
                generation_diagnostics={},
                trace_context=None,
            )
        )

    assert error.value.error_code is ErrorCode.LLM_INVALID_RESPONSE_ERROR


def test_autofill_value_selection_records_allowed_scope_mlflow_span() -> None:
    captured: dict[str, object] = {}

    class FakeSpan:
        pass

    class FakeManager:
        def __enter__(self) -> FakeSpan:
            return FakeSpan()

        def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
            return None

    def start_span(**kwargs: object) -> FakeManager:
        captured.update(kwargs)
        return FakeManager()

    settings_module = ModuleType("apps.common.configs.config")
    settings_module.get_settings = Mock(  # type: ignore[attr-defined]
        return_value=SimpleNamespace(is_mlflow_tracing_enabled=lambda **_kwargs: True),
    )
    mlflow_module = ModuleType("mlflow")
    mlflow_module.start_span = start_span  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.config": settings_module, "mlflow": mlflow_module},
        ),
        _v4_autofill_selection_span(request_count=2) as span,
    ):
        assert isinstance(span, FakeSpan)

    assert captured == {
        "name": "v4_additional_dimension_value_selection",
        "span_type": "CHAIN",
        "attributes": {"request_count": 2, "selection_scope": "allowed_values_only"},
    }


def test_new_row_autofill_direction_is_inferred_from_existing_dimension_values() -> None:
    table = _table_with_null_additional()
    table["rows"].append(
        {
            "scenario_id": None,
            "display_order": 4,
            "title": "신규 상방",
            "cells": {"demand": "demand_high", "supply": "supply_low", "ad_duration": None},
        }
    )
    plan = build_v4_additional_dimension_autofill_plan(
        request_table=table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(_directional_candidate()),
        stored_header_order=["demand", "supply"],
    )

    assert plan.request_table["rows"][3]["cells"]["ad_duration"] == "duration_bullish"


def test_new_rows_with_duplicate_display_order_use_distinct_row_index_keys_and_review_ids() -> None:
    scenarios = _scenarios()[:2]
    table = _table()
    table["rows"] = table["rows"][:2]
    table["rows"].extend(
        [
            {
                "scenario_id": None,
                "display_order": 9,
                "title": "신규 하방",
                "cells": {"demand": "demand_low", "supply": "supply_high"},
            },
            {
                "scenario_id": None,
                "display_order": 9,
                "title": "신규 균형",
                "cells": {"demand": "demand_low", "supply": "supply_low"},
            },
        ]
    )

    analysis = analyze_v4_validation_request(
        request_table=table,
        persisted_scenarios=scenarios,
        dimension_definitions=DEFINITIONS,
        generation_diagnostics={},
        stored_header_order=["demand", "supply"],
    )

    new_rows = [row for row in analysis.canonical_rows if row.scenario_id is None]
    assert [row.client_row_key for row in new_rows] == ["new:3", "new:4"]
    assert [row.review_scenario_id() for row in new_rows] == [-3, -4]
    assert [row.display_order for row in new_rows] == [9, 9]


def test_duplicate_display_order_new_rows_preserve_generated_fields_and_change_set_keys() -> None:
    scenarios = _scenarios()[:2]
    table = _table()
    table["rows"] = table["rows"][:2]
    table["rows"].extend(
        [
            {
                "scenario_id": None,
                "display_order": 9,
                "title": "신규 하방",
                "cells": {"demand": "demand_low", "supply": "supply_high"},
            },
            {
                "scenario_id": None,
                "display_order": 9,
                "title": "신규 균형",
                "cells": {"demand": "demand_low", "supply": "supply_low"},
            },
        ]
    )
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=101,
        operation_id="validation-op",
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            request_usr_id=101,
            dimension_selected=["demand", "supply"],
            generation_strategy="multi_event_model_lever_dimensions",
            api_version="v4",
            dimension_definitions=DEFINITIONS,
        ),
        scenarios=[ScenarioPayload.model_validate(item) for item in scenarios],
        request_table=table,
    )
    report = ReviewReport(
        verdict="PASS",
        is_valid=True,
        reason="통과",
        summary={"PASS": 1, "WARN": 0, "FAIL": 0, "INFO": 0},
        checks=[],
    )
    review_subgraph = SimpleNamespace(ainvoke=AsyncMock(return_value=ScenarioReviewState(report=report)))
    generated = V4ValidationGeneratedScenariosOutput(
        items=[
            V4ValidationGeneratedScenario(
                client_row_key="new:3",
                narrative="신규 하방 narrative",
                probability_score=10,
                pressure_band="strong_bearish",
                pressure_rationale="수요 약세와 공급 우위",
                related_markets=[],
            ),
            V4ValidationGeneratedScenario(
                client_row_key="new:4",
                narrative="신규 균형 narrative",
                probability_score=10,
                pressure_band="balanced",
                pressure_rationale="수요와 공급 기여 상쇄",
                related_markets=[],
            ),
        ]
    )

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes.get_scenario_review_subgraph",
            return_value=review_subgraph,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes._invoke_v4_generated_fields",
            new=AsyncMock(return_value=generated),
        ),
    ):
        result = asyncio.run(_run_v4_scenario_validation(state, runtime=None))

    review_state = review_subgraph.ainvoke.await_args.args[0]
    operation_result = ValidationOperationResultPayload.model_validate(result["operation_result"])
    change_set = operation_result.scenario_change_set
    assert review_state.review_scenario_ids == [-3, -4]
    assert change_set is not None
    assert [item.client_row_key for item in change_set.upserts if item.scenario_id is None] == ["new:3", "new:4"]
    assert [item.client_row_key for item in operation_result.validation_result.generated_details] == [
        "new:3",
        "new:4",
    ]


def test_directional_autofill_falls_back_to_balanced_then_opposite() -> None:
    neutral_only = _directional_candidate()
    neutral_only["values"] = [neutral_only["values"][1], neutral_only["values"][0]]
    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(neutral_only),
        stored_header_order=["demand", "supply"],
    )
    assert plan.request_table["rows"][0]["cells"]["ad_duration"] == "duration_balanced"

    opposite_only = _directional_candidate()
    opposite_only["values"] = [opposite_only["values"][0]]
    fallback = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(opposite_only),
        stored_header_order=["demand", "supply"],
    )
    assert [row["cells"]["ad_duration"] for row in fallback.request_table["rows"]] == [
        "duration_bearish",
        "duration_bearish",
        "duration_bearish",
    ]
    assert fallback.checks == []


def test_bearish_scenario_uses_bullish_only_legacy_candidate_as_opposite_fallback() -> None:
    bullish_only = _directional_candidate()
    bullish_only["values"] = [bullish_only["values"][2]]

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(bullish_only),
        stored_header_order=["demand", "supply"],
    )

    assert plan.request_table["rows"][2]["cells"]["ad_duration"] == "duration_bullish"
    assert plan.checks == []


def test_opposite_fallback_with_multiple_values_restricts_constrained_llm_scope() -> None:
    bearish_only = _directional_candidate()
    bearish_alternative = deepcopy(bearish_only["values"][0])
    bearish_alternative.update(
        {
            "value_id": "duration_bearish_alt",
            "label": "즉시 종료",
            "assumption_rationale": "충격이 즉시 해소되는 가정",
        }
    )
    bearish_only["values"] = [bearish_only["values"][0], bearish_alternative]

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=_table_with_null_additional(),
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=_additional_diagnostics(bearish_only),
        stored_header_order=["demand", "supply"],
    )

    bullish_request = next(item for item in plan.requests if item.client_row_key == "scenario:1")
    assert bullish_request.target_direction == "bearish"
    assert {value["value_id"] for value in bullish_request.allowed_values} == {
        "duration_bearish",
        "duration_bearish_alt",
    }


def test_group_454_shape_fills_all_four_null_cells_with_single_direction_legacy_candidate() -> None:
    bullish_only = _directional_candidate()
    bullish_only["values"] = [bullish_only["values"][2]]
    persisted = [
        {
            "scenario_id": index,
            "title": f"Scenario {index}",
            "global_pressure_band": pressure_band,
            "dimension_values": {},
        }
        for index, pressure_band in enumerate(
            ("strong_bullish", "bullish", "bearish", "strong_bearish"),
            start=1,
        )
    ]
    request_table = {
        "headers": [{"key": "ad_duration", "label": "지속 기간", "display_order": 1}],
        "rows": [
            {
                "scenario_id": scenario["scenario_id"],
                "display_order": index,
                "title": scenario["title"],
                "cells": {"ad_duration": None},
            }
            for index, scenario in enumerate(persisted, start=1)
        ],
    }

    plan = build_v4_additional_dimension_autofill_plan(
        request_table=request_table,
        persisted_scenarios=persisted,
        dimension_definitions=[],
        generation_diagnostics=_additional_diagnostics(bullish_only),
        stored_header_order=[],
    )

    assert [row["cells"]["ad_duration"] for row in plan.request_table["rows"]] == ["duration_bullish"] * 4
    assert plan.requests == []
    assert plan.checks == []


def test_probability_normalization_is_integer_and_exactly_one_hundred() -> None:
    assert normalize_v4_probability_scores([30, 25, 20]) == [40, 33, 27]
    assert sum(normalize_v4_probability_scores([0, 0, 0])) == 100


def test_pressure_aggregate_order_and_strong_sign_are_blocking() -> None:
    analysis = _analyze(_table())
    checks = validate_v4_pressure_aggregate(
        rows=analysis.canonical_rows,
        dimension_definitions=DEFINITIONS,
        pressure_bands={
            "scenario:1": "strong_bearish",
            "scenario:2": "balanced",
            "scenario:3": "strong_bullish",
        },
    )

    assert {check.check_id for check in checks} == {
        "V4_PRESSURE_EXTREME_SIGN",
        "V4_PRESSURE_AGGREGATE_ORDER",
    }
    assert all(check.blocking for check in checks)


def test_scenario_fingerprint_ignores_workflow_status_but_detects_content_changes() -> None:
    scenarios = _scenarios()
    original = scenario_fingerprint(scenarios)
    status_changed = deepcopy(scenarios)
    status_changed[0]["status"] = "created"
    title_changed = deepcopy(scenarios)
    title_changed[0]["title"] = "외부 수정"

    assert scenario_fingerprint(status_changed) == original
    assert scenario_fingerprint(title_changed) != original


def test_changed_validation_refreshes_decimals_before_signpost_stale_check() -> None:
    analysis = _analyze(_table())
    result_payload = ValidationOperationResultPayload(
        mode="changed",
        base_scenario_fingerprint=analysis.base_scenario_fingerprint,
        dimension_definition_fingerprint=analysis.dimension_definition_fingerprint,
        validation_result=ValidationResultPayload(
            verdict="PASS",
            is_valid=True,
            can_proceed=True,
            reason_markdown="변경 통과",
        ),
        scenario_change_set=ValidationScenarioChangeSetPayload(
            upserts=[
                ValidationScenarioUpsertPayload(
                    scenario_id=1,
                    client_row_key="scenario:1",
                    change_type="TITLE_CHANGED",
                    display_order=1,
                    title="상방 수정",
                    dimension_values={"demand": "demand_high", "supply": "supply_low"},
                    generated_fields=ValidationGeneratedFieldsPayload(
                        narrative="상방 수정 narrative",
                        probability_score=23.0,
                        probability_delta=0,
                        pressure_band="strong_bullish",
                        pressure_rationale="상방 수정 pressure",
                        related_markets=[],
                    ),
                ),
            ],
        ),
    )
    group = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=101,
        stage="scenario_created",
        status="creating",
        api_version="v4",
        dimension_selected=["demand", "supply"],
        dimension_definitions=deepcopy(DEFINITIONS),
    )
    scenarios = [SimpleNamespace(**deepcopy(item)) for item in _scenarios()]
    validation_operation = SimpleNamespace(
        operation_id="validation-op",
        operation_type="validation",
        status="running",
        result_payload=None,
    )
    signpost_operation = SimpleNamespace(result_payload=None)
    session = Mock()
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.side_effect = [scenarios, scenarios]

    def model_to_dict(target: SimpleNamespace) -> dict[str, object]:
        return {
            key: getattr(target, key)
            for key in (
                "scenario_id",
                "scenario_group_id",
                "display_order",
                "title",
                "narrative",
                "dimension_values",
                "probability_score",
                "probability_delta",
                "baseline_yn",
                "global_pressure_band",
                "scenario_role",
                "global_pressure_rationale",
                "related_markets",
                "status",
            )
        }

    def update_model(target: SimpleNamespace, payload: dict[str, object]) -> None:
        for key, value in payload.items():
            setattr(target, key, value)

    def refresh_decimal_columns(target: SimpleNamespace) -> None:
        target.probability_score = Decimal(str(target.probability_score)).quantize(Decimal("0.00"))
        target.probability_delta = Decimal(str(target.probability_delta)).quantize(Decimal("0.00"))

    scenario_repository.model_to_dict.side_effect = model_to_dict
    scenario_repository.update_from_payload.side_effect = update_model
    session.refresh.side_effect = refresh_decimal_columns
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "creating",
        "stage": "scenario_validated",
    }
    group_repository.update_group.side_effect = update_model
    signpost_repository = Mock()
    operation_repository = Mock()
    operation_repository.fetch_by_id.return_value = validation_operation

    def complete_event(target: SimpleNamespace, **kwargs: object) -> None:
        target.status = kwargs["status"]

    operation_repository.append_event.side_effect = complete_event

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.SignpostRepository",
            return_value=signpost_repository,
        ),
    ):
        ScenarioGroupOperationService().complete_validation(
            scenario_group_id=10,
            operation_id="validation-op",
            result_payload=result_payload,
            user_id=101,
        )

    stored = ValidationOperationResultPayload.model_validate(validation_operation.result_payload)
    assert stored.application is not None
    assert scenarios[0].probability_score == Decimal("23.00")
    assert scenarios[0].probability_delta == Decimal("0.00")
    assert stored.application.applied_scenario_fingerprint == scenario_fingerprint(
        [model_to_dict(item) for item in scenarios]
    )
    assert session.method_calls[:4] == [
        call.flush(),
        *(call.refresh(scenario) for scenario in scenarios),
    ]

    scenario_repository.fetch_models_by_group_id.side_effect = None
    scenario_repository.fetch_models_by_group_id.return_value = scenarios
    operation_repository.fetch_active.return_value = None
    operation_repository.fetch_latest_by_type.return_value = validation_operation
    operation_repository.fetch_by_id.return_value = signpost_operation

    def accept_change_set() -> dict[str, object]:
        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                        get_sync_session=lambda: session,
                    ),
                },
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
                return_value=scenario_repository,
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
                return_value=group_repository,
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
                return_value=signpost_repository,
            ),
            patch(
                "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
                return_value=operation_repository,
            ),
            patch.object(ScenarioGroupOperationService, "create_accepted_in_session", return_value=Mock()),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.new_operation_id",
                return_value="signpost-op",
            ),
        ):
            return ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    accepted = accept_change_set()

    assert accepted["validation_operation_id"] == "validation-op"
    assert signpost_operation.result_payload["validationOperationId"] == "validation-op"

    scenarios[0].title = "validation 이후 외부 변경"
    group.stage = "scenario_validated"
    with pytest.raises(MIBaseError) as error:
        accept_change_set()

    assert error.value.error_code is ErrorCode.SCENARIO_VALIDATION_STALE


def test_v4_signpost_request_accepts_user_id_without_table() -> None:
    request = CreateSignpostsIn.model_validate({"userId": 101})

    assert request.user_id == 101
    assert request.table is None


def test_v4_validation_callback_table_preserves_value_ids() -> None:
    source = _table()
    projected = _validation_table_for_output(
        source,
        {
            "generation_strategy": "multi_event_model_lever_dimensions",
            "dimension_definitions": DEFINITIONS,
        },
    )

    assert projected is not None
    assert projected["rows"][0]["cells"] == {"demand": "demand_high", "supply": "supply_low"}
    assert source["rows"][0]["cells"] == {"demand": "demand_high", "supply": "supply_low"}


def test_v4_validation_callback_accepts_nested_scenario_table_state() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        generation_strategy="multi_event_model_lever_dimensions",
        dimension_definitions=DEFINITIONS,
    )
    request_table = ScenarioTableState.model_validate(_table())

    output = _bg_to_output(
        {
            "scenario_group_id": 10,
            "scenario_group": group,
            "request_table": request_table,
            "operation_result": {
                "validation_result": {
                    "verdict": "PASS",
                    "is_valid": True,
                    "can_proceed": True,
                },
            },
        },
    )

    assert output.table is not None
    assert output.table.rows[0].cells == {"demand": "demand_high", "supply": "supply_low"}


def test_public_operation_payload_does_not_expose_internal_result_payload() -> None:
    operation = SimpleNamespace(
        operation_id="01JVALIDATION0000000000000",
        scenario_group_id=10,
        operation_type="validation",
        engine_version="v4",
        source="api",
        status="succeeded",
        current_phase="validation",
        retry_summary={},
        presentation_snapshot={},
        result_payload={"scenarioChangeSet": {"secret": True}},
        snapshot_revision=0,
        latest_sequence=1,
        last_error=None,
        mlflow_trace_id=None,
        started_at=None,
        completed_at=None,
        heartbeat_at=None,
        crt_dtm=datetime(2026, 8, 13, tzinfo=UTC),
        mod_dtm=datetime(2026, 8, 13, tzinfo=UTC),
    )

    public = ScenarioGroupOperationService.operation_payload_from_model(operation)

    assert "result_payload" not in public.model_dump()
    assert "resultPayload" not in public.model_dump(by_alias=True)


def _acceptance_fixture(
    *,
    base_fingerprint: str | None = None,
) -> tuple[Mock, Mock, Mock, Mock, Mock, SimpleNamespace]:
    analysis = _analyze(_table())
    result_payload = ValidationOperationResultPayload(
        mode="unchanged",
        base_scenario_fingerprint=base_fingerprint or analysis.base_scenario_fingerprint,
        dimension_definition_fingerprint=analysis.dimension_definition_fingerprint,
        validation_result=ValidationResultPayload(
            verdict="PASS",
            is_valid=True,
            can_proceed=True,
            review_skipped=True,
            reason_markdown="변경 없음",
        ),
        scenario_change_set=None,
    )
    group = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=101,
        stage="scenario_validated",
        api_version="v4",
        dimension_definitions=deepcopy(DEFINITIONS),
    )
    scenario_models = [SimpleNamespace(scenario_id=item["scenario_id"]) for item in _scenarios()]
    scenario_by_id = {int(item["scenario_id"]): item for item in _scenarios()}
    validation_operation = SimpleNamespace(
        operation_id="validation-op",
        operation_type="validation",
        status="succeeded",
        result_payload=result_payload.model_dump(mode="json", by_alias=True),
    )
    signpost_operation = SimpleNamespace(result_payload=None)
    session = Mock()
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.return_value = scenario_models
    scenario_repository.model_to_dict.side_effect = lambda model: scenario_by_id[int(model.scenario_id)]
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "creating",
        "stage": "scenario_validated",
    }
    signpost_repository = Mock()
    operation_repository = Mock()
    operation_repository.fetch_active.return_value = None
    operation_repository.fetch_latest_by_type.return_value = validation_operation
    operation_repository.fetch_by_id.return_value = signpost_operation
    return (
        session,
        scenario_repository,
        group_repository,
        signpost_repository,
        operation_repository,
        signpost_operation,
    )


def test_signpost_accepts_unchanged_validation_without_scenario_write() -> None:
    fixture = _acceptance_fixture()
    session, scenarios, groups, signposts, operations, signpost_operation = fixture
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
            return_value=signposts,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operations,
        ),
        patch.object(
            ScenarioGroupOperationService,
            "create_accepted_in_session",
            return_value=Mock(),
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.new_operation_id",
            return_value="signpost-op",
        ),
    ):
        accepted = ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    assert accepted["validation_operation_id"] == "validation-op"
    assert accepted["signpost_target_scenario_ids"] == []
    assert signpost_operation.result_payload["validationOperationId"] == "validation-op"
    scenarios.insert_scenario.assert_not_called()
    scenarios.update_from_payload.assert_not_called()
    scenarios.soft_delete_by_ids.assert_not_called()
    session.commit.assert_called_once()


def test_direct_confirmation_accepts_validation_without_creating_signpost_operation() -> None:
    fixture = _acceptance_fixture()
    session, scenarios, groups, signposts, operations, _signpost_operation = fixture
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
            return_value=signposts,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operations,
        ),
        patch.object(
            ScenarioGroupOperationService,
            "create_accepted_in_session",
            return_value=Mock(),
        ) as create_operation,
    ):
        accepted = ScenarioService().accept_validation_change_set(
            scenario_group_id=10,
            user_id=101,
            create_signpost_operation=False,
        )

    assert accepted["operation_id"] is None
    assert accepted["validation_operation_id"] == "validation-op"
    create_operation.assert_not_called()
    operations.fetch_by_id.assert_not_called()
    session.commit.assert_called_once_with()


def test_signpost_rejects_stale_validation_and_resets_stage() -> None:
    fixture = _acceptance_fixture(base_fingerprint="stale")
    session, scenarios, groups, signposts, operations, _signpost_operation = fixture
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
            return_value=signposts,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operations,
        ),
        pytest.raises(MIBaseError) as error,
    ):
        ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    assert error.value.error_code is ErrorCode.SCENARIO_VALIDATION_STALE
    groups.update_group.assert_called_once()
    assert groups.update_group.call_args.args[1]["stage"] == "scenario_created"
    scenarios.insert_scenario.assert_not_called()
    session.commit.assert_called_once()


def test_signpost_applies_changed_validation_and_records_application() -> None:
    analysis = _analyze(_table())
    change_set = ValidationScenarioChangeSetPayload(
        upserts=[
            ValidationScenarioUpsertPayload(
                scenario_id=1,
                client_row_key="scenario:1",
                change_type="TITLE_CHANGED",
                display_order=1,
                title="상방 수정",
                dimension_values={"demand": "demand_high", "supply": "supply_low"},
                generated_fields=ValidationGeneratedFieldsPayload(
                    narrative="기존 상방 narrative",
                    probability_score=30,
                    probability_delta=0,
                    pressure_band="strong_bullish",
                    pressure_rationale="기존 상방 pressure",
                    related_markets=[],
                ),
            ),
            ValidationScenarioUpsertPayload(
                scenario_id=None,
                client_row_key="new:4",
                change_type="NEW",
                display_order=4,
                title="신규 약상방",
                dimension_values={"demand": "demand_low", "supply": "supply_low"},
                generated_fields=ValidationGeneratedFieldsPayload(
                    narrative="신규 narrative",
                    probability_score=10,
                    probability_delta=0,
                    pressure_band="bullish",
                    pressure_rationale="낮은 공급 우세",
                    related_markets=[],
                ),
            ),
            ValidationScenarioUpsertPayload(
                scenario_id=None,
                client_row_key="new:5",
                change_type="NEW",
                display_order=4,
                title="신규 하방",
                dimension_values={"demand": "demand_low", "supply": "supply_high"},
                generated_fields=ValidationGeneratedFieldsPayload(
                    narrative="신규 하방 narrative",
                    probability_score=10,
                    probability_delta=0,
                    pressure_band="strong_bearish",
                    pressure_rationale="낮은 수요 우세",
                    related_markets=[],
                ),
            ),
        ],
        delete_scenario_ids=[3],
    )
    result_payload = ValidationOperationResultPayload(
        mode="changed",
        base_scenario_fingerprint=analysis.base_scenario_fingerprint,
        dimension_definition_fingerprint=analysis.dimension_definition_fingerprint,
        validation_result=ValidationResultPayload(
            verdict="PASS",
            is_valid=True,
            can_proceed=True,
            reason_markdown="변경 통과",
        ),
        scenario_change_set=change_set,
    )
    group = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=101,
        stage="scenario_validated",
        api_version="v4",
        dimension_definitions=deepcopy(DEFINITIONS),
    )

    def model(item: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(**deepcopy(item))

    current_models = [model(item) for item in _scenarios()]
    new_models = [
        model(
            {
                "scenario_id": scenario_id,
                "scenario_group_id": 10,
                "display_order": 4,
                "title": title,
                "narrative": narrative,
                "dimension_values": dimension_values,
                "probability_score": 10,
                "probability_delta": 0,
                "baseline_yn": "N",
                "global_pressure_band": pressure_band,
                "scenario_role": None,
                "global_pressure_rationale": pressure_rationale,
                "related_markets": [],
                "status": "creating",
            }
        )
        for scenario_id, title, narrative, dimension_values, pressure_band, pressure_rationale in (
            (
                4,
                "신규 약상방",
                "신규 narrative",
                {"demand": "demand_low", "supply": "supply_low"},
                "bullish",
                "낮은 공급 우세",
            ),
            (
                5,
                "신규 하방",
                "신규 하방 narrative",
                {"demand": "demand_low", "supply": "supply_high"},
                "strong_bearish",
                "낮은 수요 우세",
            ),
        )
    ]
    active_models = [current_models[0], current_models[1], *new_models]
    session = Mock()
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.side_effect = [current_models, active_models]
    scenario_repository.insert_scenario.side_effect = [4, 5]

    def update_from_payload(target: SimpleNamespace, payload: dict[str, object]) -> None:
        for key, value in payload.items():
            setattr(target, key, value)

    scenario_repository.update_from_payload.side_effect = update_from_payload
    scenario_repository.model_to_dict.side_effect = lambda target: {
        key: getattr(target, key)
        for key in (
            "scenario_id",
            "scenario_group_id",
            "display_order",
            "title",
            "narrative",
            "dimension_values",
            "probability_score",
            "probability_delta",
            "baseline_yn",
            "global_pressure_band",
            "scenario_role",
            "global_pressure_rationale",
            "related_markets",
            "status",
        )
    }
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "creating",
        "stage": "scenario_validated",
    }
    signpost_repository = Mock()
    validation_operation = SimpleNamespace(
        operation_id="validation-op",
        status="succeeded",
        result_payload=result_payload.model_dump(mode="json", by_alias=True),
    )
    signpost_operation = SimpleNamespace(result_payload=None)
    operation_repository = Mock()
    operation_repository.fetch_active.return_value = None
    operation_repository.fetch_latest_by_type.return_value = validation_operation
    operation_repository.fetch_by_id.return_value = signpost_operation

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
            return_value=signpost_repository,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch.object(
            ScenarioGroupOperationService,
            "create_accepted_in_session",
            return_value=Mock(),
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.new_operation_id",
            return_value="signpost-op",
        ),
    ):
        accepted = ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    assert accepted["signpost_target_scenario_ids"] == [1, 4, 5]
    scenario_repository.update_from_payload.assert_called_once()
    assert scenario_repository.insert_scenario.call_count == 2
    scenario_repository.soft_delete_by_ids.assert_called_once_with([3], user_id=101)
    signpost_repository.soft_delete_by_scenario_ids.assert_called_once_with([1, 3], user_id=101)
    stored = ValidationOperationResultPayload.model_validate(validation_operation.result_payload)
    assert stored.application is not None
    assert stored.application.new_scenario_id_map == {"new:4": 4, "new:5": 5}
    assert signpost_operation.result_payload["validationOperationId"] == "validation-op"


def test_v4_role_recalculation_keeps_floor_and_ceiling_distinct_on_ties() -> None:
    scenarios = [
        SimpleNamespace(
            scenario_id=index,
            display_order=index,
            probability_score=30 if index == 2 else 20,
            dimension_values={"demand": "demand_low", "supply": "supply_high"},
            global_pressure_band="balanced",
            baseline_yn="N",
            scenario_role=None,
            mod_usr_logn_id=None,
        )
        for index in range(1, 4)
    ]
    balanced_definitions = deepcopy(DEFINITIONS)
    for definition in balanced_definitions:
        for value in definition["values"]:
            value["pressure_contribution"] = "balanced"

    ScenarioService()._apply_v4_baseline_and_roles(scenarios, balanced_definitions, user_id=101)

    assert scenarios[0].scenario_role == "floor"
    assert scenarios[-1].scenario_role == "ceiling"
    assert scenarios[1].baseline_yn == "Y"


@pytest.mark.parametrize(
    ("mutation", "check_id"),
    [
        (lambda table: table["rows"][0]["cells"].update({"demand": "outside"}), "V4_VALUE_ENUM"),
        (lambda table: table["rows"][0]["cells"].update({"demand": None}), "V4_VALUE_ENUM"),
        (lambda table: table["rows"][0]["cells"].pop("supply"), "V4_INPUT_CELLS"),
        (lambda table: table["rows"][1].update({"title": "상 방!!"}), "V4_TITLE_DUPLICATE"),
        (
            lambda table: table["rows"][1].update({"cells": deepcopy(table["rows"][0]["cells"])}),
            "V4_COMBINATION_DUPLICATE",
        ),
    ],
)
def test_deterministic_v4_input_checks_block(
    mutation: Callable[[dict[str, object]], object],
    check_id: str,
) -> None:
    table = _table()
    mutation(table)

    analysis = _analyze(table)

    assert analysis.blocking is True
    assert any(check.check_id == check_id and check.blocking for check in analysis.checks)


@pytest.mark.parametrize(("row_count", "blocking"), [(1, True), (2, False), (7, False), (8, True)])
def test_v4_scenario_count_accepts_two_through_seven(row_count: int, blocking: bool) -> None:
    base_rows = _table()["rows"]
    rows = []
    for index in range(row_count):
        source = deepcopy(base_rows[index % len(base_rows)])
        source["scenarioId"] = None
        source["displayOrder"] = index + 1
        source["title"] = f"시나리오 {index + 1}"
        source["cells"] = {
            "demand": f"demand_{'high' if index % 2 == 0 else 'low'}",
            "supply": f"supply_{'low' if index // 2 % 2 == 0 else 'high'}",
        }
        rows.append(source)
    analysis = _analyze({"headers": _table()["headers"], "rows": rows})

    count_checks = [check for check in analysis.checks if check.check_id == "V4_SCENARIO_COUNT"]
    assert bool(count_checks) is blocking


def test_low_probability_excluded_combination_warns_but_can_proceed() -> None:
    table = _table()
    table["rows"][0]["title"] = "상방 수정"
    diagnostics = {
        "excludedCandidates": [
            {
                "reasonCode": "LOW_PROBABILITY",
                "reason": "관측 사실 대비 가능성이 낮습니다.",
                "dimensionValues": {"demand": "demand_high", "supply": "supply_low"},
            }
        ]
    }

    analysis = _analyze(table, diagnostics)

    warning = next(check for check in analysis.checks if check.check_id == "V4_LOW_PROBABILITY_REINTRODUCED")
    assert warning.status == "WARN"
    assert warning.blocking is False


def test_changed_v4_result_stores_only_changed_full_upsert() -> None:
    table = _table()
    table["rows"][0]["title"] = "상방 제목 수정"
    table["rows"][1]["cells"] = {"demand": "demand_low", "supply": "supply_low"}
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=101,
        operation_id="validation-op",
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            request_usr_id=101,
            dimension_selected=["demand", "supply"],
            generation_strategy="multi_event_model_lever_dimensions",
            api_version="v4",
            dimension_definitions=DEFINITIONS,
        ),
        scenarios=[ScenarioPayload.model_validate(item) for item in _scenarios()],
        dimension_template=[
            ScenarioTemplateDimension(
                dimension_id=definition["dimension_id"],
                label_ko=definition["label"],
                description=definition["label"],
                enum=[
                    ScenarioTemplateEnum(id=value["value_id"], label=value["label"]) for value in definition["values"]
                ],
            )
            for definition in DEFINITIONS
        ],
        request_table=table,
    )
    report = ReviewReport(
        verdict="PASS",
        is_valid=True,
        reason="통과",
        summary={"PASS": 1, "WARN": 0, "FAIL": 0, "INFO": 0},
        checks=[],
    )
    review_subgraph = SimpleNamespace(
        ainvoke=AsyncMock(return_value=ScenarioReviewState(report=report)),
    )
    generated = V4ValidationGeneratedScenariosOutput(
        items=[
            V4ValidationGeneratedScenario(
                client_row_key="scenario:2",
                narrative="변경 조합 narrative",
                probability_score=25,
                pressure_band="bearish",
                pressure_rationale="공급과 수요 조합의 하방 압력",
                related_markets=[],
            )
        ]
    )

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes.get_scenario_review_subgraph",
            return_value=review_subgraph,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes._invoke_v4_generated_fields",
            new=AsyncMock(return_value=generated),
        ),
    ):
        result = asyncio.run(_run_v4_scenario_validation(state, runtime=None))

    operation_result = ValidationOperationResultPayload.model_validate(result["operation_result"])
    change_set = operation_result.scenario_change_set
    assert operation_result.mode == "changed"
    assert operation_result.validation_result.can_proceed is True
    assert change_set is not None
    assert [upsert.scenario_id for upsert in change_set.upserts] == [1, 2, 3]
    assert sum(upsert.generated_fields.probability_score for upsert in change_set.upserts) == 100
    assert all(upsert.generated_fields.narrative for upsert in change_set.upserts)
    assert change_set.upserts[0].generated_fields.narrative == "상방 narrative"
    assert change_set.upserts[1].generated_fields.probability_delta == 0
    assert not hasattr(change_set.upserts[1], "lever_state")


def test_autofill_only_preserves_band_and_probability_and_returns_warning_table() -> None:
    candidate = _directional_candidate()
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=101,
        operation_id="validation-op",
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            request_usr_id=101,
            dimension_selected=["demand", "supply"],
            generation_strategy="multi_event_model_lever_dimensions",
            api_version="v4",
            dimension_definitions=DEFINITIONS,
            generation_diagnostics=_additional_diagnostics(candidate),
        ),
        generation_diagnostics=_additional_diagnostics(candidate),
        scenarios=[ScenarioPayload.model_validate(item) for item in _scenarios()],
        request_table=_table_with_null_additional(),
    )
    report = ReviewReport(
        verdict="REVIEW",
        is_valid=True,
        reason="의미 경고",
        summary={"PASS": 0, "WARN": 1, "FAIL": 0, "INFO": 0},
        checks=[
            CheckResult(
                check_id="R03",
                stage="Stage4",
                name="Compatibility",
                status="WARN",
                detail="새 분류값이 narrative와 다소 어색합니다.",
            )
        ],
    )
    review_subgraph = SimpleNamespace(ainvoke=AsyncMock(return_value=ScenarioReviewState(report=report)))
    generated = V4ValidationGeneratedScenariosOutput(
        items=[
            V4ValidationGeneratedScenario(
                client_row_key=f"scenario:{index}",
                narrative=f"{scenario['title']} + duration narrative",
                probability_score=1,
                pressure_band="balanced",
                pressure_rationale=f"{scenario['title']} + duration pressure",
                related_markets=[],
            )
            for index, scenario in enumerate(_scenarios(), start=1)
        ]
    )

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes.get_scenario_review_subgraph",
            return_value=review_subgraph,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes._invoke_v4_generated_fields",
            new=AsyncMock(return_value=generated),
        ),
    ):
        result = asyncio.run(_run_v4_scenario_validation(state, runtime=None))

    operation_result = ValidationOperationResultPayload.model_validate(result["operation_result"])
    validation = operation_result.validation_result
    assert validation.verdict == "PASS_WITH_WARNINGS"
    assert validation.is_valid is True
    assert validation.can_proceed is True
    assert operation_result.scenario_change_set is not None
    assert [item.generated_fields.probability_score for item in operation_result.scenario_change_set.upserts] == [
        30,
        50,
        20,
    ]
    assert [item.generated_fields.pressure_band for item in operation_result.scenario_change_set.upserts] == [
        "strong_bullish",
        "balanced",
        "strong_bearish",
    ]
    assert sum(check.check_id == "V4_ADDITIONAL_DIMENSION_AUTOFILL" for check in validation.checks) == 3
    assert next(check for check in validation.checks if check.check_id == "R03").blocking is False
    assert [row["cells"]["ad_duration"] for row in result["request_table"]["rows"]] == [
        "duration_bullish",
        "duration_balanced",
        "duration_bearish",
    ]


def test_unchanged_v4_skips_review_and_generation() -> None:
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=101,
        operation_id="validation-op",
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            request_usr_id=101,
            dimension_selected=["demand", "supply"],
            generation_strategy="multi_event_model_lever_dimensions",
            api_version="v4",
            dimension_definitions=DEFINITIONS,
        ),
        scenarios=[ScenarioPayload.model_validate(item) for item in _scenarios()],
        request_table=_table(labels=True),
    )

    with (
        patch("apps.agents.scenario_group_agent.flows.validate_scenarios.nodes.get_scenario_review_subgraph") as review,
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes._invoke_v4_generated_fields"
        ) as generate,
    ):
        result = asyncio.run(_run_v4_scenario_validation(state, runtime=None))

    operation_result = ValidationOperationResultPayload.model_validate(result["operation_result"])
    assert operation_result.mode == "unchanged"
    assert operation_result.scenario_change_set is None
    assert operation_result.validation_result.review_skipped is True
    review.assert_not_called()
    generate.assert_not_called()
