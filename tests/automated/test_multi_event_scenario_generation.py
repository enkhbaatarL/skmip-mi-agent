from __future__ import annotations

from pathlib import Path

# ruff: noqa: S101
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import ValidationError
import pytest

from apps.agents.scenario_group_agent.api import router as agent_router
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    MultiEventGenerationResult,
    finalize_generation_result,
)
from apps.agents.scenario_group_agent.flows.create_signposts.nodes import (
    _load_group_event_context,
    sync_scenarios_from_table,
)
from apps.agents.scenario_group_agent.flows.create_signposts.state import (
    CreateSignpostsState,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    create_mapping_proposals,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.state import (
    ValidateScenariosState,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.agents.scenario_group_agent.prompts.multi_event_scenario_generation import (
    build_multi_event_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    MULTI_EVENT_COMPAT_SYSTEM_PROMPT,
    CompatibilityItem,
)
from apps.agents.scenario_group_agent.routers.scenario_generation import router
from apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes import (
    _has_only_unusable_enum_recommendations,
    build_context,
)
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import SourceLineage
from apps.persistence.scenario_group.schema import ScenarioGroupPayload
from scripts.scenario_generation.import_template_domain_knowledge import (
    load_template_updates,
)


EVENT_IDS = [101, 202]


def _source(event_id: int, dim_key: str, value: str | None = None) -> dict[str, object]:
    return {
        "eventId": event_id,
        "eventTypeL2Id": 8 if event_id == 101 else 12,
        "dimKey": dim_key,
        "value": value,
        "sourceType": "event_fact",
        "assumptionYn": "N",
        "rationale": "현재 Event 사실을 해당 source dimension에 투영한다.",
    }


def _dimension(
    *,
    dimension_id: str,
    event_id: int,
    dim_key: str,
    display_order: int,
    source_event_ids: list[int] | None = None,
) -> dict[str, object]:
    source_event_ids = source_event_ids or [event_id]
    refs = [_source(source_id, dim_key) for source_id in source_event_ids]
    values = []
    for value_id, label, contribution in (
        ("low", "Event별 완화", "bearish"),
        ("mid", "Event 사실 기반 균형", "balanced"),
        ("high", "Event별 심화", "bullish"),
    ):
        values.append(
            {
                "valueId": value_id,
                "label": label,
                "globalPressureContribution": contribution,
                "sourceAssignments": [_source(source_id, dim_key, label) for source_id in source_event_ids],
            },
        )
    return {
        "dimensionId": dimension_id,
        "label": dimension_id,
        "description": f"{dimension_id} 설명",
        "displayOrder": display_order,
        "sourceRefs": refs,
        "values": values,
    }


def _result(
    *,
    strategy: str,
) -> MultiEventGenerationResult:
    if strategy == "multi_event_source_dimensions":
        dimensions = [
            _dimension(
                dimension_id="e101__heat",
                event_id=101,
                dim_key="heat",
                display_order=1,
            ),
            _dimension(
                dimension_id="e101__duration",
                event_id=101,
                dim_key="duration",
                display_order=2,
            ),
            _dimension(
                dimension_id="e202__inventory",
                event_id=202,
                dim_key="inventory",
                display_order=3,
            ),
            _dimension(
                dimension_id="e202__recovery",
                event_id=202,
                dim_key="recovery",
                display_order=4,
            ),
            _dimension(
                dimension_id="e202__competition",
                event_id=202,
                dim_key="competition",
                display_order=5,
            ),
        ]
    else:
        dimensions = [
            _dimension(
                dimension_id="demand_inventory_tightness",
                event_id=101,
                dim_key="tightness",
                display_order=1,
                source_event_ids=[101, 202],
            ),
            _dimension(
                dimension_id="heat_duration",
                event_id=101,
                dim_key="duration",
                display_order=2,
            ),
            _dimension(
                dimension_id="inventory_recovery",
                event_id=202,
                dim_key="recovery",
                display_order=3,
            ),
            _dimension(
                dimension_id="regional_competition",
                event_id=202,
                dim_key="competition",
                display_order=4,
            ),
        ]
    dimension_ids = [str(dimension["dimensionId"]) for dimension in dimensions]
    return MultiEventGenerationResult.model_validate(
        {
            "scenarioGroupTitle": "복수 Event 시나리오",
            "scenarioGroupDescription": "두 Event를 공동 전제로 비교한다.",
            "eventShocks": [
                {
                    "eventId": event_id,
                    "supplyDirection": "neutral",
                    "demandDirection": "increase",
                    "tradeDirection": "neutral",
                    "affectedRegions": ["아시아"],
                    "duration": "계절",
                    "intensity": "중간",
                    "recoveryOrPersistence": "점진",
                    "mitigation": "대체 조달",
                    "sourceDimensionKeys": ["heat"],
                    "generatedEventValues": {"heat": "현재 Event에 맞춘 신규 값"},
                }
                for event_id in EVENT_IDS
            ],
            "interactions": (
                [
                    {
                        "eventIds": EVENT_IDS,
                        "relation": "regional_coupling",
                        "rationale": "수요와 재고가 지역 구매 경쟁으로 연결된다.",
                    },
                ]
                if strategy == "multi_event_composite_dimensions"
                else []
            ),
            "dimensionDefinitions": dimensions,
            "scenarios": [
                {
                    "title": "상단",
                    "narrative": "공동 전제의 상승 압력이 심화된다.",
                    "dimensionValues": {key: "Event별 심화" for key in dimension_ids},
                    "globalPressureBand": "strong_bullish",
                    "probabilityScore": 20,
                    "globalPressureRationale": "공급·수요 압력이 가격을 높인다.",
                },
                {
                    "title": "혼합",
                    "narrative": "상승과 완화 요인이 함께 작용한다.",
                    "dimensionValues": {
                        key: (
                            "Event별 심화" if index == 0 else ("Event별 완화" if index == 1 else "Event 사실 기반 균형")
                        )
                        for index, key in enumerate(dimension_ids)
                    },
                    "globalPressureBand": "balanced",
                    "probabilityScore": 60,
                    "globalPressureRationale": "상승과 하락 요인이 상쇄된다.",
                    "mixedFactors": True,
                },
                {
                    "title": "하단",
                    "narrative": "완화와 대체 공급이 가격 압력을 낮춘다.",
                    "dimensionValues": {key: "Event별 완화" for key in dimension_ids},
                    "globalPressureBand": "strong_bearish",
                    "probabilityScore": 20,
                    "globalPressureRationale": "완화 경로가 우세하다.",
                },
            ],
            "excludedCandidates": [
                {
                    "globalPressureBand": "bullish",
                    "reasonCode": "NOT_INDEPENDENT",
                    "reason": "상단 후보와 독립적인 검토 가치가 부족하다.",
                },
                {
                    "globalPressureBand": "bearish",
                    "reasonCode": "LOW_PROBABILITY",
                    "reason": "Event 사실을 유지한 현실적 조합의 가능성이 낮다.",
                },
            ],
        },
    )


def test_multi_event_request_requires_two_to_five_unique_events() -> None:
    valid = MultiEventCreateScenariosIn.model_validate(
        {
            "miEventIds": [1, 2, 3, 4, 5],
            "userId": 10,
            "comparisonRunId": "compare-1",
        },
    )
    assert valid.mi_event_ids == [1, 2, 3, 4, 5]

    for event_ids in ([1], [1, 1], [1, 2, 3, 4, 5, 6]):
        with pytest.raises(ValidationError):
            MultiEventCreateScenariosIn.model_validate(
                {
                    "miEventIds": event_ids,
                    "userId": 10,
                    "comparisonRunId": "compare-1",
                },
            )


@pytest.mark.parametrize(
    "strategy",
    [
        "multi_event_source_dimensions",
        "multi_event_composite_dimensions",
    ],
)
def test_finalization_assigns_roles_and_single_highest_probability_baseline(
    strategy: str,
) -> None:
    finalized = finalize_generation_result(
        _result(strategy=strategy),
        generation_strategy=strategy,
        event_ids=EVENT_IDS,
    )

    roles = [scenario.scenario_role for scenario in finalized.scenarios]
    assert roles.count("floor") == 1
    assert roles.count("ceiling") == 1
    assert roles.count("mixed") == 1
    baselines = [scenario for scenario in finalized.scenarios if scenario.baseline_yn == "Y"]
    assert len(baselines) == 1
    assert baselines[0].global_pressure_band == "balanced"


def test_v2_requires_namespaced_source_dimensions_and_event_coverage() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                result.dimension_definitions[0].model_copy(
                    update={"dimension_id": "heat"},
                ),
                *result.dimension_definitions[1:],
            ],
        },
    )
    with pytest.raises(ValueError, match="namespaced"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v3_allows_independent_single_source_dimension_without_forced_merge() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    assert any(len(dimension.source_refs) == 1 for dimension in result.dimension_definitions)
    finalized = finalize_generation_result(
        result,
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )
    assert len(finalized.dimension_definitions) == 4


def test_v3_non_independent_interaction_requires_a_multi_source_dimension() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    single_source = first_dimension.source_refs[:1]
    broken_dimension = first_dimension.model_copy(
        update={
            "source_refs": single_source,
            "values": [
                value.model_copy(
                    update={"source_assignments": value.source_assignments[:1]},
                )
                for value in first_dimension.values
            ],
        },
    )
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                broken_dimension,
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(
        ValueError,
        match="non-independent interactions must be represented",
    ):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v2_source_refs_must_exist_in_the_event_type_templates() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    source_dimensions = {
        101: {"heat": True, "duration": True},
        202: {
            "heat": False,
            "inventory": True,
            "recovery": True,
            "competition": True,
        },
    }
    first_dimension = result.dimension_definitions[0]
    unknown_ref = first_dimension.source_refs[0].model_copy(
        update={"dim_key": "not_in_template"},
    )
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                first_dimension.model_copy(
                    update={"source_refs": [unknown_ref]},
                ),
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="sourceRef is not present"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
            source_dimensions_by_event=source_dimensions,
        )


