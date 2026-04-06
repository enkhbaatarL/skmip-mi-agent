"""NL to SQL 프롬프트 모듈."""
from __future__ import annotations

import json

from apps.agents.mi_agent.prompts.loader import load_prompt
from apps.common.logging.logger_config import logger
from apps.common.utils.time_utils import now


def build_nl_to_sql_prompt(
    query: str,
    data_json: str | None,
    schema_json: str | None,
    codes_json: str | None = None,
    column_names_json: str | None = None,
) -> str:
    """자연어를 MySQL 쿼리로 변환하는 프롬프트를 생성합니다."""
    today = now()
    def _s(v: str | None) -> str:
        return (v or "").replace("\n", " ")

    logger.debug(
        f"[build_nl_to_sql_prompt] INPUT | query={query!r} | column_names_json={_s(column_names_json)} | "
        f"data_json={_s(data_json)} | schema_json={_s(schema_json)} | codes_json={_s(codes_json)}",
    )

    return load_prompt(
        "nl_to_sql",
        today=today,
        query=query,
        schema_json=_schema_to_md(schema_json or ""),
        data_json=_data_to_md(data_json or ""),
        codes_json=_codes_to_md(codes_json or "[]"),
        column_names_json=_column_names_to_md(column_names_json or "[]"),
    )


def _schema_to_md(schema_json: str) -> str:
    """테이블 스키마 JSON을 Markdown으로 변환합니다."""
    try:
        data = json.loads(schema_json)
    except (json.JSONDecodeError, ValueError):
        return schema_json

    lines: list[str] = []
    for table in data.get("tables", []):
        name = table.get("name", "")
        description = table.get("description", "")
        lines.append(f"### Table: {name}")
        if description:
            lines.append(f"*{description}*")
        lines.append("")
        lines.append("| Column | Type | Nullable | Default | Description | Constraints |")
        lines.append("|--------|------|----------|---------|-------------|-------------|")
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            col_type = col.get("type", "")
            nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
            default = str(col.get("default") or "—")
            col_desc = col.get("description", "")
            constraints = ", ".join(col.get("constraints", [])) or "—"
            lines.append(f"| {col_name} | {col_type} | {nullable} | {default} | {col_desc} | {constraints} |")
        lines.append("")

    return "\n".join(lines).strip()


def _data_to_md(data_json: str) -> str:
    """테이블 정보 JSON을 Markdown으로 변환합니다."""
    try:
        data = json.loads(data_json)
    except (json.JSONDecodeError, ValueError):
        return data_json

    if not isinstance(data, dict):
        return data_json

    lines = [f"- **{k}**: {v}" for k, v in data.items()]
    return "\n".join(lines)


def _codes_to_md(codes_json: str) -> str:
    """코드 정보 JSON을 Markdown 테이블로 변환합니다."""
    try:
        codes = json.loads(codes_json)
    except (json.JSONDecodeError, ValueError):
        return codes_json

    if not isinstance(codes, list) or not codes:
        return codes_json

    keys = ["code", "code_expn", "product_num", "product_data_num"]
    header = "| " + " | ".join(keys) + " |"
    separator = "|" + "|".join("---" for _ in keys) + "|"
    rows = [
        "| " + " | ".join(str(item.get(k, "")) for k in keys) + " |"
        for item in codes
        if isinstance(item, dict)
    ]
    return "\n".join([header, separator, *rows])


def _column_names_to_md(column_names_json: str) -> str:
    """컬럼명 JSON 배열을 backtick 목록으로 변환합니다."""
    try:
        names = json.loads(column_names_json)
    except (json.JSONDecodeError, ValueError):
        return column_names_json

    if not isinstance(names, list):
        return column_names_json

    return ", ".join(f"`{n}`" for n in names)
