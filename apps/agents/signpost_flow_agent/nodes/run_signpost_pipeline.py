"""
Node: Run Signpost Generation Pipeline

For each scenario loaded from DB:
1. Check if signposts already exist → skip
2. Run Stages 2~5 → generate signposts
3. Collect results
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from apps.agents.signpost_flow_agent.services.signpost_db_service import SignpostDbService
from apps.agents.signpost_flow_agent.services.signpost_pipeline import build_signposts_for_scenario
from apps.agents.signpost_flow_agent.state.signpost_flow_state import SignpostFlowState
from apps.common.logging.logger_config import logger as app_logger

_MAX_CONCURRENT_SCENARIOS = 7


async def _process_one_scenario(
    scenario: dict[str, Any],
    base_event_summary: dict[str, str],
    sem: asyncio.Semaphore,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Check existence and generate signposts for a single scenario."""
    scenario_id = scenario.get("scenario_id", 0)
    scenario_title = scenario.get("title", "")
    db_service = SignpostDbService()

    async with sem:
        try:
            exists = await asyncio.to_thread(db_service.check_signposts_exist, int(scenario_id))
        except Exception as e:
            app_logger.error("Existence check failed for scenario_id={}: {}", scenario_id, e)
            return [], {
                "scenario_id": scenario_id,
                "status": "failure",
                "message": f"Existence check failed: {e}",
            }

        if exists:
            app_logger.info("Signposts already exist, skipping scenario_id={}", scenario_id)
            return [], {
                "scenario_id": scenario_id,
                "status": "already_exist",
                "message": "Signposts already exist",
            }

        try:
            signposts = await build_signposts_for_scenario(scenario, base_event_summary)
            if signposts:
                app_logger.info("Generated {} signposts for scenario_id={}", len(signposts), scenario_id)
            return signposts, {
                "scenario_id": scenario_id,
                "title": scenario_title,
                "status": "success",
                "signpost_count": len(signposts),
                "message": f"Generated {len(signposts)} signposts",
            }
        except Exception as e:
            app_logger.error("Pipeline failed for scenario_id={}: {}", scenario_id, e)
            return [], {
                "scenario_id": scenario_id,
                "status": "failure",
                "message": str(e),
            }


async def run_signpost_pipeline(state: SignpostFlowState) -> dict[str, Any]:
    """Execute complete signpost generation pipeline for each scenario concurrently.

    Args:
        state: Current flow state with scenarios_from_db and stage1_context_pack
               from load_event_from_db

    Returns:
        State updates with signposts_generated and per-scenario results

    """
    if state.scenarios_from_db is None:
        return {
            "error": "scenarios_from_db is None. Ensure load_event_from_db ran successfully.",
        }

    if state.stage1_context_pack is None:
        return {
            "error": "stage1_context_pack is None. Ensure load_event_from_db ran successfully.",
        }

    c1 = state.stage1_context_pack.get("C1_base_event", {})
    base_event_summary = {
        "title": c1.get("title", ""),
        "summary": c1.get("summary", ""),
        "driver": c1.get("driver", ""),
    }

    scenarios = state.scenarios_from_db
    app_logger.info(
        "Processing {} scenarios for signposts (concurrent, max={})",
        len(scenarios),
        _MAX_CONCURRENT_SCENARIOS,
    )

    sem = asyncio.Semaphore(_MAX_CONCURRENT_SCENARIOS)
    results = await asyncio.gather(
        *[_process_one_scenario(scenario, base_event_summary, sem) for scenario in scenarios],
    )

    all_generated_signposts: list[dict[str, Any]] = []
    scenario_results: list[dict[str, Any]] = []
    for signposts, result in results:
        all_generated_signposts.extend(signposts)
        scenario_results.append(result)

    return {
        "signposts_generated": all_generated_signposts,
        "scenario_results": scenario_results,
        "completed_at": datetime.utcnow(),
        "error": None,
    }