def test_v2_preserves_source_template_label_and_description() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    source_dimensions = {
        101: {
            "heat": {
                "required": True,
                "label": "원본 폭염 강도",
                "description": "원본 폭염 강도의 의미",
            },
            "duration": False,
        },
        202: {
            "heat": False,
            "inventory": True,
            "recovery": True,
            "competition": True,
        },
    }

    with pytest.raises(ValueError, match="preserve the source template"):
        finalize_generation_result(
            result,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
            source_dimensions_by_event=source_dimensions,
        )


def test_v2_requires_all_required_dimensions_when_at_most_eight() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    source_dimensions = {
        101: {
            "heat": True,
            "duration": True,
            "missing_required": True,
        },
        202: {
            "heat": False,
            "inventory": True,
            "recovery": True,
            "competition": True,
        },
    }

    with pytest.raises(ValueError, match="must select every required"):
        finalize_generation_result(
            result,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
            source_dimensions_by_event=source_dimensions,
        )


def test_v2_documents_required_dimension_exclusions_when_more_than_eight() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    source_dimensions = {
        101: {
            "heat": True,
            "duration": True,
            "omitted_a": True,
            "omitted_b": True,
        },
        202: {
            "heat": False,
            "inventory": True,
            "recovery": True,
            "competition": True,
            "omitted_c": True,
            "omitted_d": True,
        },
    }
    excluded_dimensions = [
        {
            "eventId": event_id,
            "dimKey": dim_key,
            "reason": "LNG 가격 영향 관련성이 선택 dimension보다 낮다.",
        }
        for event_id, dim_key in (
            (101, "omitted_a"),
            (101, "omitted_b"),
            (202, "omitted_c"),
            (202, "omitted_d"),
        )
    ]
    documented = result.model_copy(
        update={"excluded_dimensions": excluded_dimensions},
    )

    finalized = finalize_generation_result(
        documented,
        generation_strategy="multi_event_source_dimensions",
        event_ids=EVENT_IDS,
        source_dimensions_by_event=source_dimensions,
    )

    assert finalized.excluded_dimensions == excluded_dimensions


