# ruff: noqa: S101

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
SCENARIO_PIPELINE = (
    ROOT
    / "apps"
    / "agents"
    / "scenario_group_agent"
    / "subgraphs"
    / "scenario_generation"
    / "pipeline.py"
)


def test_scenario_stage4_prompt_and_schema_include_text_length_guidance() -> None:
    source = SCENARIO_PIPELINE.read_text(encoding="utf-8")

    assert "title 은 1줄이며, 공백과 문장부호를 포함해 100자 이내" in source
    assert "description 은 3~5줄이며, 공백과 문장부호를 포함해 300~500자" in source
    assert "각 narrative 의 title 은 한 줄이며, 공백과 문장부호를 포함해 100자 이내" in source
    assert "각 narrative 의 description 은 3~5줄이며, 공백과 문장부호를 포함해 300~500자" in source
    assert "공백과 문장부호를 포함해 100자 이내." in source
    assert "공백과 문장부호를 포함해 300~500자." in source


def test_scenario_group_metadata_prompt_includes_text_length_guidance() -> None:
    source = SCENARIO_PIPELINE.read_text(encoding="utf-8")

    assert "Scenario Group Metadata Writer" in source
    assert "SCENARIO_GROUP_METADATA_RULES" in source
    assert "title 은 공백과 문장부호를 포함해 100자 이내." in source
    assert "description 은 공백과 문장부호를 포함해 300~400자." in source
    assert "기존 detail_analysis를 그대로 복사하지 말고" in source
