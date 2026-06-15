from __future__ import annotations

from collections.abc import Iterable
import contextlib
import json
import re
from typing import Any
from urllib.parse import quote

import sqlglot
import sqlglot.expressions as exp

from apps.agents.mi_agent.prompts.rdb_search_nl_to_sql import build_nl_to_sql_prompt
from apps.agents.mi_agent.prompts.rdb_search_select_target_table import build_select_table_prompt
from apps.agents.mi_agent.prompts.rdb_search_sql_column_fix import build_sql_column_fix_prompt
from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSearchCandidate, RDBSearchResult, VDBSearchCandidate
from apps.common.configs.settings import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.common.runtime.runtime import ensure_runtime_context_ready, get_rdb_exec_semaphore
from apps.common.values.enums import AnalysisType, ModelPreference
from apps.connectors.llm.llm_client import invoke_llm_function_call
from apps.connectors.mcp.mcp_adapter import mcp_call_tool_by_pool_key, mcp_read_resource


@log_tool
async def execute_rdb_search_tool(
    rdb_search_candidate: RDBSearchCandidate,
    analysis_type: AnalysisType,
) -> RDBSearchResult:
    await ensure_runtime_context_ready()
    rdb_exec_sem = get_rdb_exec_semaphore()

    async with rdb_exec_sem:
        company_code: str = rdb_search_candidate.company_code
        query: str = rdb_search_candidate.query

        text: str = await _read_metadata(
            rdb_search_candidate.vdb_search_candidates,
            rdb_search_candidate.company_code,
        )
        target_data_info: Any = await _select_target_data(rdb_search_candidate.query, text)

        codes, db_table_info = await _read_metadata_codes(target_data_info["agtmtm_id"], company_code)
        table_schemas: list[str] = await _read_metadata_table_schema(db_table_info, company_code)
        _validate_db_access(company_code=company_code, db_name=db_table_info["database_name"])

        if analysis_type == AnalysisType.SIMILARITY_PATTERN:
            pass
        sql = await _generate_sql(query=query, schemas=table_schemas, table_info=db_table_info, codes=codes)
        sql = await _validate_and_refine_sql(sql=sql, schemas=table_schemas)
        sql_execution_result: list[dict] = await _execute_sql(sql, db_table_info["database_name"])

        rdb_search_output: RDBSearchResult = _convert_sql_result_to_output(
            query=query,
            table_name=db_table_info["table_name"],
            data_description=target_data_info["data_description"],
            codes=codes,
            sql=sql,
            sql_result=sql_execution_result,
        )
        return rdb_search_output

@log_tool
def _convert_sql_result_to_output(
    query: str,
    table_name: str,
    data_description: str,
    codes: list[dict],
    sql: str,
    sql_result: list[dict],
) -> RDBSearchResult:
    used_table = f"{table_name}: {data_description}"
    related_data, product_data_nums = _find_related_data_source_nums(
        sql=sql,
        codes=codes,
    )

    nl2sql_result = {"query_target": query, "result": sql_result}
    rdb_search_output: RDBSearchResult = RDBSearchResult(
        used_table=used_table,
        metric_data=nl2sql_result,
        related_data=related_data,
        product_data_nums=product_data_nums,
        sql=sql,
    )
    return rdb_search_output

@log_tool
def _validate_db_access(company_code: str, db_name: str) -> None:

    cfg = get_settings()
    pool_urls: dict[str, str] = cfg.mcp_pool_urls or {}

    if db_name not in pool_urls or db_name == "default":
        return

    allowed_pool_key: str | None = (cfg.company_mcp_map or {}).get(company_code)
    if db_name != allowed_pool_key:
        detail = (
            f"company_code={company_code!r}는 database={db_name!r}에 접근 권한이 없습니다. "
            f"허용된 database: {allowed_pool_key!r}"
        )
        raise MIBaseError(ErrorCode.RDB_ACCESS_DENIED, detail=detail)


@log_tool
async def _execute_sql(sql: str, db_name: str) -> list[dict]:
    result = await mcp_call_tool_by_pool_key(
        name="mysql_query",
        args={"query": sql},
        pool_key=db_name,
    )
    rows = _collect_rows_from_mcp_result(result)
    logger.debug(f"[_execute_sql] OUTPUT | rows={rows!r}")
    return rows