def test_multi_event_dimension_requires_three_to_five_values() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                first_dimension.model_copy(
                    update={"values": first_dimension.values[:2]},
                ),
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="3 to 5 generated values"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_composite_value_projects_to_every_source_dimension() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    first_value = first_dimension.values[0]
    broken_value = first_value.model_copy(
        update={"source_assignments": first_value.source_assignments[:1]},
    )
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                first_dimension.model_copy(
                    update={
                        "values": [
                            broken_value,
                            *first_dimension.values[1:],
                        ],
                    },
                ),
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="project to every sourceRef"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_mixed_scenario_requires_bullish_and_bearish_contributions() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    mixed = next(scenario for scenario in result.scenarios if scenario.mixed_factors)
    balanced_only = mixed.model_copy(
        update={
            "dimension_values": {
                dimension.dimension_id: "Event 사실 기반 균형" for dimension in result.dimension_definitions
            },
        },
    )
    broken = result.model_copy(
        update={
            "scenarios": [balanced_only if scenario.mixed_factors else scenario for scenario in result.scenarios],
        },
    )

    with pytest.raises(ValueError, match="requires both bullish and bearish"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_interpretation_conflict_resolution_covers_all_interaction_events() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    interaction = result.interactions[0].model_copy(
        update={
            "relation": "interpretation_conflict",
            "resolution_dimension_id": "heat_duration",
        },
    )
    broken = result.model_copy(update={"interactions": [interaction]})

    with pytest.raises(
        ValueError,
        match="resolution dimension must reference every interaction event",
    ):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_interpretation_conflict_with_composite_resolution_is_valid() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    interaction = result.interactions[0].model_copy(
        update={
            "relation": "interpretation_conflict",
            "resolution_dimension_id": "demand_inventory_tightness",
        },
    )

    finalized = finalize_generation_result(
        result.model_copy(update={"interactions": [interaction]}),
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )

    assert finalized.interactions[0].relation == "interpretation_conflict"


def test_final_scenarios_are_sorted_by_global_pressure() -> None:
    finalized = finalize_generation_result(
        _result(strategy="multi_event_composite_dimensions"),
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )

    assert [scenario.global_pressure_band for scenario in finalized.scenarios] == [
        "strong_bullish",
        "balanced",
        "strong_bearish",
    ]


def test_lineage_only_marks_scenario_assumptions_as_assumptions() -> None:
    with pytest.raises(ValidationError):
        SourceLineage.model_validate(
            {
                **_source(101, "heat"),
                "sourceType": "event_fact",
                "assumptionYn": "Y",
            },
        )

    generated_outside_template = SourceLineage.model_validate(
        {
            **_source(101, "heat", "Event별 자연스러운 신규 value"),
            "sourceType": "event_fact",
            "assumptionYn": "N",
        },
    )
    assert generated_outside_template.source_type == "event_fact"

    with pytest.raises(ValidationError):
        SourceLineage.model_validate(
            {
                **_source(101, "heat"),
                "rationale": "",
            },
        )


def test_prompt_separates_event_facts_from_template_domain_knowledge() -> None:
    prompt = build_multi_event_user_prompt(
        api_version="v3",
        events=[
            {
                "mi_event_id": 101,
                "event_type_l2_id": 8,
                "event_title_ko": "현재 폭염 Event",
                "key_bullets": ["현재 사실"],
            },
        ],
        templates=[
            {
                "scenario_dimension_template_id": 1,
                "template_checksum": "checksum",
                "event_type_definition": "폭염 정의",
                "lng_price_impact_examples": "과거 대표 사례",
                "dimensions": [
                    {
                        "dim_key": "heat",
                        "label": "폭염",
                        "description": "현재 Event와 별개의 dimension 의미",
                        "value_enums": ["과거 예시값"],
                    },
                ],
            },
        ],
    )

    assert "## Event Context (authoritative current facts)" in prompt
    assert "## Template Domain Knowledge (reference examples" in prompt
    assert prompt.index("현재 사실") < prompt.index("과거 대표 사례")
    assert "valueEnumExamples" in prompt


def test_legacy_template_description_falls_back_but_new_write_requires_it() -> None:
    legacy = [
        {
            "dim_key": f"dimension_{index}",
            "label": f"Dimension {index}",
            "value_enums": ["낮음", "높음"],
            "display_order": index,
        }
        for index in range(1, 4)
    ]
    mapped = ScenarioService()._map_template_json_to_pipeline_template(
        legacy,
        event_type_l2_id=8,
    )
    assert mapped.dimensions[0].description == "Dimension 1"

    with pytest.raises(ValueError, match="description is required"):
        ScenarioService().validate_template_for_write(
            legacy,
            event_type_l2_id=8,
        )

    for item in legacy:
        item["description"] = f"{item['label']} 상세 설명"
    strict = ScenarioService().validate_template_for_write(
        legacy,
        event_type_l2_id=8,
    )
    assert strict.dimensions[0].description == "Dimension 1 상세 설명"


def test_template_domain_fields_round_trip_and_affect_revision_checksum() -> None:
    template_json = [
        {
            "dim_key": f"dimension_{index}",
            "label": f"Dimension {index}",
            "description": f"Dimension {index} 설명",
            "value_enums": ["낮음", "높음"],
            "display_order": index,
        }
        for index in range(1, 4)
    ]
    first_model = SimpleNamespace(
        scenario_dimension_template_id=81,
        template_json=template_json,
        event_type_definition="폭염 정의 v1",
        lng_price_impact_examples="LNG 가격 영향 사례",
    )
    revised_model = SimpleNamespace(
        scenario_dimension_template_id=81,
        template_json=template_json,
        event_type_definition="폭염 정의 v2",
        lng_price_impact_examples="LNG 가격 영향 사례",
    )
    session = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository.fetch_template_model",
            side_effect=[first_model, revised_model],
        ),
    ):
        first = ScenarioService()._load_template_record_from_db(8)
        revised = ScenarioService()._load_template_record_from_db(8)

    assert first["event_type_definition"] == "폭염 정의 v1"
    assert first["lng_price_impact_examples"] == "LNG 가격 영향 사례"
    assert first["template_json"][0]["description"] == "Dimension 1 설명"
    assert first["template_checksum"] != revised["template_checksum"]
    assert session.close.call_count == 2


