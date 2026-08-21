from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.agents.scenario_group_agent.api import router as agent_router
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.presentation import (
    build_presentation_follow_up_request_bodies,
    build_scenario_group_presentation,
)
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario_group_operation.schema import ScenarioGroupOperationPayload


def _event(event_id: int, title: str = "Event <script>alert(1)</script>") -> EventPayload:
    return EventPayload(
        mi_event_id=event_id,
        event_type_l2_id=10,
        event_title_ko=title,
        one_line_summary="요약 <b>raw</b>",
        occurred_at="2026-08-01",
    )


def _group(version: str, definitions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "scenario_group_id": 120,
        "api_version": version,
        "generation_strategy": "multi_event_composite_dimensions",
        "title": "Group <iframe>",
        "summary": "summary",
        "description": "description",
        "dimension_selected": ["d1"],
        "dimension_definitions": definitions,
        "generation_diagnostics": {},
        "updated_at": datetime(2026, 8, 11, tzinfo=UTC),
    }


def _scenario(*, cell: str, role: str = "ceiling") -> dict[str, object]:
    return {
        "scenario_id": 2056,
        "display_order": 1,
        "title": "Scenario <img src=x onerror=alert(1)>",
        "narrative": "narrative",
        "dimension_values": {"d1": cell},
        "scenario_role": role,
        "baseline_yn": "Y",
        "global_pressure_band": "strong_bullish",
        "probability_score": 17,
        "global_pressure_rationale": "stored rationale <script>",
    }


def _operation(
    *,
    status: str = "running",
    revision: int = 1,
    presentation_snapshot: dict[str, object] | None = None,
) -> ScenarioGroupOperationPayload:
    return ScenarioGroupOperationPayload(
        operation_id="01JABCDEF0123456789ABCDEFX",
        scenario_group_id=120,
        operation_type="create",
        engine_version="v4",
        status=status,
        current_phase="event_analysis",
        latest_sequence=8,
        snapshot_revision=revision,
        presentation_snapshot=presentation_snapshot or {},
    )


def _v4_definition() -> dict[str, object]:
    return {
        "dimensionId": "d1",
        "label": "수급 방향",
        "description": "질문",
        "rationale": "수급 방향에 따라 가용 LNG 물량과 JKM 압력이 변화됨",
        "sourceEventIds": [101],
        "modelSupportStatus": "price_only",
        "values": [
            {
                "valueId": "d1_v1",
                "label": "상승",
                "assumptionRationale": "v4 assumption",
                "pressureContribution": "bullish",
                "leverStates": [{"leverCode": "weather_demand"}],
            },
        ],
    }


def _v4_diagnostics(*, include_interaction: bool = True) -> dict[str, object]:
    return {
        "eventFacts": [
            {
                "factId": "f1",
                "eventId": 101,
                "observedBasis": "확인된 <script>사실</script>",
            },
        ],
        "eventExclusions": [],
        "impactPaths": [
            {
                "impactPathId": "p1",
                "eventId": 101,
                "mechanism": "JKM <b>영향</b>",
            },
        ],
        "pathUncertainties": [
            {
                "uncertaintyId": "u1",
                "impactPathIds": ["p1"],
                "subject": "지속 기간",
            },
        ],
        "eventInteractions": (
            [{"interactionId": "i1", "eventIds": [101, 102], "mechanism": "상호 증폭"}] if include_interaction else []
        ),
        "interactionUncertainties": [],
        "scenarioPressureBreakdowns": [],
    }


