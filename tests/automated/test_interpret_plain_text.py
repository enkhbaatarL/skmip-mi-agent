from __future__ import annotations

import unittest

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    GroupSynthesisOut,
    PriceInterpretationCallbackItem,
    ScenarioComparisonOut,
)
from apps.agents.interpret_agent.prompts import group_synthesizer, scenario_interpreter
from apps.agents.interpret_agent.utils.plain_text import to_plain_text


FORBIDDEN_MARKERS = ("**", "__", "`", "<strong", "<b>", "<em", "<i>")


class InterpretPlainTextTest(unittest.TestCase):
    def assert_plain_text(self, value: str) -> None:
        for marker in FORBIDDEN_MARKERS:
            self.assertNotIn(marker, value)
        for line in value.splitlines():
            self.assertFalse(line.lstrip().startswith("# "))
            self.assertFalse(line.lstrip().startswith("> "))

    def test_sanitizer_removes_rich_text_and_preserves_meaning(self) -> None:
        rich_text = (
            "## **공급 충격**\n"
            "> __동인__과 <strong>JKM</strong>, `TTF`\n"
            "[근거](https://example.com/report)\n"
            "■ -0.5 / model_parameter / 2 * 3"
        )

        result = to_plain_text(rich_text)

        self.assertEqual(
            result,
            ("공급 충격\n동인과 JKM, TTF\n근거 (https://example.com/report)\n■ -0.5 / model_parameter / 2 * 3"),
        )
        self.assert_plain_text(result)

    def test_sanitizer_removes_incomplete_bold_markers_without_damaging_plain_text(self) -> None:
        result = to_plain_text("**미완성 강조\n__잔여 표식\n-0.5, +0.003, model_parameter, 2 * 3")

        self.assertEqual(
            result,
            "미완성 강조\n잔여 표식\n-0.5, +0.003, model_parameter, 2 * 3",
        )
        self.assert_plain_text(result)

    def test_sanitizer_converts_markdown_lists_and_preserves_domain_values(self) -> None:
        result = to_plain_text(
            "- **조달 점검**\n"
            "* 재고 확인\n"
            "+ 헤지 검토\n"
            "1. 우선 대응\n"
            "    indented code\n"
            "---\n"
            "-0.5, <JKM>, JKM <Base> 대비, 2 * 3",
        )

        self.assertEqual(
            result,
            ("• 조달 점검\n• 재고 확인\n• 헤지 검토\n1) 우선 대응\nindented code\n\n-0.5, JKM, JKM Base 대비, 2 * 3"),
        )
        self.assert_plain_text(result)

    def test_output_schemas_normalize_every_user_visible_text_field(self) -> None:
        scenario = ScenarioComparisonOut(
            scenario_id="315",
            identity="**공급 충격**",
            driver_phase="## __동인__",
            price_character="<strong>가격</strong>",
            summary="`대응`과 [근거](https://example.com)",
        )
        synthesis = GroupSynthesisOut(
            overall_message="**종합**\n■ <em>점검</em>",
        )
        callback = PriceInterpretationCallbackItem(
            scenario_id=315,
            content="## **제목**\n<strong>본문</strong>",
        )

        self.assertEqual(scenario.identity, "공급 충격")
        self.assertEqual(scenario.driver_phase, "동인")
        self.assertEqual(scenario.price_character, "가격")
        self.assertEqual(scenario.summary, "대응과 근거 (https://example.com)")
        self.assertEqual(synthesis.overall_message, "종합\n■ 점검")
        self.assertEqual(callback.content, "제목\n본문")
        for value in (
            scenario.identity,
            scenario.driver_phase,
            scenario.price_character,
            scenario.summary,
            synthesis.overall_message,
            callback.content,
        ):
            self.assert_plain_text(value)

    def test_prompts_require_plain_text_and_no_longer_request_bold_headlines(self) -> None:
        scenario_user_prompt = scenario_interpreter.build_user_prompt(
            scenario_id="315",
            feature_metrics=[],
            price_metrics=[],
            data_quality=[],
        )
        group_user_prompt = group_synthesizer.build_user_prompt(scenarios_brief=[])
        prompt_text = "\n".join(
            (
                scenario_interpreter.SYSTEM_PROMPT,
                scenario_user_prompt,
                group_synthesizer.SYSTEM_PROMPT,
                group_user_prompt,
            )
        )

        self.assertNotIn("굵게 표기되는", prompt_text)
        self.assertNotIn("굵은 헤드라인", prompt_text)
        self.assertIn("일반 텍스트", prompt_text)
        self.assertIn("Markdown", prompt_text)
        self.assertIn("HTML", prompt_text)
        self.assertIn("**", prompt_text)
        self.assertIn("표식은 금지", prompt_text)

        scenario_schema = scenario_interpreter.ScenarioComparisonLLMOutput.model_json_schema()
        for field in ("identity", "driver_phase", "price_character", "summary"):
            description = scenario_schema["properties"][field]["description"]
            self.assertIn("일반 텍스트", description)
        group_schema = group_synthesizer.GroupSynthesisLLMOutput.model_json_schema()
        self.assertIn("일반 텍스트", group_schema["properties"]["overall_message"]["description"])


if __name__ == "__main__":
    unittest.main()
