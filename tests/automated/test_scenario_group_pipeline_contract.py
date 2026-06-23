# ruff: noqa: PT009, S101

from __future__ import annotations

import ast
from pathlib import Path
import unittest


PIPELINE_PATH = (
    Path(__file__).parents[2]
    / "apps"
    / "agents"
    / "scenario_group_agent"
    / "subgraphs"
    / "scenario_generation"
    / "pipeline.py"
)


class ScenarioGroupPipelineContractTest(unittest.TestCase):
    def test_pipeline_has_no_file_template_registry_loader(self) -> None:
        source = PIPELINE_PATH.read_text(encoding="utf-8")

        self.assertNotIn("TEMPLATE_REGISTRY", source)
        self.assertNotIn("_load_template_registry", source)
        self.assertNotIn("_resolve_template_registry_paths", source)
        self.assertNotIn("template_registry", source)
        self.assertNotIn("FileNotFoundError", source)

    def test_pipeline_has_no_scenario_agent_dependency(self) -> None:
        source = PIPELINE_PATH.read_text(encoding="utf-8")

        self.assertNotIn("apps.agents.scenario_agent", source)

    def test_pipeline_is_valid_python(self) -> None:
        source = PIPELINE_PATH.read_text(encoding="utf-8")

        ast.parse(source, filename=str(PIPELINE_PATH))


if __name__ == "__main__":
    unittest.main()
