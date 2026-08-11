from __future__ import annotations

# ruff: noqa: S101
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import pytest

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    MultiEventCreateScenariosIn,
    V4MultiEventCreateScenariosSyncIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.flow import (
    prepare_multi_event_scenarios,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDefinition,
    V4DimensionValueDefinition,
    V4LeverState,
)
from apps.common.configs.config import Settings
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


def test_cors_allowed_origins_env_accepts_comma_and_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://dev.example, https://staging.example/",
    )
    comma_settings = Settings()
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["https://one.example", "https://two.example"]',
    )
    json_settings = Settings()

    assert comma_settings.cors_allowed_origins == [
        "https://dev.example",
        "https://staging.example",
    ]
    assert json_settings.cors_allowed_origins == [
        "https://one.example",
        "https://two.example",
    ]


def test_cors_preflight_reflects_only_allowed_origin() -> None:
    from main import app

    client = TestClient(app)
    allowed = client.options(
        "/events",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    disallowed = client.options(
        "/events",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-origin" not in disallowed.headers


def test_multi_event_validation_error_is_json_serializable() -> None:
    from main import app

    response = TestClient(app).post(
        "/v2/scenario-groups/sync",
        json={"miEventIds": [101, 101], "userId": 7},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "value_error"


def test_multi_event_prepare_preserves_request_event_order() -> None:
    payload = MultiEventCreateScenariosIn(
        mi_event_ids=[202, 101],
        user_id=7,
    )
    events = [
        EventPayload(mi_event_id=101, event_type_l2_id=8),
        EventPayload(mi_event_id=202, event_type_l2_id=12),
    ]
    template = SimpleNamespace(
        model_dump=Mock(return_value={"template_checksum": "checksum"}),
    )
    group = ScenarioGroupPayload(scenario_group_id=99)

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.flow.EventService.load_events",
            return_value=events,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.flow."
            "ScenarioService.load_pipeline_template_with_metadata",
            return_value=template,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.flow."
            "ScenarioGroupService.prepare_multi_event_group",
            return_value=group,
        ) as prepare_group,
    ):
        prepared = prepare_multi_event_scenarios(payload, api_version="v2")

    assert [int(event.mi_event_id) for event in prepared["events"]] == [202, 101]
    assert [event["mi_event_id"] for event in prepare_group.call_args.kwargs["events"]] == [202, 101]


def test_v4_sync_accepts_one_event_and_keeps_impact_path_lineage() -> None:
    payload = V4MultiEventCreateScenariosSyncIn(
        mi_event_ids=[101],
        user_id=7,
    )
    definition = V4DimensionDefinition(
        dimension_id="supply_pressure",
        label="공급 압력",
        description="선택 Event의 공급 영향을 결합한다.",
        rationale="공급 영향의 변화에 따라 가용 LNG 물량과 JKM 압력이 구분됨",
        source_event_ids=[101, 202],
        source_impact_path_ids=["path_101", "path_202"],
        source_uncertainty_ids=["u_101", "u_202"],
        primary_lever_code="liquefaction_availability",
        primary_impact_lever_id=6,
        dimension_type="magnitude",
        value_kind="categorical",
        model_support_status="partial",
        values=[
            V4DimensionValueDefinition(
                value_id="low",
                label="낮음",
                lever_states=[
                    V4LeverState(
                        impact_lever_id=6,
                        lever_code="liquefaction_availability",
                        direction="recover",
                        level="high_availability",
                        scope="US Gulf",
                        time_window="2주",
                    ),
                ],
                pressure_contribution="bearish",
                assumption_rationale="빠른 회복",
            ),
            V4DimensionValueDefinition(
                value_id="high",
                label="높음",
                lever_states=[
                    V4LeverState(
                        impact_lever_id=6,
                        lever_code="liquefaction_availability",
                        direction="disrupt",
                        level="low_availability",
                        scope="US Gulf",
                        time_window="6주 이상",
                    ),
                ],
                pressure_contribution="bullish",
                assumption_rationale="회복 지연",
            ),
        ],
    )

    assert payload.mi_event_ids == [101]
    assert definition.source_event_ids == [101, 202]
    assert definition.source_impact_path_ids == ["path_101", "path_202"]
    assert "event_groundings" not in definition.model_dump()
    assert "lever_mappings" not in definition.model_dump()
