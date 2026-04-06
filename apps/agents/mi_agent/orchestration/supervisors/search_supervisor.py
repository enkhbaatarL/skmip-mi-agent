from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
import time
import traceback
from typing import Any

from apps.agents.mi_agent.components.combine import merge_and_dedupe
from apps.agents.mi_agent.components.policies import ExecutionPolicy, SearchPolicySet
from apps.agents.mi_agent.schemas.search_output import SearchOutput
from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSearchOutput
from apps.agents.mi_agent.subgraphs.rdb_search.state import RDBSearchState
from apps.agents.mi_agent.subgraphs.rdb_search.subgraph_builder import run_rdb
from apps.agents.mi_agent.subgraphs.vdb_search.schemas import VDBSearchOutput
from apps.agents.mi_agent.subgraphs.vdb_search.state import VDBSearchState
from apps.agents.mi_agent.subgraphs.vdb_search.subgraph_builder import run_vdb
from apps.agents.mi_agent.subgraphs.web_search.schemas import WebSearchOutput
from apps.agents.mi_agent.subgraphs.web_search.state import WebSearchState
from apps.agents.mi_agent.subgraphs.web_search.subgraph_builder import run_web
from apps.common.exceptions.custom import DataRetrievalError
from apps.common.values.enums import SearchSource


SearchRunner = Callable[[MariAgentState], Awaitable[object]]

SEARCH_RUNNERS: dict[SearchSource, SearchRunner] = {
    SearchSource.RDB: run_rdb,
    SearchSource.VDB: run_vdb,
    SearchSource.WEB: run_web,
}


def _extract_rdb_search_results(search_result: Any) -> list[dict]:
    """RDB 검색 결과(RDBSearchState 또는 list)를 문서 리스트로 추출."""
    if isinstance(search_result, RDBSearchState):
        return getattr(search_result, "rows", [])
    if isinstance(search_result, list):
        return search_result
    if isinstance(search_result, RDBSearchOutput):
        return search_result
    return []


def _extract_vdb_search_results(search_result: Any) -> list[dict]:
    """VDB 검색 결과(VDBSearchState 또는 list)를 문서 리스트로 추출."""
    if isinstance(search_result, VDBSearchState):
        return getattr(search_result, "rows", [])
    if isinstance(search_result, list):
        return search_result
    if isinstance(search_result, VDBSearchOutput):
        return search_result
    return []


def _extract_web_search_results(search_result: Any) -> list[dict]:
    """Web 검색 결과를 문서 리스트로 추출."""
    if isinstance(search_result, WebSearchState):
        return getattr(search_result, "web_search_results", [])
    if isinstance(search_result, list):
        return search_result
    if isinstance(search_result, WebSearchOutput):
        return search_result.web_sources
    return []


