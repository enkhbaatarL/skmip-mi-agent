# ruff: noqa: S101

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.agents.scenario_group_agent.routers.scenario_generation_sync import router
from apps.agents.scenario_group_agent.schemas.endpoint import (
    ValidateScenariosCallBackScenarioGroup,
    ValidateScenariosOut,
)


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestScenarioGenerationSyncRouter:
    def test_validate_scenarios_sync_returns_callback_body(self) -> None:
        with (
            patch(
                "apps.agents.scenario_group_agent.routers.scenario_generation_sync.prepare_validate_scenarios",
                return_value={
                    "scenario_group_id": 10,
                    "user_id": 101,
                    "request_table": {"headers": [], "rows": []},
                },
            ),
            patch(
                "apps.agents.scenario_group_agent.routers.scenario_generation_sync.run_validate_scenarios_inline",
                new=AsyncMock(
                    return_value=ValidateScenariosOut(
                        result="success",
                        is_valid=True,
                        reason=None,
                        scenario_group=ValidateScenariosCallBackScenarioGroup(
                            scenario_group_id=10,
                            status="creating",
                            stage="scenario_validated",
                        ),
                        table=None,
                    ),
                ),
            ) as run_inline,
        ):
            response = _client().post(
                "/scenario-groups/10/validation/sync",
                json={"userId": 101, "table": {"headers": [], "rows": []}},
            )

        assert response.status_code == 200
        assert response.json()["result"] == "success"
        assert response.json()["isValid"] is True
        assert response.json()["scenarioGroup"]["scenarioGroupId"] == 10
        run_inline.assert_awaited_once_with(
            scenario_group_id=10,
            user_id=101,
            request_table={"headers": [], "rows": []},
        )

    def test_create_signposts_sync_returns_failure_body_when_graph_fails(self) -> None:
        with (
            patch(
                "apps.agents.scenario_group_agent.routers.scenario_generation_sync.prepare_create_signposts",
                return_value={
                    "scenario_group_id": 10,
                    "user_id": 101,
                    "request_table": {"headers": [], "rows": []},
                },
            ),
            patch(
                "apps.agents.scenario_group_agent.routers.scenario_generation_sync.run_create_signposts_inline",
                new=AsyncMock(side_effect=RuntimeError("graph failed")),
            ),
        ):
            response = _client().post(
                "/scenario-groups/10/signposts/sync",
                json={"userId": 101, "table": {"headers": [], "rows": []}},
            )

        assert response.status_code == 200
        assert response.json() == {
            "result": "failure",
            "reason": "graph failed",
            "scenarioGroup": None,
            "table": None,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
