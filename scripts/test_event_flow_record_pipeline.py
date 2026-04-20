#   scripts/test_event_flow_record_pipeline.py
#   kmj20260417금, event_flow_agent의 record -> event 파이프라인 테스트
#   실행명령어 bash: python -m scripts.test_event_flow_record_pipeline

from __future__ import annotations

import asyncio
import json

from apps.agents.event_flow_agent.nodes.analyze_records_with_llm import (
    analyze_records_with_llm,
)
from apps.agents.event_flow_agent.nodes.extract_events_with_llm import (
    extract_events_with_llm,
)
from apps.agents.event_flow_agent.nodes.read_record_source import read_record_source
from apps.agents.event_flow_agent.repositories.sync_record_repository import (
    SyncRecordRepository,
)
from apps.agents.event_flow_agent.services.event_extraction_service import (
    EventExtractionService,
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
        event_extraction_service = EventExtractionService()

        state = EventFlowState(
            market_category="LNG",
            limit=3,
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

        print("\n=== STEP 2-1. analyze_records_with_llm started ===")
        state = await analyze_records_with_llm(
            state=state,
            service=record_analysis_service,
        )
        print("=== STEP 2-2. analyze_records_with_llm finished ===")

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

        print("\n=== STEP 3-1. extract_events_with_llm started ===")
        state = await extract_events_with_llm(
            state=state,
            service=event_extraction_service,
        )
        print("=== STEP 3-2. extract_events_with_llm finished ===")

        print(f"extracted_events count: {len(state.extracted_events)}")
        if state.extracted_events:
            print("first extracted event:")
            print(
                json.dumps(
                    state.extracted_events[0],
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        else:
            print("extracted_events is empty")

        print("\n=== STEP 4. errors ===")
        print(
            json.dumps(
                state.errors,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

        print("\n=== SCRIPT FINISHED ===")

    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())