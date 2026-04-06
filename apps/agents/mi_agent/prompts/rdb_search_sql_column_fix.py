"""SQL 컬럼 유효성 검증 및 수정 프롬프트 모듈."""
from __future__ import annotations

import json

from apps.agents.mi_agent.prompts.loader import load_prompt
from apps.common.logging.logger_config import logger


def build_sql_column_fix_prompt(sql: str, schema_json: str, invalid_columns: list[str]) -> str:
    """잘못된 컬럼이 포함된 SQL을 수정하도록 LLM에 전달할 프롬프트를 생성합니다."""
    invalid_cols_str = ", ".join(f"`{c}`" for c in invalid_columns)
    schema_md = _schema_to_md(schema_json)

    logger.debug(
        f"[build_sql_column_fix_prompt] INPUT | invalid_cols={invalid_cols_str!r} | sql={sql!r}",
    )

    return load_prompt(
        "rdb_sql_column_fix",
        invalid_cols=invalid_cols_str,
        schema_md=schema_md,
        original_sql=sql,
    )


def _schema_to_md(schema_json: str) -> str:
    """테이블 스키마 JSON을 Markdown 테이블로 변환합니다."""
    if not schema_json or not schema_json.strip():
        logger.warning("[_schema_to_md] schema_json이 비어있음")
        return "(스키마 정보 없음)"

    try:
        data = json.loads(schema_json)
    except (json.JSONDecodeError, ValueError):
        return schema_json

    tables = data.get("tables", [])
    if not tables:
        logger.warning("[_schema_to_md] tables 목록이 비어있음")
        return "(테이블 정보 없음)"

    lines: list[str] = []
    for table in tables:
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