def test_v3_and_v4_values_and_cell_forms_share_the_presentation_contract() -> None:
    v3_definition = {
        "dimension_id": "d1",
        "label": "수급 방향",
        "description": "질문",
        "rationale": "dimension rationale",
        "source_event_ids": [101],
        "values": [
            {
                "value_id": "d1_v1",
                "label": "상승",
                "description": "legacy description fallback",
                "derivation_rationale": None,
                "pressure_contribution": "bullish",
            },
        ],
    }
    v3_group = _group("v3", [v3_definition])
    v3_group["generation_diagnostics"] = {
        "event_shocks": [{"event_id": 101, "shock_summary": "상승 충격"}],
        "event_interactions": [],
        "template_dimension_selections": [
            {
                "event_id": 101,
                "scenario_dimension_template_id": 10,
                "dim_key": "d1",
                "observed_basis": "관찰 근거",
            },
        ],
    }
    v4_group = _group("v4", [_v4_definition()])
    v4_group["generation_diagnostics"] = _v4_diagnostics()

    v3 = build_scenario_group_presentation(
        group=v3_group,
        scenarios=[_scenario(cell="d1_v1")],
        signposts=[],
        events=[_event(101, "v3 event")],
        operation=None,
    )
    v4 = build_scenario_group_presentation(
        group=v4_group,
        scenarios=[_scenario(cell="상승")],
        signposts=[],
        events=[_event(101, "v4 event")],
        operation=None,
    )

    for result in (v3, v4):
        payload = result.model_dump(mode="json", by_alias=True)
        assert set(payload["sections"]) == {"eventAnalysis", "scenarioDesign", "roleSelectionRationale"}
        assert payload["sections"]["scenarioDesign"]["scenarioTable"]["rows"][0]["cells"] == {"d1": "d1_v1"}
        assert (
            payload["sections"]["scenarioDesign"]["scenarioTable"]["rows"][0]["cellEvidence"]["d1"]["valueId"]
            == "d1_v1"
        )

    assert v3.sections.scenario_design.dimension_definitions.items[0].values[0].rationale == (
        "legacy description fallback"
    )
    assert v4.sections.scenario_design.dimension_definitions.items[0].values[0].rationale == "v4 assumption"
    assert v4.sections.scenario_design.dimension_definitions.items[0].rationale == (
        "수급 방향에 따라 가용 LNG 물량과 JKM 압력이 변화됨"
    )
    assert v4.sections.scenario_design.dimension_definitions.items[0].values[0].lever_states == [
        {"leverCode": "weather_demand"},
    ]


def test_v4_value_description_is_derived_from_valid_lever_states() -> None:
    definition = _v4_definition()
    values = definition["values"]
    assert isinstance(values, list)
    values.extend(
        [
            {
                "valueId": "d1_v2",
                "label": "차익 폐쇄",
                "assumptionRationale": "하락 가정",
                "pressureContribution": "bearish",
                "leverStates": [
                    {
                        "leverCode": "regional_price_spread",
                        "direction": "decrease",
                        "level": "JKM-NWE 차익 폐쇄",
                        "scope": "동서 재정거래",
                        "timeWindow": "2026년 9월 이후물",
                    },
                ],
            },
            {
                "valueId": "d1_v3",
                "label": "복합 상태",
                "assumptionRationale": "복합 가정",
                "pressureContribution": "balanced",
                "lever_states": [
                    {
                        "lever_code": "inventory_condition",
                        "direction": "recover",
                        "level": "저장 부담 완화",
                        "scope": "유럽 NWE",
                        "time_window": "분석 기준일 이후 단기",
                    },
                    {
                        "lever_code": "route_disruption",
                        "direction": "unchanged",
                        "level": "일부 지연",
                        "scope": "중동발 아시아향",
                        "time_window": "단기",
                    },
                ],
            },
            {
                "valueId": "d1_v4",
                "label": "명시 설명",
                "description": "저장된 설명을 우선한다.",
                "assumptionRationale": "명시 설명 가정",
                "pressureContribution": "bullish",
                "leverStates": [
                    {
                        "direction": "increase",
                        "level": "현물 경쟁 확대",
                        "scope": "아시아",
                        "timeWindow": "단기",
                    },
                ],
            },
            {
                "valueId": "d1_v5",
                "label": "과거 미등록 방향",
                "assumptionRationale": "과거 데이터 가정",
                "pressureContribution": "balanced",
                "leverStates": [
                    {
                        "direction": "sideways",
                        "level": "횡보",
                        "scope": "글로벌 LNG",
                        "timeWindow": "중기",
                    },
                ],
            },
        ],
    )
    group = _group("v4", [definition])
    group["generation_diagnostics"] = _v4_diagnostics()

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[_scenario(cell="d1_v2")],
        signposts=[],
        events=[_event(101)],
        operation=None,
    )

    output_values = result.sections.scenario_design.dimension_definitions.items[0].values
    assert output_values[0].description is None
    assert output_values[1].description == (
        "2026년 9월 이후물 기준 동서 재정거래에서는 JKM-NWE 차익 폐쇄 상태가 전개된다(변화 방향: 감소)."
    )
    assert output_values[2].description == (
        "분석 기준일 이후 단기 기준 유럽 NWE에서는 저장 부담 완화 상태가 전개된다(변화 방향: 회복). "
        "단기 기준 중동발 아시아향에서는 일부 지연 상태가 전개된다(변화 방향: 현 수준 유지)."
    )
    assert output_values[3].description == "저장된 설명을 우선한다."
    assert output_values[4].description is None
    assert output_values[1].rationale == "하락 가정"