def test_template_excel_migration_builds_domain_fields_and_descriptions(
    tmp_path: Path,
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "eventTypeL2Id",
            "이벤트 유형 정의",
            "LNG 가격 영향 대표 사례",
            "dimKey",
            "항목",
            "기준",
            "참고",
            "required",
            "valueEnums",
            "displayOrder",
        ],
    )
    for index in range(1, 4):
        sheet.append(
            [
                8,
                "폭염 정의",
                "대표 사례",
                f"heat_{index}",
                f"폭염 항목 {index}",
                "평년 대비 편차",
                "CDD 참고",
                "Y" if index == 1 else "N",
                "낮음|높음",
                index,
            ],
        )
    workbook_path = tmp_path / "scenario-template.xlsx"
    workbook.save(workbook_path)

    updates = load_template_updates(workbook_path)

    assert len(updates) == 1
    assert updates[0]["event_type_definition"] == "폭염 정의"
    assert updates[0]["lng_price_impact_examples"] == "대표 사례"
    assert updates[0]["template_json"][0]["description"] == ("폭염 항목 1 - 평년 대비 편차 - CDD 참고")
    assert updates[0]["template_json"][0]["value_enums"] == [
        "낮음",
        "높음",
    ]


def test_multi_event_rows_round_trip_pressure_role_and_rationale() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        dimension_selected=["tightness"],
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "description": "설명",
                "display_order": 1,
                "values": [],
            },
        ],
    )
    result = build_scenario_group_table_data(
        group.model_dump(),
        [
            {
                "scenario_id": 100,
                "title": "상단",
                "narrative": "설명",
                "dimension_values": {"tightness": "심화"},
                "probability_score": 30,
                "probability_delta": 0,
                "baseline_yn": "N",
                "global_pressure_band": "strong_bullish",
                "scenario_role": "ceiling",
                "global_pressure_rationale": "상승 근거",
            },
        ],
    )
    row = result.table.rows[0]
    assert row.global_pressure_band == "strong_bullish"
    assert row.scenario_role == "ceiling"
    assert row.probability_score == 30
    assert row.global_pressure_rationale == "상승 근거"


