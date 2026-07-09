from __future__ import annotations

from functools import lru_cache

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes import (
    REF_QUICK_VALIDATE_MAX_RETRIES,
    BuildContextNode,
    QuickValidateNode,
    ReduceValuesNode,
    SelectDimensionsNode,
    SynthesizeScenariosNode,
    ValidateScenariosNode,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.state import (
    ScenarioGenerationState,
)
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext


def _route_after_quick_validate(state: ScenarioGenerationState) -> str:
    if state.skip_generation or state.error:
        return "done"
    if state.validation_feedback is None:
        return "done"
    if state.quick_validate_retry_count > REF_QUICK_VALIDATE_MAX_RETRIES:
        logger.info(
            "[SCENARIO_GENERATION][stage5] quick validate retry limit exceeded; proceeding to stage6 "
            f"| retry_count={state.quick_validate_retry_count} | max_retries={REF_QUICK_VALIDATE_MAX_RETRIES}",
        )
        return "done"
    logger.info(
        "[SCENARIO_GENERATION][stage5] routing back to stage4 for regeneration "
        f"| retry_count={state.quick_validate_retry_count} | max_retries={REF_QUICK_VALIDATE_MAX_RETRIES}",
    )
    return "retry"


def build_scenario_generation_subgraph() -> Runnable:
    graph = StateGraph(state_schema=ScenarioGenerationState, context_schema=TraceContext)
    graph.add_node("build_context", BuildContextNode())
    graph.add_node("select_dimensions", SelectDimensionsNode())
    graph.add_node("reduce_values", ReduceValuesNode())
    graph.add_node("synthesize_scenarios", SynthesizeScenariosNode())
    graph.add_node("quick_validate", QuickValidateNode())
    graph.add_node("validate_scenarios", ValidateScenariosNode())
    graph.set_entry_point("build_context")
    graph.add_edge("build_context", "select_dimensions")
    graph.add_edge("select_dimensions", "reduce_values")
    graph.add_edge("reduce_values", "synthesize_scenarios")
    graph.add_edge("synthesize_scenarios", "quick_validate")
    graph.add_conditional_edges(
        "quick_validate",
        _route_after_quick_validate,
        {"retry": "synthesize_scenarios", "done": "validate_scenarios"},
    )
    graph.set_finish_point("validate_scenarios")
    return graph.compile()


@lru_cache(maxsize=1)
def get_scenario_generation_subgraph() -> Runnable:
    return build_scenario_generation_subgraph()
