# ruff: noqa: S101

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    generate_dimension_values,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.review import (
    DimensionValueGenerationOutput,
    GeneratedDimensionCell,
)
from apps.agents.scenario_group_agent.schemas.common import (
    ScenarioTemplate,
    ScenarioTemplateDimension,
    ScenarioTemplateEnum,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.common.exceptions.custom import MIBaseError


def _template() -> ScenarioTemplate:
    return ScenarioTemplate(
        template_dimensions_total=3,
        dimensions=[
            ScenarioTemplateDimension(
                dimension_id="period",
                label_ko="기간",
                description="기간",
                required=True,
                enum=[
                    ScenarioTemplateEnum(id="period_v1", label="단기"),
                    ScenarioTemplateEnum(id="period_v2", label="장기", tail=True),
                ],
            ),
            ScenarioTemplateDimension(
                dimension_id="severity",
                label_ko="강도",
                description="강도",
                required=True,
                enum=[
                    ScenarioTemplateEnum(id="severity_v1", label="낮음"),
                    ScenarioTemplateEnum(id="severity_v2", label="높음", tail=True),
                ],
            ),
            ScenarioTemplateDimension(
                dimension_id="recovery",
                label_ko="회복",
                description="회복",
                required=False,
                enum=[
                    ScenarioTemplateEnum(id="recovery_v1", label="빠름"),
                    ScenarioTemplateEnum(id="recovery_v2", label="느림", tail=True),
                ],
            ),
        ],
    )


def _state(headers: list[dict], rows: list[dict]) -> ScenarioDesignState:
    return ScenarioDesignState(
        scenario_group_id=10,
        user_id=1,
        scenario_group={"scenario_group_id": 10, "event_type_l2_id": 30},
        request_table={"headers": headers, "rows": rows},
    )


HEADERS = [
    {"key": "period", "label": "기간", "display_order": 1},
    {"key": "severity", "label": "강도", "display_order": 2},
]


class GenerateDimensionValuesNodeTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_required_dimension_raises(self) -> None:
        headers = [{"key": "period", "label": "기간", "display_order": 1}]
        rows = [
            {"scenario_id": 100, "title": "a", "cells": {"period": "단기"}},
        ]
        state = _state(headers, rows)

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ):
            with self.assertRaises(MIBaseError) as ctx:
                await generate_dimension_values(state)

        assert "강도" in ctx.exception.error_message

    async def test_new_scenario_with_null_cell_raises(self) -> None:
        rows = [
            {
                "scenario_id": 100,
                "title": "existing",
                "cells": {"period": "단기", "severity": "낮음"},
            },
            {
                "scenario_id": None,
                "title": "new",
                "cells": {"period": "장기", "severity": None},
            },
        ]
        state = _state(HEADERS, rows)

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ):
            with self.assertRaises(MIBaseError) as ctx:
                await generate_dimension_values(state)

        assert "new" in ctx.exception.error_message

    async def test_null_column_is_auto_filled(self) -> None:
        headers = HEADERS + [{"key": "recovery", "label": "회복", "display_order": 3}]
        rows = [
            {
                "scenario_id": 100,
                "title": "a",
                "cells": {"period": "단기", "severity": "낮음", "recovery": None},
            },
            {
                "scenario_id": 101,
                "title": "b",
                "cells": {"period": "장기", "severity": "높음", "recovery": None},
            },
        ]
        state = _state(headers, rows)

        generated = SimpleNamespace(
            result=DimensionValueGenerationOutput(
                items=[
                    GeneratedDimensionCell(
                        scenario_index=0, dim_key="recovery", value="빠름"
                    ),
                    GeneratedDimensionCell(
                        scenario_index=1, dim_key="recovery", value="느림"
                    ),
                ]
            )
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ), patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_dimension_values",
            new=AsyncMock(return_value=generated),
        ):
            result = await generate_dimension_values(state)

        filled = result["request_table"]["rows"]
        assert filled[0]["cells"]["recovery"] == "빠름"
        assert filled[1]["cells"]["recovery"] == "느림"

    async def test_auto_fill_uses_persisted_narrative_without_returning_it(self) -> None:
        headers = HEADERS + [{"key": "recovery", "label": "회복", "display_order": 3}]
        rows = [
            {
                "scenario_id": 100,
                "title": "",
                "cells": {"period": "단기", "severity": "낮음", "recovery": None},
            },
        ]
        state = _state(headers, rows)
        state.scenarios = [
            {
                "scenario_id": 100,
                "title": "persisted title",
                "narrative": "persisted narrative",
            },
        ]

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ), patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "generate_new_dimension_values",
            new=AsyncMock(return_value={0: {"recovery": "빠름"}}),
        ) as generate:
            result = await generate_dimension_values(state)

        generation_rows = generate.call_args.args[1]
        assert generation_rows[0]["title"] == "persisted title"
        assert generation_rows[0]["narrative"] == "persisted narrative"
        returned_row = result["request_table"]["rows"][0]
        assert "narrative" not in returned_row
        assert returned_row["cells"]["recovery"] == "빠름"

    async def test_out_of_enum_value_falls_back(self) -> None:
        headers = HEADERS + [{"key": "recovery", "label": "회복", "display_order": 3}]
        rows = [
            {
                "scenario_id": 100,
                "title": "a",
                "cells": {"period": "단기", "severity": "낮음", "recovery": None},
            },
        ]
        state = _state(headers, rows)

        generated = SimpleNamespace(
            result=DimensionValueGenerationOutput(
                items=[
                    GeneratedDimensionCell(
                        scenario_index=0, dim_key="recovery", value="없는값"
                    ),
                ]
            )
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ), patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_dimension_values",
            new=AsyncMock(return_value=generated),
        ):
            result = await generate_dimension_values(state)

        # Out-of-enum value is replaced by the deterministic fallback (first enum).
        assert result["request_table"]["rows"][0]["cells"]["recovery"] == "빠름"


if __name__ == "__main__":
    unittest.main()