def test_validation_creates_pending_mapping_for_free_value() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["tightness"],
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "description": "설명",
                "display_order": 1,
                "source_refs": [_source(101, "heat")],
                "values": [{"value_id": "known", "label": "기존 값"}],
            },
        ],
    )
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=group,
        request_table={
            "headers": [
                {"key": "tightness", "label": "수급 긴축", "display_order": 1},
            ],
            "rows": [
                {
                    "scenario_id": 100,
                    "cells": {"tightness": "사용자 자유 값"},
                },
            ],
        },
    )
    saved = [
        {
            "dimension_value_id": "dv_test",
            "dimension_id": "tightness",
            "display_value": "사용자 자유 값",
            "mapping_version": 1,
            "status": "pending",
        },
    ]
    with (
        patch.object(
            ScenarioService,
            "save_mapping_proposals",
            return_value=saved,
        ) as save,
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioGroupService.set_parameter_mapping_ready",
        ) as set_ready,
    ):
        update = create_mapping_proposals(state)

    assert update["mapping_proposals"] == saved
    assert update["parameter_mapping_ready"] is False
    proposal = save.call_args.args[1][0]
    assert proposal["display_value"] == "사용자 자유 값"
    assert proposal["source_projections"][0]["source_type"] == "derived_interpretation"
    set_ready.assert_called_once_with(10, ready=False, user_id=7)


def test_validation_keeps_parameter_mapping_ready_for_approved_free_value() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["tightness"],
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "description": "설명",
                "display_order": 1,
                "source_refs": [_source(101, "heat")],
                "values": [{"value_id": "known", "label": "기존 값"}],
            },
        ],
    )
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=group,
        request_table={
            "headers": [
                {
                    "key": "tightness",
                    "label": "수급 긴축",
                    "display_order": 1,
                },
            ],
            "rows": [
                {
                    "scenario_id": 100,
                    "cells": {"tightness": "승인된 자유 값"},
                },
            ],
        },
    )
    saved = [
        {
            "dimension_value_id": "dv_test",
            "dimension_id": "tightness",
            "display_value": "승인된 자유 값",
            "mapping_version": 1,
            "status": "approved",
        },
    ]
    with (
        patch.object(
            ScenarioService,
            "save_mapping_proposals",
            return_value=saved,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioGroupService.set_parameter_mapping_ready",
        ) as set_ready,
    ):
        update = create_mapping_proposals(state)

    assert update["parameter_mapping_ready"] is True
    set_ready.assert_called_once_with(10, ready=True, user_id=7)