@log_tool
def _collect_rows_from_mcp_result(result: Any) -> list[dict]:
    rows: list[dict] = []

    contents = getattr(result, "content", []) or getattr(result, "contents", [])
    for content in contents:
        text = getattr(content, "text", None)
        if not text:
            continue
        parsed = json.loads(text)

        if isinstance(parsed, list):
            rows.extend(parsed)
        elif isinstance(parsed, dict):
            rows.append(parsed)
        else:
            msg = "Unexpected parsed type from MCP: %s"
            raise MIBaseError(ErrorCode.RDB_DATA_FETCH_FAILED, detail=msg % type(parsed))

    return rows

@log_tool
def _extract_column_names_from_schemas(schemas: list[str]) -> list[str]:
    names: list[str] = []
    for s in schemas:
        try:
            data = json.loads(s)
            for table in data.get("tables", []):
                names.extend(col["name"] for col in table.get("columns", []) if col.get("name"))
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    return names


def _build_schema_json(schemas: list[str]) -> str:
    all_tables: list[dict] = []
    for s in schemas:
        try:
            data = json.loads(s)
            all_tables.extend(data.get("tables", []))
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    return json.dumps({"tables": all_tables}, ensure_ascii=False)


@log_tool
async def _generate_sql(query: str, schemas: list[str], table_info: dict[str, str], codes: list[dict]) -> str:
    column_names: list[str] = _extract_column_names_from_schemas(schemas)
    return await _invoke_nl_to_sql(
        query=query,
        schemas=_build_schema_json(schemas),
        table_info=table_info,
        codes=codes,
        column_names=column_names,
    )


@log_tool
async def _invoke_nl_to_sql(
    query: str,
    schemas: str,
    table_info: dict[str, str],
    codes: list[dict],
    column_names: list[str],
) -> str:
    nl_to_sql_prompt: str = _build_nl_to_sql_prompt(
        query=query,
        schema_json=schemas,
        data_json=json.dumps(table_info, ensure_ascii=False),
        codes_json=json.dumps(codes, ensure_ascii=False),
        column_names_json=json.dumps(column_names, ensure_ascii=False),
    )
    sql = await _extract_sql_from_response(nl_to_sql_prompt)
    sql = _maybe_fix_mojibake(sql)
    logger.info(f"[SQL 코드] {sql.replace(chr(10), ' ')}")
    return sql


def _extract_column_refs_from_sql(sql: str) -> set[str]:
    """SQL을 sqlglot AST로 파싱하여 스키마 컬럼 참조 식별자를 추출합니다.

    서브쿼리/CTE 파생 별칭을 테이블 접두사로 갖는 컬럼은 스키마 검증 대상에서 제외합니다.
    """
    try:
        tree = sqlglot.parse_one(sql, dialect="mysql")
        if tree is None:
            return set()

        # 서브쿼리 인라인 별칭 및 CTE 이름 수집 (파생 테이블 접두사는 스키마 검증 제외)
        derived_aliases: set[str] = {
            subq.alias.lower() for subq in tree.find_all(exp.Subquery) if subq.alias
        } | {
            cte.alias.lower() for cte in tree.find_all(exp.CTE) if cte.alias
        }

        return {
            col.name.lower()
            for col in tree.find_all(exp.Column)
            if not (col.table and col.table.lower() in derived_aliases)
        }
    except (sqlglot.errors.SqlglotError, AttributeError, ValueError, RecursionError):
        logger.warning(f"[_extract_column_refs_from_sql] SQL 파싱 실패 — 빈 집합 반환 | sql={sql!r}")
        return set()


def _find_invalid_columns_in_sql(sql: str, valid_columns: set[str]) -> set[str]:
    """SQL에서 스키마에 존재하지 않는 컬럼을 반환합니다."""
    refs = _extract_column_refs_from_sql(sql)
    return refs - valid_columns