def test_historical_v4_dimension_without_rationale_remains_null() -> None:
    definition = _v4_definition()
    definition.pop("rationale")
    group = _group("v4", [definition])
    group["generation_diagnostics"] = _v4_diagnostics()

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[_scenario(cell="d1_v1")],
        signposts=[],
        events=[_event(101)],
        operation=None,
    )

    assert result.sections.scenario_design.dimension_definitions.items[0].rationale is None


def test_v4_markdown_is_deterministic_escaped_and_reports_missing_mixed() -> None:
    group = _group("v4", [_v4_definition()])
    group["generation_diagnostics"] = _v4_diagnostics()
    kwargs = {
        "group": group,
        "scenarios": [_scenario(cell="d1_v1")],
        "signposts": [],
        "events": [_event(101)],
        "operation": None,
    }

    first = build_scenario_group_presentation(**kwargs).model_dump_json(by_alias=True)
    second = build_scenario_group_presentation(**kwargs).model_dump_json(by_alias=True)
    result = build_scenario_group_presentation(**kwargs)

    assert first == second
    assert "<script>" not in result.sections.event_analysis.markdown
    assert "&lt;script&gt;" in result.sections.event_analysis.markdown
    assert "<img" not in result.sections.role_selection_rationale.markdown
    assert "선정 가능한 Mixed Scenario 없음" in result.sections.role_selection_rationale.markdown
    assert result.sections.role_selection_rationale.markdown.index("### Ceiling") < (
        result.sections.role_selection_rationale.markdown.index("### Mixed")
    )


def test_v4_role_rationale_uses_current_lever_display_labels() -> None:
    definition = _v4_definition()
    definition["values"][0]["assumptionRationale"] = (
        "liquefaction_availability 하락과 inventory_condition_extra는 구분한다."
    )
    group = _group("v4", [definition])
    diagnostics = _v4_diagnostics()
    diagnostics["scenarioPressureBreakdowns"] = [
        {
            "title": "검증 전 과거 제목",
            "dimensionValues": {"수급 방향": "상승"},
            "pressureBreakdown": {
                "commonImpact": "regional_price_spread 경로",
                "valueDelta": "inventory_condition을 반영",
            },
        },
    ]
    group["generation_diagnostics"] = diagnostics
    scenario = _scenario(cell="d1_v1")
    scenario["global_pressure_rationale"] = (
        "inventory_condition을 통해 regional_price_spread 경로를 강화하고 unknown_lever는 그대로 둔다."
    )

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[scenario],
        signposts=[],
        events=[_event(101)],
        operation=None,
        lever_labels={
            "inventory_condition": "재고 여건",
            "regional_price_spread": "지역 가격 스프레드",
            "liquefaction_availability": "액화설비 가용성",
        },
    )

    markdown = result.sections.role_selection_rationale.markdown
    assert "재고 여건을 통해 지역 가격 스프레드 경로" in markdown
    assert "공통 영향: 지역 가격 스프레드 경로" in markdown
    assert "Dimension 값 차이: 재고 여건을 반영" in markdown
    assert "근거: 액화설비 가용성 하락" in markdown
    assert "inventory_condition_extra" in markdown
    assert "unknown_lever" in markdown


