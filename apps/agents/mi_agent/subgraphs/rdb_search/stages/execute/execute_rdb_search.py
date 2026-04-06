from __future__ import annotations

import asyncio

from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSearchResult, RDBSearchResults
from apps.agents.mi_agent.subgraphs.rdb_search.state import RDBSearchCandidate, RDBSearchState
from apps.common.logging.logger_config import logger
from apps.common.values.enums import AnalysisType


async def execute_rdb_search_node(state: RDBSearchState) -> RDBSearchState:
    tasks: list[asyncio.Task[RDBSearchResult]] = []
    task_scopes: dict[asyncio.Task[RDBSearchResult], str] = {}

    for idx, item in enumerate(state.candidate_items):
        task = asyncio.create_task(_run_one(item, state.company_code, state.analysis_type))
        task.set_name(f"rdb_candidate[{idx}]")
        tasks.append(task)
        task_scopes[task] = "current"

    if state.analysis_type == AnalysisType.SIMILARITY_PATTERN:
        for idx, item in enumerate(state.candidate_items_historical):
            task = asyncio.create_task(_run_one(item, state.company_code, state.analysis_type))
            task.set_name(f"rdb_candidate_historical[{idx}]")
            tasks.append(task)
            task_scopes[task] = "historical"

    query_results_by_scope: dict[str, list[object]] = {"current": [], "historical": []}
    used_tables_by_scope: dict[str, list[str]] = {"current": [], "historical": []}
    sqls_by_scope: dict[str, list[str]] = {"current": [], "historical": []}
    related_data_by_scope: dict[str, list[int]] = {"current": [], "historical": []}
    product_data_nums_by_scope: dict[str, list[int]] = {"current": [], "historical": []}

    first_exc: BaseException | None = None

    try:
        for task in asyncio.as_completed(tasks):
            try:
                r: RDBSearchResult = await task
            except BaseException as ex:
                first_exc = ex
                logger.exception(
                    "[execute_rdb_search_node] candidate failed. company_code=%r task=%s ex=%r",
                    state.company_code,
                    getattr(task, "get_name", lambda: "<unnamed>")(),
                    ex,
                )
                break

            scope = task_scopes.get(task, "current")
            query_results_by_scope[scope].append(r.metric_data)
            used_tables_by_scope[scope].append(r.used_table)
            sqls_by_scope[scope].append(r.sql)
            if r.related_data:
                related_data_by_scope[scope].extend(r.related_data)
            if r.product_data_nums:
                product_data_nums_by_scope[scope].extend(r.product_data_nums)

    finally:
        if first_exc is not None:
            await _cancel_pending_tasks(tasks)

    if first_exc is not None:
        raise first_exc

    used_tables: list[str] = list(
        set(used_tables_by_scope["current"] + used_tables_by_scope["historical"]),
    )
    sqls: list[str] = [
        *sqls_by_scope["current"],
        *sqls_by_scope["historical"],
    ]
    related_data: list[int] = list(
        set(related_data_by_scope["current"] + related_data_by_scope["historical"]),
    )
    product_data_nums: list[int] = list(
        set(product_data_nums_by_scope["current"] + product_data_nums_by_scope["historical"]),
    )

    if state.analysis_type == AnalysisType.SIMILARITY_PATTERN:
        state.rdb_search_results = RDBSearchResults(
            # similarity_current_data=json.dumps(*query_results_by_scope["current"], ensure_ascii=False),
            # similarity_historical_data=json.dumps(*query_results_by_scope["historical"], ensure_ascii=False),
            similarity_current_data=query_results_by_scope["current"],
            similarity_historical_data=query_results_by_scope["historical"],
            used_tables=list(set(used_tables)),
            sqls="\n".join(sqls),
            related_data=related_data,
            product_data_nums=product_data_nums,
        )
    else:
        state.rdb_search_results = RDBSearchResults(
            # metric_data=json.dumps(*query_results_by_scope["current"], ensure_ascii=False),
            metric_data=query_results_by_scope["current"],
            used_tables=list(set(used_tables)),
            sqls="\n".join(sqls),
            related_data=related_data,
            product_data_nums=product_data_nums,
        )

    return state


def _get_candidate_items(state: RDBSearchState) -> list[RDBSearchCandidate]:
    items = getattr(state, "candidate_items", None) or getattr(state, "cantidate_items", None) or []
    return list(items)


async def _run_one(
    item: RDBSearchCandidate,
    company_code: str,
    analysis_type: AnalysisType,
) -> RDBSearchResult:
    from apps.agents.mi_agent.subgraphs.rdb_search.tools.search_execution import execute_rdb_search_tool

    return await execute_rdb_search_tool(
        RDBSearchCandidate(
            query=item.query,
            company_code=company_code,
            vdb_search_candidates=item.vdb_search_candidates,
        ),
        analysis_type=analysis_type,
    )


def _init_empty_results(state: RDBSearchState) -> None:
    state.rdb_search_results = RDBSearchResults(
        metric_data=[],
        used_tables=[],
        sqls="",
        related_data=[],
    )


async def _cancel_pending_tasks(tasks: list[asyncio.Task[RDBSearchResult]]) -> None:
    for t in tasks:
        if not t.done():
            t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
