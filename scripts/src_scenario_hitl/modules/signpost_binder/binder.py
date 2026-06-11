from __future__ import annotations

from typing import Any

from stage_integrated_signpost import run_signpost_pipeline


def attach_signposts(scenario_state: dict[str, Any]) -> dict[str, Any]:
    return run_signpost_pipeline(scenario_state)