def test_v4_role_rationale_keeps_breakdowns_with_dimension_combinations_after_title_swap() -> None:
    definition = _v4_definition()
    definition["values"].append(
        {
            "valueId": "d1_v2",
            "label": "하락",
            "assumptionRationale": "하락 가정",
            "pressureContribution": "bearish",
            "leverStates": [],
        }
    )
    group = _group("v4", [definition])
    diagnostics = _v4_diagnostics()
    diagnostics["scenarioPressureBreakdowns"] = [
        {
            "title": "상방 제목",
            "dimensionValues": {"수급 방향": "상승"},
            "pressureBreakdown": {"commonImpact": "상승 조합 근거"},
        },
        {
            "title": "하방 제목",
            "dimensionValues": {"d1": "d1_v2"},
            "pressureBreakdown": {"commonImpact": "하락 조합 근거"},
        },
    ]
    group["generation_diagnostics"] = diagnostics
    ceiling = _scenario(cell="d1_v1", role="ceiling")
    ceiling["scenario_id"] = 1
    ceiling["title"] = "하방 제목"
    floor = _scenario(cell="d1_v2", role="floor")
    floor["scenario_id"] = 2
    floor["title"] = "상방 제목"

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[ceiling, floor],
        signposts=[],
        events=[_event(101)],
        operation=None,
    )

    markdown = result.sections.role_selection_rationale.markdown
    floor_section = markdown.index("### Floor")
    assert markdown.index("상승 조합 근거") < floor_section
    assert markdown.index("하락 조합 근거") > floor_section


def test_v4_role_rationale_omits_stale_pressure_breakdown_for_unmatched_combination() -> None:
    definition = _v4_definition()
    definition["values"].append(
        {
            "valueId": "d1_v2",
            "label": "하락",
            "assumptionRationale": "하락 가정",
            "pressureContribution": "bearish",
            "leverStates": [],
        }
    )
    group = _group("v4", [definition])
    diagnostics = _v4_diagnostics()
    diagnostics["scenarioPressureBreakdowns"] = [
        {
            "title": "Scenario <img src=x onerror=alert(1)>",
            "dimensionValues": {"d1": "d1_v2"},
            "pressureBreakdown": {"commonImpact": "다른 조합 근거"},
        },
    ]
    group["generation_diagnostics"] = diagnostics

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[_scenario(cell="d1_v1")],
        signposts=[],
        events=[_event(101)],
        operation=None,
    )

    markdown = result.sections.role_selection_rationale.markdown
    assert "Pressure 구성" not in markdown
    assert "다른 조합 근거" not in markdown
    assert "적용된 Dimension 근거" in markdown


def test_running_v4_projection_moves_partial_to_ready_with_snapshot_revision() -> None:
    analysis_snapshot = {
        "generationDiagnostics": _v4_diagnostics(include_interaction=False),
        "sections": {"eventAnalysis": {"status": "partial"}},
    }
    ready_snapshot = {
        "generationDiagnostics": _v4_diagnostics(),
        "dimensionDefinitions": [_v4_definition()],
        "sections": {
            "eventAnalysis": {"status": "ready"},
            "scenarioDesign": {
                "status": "partial",
                "dimensionDefinitions": {"status": "ready"},
                "scenarioTable": {"status": "pending"},
            },
        },
    }
    group = _group("v4", [])

    partial = build_scenario_group_presentation(
        group=group,
        scenarios=[],
        signposts=[],
        events=[_event(101)],
        operation=_operation(revision=1, presentation_snapshot=analysis_snapshot),
    )
    ready = build_scenario_group_presentation(
        group=group,
        scenarios=[],
        signposts=[],
        events=[_event(101)],
        operation=_operation(revision=3, presentation_snapshot=ready_snapshot),
    )

    assert partial.operation is not None and partial.operation.snapshot_revision == 1
    assert partial.sections.event_analysis.status == "partial"
    assert partial.sections.scenario_design.status == "pending"
    assert ready.operation is not None and ready.operation.snapshot_revision == 3
    assert ready.sections.event_analysis.status == "ready"
    assert ready.sections.scenario_design.status == "partial"
    assert ready.sections.scenario_design.dimension_definitions.status == "ready"
    assert ready.sections.scenario_design.scenario_table.status == "pending"