@log_tool
async def _validate_and_refine_sql(sql: str, schemas: list[str]) -> str:
    """생성된 SQL에 스키마에 없는 컬럼이 포함된 경우 LLM으로 정제합니다."""
    valid_columns: set[str] = {c.lower() for c in _extract_column_names_from_schemas(schemas)}
    invalid_cols = _find_invalid_columns_in_sql(sql, valid_columns)
    if not invalid_cols:
        return sql

    logger.warning(f"[_validate_and_refine_sql] 유효하지 않은 컬럼 발견: {sorted(invalid_cols)!r} | SQL 정제 시작")
    schema_json = _build_schema_json(schemas)
    refined_sql = await _invoke_sql_column_fix(sql=sql, schema_json=schema_json, invalid_columns=sorted(invalid_cols))
    refined_sql = _maybe_fix_mojibake(refined_sql)
    if not refined_sql.strip():
        logger.warning("[_validate_and_refine_sql] LLM 정제 결과가 비어있음 — 원본 SQL 유지")
        return sql
    logger.info(f"[SQL 정제 결과] {refined_sql.replace(chr(10), ' ')}")
    return refined_sql


@log_tool
async def _invoke_sql_column_fix(sql: str, schema_json: str, invalid_columns: list[str]) -> str:
    """유효하지 않은 컬럼을 LLM으로 수정한 SQL을 반환합니다."""
    prompt = build_sql_column_fix_prompt(sql=sql, schema_json=schema_json, invalid_columns=invalid_columns)
    return await _extract_sql_from_response(prompt)


@log_tool
def _build_nl_to_sql_prompt(
    query: str,
    schema_json: str,
    data_json: str,
    codes_json: str,
    column_names_json: str,
) -> str:
    return build_nl_to_sql_prompt(
        query=query,
        schema_json=schema_json,
        data_json=data_json,
        codes_json=codes_json,
        column_names_json=column_names_json,
    )


@log_tool
def _extract_code_values_from_sql(sql: str) -> list[str]:
    found: list[str] = []
    _code_eq_re = re.compile(
        r"\b(?:[A-Za-z_]\w*\.)?code\s*=\s*(['\"])(?P<code>.*?)\1",
        re.IGNORECASE,
    )

    _code_in_re = re.compile(
        r"\b(?:[A-Za-z_]\w*\.)?code\s+IN\s*\((?P<vals>[^)]*)\)",
        re.IGNORECASE,
    )
    for m in _code_eq_re.finditer(sql):
        code = m.group("code").strip()
        if code:
            found.append(code)

    for m in _code_in_re.finditer(sql):
        vals = m.group("vals")
        for _q, v in re.findall(r"(['\"])(.*?)\1", vals):
            v = v.strip()
            if v:
                found.append(v)

    result = list(dict.fromkeys(found))
    # logger.debug(f"[_extract_code_values_from_sql] OUTPUT | result={result!r}")
    return result

@log_tool
def _find_related_data_source_nums(sql: str, codes: list[dict]) -> tuple[list[int], list[int]]:
    # logger.debug(f"[_find_related_data_source_nums] INPUT | sql={sql!r} | codes_count={len(codes)}")
    code_values = _extract_code_values_from_sql(sql)
    if not code_values:
        msg = "SQL에서 code 조건을 찾지 못했습니다. (예: t1.code = 'XXXX')"
        raise ValueError(msg)

    items = _normalize_codes(codes)

    matched_nums: list[int] = []
    matched_data_nums: list[int] = []
    for code_value in code_values:
        code_key_full = f"code='{code_value}'"
        for code_info in items:
            code_field = code_info.get("code")
            if code_field in (code_key_full, code_value):
                num = code_info.get("product_num")
                data_num = code_info.get("product_data_num")
                if num is not None:
                    matched_nums.append(num)
                if data_num is not None:
                    matched_data_nums.append(data_num)

    return list(dict.fromkeys(matched_nums)), list(dict.fromkeys(matched_data_nums))

@log_tool
def _normalize_codes(codes) -> list[dict]:
    result: list[dict]
    if isinstance(codes, list) and codes and isinstance(codes[0], str) and codes[0].lstrip().startswith("["):
        result = json.loads(codes[0])
    elif isinstance(codes, str) and codes.lstrip().startswith("["):
        result = json.loads(codes)
    elif isinstance(codes, Iterable) and codes and isinstance(next(iter(codes)), dict):
        result = list(codes)
    elif isinstance(codes, list) and all(isinstance(x, str) and x.strip().startswith("{") for x in codes):
        result = []
        for x in codes:
            with contextlib.suppress(Exception):
                result.append(json.loads(x))
    else:
        result = []
    return result