def test_multi_event_compatibility_does_not_treat_values_as_closed_enum() -> None:
    context = build_context(
        group={
            "generation_strategy": ("multi_event_composite_dimensions"),
            "dimension_selected": ["tightness"],
        },
        requested_rows=[
            {
                "scenario_id": 100,
                "title": "자유값 조합",
                "narrative": "현재 Event에 맞춘 자유값 조합",
                "cells": {"tightness": "사용자 자유 값"},
                "metrics": {"probability_score": 60},
            },
        ],
        persisted_scenarios=[],
        template_dims=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "enum": [
                    {
                        "id": "known",
                        "label": "기존 생성 값",
                    },
                ],
            },
        ],
    )
    incompatible = [
        CompatibilityItem(
            scenario_id=100,
            compatible=False,
            reason="자유값 조합이 다른 dimension과 모순된다.",
            conflict_dim_a="다른 분기",
            conflict_value_a="심화",
            conflict_dim_b="tightness",
            conflict_value_b="사용자 자유 값",
            recommended_value_b="새로운 자연스러운 값",
        ),
    ]

    assert not _has_only_unusable_enum_recommendations(
        context,
        incompatible,
    )
    assert "closed enum이 아닙니다" in MULTI_EVENT_COMPAT_SYSTEM_PROMPT


def test_mapping_proposal_sync_deactivates_values_no_longer_in_the_table() -> None:
    session = Mock()
    repository = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=repository,
        ),
    ):
        saved = ScenarioService().save_mapping_proposals(
            10,
            [],
            7,
        )

    assert saved == []
    repository.deactivate_mappings_except.assert_called_once_with(
        10,
        set(),
        7,
    )
    session.commit.assert_called_once()


def test_mapping_approval_rejects_stale_version() -> None:
    mapping = Mock(
        mapping_version=2,
        dimension_value_id="dv_test",
        status="pending",
    )
    session = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service."
            "ScenarioRepository.fetch_mapping_by_value_id",
            return_value=mapping,
        ),
    ):
        with pytest.raises(MIBaseError, match="Stale mapping version"):
            ScenarioService().decide_mapping_proposals(
                10,
                [
                    {
                        "dimension_value_id": "dv_test",
                        "mapping_version": 1,
                        "decision": "approve",
                    },
                ],
                7,
            )
    session.rollback.assert_called_once()


def test_multi_event_group_has_no_fake_representative_event_and_keeps_order() -> None:
    session = Mock()
    repository = Mock()
    repository.fetch_all_by_comparison_run.return_value = []
    repository.fetch_by_comparison_run.return_value = None
    repository.insert_group.return_value = 99
    repository.fetch_by_id.return_value = SimpleNamespace(
        scenario_group_id=99,
        mi_event_id=None,
        event_type_l2_id=None,
        request_usr_id=7,
        title="Multi-event scenario group (2 events)",
        summary="복수 MI Event 공동 전제 시나리오",
        description=None,
        dimension_selected=[],
        scenario_count=0,
        status="creating",
        stage="ready",
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        comparison_run_id="compare-1",
        template_checksum="aggregate",
        parameter_mapping_ready=False,
        dimension_definitions=[],
        generation_diagnostics={},
    )
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    events = [
        {"mi_event_id": 101, "event_type_l2_id": 8},
        {"mi_event_id": 202, "event_type_l2_id": 12},
    ]
    templates = [
        {
            "scenario_dimension_template_id": 81,
            "template_checksum": "checksum-8",
        },
        {
            "scenario_dimension_template_id": 121,
            "template_checksum": "checksum-12",
        },
    ]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=repository,
        ),
    ):
        group = ScenarioGroupService().prepare_multi_event_group(
            events=events,
            templates=templates,
            api_version="v3",
            generation_strategy="multi_event_composite_dimensions",
            comparison_run_id="compare-1",
            user_id=7,
        )

    inserted_group = repository.insert_group.call_args.args[0]
    assert inserted_group["mi_event_id"] is None
    assert inserted_group["event_type_l2_id"] is None
    assert group.mi_event_id is None
    assert [call.args[0]["mi_event_id"] for call in repository.insert_group_event.call_args_list] == EVENT_IDS
    assert [call.args[0]["template_checksum"] for call in repository.insert_group_event.call_args_list] == [
        "checksum-8",
        "checksum-12",
    ]
    session.commit.assert_called_once()


def test_comparison_run_rejects_different_event_or_template_revision() -> None:
    session = Mock()
    repository = Mock()
    repository.fetch_all_by_comparison_run.return_value = [
        SimpleNamespace(scenario_group_id=55),
    ]
    repository.fetch_group_events.return_value = [
        SimpleNamespace(mi_event_id=101, template_checksum="checksum-8"),
        SimpleNamespace(mi_event_id=999, template_checksum="different"),
    ]
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=repository,
        ),
        pytest.raises(
            MIBaseError,
            match="same events and template revisions",
        ),
    ):
        ScenarioGroupService().prepare_multi_event_group(
            events=[
                {"mi_event_id": 101, "event_type_l2_id": 8},
                {"mi_event_id": 202, "event_type_l2_id": 12},
            ],
            templates=[
                {
                    "scenario_dimension_template_id": 81,
                    "template_checksum": "checksum-8",
                },
                {
                    "scenario_dimension_template_id": 121,
                    "template_checksum": "checksum-12",
                },
            ],
            api_version="v2",
            generation_strategy="multi_event_source_dimensions",
            comparison_run_id="compare-1",
            user_id=7,
        )

    session.rollback.assert_called_once()


