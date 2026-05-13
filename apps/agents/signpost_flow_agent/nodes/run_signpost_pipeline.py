"""
Node: Run Signpost Generation Pipeline

For each scenario loaded from DB:
1. Check if signposts already exist → skip
2. Run Stages 2~5 → generate signposts
3. Collect results
"""
from datetime import datetime
from typing import Any, Dict, List

from apps.agents.signpost_flow_agent.services.signpost_db_service import SignpostDbService
from apps.agents.signpost_flow_agent.services.signpost_pipeline import build_signposts_for_scenario
from apps.agents.signpost_flow_agent.state.signpost_flow_state import SignpostFlowState
from apps.common.logging.logger_config import logger as app_logger


def run_signpost_pipeline(state: SignpostFlowState) -> Dict[str, Any]:
    """
    Execute complete signpost generation pipeline for each scenario.

    Args:
        state: Current flow state with scenarios_from_db and stage1_context_pack
               from load_event_from_db

    Returns:
        State updates with signposts_generated and per-scenario results
    """
    if state.scenarios_from_db is None:
        return {
            "error": "scenarios_from_db is None. Ensure load_event_from_db ran successfully."
        }

    if state.stage1_context_pack is None:
        return {
            "error": "stage1_context_pack is None. Ensure load_event_from_db ran successfully."
        }

    # Extract base event summary for LLM context
    c1 = state.stage1_context_pack.get("C1_base_event", {})
    base_event_summary = {
        "title": c1.get("title", ""),
        "summary": c1.get("summary", ""),
        "driver": c1.get("driver", ""),
    }

    db_service = SignpostDbService()
    all_generated_signposts: List[Dict[str, Any]] = []
    scenario_results: List[Dict[str, Any]] = []

    scenarios = state.scenarios_from_db
    app_logger.info("Processing {} scenarios for signposts", len(scenarios))

    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", 0)
        scenario_title = scenario.get("title", "")

        # Step 1: Check if signposts already exist for this scenario
        try:
            exists = db_service.check_signposts_exist(int(scenario_id))
        except Exception as e:
            app_logger.error("Existence check failed for scenario_id={}: {}", scenario_id, e)
            scenario_results.append({
                "scenario_id": scenario_id,
                "status": "failure",
                "message": f"Existence check failed: {e}",
            })
            continue

        if exists:
            app_logger.info("Signposts already exist, skipping scenario_id={}", scenario_id)
            scenario_results.append({
                "scenario_id": scenario_id,
                "status": "already_exist",
                "message": "Signposts already exist",
            })
            continue

        # Step 2: Generate signposts
        try:
            signposts = build_signposts_for_scenario(scenario, base_event_summary)
            if signposts:
                all_generated_signposts.extend(signposts)
                app_logger.info(
                    "Generated {} signposts for scenario_id={}",
                    len(signposts),
                    scenario_id,
                )
            scenario_results.append({
                "scenario_id": scenario_id,
                "title": scenario_title,
                "status": "success",
                "signpost_count": len(signposts),
                "message": f"Generated {len(signposts)} signposts",
            })
        except Exception as e:
            app_logger.error("Pipeline failed for scenario_id={}: {}", scenario_id, e)
            scenario_results.append({
                "scenario_id": scenario_id,
                "status": "failure",
                "message": str(e),
            })

    return {
        "signposts_generated": all_generated_signposts,
        "scenario_results": scenario_results,
        "completed_at": datetime.utcnow(),
        "error": None,
    }