def _maybe_fix_mojibake(text: str) -> str:
    if "ì" in text or "ê" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeError:
            return text
    return text


@log_tool
async def _read_metadata(vdb_search_candidates: list[VDBSearchCandidate], company_code: str) -> str:
    agtmtm_id_list: list[int] = [c.agtmtm_id for c in vdb_search_candidates]
    ids_str = ",".join(map(str, agtmtm_id_list))
    agtmtm_ids = quote(ids_str, safe=",")
    meta_res = await mcp_read_resource(
        uri=f"mimcp://database/metas/ids/{agtmtm_ids}",
    )
    return meta_res.contents[0].text


@log_tool
async def _select_target_data(query: str, text: str) -> Any:
    table_selection_prompt: str = build_select_table_prompt(
        query=query,
        table=text,
    )
    return await _extract_target_table_info(table_selection_prompt)



@log_tool
async def _read_metadata_table_schema(db_table_info: dict[str, str], company_code: str) -> list[str]:
    schemas: list[str] = []
    schema_res = await mcp_read_resource(
        uri=f"mimcp://database/schemas/{db_table_info['database_name']}/tables/{db_table_info['table_name']}/all",
    )
    schema_content = schema_res.contents[0] if hasattr(schema_res, "contents") else None
    if schema_content and hasattr(schema_content, "text"):
        schemas.append(schema_content.text)
    return schemas


@log_tool
async def _read_metadata_codes(
    agtmtm_id: str,
    company_code: str,
) -> tuple[
    list[dict],
    dict[str, str],
]:
    codes: list[dict] = []
    db_info: dict[str, str] | None = None
    codes_res = await mcp_read_resource(
        uri=f"mimcp://database/metas/codes/{agtmtm_id}",
    )
    codes_content = codes_res.contents[0] if hasattr(codes_res, "contents") else None

    parsed = json.loads(codes_content.text)

    first = parsed[0]
    db_name = first.get("database_name")
    table_name = first.get("table_name")
    if db_name or table_name:
        db_info = {
            "database_name": db_name,
            "table_name": table_name,
        }

    codes = [
        {
            "code": item.get("code"),
            "code_expn": item.get("code_expn"),
            "product_num": item.get("product_num"),
            "product_data_num": item.get("product_data_num"),
        }
        for item in parsed
    ]

    return codes, db_info

@log_tool
async def _read_metadata_db_table_info(db_table_info: dict[str, str], company_code: str) -> list[str]:
    schemas: list[str] = []
    schema_res = await mcp_read_resource(
        uri=f"mimcp://database/schemas/{db_table_info['database_name']}/tables/{db_table_info['table_name']}/all",
        company_code=company_code,
    )
    schema_content = schema_res.contents[0] if hasattr(schema_res, "contents") else None
    if schema_content and hasattr(schema_content, "text"):
        schemas.append(schema_content.text)
    return schemas


@log_tool
async def _extract_sql_from_response(prompt: str) -> str:
    result = await invoke_llm_function_call(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        preference=ModelPreference.QUALITY,
    )

    response = result["content"]

    # 코드 펜스 우선 추출 (sql/SQL 대소문자 무관)
    fence_match = re.search(r"```(?:sql|SQL|mysql|MySQL)?\s*\n(.*?)```", response, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # 코드 펜스 없으면 SELECT/WITH 패턴으로 fallback
    bare_match = re.search(r"(SELECT|WITH)\b[\s\S]+?;", response, re.IGNORECASE)
    return bare_match.group(0).strip() if bare_match else ""

@log_tool
async def _extract_target_table_info(prompt: str) -> Any:
    result = await invoke_llm_function_call(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    llm_response: str = result["content"].strip()

    code_fence_re = re.compile(r"```(?:json|JSON|jsonc)?\s*\r?\n([\s\S]*?)```")
    m = code_fence_re.search(llm_response)
    raw = m.group(1).strip() if m else llm_response

    raw = re.sub(r",(\s*[}\]])", r"\1", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        msg = "JSON 파싱 실패: %s | head=%r"
        raise MIBaseError(ErrorCode.RDB_DATA_FETCH_FAILED, detail=msg % (str(e), raw[:240])) from e

    return parsed