def test_versioned_sync_and_mapping_routes_are_registered() -> None:
    paths = {route.path for route in agent_router.routes}
    assert "/v1/scenario-groups/sync" in paths
    assert "/v2/scenario-groups/sync" in paths
    assert "/v3/scenario-groups/sync" in paths
    assert "/scenario-groups/{scenario_group_id}/dimension-mapping-approvals" in paths


def test_mapping_approval_endpoint_does_not_invoke_llm() -> None:
    app = FastAPI()
    app.include_router(router)
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        parameter_mapping_ready=False,
    )
    approved_group = group.model_copy(
        update={"parameter_mapping_ready": True},
    )
    with (
        patch.object(
            ScenarioService,
            "decide_mapping_proposals",
            return_value=[
                {
                    "dimension_value_id": "dv_test",
                    "mapping_version": 1,
                    "status": "approved",
                },
            ],
        ) as decide,
        patch(
            "apps.agents.scenario_group_agent.routers.scenario_generation.ScenarioGroupService.load_by_id",
            side_effect=[group, approved_group],
        ),
    ):
        response = TestClient(app).post(
            "/scenario-groups/10/dimension-mapping-approvals",
            json={
                "userId": 7,
                "decisions": [
                    {
                        "dimensionValueId": "dv_test",
                        "mappingVersion": 1,
                        "decision": "approve",
                    },
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["parameterMappingReady"] is True
    decide.assert_called_once()


def test_confirmation_uses_stored_multi_event_dimensions() -> None:
    session = Mock()
    group = SimpleNamespace(
        scenario_group_id=10,
        generation_strategy="multi_event_composite_dimensions",
        parameter_mapping_ready=True,
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
            },
        ],
        event_type_l2_id=None,
    )
    scenario = SimpleNamespace(
        scenario_id=100,
        probability_score=60,
        display_order=1,
        baseline_yn="Y",
        mod_usr_logn_id=7,
    )
    signpost = SimpleNamespace(
        signpost_id=1000,
        scenario_id=100,
    )
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.create_confirmation_snapshot.return_value = 500
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "created",
        "stage": "completed",
    }
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.return_value = [scenario]
    signpost_repository = Mock()
    signpost_repository.fetch_models_by_scenario_ids.return_value = [
        signpost,
    ]
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.SignpostRepository",
            return_value=signpost_repository,
        ),
        patch.object(
            ScenarioService,
            "cells_to_dimension_values",
        ) as legacy_cell_mapping,
    ):
        result = ScenarioGroupService().apply_confirmation(
            10,
            {"title": "복수 Event 확정"},
            {
                "rows": [
                    {
                        "scenario_id": 100,
                        "cells": {"tightness": "사용자 승인 값"},
                        "metrics": {
                            "probability_score": 60,
                            "probability_delta": 0,
                        },
                        "signposts": [
                            {
                                "signpost_id": 1000,
                                "label": "관찰 지표",
                            },
                        ],
                    },
                ],
            },
            user_id=7,
        )

    assert result["status"] == "success"
    scenario_update = scenario_repository.update_from_payload.call_args.args[1]
    assert scenario_update["dimension_values"] == {
        "tightness": "사용자 승인 값",
    }
    legacy_cell_mapping.assert_not_called()
    group_repository.create_confirmation_snapshot.assert_called_once()
    session.commit.assert_called_once()


def test_confirmation_waits_for_multi_event_mapping_approval() -> None:
    session = Mock()
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = SimpleNamespace(
        generation_strategy="multi_event_source_dimensions",
        parameter_mapping_ready=False,
    )
    scenario_repository = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
    ):
        result = ScenarioGroupService().apply_confirmation(
            10,
            {},
            {"rows": []},
            user_id=7,
        )

    assert result == {
        "status": "failure",
        "message": "Dimension value mapping approvals are not complete",
    }
    scenario_repository.fetch_models_by_group_id.assert_not_called()
    session.commit.assert_not_called()


