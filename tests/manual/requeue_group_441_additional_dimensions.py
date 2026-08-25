from __future__ import annotations

# ruff: noqa: CPY001, E402
import asyncio
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.agents.scenario_group_agent.flows.add_dimension.flow import (
    get_additional_dimensions,
    run_additional_dimension_generation,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.common.logging.logger_config import logger


TARGET_SCENARIO_GROUP_ID = 441


async def main() -> None:
    service = ScenarioGroupService()
    queued = await asyncio.to_thread(
        service.requeue_empty_ready_additional_dimension_generation,
        TARGET_SCENARIO_GROUP_ID,
    )
    logger.info(
        "Group 441 Additional Dimension manually requeued | scenario_group_id={} | status={} | source_count={}",
        TARGET_SCENARIO_GROUP_ID,
        queued["status"],
        len(queued["source_uncertainty_ids"]),
    )
    await run_additional_dimension_generation(TARGET_SCENARIO_GROUP_ID)
    output = await asyncio.to_thread(get_additional_dimensions, TARGET_SCENARIO_GROUP_ID)
    loaded = await asyncio.to_thread(service.load_additional_dimensions, TARGET_SCENARIO_GROUP_ID)
    stored_definition_ids = {
        str(item.get("dimension_id") or item.get("dimensionId")) for item in loaded["dimension_definitions"]
    }
    returned_candidate_ids = {
        item.dimension_id
        for item in (output.data.dimension_definitions.items if output.data is not None else [])
        if item.dimension_id not in stored_definition_ids
    }
    if output.data is None or output.data.generation_status != "ready" or not returned_candidate_ids:
        message = "Group 441 Additional Dimension regeneration did not produce an available candidate"
        raise RuntimeError(message)
    logger.info(
        "Group 441 Additional Dimension regeneration verified | scenario_group_id={} | candidate_count={}",
        TARGET_SCENARIO_GROUP_ID,
        len(returned_candidate_ids),
    )


if __name__ == "__main__":
    asyncio.run(main())
