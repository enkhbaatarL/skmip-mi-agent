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
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_flow import (
    _with_event_lineage,
)
from apps.common.configs.config import Settings
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import DimensionDefinition
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


def test_multi_event_prepare_preserves_request_event_order() -> None:
    payload = MultiEventCreateScenariosIn(
        mi_event_ids=[202, 101],
        user_id=7,
        comparison_run_id="compare-order",
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


def test_v4_sync_requires_run_id_and_adds_event_type_lineage() -> None:
    payload = V4MultiEventCreateScenariosSyncIn(
        mi_event_ids=[101, 202],
        target_market="JKM",
        user_id=7,
        comparison_run_id="compare-1",
    )
    definition = DimensionDefinition(
        dimension_id="supply_pressure",
        label="공급 압력",
        description="선택 Event의 공급 영향을 결합한다.",
        display_order=1,
        source_event_ids=[101, 202],
        lever_refs=["liquefaction_availability"],
    )
    definitions = _with_event_lineage(
        [definition],
        [
            EventPayload(mi_event_id=101, event_type_l2_id=8),
            EventPayload(mi_event_id=202, event_type_l2_id=12),
        ],
    )

    assert payload.comparison_run_id == "compare-1"
    assert {(source.event_id, source.event_type_l2_id) for source in definitions[0].source_refs} == {
        (101, 8),
        (202, 12),
    }
    with pytest.raises(ValueError, match="comparisonRunId"):
        V4MultiEventCreateScenariosSyncIn(
            mi_event_ids=[101, 202],
            target_market="JKM",
            user_id=7,
        )
