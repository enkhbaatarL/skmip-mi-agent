from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from apps.agents.interpret_agent.flows.interpret_price import flow
from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    GroupSynthesisOut,
    PriceInterpretationMetaOut,
    PriceInterpretationResult,
    ScenarioComparisonOut,
)


class InterpretCallbackContractTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _result() -> PriceInterpretationResult:
        return PriceInterpretationResult(
            meta=PriceInterpretationMetaOut(
                scenario_group_id=52,
                base_scenario_id="MI Base",
            ),
            scenarios=[
                ScenarioComparisonOut(
                    scenario_id="315",
                    identity="공급 충격 이후 점진적 정상화",
                    driver_phase="공급 감소가 초기 상승을 주도합니다.",
                    price_character="JKM과 TTF가 먼저 상승한 뒤 안정화됩니다.",
                    summary="조달 다변화와 재고 확보가 필요합니다.",
                )
            ],
            synthesis=GroupSynthesisOut(overall_message="그룹 종합 해석"),
        )

    def test_callback_url_keeps_existing_path(self) -> None:
        settings = SimpleNamespace(
            callback_base_url="https://mi.mingovvv.info",
            callback_price_interpretations_path=(
                "/api/v1/mi/next-gen/scenario-groups/"
                "{scenario_group_id}/price-interpretations/callback"
            ),
        )
        with patch("apps.common.configs.config.get_settings", return_value=settings):
            callback_url = flow._resolve_callback_url(52)

        self.assertEqual(
            callback_url,
            "https://mi.mingovvv.info/api/v1/mi/next-gen/"
            "scenario-groups/52/price-interpretations/callback",
        )

    async def test_success_callback_matches_backend_contract(self) -> None:
        send_callback = AsyncMock()
        with (
            patch.object(flow, "run_interpret_price", new=AsyncMock(return_value=self._result())),
            patch.object(
                flow,
                "_resolve_callback_url",
                return_value=(
                    "https://mi.mingovvv.info/api/v1/mi/next-gen/"
                    "scenario-groups/52/price-interpretations/callback"
                ),
            ),
            patch(
                "apps.connectors.callback.callback_client.send_callback",
                new=send_callback,
            ),
        ):
            await flow.run_price_interpretation_background(52, [315])

        callback_url, payload = send_callback.await_args.args
        self.assertEqual(
            callback_url,
            "https://mi.mingovvv.info/api/v1/mi/next-gen/"
            "scenario-groups/52/price-interpretations/callback",
        )
        self.assertEqual(
            payload.model_dump(by_alias=True, mode="json"),
            {
                "result": "success",
                "reason": None,
                "interpretations": [
                    {
                        "scenarioId": 315,
                        "content": (
                            "공급 충격 이후 점진적 정상화\n"
                            "동인 및 국면\n"
                            "공급 감소가 초기 상승을 주도합니다.\n"
                            "가격 특성\n"
                            "JKM과 TTF가 먼저 상승한 뒤 안정화됩니다.\n"
                            "시나리오 요약\n"
                            "조달 다변화와 재고 확보가 필요합니다."
                        ),
                    }
                ],
            },
        )

    async def test_failure_callback_matches_backend_contract(self) -> None:
        send_callback = AsyncMock()
        with (
            patch.object(
                flow,
                "run_interpret_price",
                new=AsyncMock(side_effect=RuntimeError("inference timeout")),
            ),
            patch.object(
                flow,
                "_resolve_callback_url",
                return_value=(
                    "https://mi.mingovvv.info/api/v1/mi/next-gen/"
                    "scenario-groups/52/price-interpretations/callback"
                ),
            ),
            patch(
                "apps.connectors.callback.callback_client.send_callback",
                new=send_callback,
            ),
        ):
            await flow.run_price_interpretation_background(52, [315])

        _, payload = send_callback.await_args.args
        self.assertEqual(
            payload.model_dump(by_alias=True, mode="json"),
            {
                "result": "failure",
                "reason": "inference timeout",
                "interpretations": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
