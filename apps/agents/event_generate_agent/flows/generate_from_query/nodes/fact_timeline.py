"""build_fact_timeline 노드 — 근거 사실이 시나리오 기준일에 유효한지 날짜로 판정한 시점표를 만든다(LLM 없음).

summarize_topics 가 뽑은 사실의 시작·종료 시점과 설비 상태를 기준일과 비교한다(tools/temporal.py).
기준일은 plan_search 가 사용자 요청에서 읽은 scenario_date 이고, 없으면 오늘이다.
시점표는 draft_events 에 제약으로 넘어가고, validate_claims 는 초안의 발생 시점 기준으로 다시 계산해 쓴다.
"""

from __future__ import annotations

from typing import Any

from apps.agents.event_generate_agent.flows.generate_from_query.schema import FactTimeline
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.flows.generate_from_query.tools.temporal import build_timeline, parse_target_date
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger
from apps.common.utils.time_utils import today as today_str


@log_node
async def build_fact_timeline(state: GenerateFromQueryState) -> dict[str, Any]:
    """시나리오 기준일을 정하고 근거 사실의 기준일 시점표를 만든다."""
    scenario_date = state.query_plan.scenario_date if state.query_plan else ""
    target = parse_target_date(scenario_date) or parse_target_date(today_str())
    facts = [fact for brief in state.topic_briefs for fact in brief.facts]
    timeline = FactTimeline(
        target_date=target.isoformat() if target else "",
        entries=build_timeline(facts, target) if target else [],
    )
    logger.info(
        f"[NODE][build_fact_timeline] DONE | target={timeline.target_date} | scenario_date={scenario_date!r} "
        f"| facts={len(facts)} | entries={len(timeline.entries)}",
    )
    return {"fact_timeline": timeline}