def test_v1_observed_fallback_does_not_invent_role_pressure_or_rationale() -> None:
    group = _group("v1", [])
    group["generation_strategy"] = "single_event_template_dimensions"
    group["dimension_selected"] = ["duration"]
    scenario = _scenario(cell="unused", role="")
    scenario["dimension_values"] = {"duration": "1개월 이하"}
    scenario["global_pressure_band"] = None
    scenario["global_pressure_rationale"] = None

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[scenario],
        signposts=[],
        events=[_event(101, "legacy event")],
        operation=None,
        legacy_template_dimensions=[],
    )

    definition = result.sections.scenario_design.dimension_definitions.items[0]
    cell = result.sections.scenario_design.scenario_table.rows[0].cell_evidence["duration"]
    assert result.legacy is True
    assert definition.source == "legacy_observed"
    assert definition.label == "duration"
    assert definition.values[0].rationale == ""
    assert cell.pressure_contribution is None
    assert cell.evidence_level == "none"
    assert result.sections.role_selection_rationale.status == "unavailable"
    assert result.sections.role_selection_rationale.markdown == ""


def test_v1_stored_value_description_is_not_promoted_to_generated_rationale() -> None:
    group = _group(
        "v1",
        [
            {
                "dimension_id": "d1",
                "label": "기간",
                "values": [
                    {
                        "value_id": "short",
                        "label": "단기",
                        "description": "값 설명일 뿐 생성 근거는 아님",
                    },
                ],
            },
        ],
    )

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[_scenario(cell="short", role="")],
        signposts=[],
        events=[_event(101, "legacy event")],
        operation=None,
    )

    value = result.sections.scenario_design.dimension_definitions.items[0].values[0]
    assert value.description == "값 설명일 뿐 생성 근거는 아님"
    assert value.rationale == ""


def test_v1_confirmation_snapshot_precedes_current_template_and_observed_values() -> None:
    group = _group("v1", [])
    group["dimension_selected"] = ["duration"]
    scenario = _scenario(cell="unused", role="")
    scenario["dimension_values"] = {"duration": "현재 값"}

    result = build_scenario_group_presentation(
        group=group,
        scenarios=[scenario],
        signposts=[],
        events=[_event(101, "legacy event")],
        operation=None,
        legacy_snapshot_dimension_values=[{"dim_key": "duration", "value": "확정 당시 값"}],
        legacy_template_dimensions=[
            {
                "dim_key": "duration",
                "label": "기간",
                "value_enums": ["Template 값"],
            },
        ],
    )

    definition = result.sections.scenario_design.dimension_definitions.items[0]
    assert definition.source == "legacy_confirmation_snapshot"
    assert [value.label for value in definition.values] == ["확정 당시 값"]


def test_v1_current_template_is_used_only_when_checksum_matches() -> None:
    group = _group("v1", [])
    group["event_type_l2_id"] = 10
    group["template_checksum"] = "stored"
    template = {"template_checksum": "current", "template_json": [{"dim_key": "duration"}]}

    with patch(
        "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioService.load_template_record",
        return_value=template,
    ):
        assert ScenarioGroupService._load_trusted_legacy_template_dimensions(group) == []

    template["template_checksum"] = "stored"
    with patch(
        "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioService.load_template_record",
        return_value=template,
    ):
        assert ScenarioGroupService._load_trusted_legacy_template_dimensions(group) == [{"dim_key": "duration"}]


def test_presentation_endpoint_selects_operation_and_returns_etag_304() -> None:
    app = FastAPI()
    app.include_router(agent_router)
    operation = _operation(status="succeeded", revision=4)
    context = {
        "group": _group("v4", [_v4_definition()]),
        "scenarios": [_scenario(cell="d1_v1")],
        "signposts": [],
        "events": [_event(101)],
        "operation": operation,
        "lever_labels": {"inventory_condition": "재고 여건"},
        "legacy_template_dimensions": [],
    }
    context["group"]["generation_diagnostics"] = _v4_diagnostics()

    with patch.object(ScenarioGroupService, "load_presentation_detail", return_value=context) as load:
        client = TestClient(app)
        first = client.get(
            "/scenario-groups/120/presentation",
            params={"operationId": operation.operation_id},
        )
        second = client.get(
            "/scenario-groups/120/presentation",
            params={"operationId": operation.operation_id},
            headers={"If-None-Match": first.headers["etag"]},
        )

    assert first.status_code == 200
    assert first.json()["rendererVersion"] == "v3"
    assert first.json()["operation"]["operationId"] == operation.operation_id
    assert second.status_code == 304
    assert second.content == b""
    assert second.headers["etag"] == first.headers["etag"]
    assert load.call_args_list[0].kwargs == {"operation_id": operation.operation_id}


