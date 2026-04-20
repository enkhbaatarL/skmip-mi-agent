#   scripts/test_event_flow_agent_invoke.py
#   kmj20260420일, event_flow_agent runnable 직접 호출 테스트
#   실행명령어 bash: python -m scripts.test_event_flow_agent_invoke

from __future__ import annotations

import asyncio
import json

from apps.agents.event_flow_agent.flows.event_flow_graph import get_event_flow_agent


async def main() -> None:
    agent = get_event_flow_agent()

    result = await agent.ainvoke(
        {
            "market_category": "LNG",
            "limit": 1,
        }
    )

    print("\n=== EVENT FLOW AGENT RESULT ===")
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())