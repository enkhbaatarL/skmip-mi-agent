# ruff: noqa: S101

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    generate_dimension_values,
)
from apps.agents.scenario_group_agent.schemas.domain.template import (
    ScenarioTemplate,
    ScenarioTemplateDimension,
    ScenarioTemplateEnum,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.subgraphs.scenario_review.review_stages import (
    DimensionValueGenerationOutput,
    GeneratedDimensionCell,
)
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

    async def test_new_scenario_with_null_in_required_dim_raises(self) -> None:
        # severity 는 필수 분기(required=True)이므로, 신규 시나리오가 null 로 두면
        # (기존/신규 여부와 무관하게) 에러여야 한다.
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
        state.scenarios = [
            {
                "scenario_id": 100,
                "dimension_values": {"period": "단기", "severity": "낮음"},
            },
        ]

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ):
            with self.assertRaises(MIBaseError) as ctx:
                await generate_dimension_values(state)

        assert "new" in ctx.exception.error_message

    async def test_new_scenario_with_null_in_optional_dim_is_filled(self) -> None:
        # recovery 는 선택 분기(required=False) → 신규 시나리오가 null 이어도
        # 에러 없이 Agent 가 채워야 한다.
        headers = HEADERS + [{"key": "recovery", "label": "회복", "display_order": 3}]
        rows = [
            {
                "scenario_id": 100,
                "title": "existing",
                "cells": {"period": "단기", "severity": "낮음", "recovery": "빠름"},
            },
            {
                "scenario_id": None,
                "title": "new",
                "cells": {"period": "장기", "severity": "높음", "recovery": None},
            },
        ]
        state = _state(headers, rows)
        # 초안(persisted) 시나리오에는 recovery 가 없다 → recovery 는 나중에 추가된 분기.
        state.scenarios = [
            {
                "scenario_id": 100,
                "dimension_values": {"period": "단기", "severity": "낮음"},
            },
        ]

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ), patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "generate_new_dimension_values",
            new=AsyncMock(return_value={1: {"recovery": "느림"}}),
        ):
            result = await generate_dimension_values(state)

        assert result["request_table"]["rows"][1]["cells"]["recovery"] == "느림"

    async def test_existing_scenario_null_in_required_dim_raises(self) -> None:
        # 기존(existing) 시나리오의 필수 분기(required=True)를 사용자가 null 로 비우면
        # 에러여야 한다.
        rows = [
            {
                "scenario_id": 100,
                "title": "a",
                "cells": {"period": "단기", "severity": "낮음"},
            },
            {
                "scenario_id": 101,
                "title": "b",
                "cells": {"period": "장기", "severity": None},
            },
        ]
        state = _state(HEADERS, rows)
        state.scenarios = [
            {
                "scenario_id": 100,
                "dimension_values": {"period": "단기", "severity": "낮음"},
            },
            {
                "scenario_id": 101,
                "dimension_values": {"period": "장기", "severity": "높음"},
            },
        ]

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ):
            with self.assertRaises(MIBaseError) as ctx:
                await generate_dimension_values(state)

        assert "b" in ctx.exception.error_message
        assert "강도" in ctx.exception.error_message

    async def test_existing_scenario_null_in_optional_dim_is_filled(self) -> None:
        # 기존(existing) 시나리오라도 선택 분기(required=False)의 부분 null 은 Agent 가 채운다.
        headers = HEADERS + [{"key": "recovery", "label": "회복", "display_order": 3}]
        rows = [
            {
                "scenario_id": 100,
                "title": "a",
                "cells": {"period": "단기", "severity": "낮음", "recovery": "빠름"},
            },
            {
                "scenario_id": 101,
                "title": "b",
                "cells": {"period": "장기", "severity": "높음", "recovery": None},
            },
        ]
        state = _state(headers, rows)
        # 초안(persisted) 시나리오에는 recovery 가 없다 → recovery 는 나중에 추가된 분기.
        state.scenarios = [
            {
                "scenario_id": 100,
                "dimension_values": {"period": "단기", "severity": "낮음"},
            },
            {
                "scenario_id": 101,
                "dimension_values": {"period": "장기", "severity": "높음"},
            },
        ]

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ), patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "generate_new_dimension_values",
            new=AsyncMock(return_value={1: {"recovery": "느림"}}),
        ):
            result = await generate_dimension_values(state)

        assert result["request_table"]["rows"][1]["cells"]["recovery"] == "느림"

    async def test_optional_dim_in_draft_null_is_filled(self) -> None:
        # recovery 는 선택 분기(required=False)지만 초안(persisted/dimension_selected)에
        # 이미 포함된 분기다. 그래도 required 기준으로 판단하므로 null 은 에러 없이
        # Agent 가 채워야 한다(구 draft/added 기준이었다면 에러였을 케이스).
        headers = HEADERS + [{"key": "recovery", "label": "회복", "display_order": 3}]
        rows = [
            {
                "scenario_id": 100,
                "title": "a",
                "cells": {"period": "단기", "severity": "낮음", "recovery": "빠름"},
            },
            {
                "scenario_id": 101,
                "title": "b",
                "cells": {"period": "장기", "severity": "높음", "recovery": None},
            },
        ]
        state = _state(headers, rows)
        state.scenario_group["dimension_selected"] = ["period", "severity", "recovery"]
        state.scenarios = [
            {
                "scenario_id": 100,
                "dimension_values": {
                    "period": "단기",
                    "severity": "낮음",
                    "recovery": "빠름",
                },
            },
            {
                "scenario_id": 101,
                "dimension_values": {
                    "period": "장기",
                    "severity": "높음",
                    "recovery": "느림",
                },
            },
        ]

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ), patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "generate_new_dimension_values",
            new=AsyncMock(return_value={1: {"recovery": "느림"}}),
        ):
            result = await generate_dimension_values(state)

        assert result["request_table"]["rows"][1]["cells"]["recovery"] == "느림"

    async def test_required_dim_added_later_null_raises(self) -> None:
        # severity 는 필수 분기(required=True)지만 초안(persisted/dimension_selected)에는
        # 없던, 나중에 추가된 컬럼이다. required 기준으로 판단하므로 null 은 에러여야 한다
        # (구 draft/added 기준이었다면 Agent 가 채웠을 케이스).
        rows = [
            {
                "scenario_id": 100,
                "title": "a",
                "cells": {"period": "단기", "severity": None},
            },
        ]
        state = _state(HEADERS, rows)
        state.scenario_group["dimension_selected"] = ["period"]
        state.scenarios = [
            {
                "scenario_id": 100,
                "dimension_values": {"period": "단기"},
            },
        ]

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioService.load_scenario_template",
            return_value=_template(),
        ):
            with self.assertRaises(MIBaseError) as ctx:
                await generate_dimension_values(state)

        assert "강도" in ctx.exception.error_message

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
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.review_stages."
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
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.review_stages."
            "_invoke_dimension_values",
            new=AsyncMock(return_value=generated),
        ):
            result = await generate_dimension_values(state)

        # Out-of-enum value is replaced by the deterministic fallback (first enum).
        assert result["request_table"]["rows"][0]["cells"]["recovery"] == "빠름"


if __name__ == "__main__":
    unittest.main()