def test_presentation_etag_changes_with_lever_display_labels() -> None:
    app = FastAPI()
    app.include_router(agent_router)
    operation = _operation(status="succeeded", revision=4)
    context = {
        "group": _group("v4", [_v4_definition()]),
        "scenarios": [_scenario(cell="d1_v1")],
        "signposts": [],
        "events": [_event(101)],
        "operation": operation,
        "lever_labels": {"inventory_condition": "재고 여건"},
        "legacy_template_dimensions": [],
        "legacy_snapshot_dimension_values": [],
    }
    context["group"]["generation_diagnostics"] = _v4_diagnostics()

    with patch.object(ScenarioGroupService, "load_presentation_detail", return_value=context):
        client = TestClient(app)
        first = client.get("/scenario-groups/120/presentation")
        context["lever_labels"] = {"inventory_condition": "유럽 재고 여건"}
        second = client.get(
            "/scenario-groups/120/presentation",
            headers={"If-None-Match": first.headers["etag"]},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers["etag"] != first.headers["etag"]


def test_follow_up_request_bodies_project_only_editable_table_fields() -> None:
    group = _group("v4", [_v4_definition()])
    group["generation_diagnostics"] = _v4_diagnostics()
    presentation = build_scenario_group_presentation(
        group=group,
        scenarios=[_scenario(cell="d1_v1")],
        signposts=[],
        events=[_event(101)],
        operation=_operation(status="succeeded", revision=4),
    )

    result = build_presentation_follow_up_request_bodies(presentation, user_id=10603)
    payload = result.model_dump(mode="json", by_alias=True)

    assert payload["ready"] is True
    assert payload["scenarioTableStatus"] == "ready"
    assert payload["operationId"] == "01JABCDEF0123456789ABCDEFX"
    assert payload["validationRequestBody"] == payload["signpostRequestBody"]
    assert payload["validationRequestBody"] == {
        "userId": 10603,
        "table": {
            "headers": [{"key": "d1", "label": "수급 방향", "displayOrder": 1}],
            "rows": [
                {
                    "scenarioId": 2056,
                    "displayOrder": 1,
                    "title": "Scenario <img src=x onerror=alert(1)>",
                    "cells": {"d1": "d1_v1"},
                },
            ],
        },
    }
    assert "cellEvidence" not in payload["validationRequestBody"]["table"]["rows"][0]
    assert "narrative" not in payload["validationRequestBody"]["table"]["rows"][0]


def test_follow_up_request_bodies_are_null_until_scenario_table_is_ready() -> None:
    presentation = build_scenario_group_presentation(
        group=_group("v4", []),
        scenarios=[],
        signposts=[],
        events=[_event(101)],
        operation=_operation(status="running", revision=1),
    )

    result = build_presentation_follow_up_request_bodies(presentation, user_id=10603)

    assert result.ready is False
    assert result.scenario_table_status == "pending"
    assert result.reason is not None
    assert result.validation_request_body is None
    assert result.signpost_request_body is None


def test_follow_up_signpost_draft_always_includes_table_for_all_engine_versions() -> None:
    definition = {
        "dimension_id": "d1",
        "label": "수급 방향",
        "values": [{"value_id": "d1_v1", "label": "상승"}],
    }

    for version in ("v1", "v2", "v3", "v4"):
        presentation = build_scenario_group_presentation(
            group=_group(version, [definition]),
            scenarios=[_scenario(cell="d1_v1")],
            signposts=[],
            events=[_event(101)],
            operation=None,
        )
        presentation.sections.scenario_design.scenario_table.rows[0].scenario_id = None

        result = build_presentation_follow_up_request_bodies(presentation, user_id=10603)

        assert result.signpost_request_body is not None
        assert result.signpost_request_body.table is not None
        assert result.signpost_request_body.table.rows[0].scenario_id is None
        assert result.signpost_request_body.table.rows[0].cells == {"d1": "d1_v1"}


def test_follow_up_request_bodies_endpoint_reuses_presentation_operation_selection() -> None:
    app = FastAPI()
    app.include_router(agent_router)
    operation = _operation(status="succeeded", revision=4)
    context = {
        "group": _group("v4", [_v4_definition()]),
        "scenarios": [_scenario(cell="d1_v1")],
        "signposts": [],
        "events": [_event(101)],
        "operation": operation,
        "legacy_template_dimensions": [],
        "legacy_snapshot_dimension_values": [],
    }
    context["group"]["generation_diagnostics"] = _v4_diagnostics()

    with patch.object(ScenarioGroupService, "load_presentation_detail", return_value=context) as load:
        response = TestClient(app).get(
            "/scenario-groups/120/presentation/follow-up-request-bodies",
            params={"userId": 10603, "operationId": operation.operation_id},
        )
        latest_response = TestClient(app).get(
            "/scenario-groups/120/presentation/follow-up-request-bodies",
            params={"userId": 10603},
        )

    assert response.status_code == 200
    assert latest_response.status_code == 200
    assert response.json()["validationRequestBody"]["userId"] == 10603
    assert response.json()["signpostRequestBody"]["table"]["rows"][0]["cells"] == {"d1": "d1_v1"}
    assert load.call_args_list[0].args == (120,)
    assert load.call_args_list[0].kwargs == {"operation_id": operation.operation_id}
    assert load.call_args_list[1].args == (120,)
    assert load.call_args_list[1].kwargs == {"operation_id": None}


def test_scenario_group_table_view_returns_metadata_and_labeled_dimension_keys() -> None:
    app = FastAPI()
    app.include_router(agent_router)
    group = {**_group("v4", [_v4_definition()]), "del_yn": "N"}
    context = {
        "group": group,
        "scenarios": [_scenario(cell="d1_v1")],
        "signposts": [],
        "events": [_event(101)],
        "latest_operation": None,
    }

    with patch.object(ScenarioGroupService, "load_common_detail", return_value=context):
        response = TestClient(app).get(
            "/scenario-groups/120",
            params={"view": "table"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert list(payload) == ["scenarioGroup", "table"]
    assert list(payload["scenarioGroup"]) == [
        "delYn",
        "scenarioGroupId",
        "miEventId",
        "eventTypeL2Id",
        "requestUsrId",
        "title",
        "summary",
        "description",
        "dimensionSelected",
        "scenarioCount",
        "status",
        "stage",
        "apiVersion",
    ]
    assert payload["scenarioGroup"]["dimensionSelected"] == ["d1|수급 방향"]
    assert payload["table"]["headers"][0]["label"] == "수급 방향"


def test_presentation_service_uses_latest_operation_when_query_is_omitted() -> None:
    service = ScenarioGroupService()
    operation = _operation()
    detail = {
        "group": _group("v4", []),
        "scenarios": [],
        "signposts": [],
    }
    with (
        patch.object(service, "load_detail", return_value=detail),
        patch.object(service, "load_event_ids", return_value=[101]),
        patch(
            "apps.agents.scenario_group_agent.persistence.event_service.EventService.load_events",
            return_value=[_event(101)],
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationService.get_latest",
            return_value=operation,
        ) as get_latest,
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationService.get_operation",
        ) as get_operation,
        patch(
            "apps.agents.scenario_group_agent.persistence.model_impact_lever_service."
            "ModelImpactLeverService.load_display_labels",
            return_value={"inventory_condition": "재고 여건"},
        ) as load_display_labels,
    ):
        result = service.load_presentation_detail(120)

    assert result["operation"] is operation
    assert result["lever_labels"] == {"inventory_condition": "재고 여건"}
    get_latest.assert_called_once_with(120)
    get_operation.assert_not_called()
    load_display_labels.assert_called_once_with()
