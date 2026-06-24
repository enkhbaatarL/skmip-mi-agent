# ruff: noqa: PT009, S101

from __future__ import annotations

import ast
from pathlib import Path
import unittest


GENERATION_STAGES_PATH = (
    Path(__file__).parents[2]
    / "apps"
    / "agents"
    / "scenario_group_agent"
    / "subgraphs"
    / "scenario_generation"
    / "generation_stages.py"
)


class ScenarioGroupPipelineContractTest(unittest.TestCase):
    def test_generation_stages_has_no_file_template_registry_loader(self) -> None:
        source = GENERATION_STAGES_PATH.read_text(encoding="utf-8")

        self.assertNotIn("TEMPLATE_REGISTRY", source)
        self.assertNotIn("_load_template_registry", source)
        self.assertNotIn("_resolve_template_registry_paths", source)
        self.assertNotIn("template_registry", source)
        self.assertNotIn("FileNotFoundError", source)

    def test_generation_stages_has_no_scenario_agent_dependency(self) -> None:
        source = GENERATION_STAGES_PATH.read_text(encoding="utf-8")

        self.assertNotIn("apps.agents.scenario_agent", source)

    def test_generation_stages_is_valid_python(self) -> None:
        source = GENERATION_STAGES_PATH.read_text(encoding="utf-8")

        ast.parse(source, filename=str(GENERATION_STAGES_PATH))


if __name__ == "__main__":
    unittest.main()