class SearchSupervisor:
    def __init__(self, search_policy_set: SearchPolicySet) -> None:
        self.search_policy_set = search_policy_set

        available_search_sources: set[SearchSource] = set(SEARCH_RUNNERS.keys())

        self.enabled_search_sources: list[SearchSource] = [
            search_source
            for search_source in search_policy_set.enabled_sources
            if search_source in available_search_sources
        ]

        self.search_result_extractors: dict[SearchSource, Callable[[Any], list[dict]]] = {
            SearchSource.RDB: _extract_rdb_search_results,
            SearchSource.VDB: _extract_vdb_search_results,
            SearchSource.WEB: _extract_web_search_results,
        }

        self.required_search_sources: set[SearchSource] = search_policy_set.required_sources & available_search_sources

    def _store_search_result(
        self,
        agent_state: MariAgentState,
        search_source: SearchSource,
        search_result: Any,
    ) -> None:
        if search_source == SearchSource.RDB:
            agent_state.search_output.rdb_search_output = search_result
        elif search_source == SearchSource.VDB:
            agent_state.search_output.vdb_search_output = search_result
        elif search_source == SearchSource.WEB:
            agent_state.search_output.web_search_output = search_result

    def _load_search_result(self, agent_state: MariAgentState, search_source: SearchSource) -> Any:
        if search_source == SearchSource.RDB:
            return agent_state.search_output.rdb_search_output
        if search_source == SearchSource.VDB:
            return agent_state.search_output.vdb_search_output
        if search_source == SearchSource.WEB:
            return agent_state.search_output.web_search_output
        return None

    async def run_parallel_searches(self, agent_state: MariAgentState) -> SearchOutput:
        enabled_search_sources = self.enabled_search_sources
        if not enabled_search_sources:
            return None

        start_time = time.perf_counter()

        search_tasks: dict[SearchSource, asyncio.Task[None]] = {}
        task_to_source: dict[asyncio.Task[None], SearchSource] = {}

        # 소스별 상태/에러 추적(반환값 대신 side-effect로 기록)
        status_by_source: dict[SearchSource, str] = {}
        last_error_by_source: dict[SearchSource, str] = {}

        for search_source in enabled_search_sources:
            search_runner = SEARCH_RUNNERS[search_source]
            task = asyncio.create_task(
                self._run_search_source_with_policy(
                    search_source=search_source,
                    search_runner=search_runner,
                    agent_state=agent_state,
                    status_by_source=status_by_source,
                    last_error_by_source=last_error_by_source,
                ),
                name=f"search:{search_source.value}",
            )
            search_tasks[search_source] = task
            task_to_source[task] = search_source

        merged_search_documents: list[dict] = []
        pending_search_tasks: set[asyncio.Task[None]] = set(search_tasks.values())

        completed_required_search_sources: set[SearchSource] = set()
        required_search_sources: set[SearchSource] = set(self.required_search_sources)

        while pending_search_tasks:
            # 전체 fanout deadline 체크
            if (time.perf_counter() - start_time) >= self.search_policy_set.search_exec_fanout_deadline_sec:
                for pending_task in pending_search_tasks:
                    pending_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await asyncio.gather(*pending_search_tasks, return_exceptions=True)
                break

            done_tasks, pending_search_tasks = await asyncio.wait(
                pending_search_tasks,
                timeout=0.1,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for done_task in done_tasks:
                search_source = task_to_source.get(done_task)

                try:
                    await done_task
                except asyncio.CancelledError:
                    if search_source is not None:
                        status_by_source[search_source] = "cancel"
                    continue
                except Exception:
                    err = traceback.format_exc()
                    done_task.get_name()
                    if search_source is not None:
                        status_by_source[search_source] = "error"
                        last_error_by_source[search_source] = err
                    continue

                if search_source is None:
                    continue

                status = status_by_source.get(search_source, "error")
                error_detail = last_error_by_source.get(search_source)

                if status != "ok" and error_detail:
                    # 디버깅/관찰용: 각 소스별 마지막 실패 원인 저장
                    # (이미 last_error_by_source에 기록되어 있음)
                    raise DataRetrievalError(detail=error_detail)
                    # logger.error(f"[search exception] : {error_detail}")

                raw_result = self._load_search_result(agent_state, search_source)
                extract_documents = self.search_result_extractors.get(
                    search_source,
                    lambda value: value if isinstance(value, list) else [],
                )
                documents = extract_documents(raw_result)

                if status == "ok":
                    merged_search_documents = merge_and_dedupe(merged_search_documents, documents)

                if search_source in required_search_sources and status == "ok":
                    completed_required_search_sources.add(search_source)

                # required가 "존재"하고, 그 required가 모두 "ok"로 충족된 경우에만 조기 종료
                if required_search_sources and completed_required_search_sources.issuperset(required_search_sources):
                    for pending_task in pending_search_tasks:
                        pending_task.cancel()
                    with suppress(asyncio.CancelledError, Exception):
                        await asyncio.gather(*pending_search_tasks, return_exceptions=True)
                    # return merged_search_documents
                    return agent_state.search_output

        # deadline 또는 기타 이유로 루프 종료 후, strict_required이면 부족한 필수 검색 소스 체크
        if self.search_policy_set.strict_required:
            missing_search_sources = required_search_sources - completed_required_search_sources
            if missing_search_sources:
                for src in sorted(missing_search_sources, key=lambda s: s.value):
                    detail = last_error_by_source.get(src)
                    if detail:
                        pass
                    else:
                        pass

                raise DataRetrievalError({s.value for s in missing_search_sources})

        return agent_state.search_output

    async def _run_search_source_with_policy(
        self,
        search_source: SearchSource,
        search_runner: SearchRunner,
        agent_state: MariAgentState,
        status_by_source: dict[SearchSource, str],
        last_error_by_source: dict[SearchSource, str],
    ) -> None:
        """단일 검색 소스(RDB/VDB 등)를 timeout + retry 정책 하에서 실행.

        - 결과는 MariAgentState.search_output에 저장한다.
        - 반환값은 사용하지 않는다(리턴으로 다른 값을 돌려주지 않음).
        - 상태: "ok" | "cancel" | "timeout" | "error" 를 status_by_source에 기록
        """
        execution_policy: ExecutionPolicy = self.search_policy_set.get(search_source.value)

        attempt = 0
        last_error_detail: str | None = None

        while attempt <= execution_policy.retry.retries:
            try:
                raw_result = await asyncio.wait_for(
                    search_runner(agent_state),
                    timeout=execution_policy.exec_timeout_sec,
                )

                self._store_search_result(agent_state, search_source, raw_result)
                status_by_source[search_source] = "ok"
                return

            except asyncio.CancelledError:
                status_by_source[search_source] = "cancel"
                return

            except Exception as exc:
                last_error_detail = (
                    f"[{search_source.value}] attempt={attempt} failed: "
                    f"{type(exc).__name__}: {exc!s}\n{traceback.format_exc()}"
                )

                should_retry = (
                    isinstance(exc, execution_policy.retry.retry_on) and attempt < execution_policy.retry.retries
                )
                if not should_retry:
                    status_by_source[search_source] = "timeout" if isinstance(exc, asyncio.TimeoutError) else "error"
                    last_error_by_source[search_source] = last_error_detail
                    return

                await asyncio.sleep(0.5)
                attempt += 1

        status_by_source[search_source] = "error"
        if last_error_detail is not None:
            last_error_by_source[search_source] = last_error_detail