def test_multi_event_signpost_context_preserves_every_event() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
    )
    events = [
        EventPayload.model_validate(
            {
                "mi_event_id": 101,
                "event_type_l2_id": 8,
                "event_title_ko": "폭염",
                "one_line_summary": "아시아 폭염",
                "key_bullets": ["수요 증가"],
                "tags": ["아시아"],
                "occurred_at": "2026-07-01",
            },
        ),
        EventPayload.model_validate(
            {
                "mi_event_id": 202,
                "event_type_l2_id": 12,
                "event_title_ko": "재고 부족",
                "one_line_summary": "유럽 재고 부족",
                "key_bullets": ["구매 경쟁"],
                "tags": ["유럽"],
                "occurred_at": "2026-07-02",
            },
        ),
    ]
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_event_ids",
            return_value=EVENT_IDS,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.EventService.load_events",
            return_value=events,
        ),
    ):
        context = _load_group_event_context(group)

    assert context is not None
    assert context.mi_event_id == "101,202"
    assert context.event_title_ko == "폭염 + 재고 부족"
    assert context.key_bullets == [
        "[Event 101] 수요 증가",
        "[Event 202] 구매 경쟁",
    ]
    assert context.tags == ["아시아", "유럽"]


def test_multi_event_signpost_table_sync_uses_stored_dimension_definitions() -> None:
    definitions = [
        {
            "dimension_id": "tightness",
            "label": "수급 긴축",
            "description": "설명",
            "display_order": 1,
            "values": [],
        },
    ]
    state = CreateSignpostsState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            api_version="v3",
            generation_strategy="multi_event_composite_dimensions",
            dimension_selected=["tightness"],
            dimension_definitions=definitions,
        ),
        request_table={
            "headers": [
                {"key": "tightness", "label": "수급 긴축", "displayOrder": 1},
            ],
            "rows": [
                {
                    "scenarioId": 100,
                    "displayOrder": 1,
                    "title": "혼합",
                    "cells": {"tightness": "균형"},
                },
            ],
        },
    )
    sync_result = {
        "active_scenario_ids": [100],
        "regenerate_scenario_ids": [],
        "inserted_scenario_ids": [],
        "updated_scenario_ids": [],
        "deleted_scenario_ids": [],
        "unchanged_existing_scenario_ids": [100],
    }
    with (
        patch.object(
            ScenarioService,
            "sync_from_table",
            return_value=sync_result,
        ) as sync,
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_by_id",
            return_value=state.scenario_group,
        ),
    ):
        update = sync_scenarios_from_table(state)

    assert update["signpost_target_scenario_ids"] == []
    assert sync.call_args.kwargs["event_type_l2_id"] is None
    assert sync.call_args.kwargs["dimension_definitions"] == definitions


def test_signpost_uses_combined_context_for_multi_event_group() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        mi_event_id=None,
        event_type_l2_id=None,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
    )
    events = [
        EventPayload(
            mi_event_id=101,
            event_type_l2_id=8,
            event_title_ko="폭염",
            one_line_summary="냉방 수요 증가",
            key_bullets=["기온 상승"],
            tags=["아시아"],
        ),
        EventPayload(
            mi_event_id=202,
            event_type_l2_id=12,
            event_title_ko="재고 부족",
            one_line_summary="유럽 재고 긴축",
            key_bullets=["재고 하락"],
            tags=["유럽"],
        ),
    ]
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_event_ids",
            return_value=EVENT_IDS,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.EventService.load_events",
            return_value=events,
        ),
    ):
        combined = _load_group_event_context(group)

    assert combined is not None
    assert combined.mi_event_id == "101,202"
    assert combined.event_title_ko == "폭염 + 재고 부족"
    assert combined.key_bullets == [
        "[Event 101] 기온 상승",
        "[Event 202] 재고 하락",
    ]
    assert combined.tags == ["아시아", "유럽"]


def test_signpost_table_sync_uses_stored_multi_event_dimensions() -> None:
    definitions = [
        {
            "dimension_id": "tightness",
            "label": "수급 긴축",
            "description": "설명",
            "display_order": 1,
            "source_refs": [_source(101, "heat")],
            "values": [{"value_id": "high", "label": "심화"}],
        },
    ]
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["tightness"],
        dimension_definitions=definitions,
    )
    state = CreateSignpostsState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=group,
        request_table={
            "headers": [
                {"key": "tightness", "label": "수급 긴축", "display_order": 1},
            ],
            "rows": [
                {
                    "scenario_id": 100,
                    "cells": {"tightness": "심화"},
                },
            ],
        },
    )
    sync_result = {
        "active_scenario_ids": [100],
        "regenerate_scenario_ids": [],
        "inserted_scenario_ids": [],
        "updated_scenario_ids": [],
        "deleted_scenario_ids": [],
        "unchanged_existing_scenario_ids": [100],
    }
    with (
        patch.object(
            ScenarioService,
            "sync_from_table",
            return_value=sync_result,
        ) as sync,
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_by_id",
            return_value=group,
        ),
    ):
        sync_scenarios_from_table(state)

    assert sync.call_args.kwargs["event_type_l2_id"] is None
    assert sync.call_args.kwargs["dimension_definitions"] == definitions
