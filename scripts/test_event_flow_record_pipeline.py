#   scripts/test_event_flow_record_pipeline.py
# 이 스크립트는 event flow의 record 처리 파이프라인을 테스트하기 위한 간단한 실행 예시입니다.
#   실행명령어 bash 창에 아래 2줄 입력 후 실행
# export ANTHROPIC_API_KEY="여기에_실제_키"
# python -m scripts.test_event_flow_record_pipeline

from __future__ import annotations

import asyncio
import json

from apps.agents.event_flow_agent.nodes.analyze_records_with_llm import (
    analyze_records_with_llm,
)
from apps.agents.event_flow_agent.nodes.read_record_source import read_record_source
from apps.agents.event_flow_agent.repositories.sync_record_repository import (
    SyncRecordRepository,
)
from apps.agents.event_flow_agent.services.record_analysis_service import (
    RecordAnalysisService,
)
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState
from apps.common.configs.database.sync_database.connection import get_sync_session


async def main() -> None:
    session = get_sync_session()

    try:
        record_repository = SyncRecordRepository(session=session)
        record_analysis_service = RecordAnalysisService()

        state = EventFlowState(
            market_category="LNG",
            limit=1,
        )

        print("\n=== STEP 1. read_record_source ===")
        state = read_record_source(
            state=state,
            repository=record_repository,
        )

        print(f"source_records count: {len(state.source_records)}")
        if state.source_records:
            print("first source record:")
            print(
                json.dumps(
                    state.source_records[0],
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        else:
            print("source_records is empty")

        print("\n=== STEP 2. analyze_records_with_llm ===")
        state = await analyze_records_with_llm(
            state=state,
            service=record_analysis_service,
        )

        print(f"record_analyses count: {len(state.record_analyses)}")
        if state.record_analyses:
            print("first analyzed record:")
            print(
                json.dumps(
                    state.record_analyses[0],
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        else:
            print("record_analyses is empty")

        print("\n=== STEP 3. errors ===")
        print(
            json.dumps(
                state.errors,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())