from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import Cursor, DictCursor


ROOT_DIR = Path(__file__).resolve().parents[3]
LOGGER = logging.getLogger("model_parameter_v4_sql_verify")
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json"
MODEL_PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.json"
IMPACT_LEVER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.json"
SQL_PATH = ROOT_DIR / "scripts/model_parameter/apply_model_parameter_canonical_v4.sql"

ALLOWED_DATABASE_PATTERN = re.compile(r"model_parameter_v4_sql_verify(?:_[a-z0-9_]+)?")

MASTER_COLUMNS = (
    "model_param_id",
    "use_yn",
    "parameter_name",
    "parameter_hint",
    "model_file",
    "model_sheet",
    "model_table",
    "semantic_axes",
    "basecase_read_mode",
    "basecase_header_row",
    "basecase_data_start_row",
    "basecase_column_roles",
    "basecase_row_filter",
    "basecase_year_row",
    "basecase_month_row",
    "basecase_period_row",
    "basecase_value_start_col",
    "basecase_value_end_col",
    "basecase_stop_rule",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
MAPPING_COLUMNS = (
    "model_param_dimension_map_id",
    "use_yn",
    "event_type_l2_id",
    "dimension_key",
    "dimension_label",
    "mapping_method",
    "model_param_id",
    "comment",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
TEMPLATE_COLUMNS = (
    "scenario_dimension_template_id",
    "event_type_l2_id",
    "template_json",
    "del_yn",
)
IMPACT_LEVER_COLUMNS = (
    "impact_lever_id",
    "lever_code",
    "domain",
    "label",
    "description",
    "applicability_hint",
    "parent_lever_code",
    "parameter_bindings",
    "catalog_version",
    "use_yn",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)

SCHEMA_STATEMENTS = (
    "DROP TABLE IF EXISTS tmm_mi_model_param_dimension_map",
    "DROP TABLE IF EXISTS tmm_mi_model_impact_lever_m",
    "DROP TABLE IF EXISTS tmm_mi_scenario_dimension_template_m",
    "DROP TABLE IF EXISTS tmm_mi_model_param_m",
    """
    CREATE TABLE tmm_mi_model_param_m (
        model_param_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        use_yn CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'Y',
        parameter_name VARCHAR(150) COLLATE utf8mb4_bin NOT NULL,
        parameter_hint TEXT COLLATE utf8mb4_bin NOT NULL,
        model_file VARCHAR(100) COLLATE utf8mb4_bin NOT NULL,
        model_sheet VARCHAR(150) COLLATE utf8mb4_bin NOT NULL,
        model_table VARCHAR(50) COLLATE utf8mb4_bin NOT NULL,
        semantic_axes TEXT COLLATE utf8mb4_bin NULL,
        basecase_read_mode VARCHAR(50) COLLATE utf8mb4_bin NOT NULL,
        basecase_header_row SMALLINT UNSIGNED NOT NULL,
        basecase_data_start_row SMALLINT UNSIGNED NOT NULL,
        basecase_column_roles VARCHAR(1000) COLLATE utf8mb4_bin NOT NULL,
        basecase_row_filter VARCHAR(200) COLLATE utf8mb4_bin NULL,
        basecase_year_row SMALLINT UNSIGNED NULL,
        basecase_month_row SMALLINT UNSIGNED NULL,
        basecase_period_row SMALLINT UNSIGNED NULL,
        basecase_value_start_col VARCHAR(10) COLLATE utf8mb4_bin NULL,
        basecase_value_end_col VARCHAR(10) COLLATE utf8mb4_bin NULL,
        basecase_stop_rule VARCHAR(100) COLLATE utf8mb4_bin NOT NULL,
        crt_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        crt_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        mod_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        mod_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
        del_yn CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N',
        PRIMARY KEY (model_param_id),
        UNIQUE KEY uk_tmm_mi_model_param_m_01 (parameter_name),
        CONSTRAINT ck_tmm_mi_model_param_m_01 CHECK (use_yn IN ('Y', 'N')),
        CONSTRAINT ck_tmm_mi_model_param_m_02 CHECK (del_yn IN ('Y', 'N')),
        CONSTRAINT ck_tmm_mi_model_param_m_03
            CHECK (basecase_read_mode IN ('fixed_columns', 'matrix_time_columns'))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
    """,
    """
    CREATE TABLE tmm_mi_scenario_dimension_template_m (
        scenario_dimension_template_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        event_type_l2_id INT UNSIGNED NOT NULL,
        template_json JSON NOT NULL,
        crt_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        crt_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        mod_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        mod_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
        del_yn CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N',
        PRIMARY KEY (scenario_dimension_template_id),
        KEY idx_tmm_mi_scenario_dimension_template_m_01 (event_type_l2_id),
        CONSTRAINT ck_tmm_mi_scenario_dimension_template_m_01
            CHECK (JSON_TYPE(template_json) = 'ARRAY')
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
    """,
    """
    CREATE TABLE tmm_mi_model_impact_lever_m (
        impact_lever_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        lever_code VARCHAR(150) COLLATE utf8mb4_bin NOT NULL,
        domain VARCHAR(30) COLLATE utf8mb4_bin NOT NULL,
        label VARCHAR(200) COLLATE utf8mb4_bin NOT NULL,
        description TEXT COLLATE utf8mb4_bin NOT NULL,
        applicability_hint TEXT COLLATE utf8mb4_bin NULL,
        parent_lever_code VARCHAR(150) COLLATE utf8mb4_bin NULL,
        parameter_bindings JSON NOT NULL,
        catalog_version VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'v1',
        use_yn CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'Y',
        crt_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        crt_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        mod_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        mod_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
        del_yn CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N',
        PRIMARY KEY (impact_lever_id),
        UNIQUE KEY uk_tmm_mi_model_impact_lever_m_01 (lever_code),
        KEY idx_tmm_mi_model_impact_lever_m_01 (domain, lever_code),
        CONSTRAINT ck_tmm_mi_model_impact_lever_m_02 CHECK (use_yn IN ('Y', 'N')),
        CONSTRAINT ck_tmm_mi_model_impact_lever_m_03 CHECK (del_yn IN ('Y', 'N')),
        CONSTRAINT ck_tmm_mi_model_impact_lever_m_04
            CHECK (JSON_TYPE(parameter_bindings) = 'ARRAY')
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
    """,
    """
    CREATE TABLE tmm_mi_model_param_dimension_map (
        model_param_dimension_map_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        use_yn CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'Y',
        event_type_l2_id INT UNSIGNED NOT NULL,
        dimension_key VARCHAR(150) COLLATE utf8mb4_bin NOT NULL,
        dimension_label VARCHAR(200) COLLATE utf8mb4_bin NOT NULL,
        mapping_method VARCHAR(50) COLLATE utf8mb4_bin NOT NULL,
        model_param_id INT UNSIGNED NULL,
        `comment` TEXT COLLATE utf8mb4_bin NULL,
        crt_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        crt_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        mod_usr_logn_id VARCHAR(100) COLLATE utf8mb4_bin NOT NULL DEFAULT 'system',
        mod_dtm DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
        del_yn CHAR(1) COLLATE utf8mb4_bin NOT NULL DEFAULT 'N',
        PRIMARY KEY (model_param_dimension_map_id),
        UNIQUE KEY uk_tmm_mi_model_param_dimension_map_01
            (event_type_l2_id, dimension_key, model_param_id),
        KEY idx_tmm_mi_model_param_dimension_map_01 (event_type_l2_id, dimension_key),
        KEY idx_tmm_mi_model_param_dimension_map_02 (model_param_id),
        CONSTRAINT ck_tmm_mi_model_param_dimension_map_01 CHECK (use_yn IN ('Y', 'N')),
        CONSTRAINT ck_tmm_mi_model_param_dimension_map_02 CHECK (del_yn IN ('Y', 'N')),
        CONSTRAINT ck_tmm_mi_model_param_dimension_map_03
            CHECK (mapping_method IN ('direct', 'indirect', 'routing', 'na')),
        CONSTRAINT fk_tmm_mi_model_param_dimension_map_02
            FOREIGN KEY (model_param_id) REFERENCES tmm_mi_model_param_m (model_param_id)
            ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
    """,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Destructively reset only a named disposable MySQL database, seed the local pre-v4 "
            "snapshot, and verify the combined v4 static SQL transaction and rollback paths."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=33319)
    parser.add_argument("--user", default="verify")
    parser.add_argument("--password", default="verify")
    parser.add_argument("--database", default="model_parameter_v4_sql_verify")
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        message = f"JSON root must be an object: {path}"
        raise TypeError(message)
    return document


def _connect(args: argparse.Namespace) -> Connection:
    if ALLOWED_DATABASE_PATTERN.fullmatch(args.database) is None:
        message = (
            "refusing destructive verification outside the isolated database namespace: "
            f"database={args.database!r}, required_pattern={ALLOWED_DATABASE_PATTERN.pattern!r}"
        )
        raise RuntimeError(message)
    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=5,
        read_timeout=60,
        write_timeout=60,
        cursorclass=DictCursor,
    )


def _drain_result_sets(cursor: Cursor) -> None:
    if cursor.description is not None:
        cursor.fetchall()
    while cursor.nextset():
        if cursor.description is not None:
            cursor.fetchall()


def _execute_statement(connection: Connection, statement: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(statement)
        _drain_result_sets(cursor)


def _static_sql_statements() -> list[str]:
    document = SQL_PATH.read_text(encoding="utf-8")
    start_marker = "DELIMITER //"
    end_marker = "DELIMITER ;"
    if document.count(start_marker) != 1 or document.count(end_marker) != 1:
        message = "canonical SQL must contain one delimiter block and one terminator"
        raise RuntimeError(message)
    payload = document.split(start_marker, maxsplit=1)[1].split(end_marker, maxsplit=1)[0]
    statements = [chunk.strip() for chunk in payload.split("//") if chunk.strip()]
    if len(statements) != 4 or not statements[1].startswith("CREATE PROCEDURE"):
        message = f"unexpected canonical SQL statement layout: count={len(statements)}"
        raise RuntimeError(message)
    return statements


def _execute_static_sql(connection: Connection) -> None:
    for statement in _static_sql_statements():
        _execute_statement(connection, statement)


def _drop_procedure(connection: Connection) -> None:
    _execute_statement(connection, "DROP PROCEDURE IF EXISTS apply_model_parameter_canonical_v4")


def _database_value(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?",
        value,
    ):
        return datetime.fromisoformat(value)
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _insert_rows(
    connection: Connection,
    *,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    quoted_columns = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    query = f"INSERT INTO `{table}` ({quoted_columns}) VALUES ({placeholders})"  # noqa: S608
    values = [tuple(_database_value(row.get(column)) for column in columns) for row in rows]
    with connection.cursor() as cursor:
        cursor.executemany(query, values)


def _seed_audit_values(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Materialize DB defaults absent from canonical-derived local evidence."""
    result: list[dict[str, Any]] = []
    fallback = "2026-08-13T00:00:00"
    for source in rows:
        row = dict(source)
        if "crt_dtm" in row and row["crt_dtm"] is None:
            row["crt_dtm"] = fallback
        if "mod_dtm" in row and row["mod_dtm"] is None:
            row["mod_dtm"] = row.get("crt_dtm") or fallback
        result.append(row)
    return result


def _reset_and_seed(connection: Connection, snapshot: Mapping[str, Any]) -> None:
    _drop_procedure(connection)
    for statement in SCHEMA_STATEMENTS:
        _execute_statement(connection, statement)
    _insert_rows(
        connection,
        table="tmm_mi_model_param_m",
        columns=MASTER_COLUMNS,
        rows=_seed_audit_values(snapshot["master"]),
    )
    _insert_rows(
        connection,
        table="tmm_mi_scenario_dimension_template_m",
        columns=TEMPLATE_COLUMNS,
        rows=snapshot["scenario_dimension_templates"],
    )
    _insert_rows(
        connection,
        table="tmm_mi_model_impact_lever_m",
        columns=IMPACT_LEVER_COLUMNS,
        rows=_seed_audit_values(snapshot["impact_levers"]),
    )
    _insert_rows(
        connection,
        table="tmm_mi_model_param_dimension_map",
        columns=MAPPING_COLUMNS,
        rows=_seed_audit_values(snapshot["dimension_mappings"]),
    )


def _read_rows(
    connection: Connection,
    *,
    table: str,
    columns: Sequence[str],
    order_by: str,
) -> list[dict[str, Any]]:
    selected_columns = ", ".join(f"`{column}`" for column in columns)
    query = f"SELECT {selected_columns} FROM `{table}` ORDER BY `{order_by}`"  # noqa: S608
    with connection.cursor() as cursor:
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def _read_master(connection: Connection) -> list[dict[str, Any]]:
    return _read_rows(
        connection,
        table="tmm_mi_model_param_m",
        columns=MASTER_COLUMNS,
        order_by="model_param_id",
    )


def _read_mappings(connection: Connection) -> list[dict[str, Any]]:
    return _read_rows(
        connection,
        table="tmm_mi_model_param_dimension_map",
        columns=MAPPING_COLUMNS,
        order_by="model_param_dimension_map_id",
    )


def _read_templates(connection: Connection) -> list[dict[str, Any]]:
    return _read_rows(
        connection,
        table="tmm_mi_scenario_dimension_template_m",
        columns=TEMPLATE_COLUMNS,
        order_by="scenario_dimension_template_id",
    )


def _read_levers(connection: Connection) -> list[dict[str, Any]]:
    return _read_rows(
        connection,
        table="tmm_mi_model_impact_lever_m",
        columns=IMPACT_LEVER_COLUMNS,
        order_by="impact_lever_id",
    )


def _normalized(value: Any, *, column: str) -> Any:  # noqa: ANN401
    if column in {"parameter_bindings", "template_json"}:
        decoded = json.loads(value) if isinstance(value, str) else value
        return json.dumps(decoded, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _projection(row: Mapping[str, Any], columns: Iterable[str]) -> tuple[Any, ...]:
    return tuple(_normalized(row.get(column), column=column) for column in columns)


def _indexed(
    rows: Iterable[Mapping[str, Any]],
    id_column: str,
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        row_id = int(row[id_column])
        if row_id in indexed:
            message = f"duplicate {id_column}: {row_id}"
            raise RuntimeError(message)
        indexed[row_id] = row
    return indexed


def _assert_mapping_unchanged(
    actual_rows: list[dict[str, Any]],
    expected_rows: list[dict[str, Any]],
) -> None:
    if not expected_rows or len(actual_rows) != len(expected_rows):
        message = "legacy mapping must match the AS-IS snapshot row count"
        raise RuntimeError(message)
    actual_by_id = _indexed(actual_rows, "model_param_dimension_map_id")
    if set(actual_by_id) != {int(row["model_param_dimension_map_id"]) for row in expected_rows}:
        message = "AS-IS legacy mapping identities changed"
        raise RuntimeError(message)
    for expected in expected_rows:
        raw_id = int(expected["model_param_dimension_map_id"])
        actual = actual_by_id[raw_id]
        if _projection(actual, MAPPING_COLUMNS) != _projection(expected, MAPPING_COLUMNS):
            message = f"legacy mapping changed: id={raw_id!r}"
            raise RuntimeError(message)


def _assert_canonical_read_back(
    connection: Connection,
    model_parameter: Mapping[str, Any],
    impact_lever: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> None:
    actual_master = _indexed(_read_master(connection), "model_param_id")
    expected_master = _indexed(model_parameter["master"], "model_param_id")
    master_columns = tuple(column for column in MASTER_COLUMNS if column != "mod_dtm")
    if len(actual_master) != 21 or set(actual_master) != set(expected_master):
        message = "unexpected master identity during canonical read-back"
        raise RuntimeError(message)
    for row_id, expected in expected_master.items():
        if _projection(actual_master[row_id], master_columns) != _projection(expected, master_columns):
            message = f"master canonical read-back mismatch: model_param_id={row_id}"
            raise RuntimeError(message)

    actual_levers = _indexed(_read_levers(connection), "impact_lever_id")
    expected_levers = _indexed(impact_lever["impact_levers"], "impact_lever_id")
    lever_columns = tuple(column for column in IMPACT_LEVER_COLUMNS if column != "mod_dtm")
    if len(actual_levers) != 16 or set(actual_levers) != set(expected_levers):
        message = "unexpected Impact Lever identity during canonical read-back"
        raise RuntimeError(message)
    for row_id, expected in expected_levers.items():
        if _projection(actual_levers[row_id], lever_columns) != _projection(expected, lever_columns):
            message = f"Impact Lever canonical read-back mismatch: impact_lever_id={row_id}"
            raise RuntimeError(message)

    actual_mappings = _read_mappings(connection)
    _assert_mapping_unchanged(actual_mappings, snapshot["dimension_mappings"])
    active_names = {
        row["parameter_name"] for row in actual_master.values() if row["use_yn"] == "Y" and row["del_yn"] == "N"
    }
    if active_names != set(model_parameter["active_parameter_names"]):
        message = f"active parameter set mismatch: {sorted(active_names)}"
        raise RuntimeError(message)
    if Counter(row["mapping_method"] for row in actual_mappings) != Counter(
        row["mapping_method"] for row in snapshot["dimension_mappings"]
    ):
        message = "legacy mapping method counts changed"
        raise RuntimeError(message)

    raw_bindings = [binding for row in actual_levers.values() for binding in json.loads(row["parameter_bindings"])]
    effective = [binding for binding in raw_bindings if binding["parameter_name"] in active_names]
    if (
        len(raw_bindings),
        len(effective),
        len({binding["parameter_name"] for binding in effective}),
    ) != (20, 18, 16):
        message = "Impact Lever binding counts changed"
        raise RuntimeError(message)


def _digest(connection: Connection, *, include_mod_dtm: bool) -> str:
    document = {
        "master": _read_master(connection),
        "mappings": _read_mappings(connection),
        "templates": _read_templates(connection),
        "impact_levers": _read_levers(connection),
    }
    for rows in document.values():
        for row in rows:
            if not include_mod_dtm:
                row.pop("mod_dtm", None)
            for column, value in row.items():
                row[column] = _normalized(value, column=column)
    serialized = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _expect_static_sql_failure(connection: Connection, *, fragment: str) -> str:
    try:
        _execute_static_sql(connection)
    except pymysql.MySQLError as exc:
        message = str(exc)
        if fragment not in message:
            detail = f"unexpected static SQL failure: expected={fragment!r}, actual={message!r}"
            raise RuntimeError(detail) from exc
        return message
    finally:
        _drop_procedure(connection)
    message = f"static SQL unexpectedly succeeded; expected failure containing {fragment!r}"
    raise RuntimeError(message)


def _assert_failure_preserved_digest(
    connection: Connection,
    *,
    fragment: str,
) -> str:
    before = _digest(connection, include_mod_dtm=True)
    error = _expect_static_sql_failure(connection, fragment=fragment)
    after = _digest(connection, include_mod_dtm=True)
    if after != before:
        message = f"failure path changed table state: expected_fragment={fragment!r}"
        raise RuntimeError(message)
    return error


def _mysql_version(connection: Connection) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION() AS mysql_version")
        row = cursor.fetchone()
    return str(row["mysql_version"])


def run(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = _load_json(SNAPSHOT_PATH)
    model_parameter = _load_json(MODEL_PARAMETER_CANONICAL_PATH)
    impact_lever = _load_json(IMPACT_LEVER_CANONICAL_PATH)
    connection = _connect(args)
    try:
        _reset_and_seed(connection, snapshot)
        _execute_static_sql(connection)
        _assert_canonical_read_back(connection, model_parameter, impact_lever, snapshot)
        first_digest = _digest(connection, include_mod_dtm=False)

        _execute_static_sql(connection)
        _assert_canonical_read_back(connection, model_parameter, impact_lever, snapshot)
        second_digest = _digest(connection, include_mod_dtm=False)
        if second_digest != first_digest:
            message = f"semantic idempotency mismatch: first={first_digest}, second={second_digest}"
            raise RuntimeError(message)

        _reset_and_seed(connection, snapshot)
        _execute_statement(
            connection,
            """
            UPDATE tmm_mi_model_param_m
               SET parameter_hint = CONCAT(parameter_hint, ' [forced-precondition-failure]')
             WHERE model_param_id = 21
            """,
        )
        master_error = _assert_failure_preserved_digest(
            connection,
            fragment="master precondition: row is neither pre-v4 nor canonical-v4",
        )

        _reset_and_seed(connection, snapshot)
        _execute_statement(
            connection,
            """
            UPDATE tmm_mi_model_impact_lever_m
               SET label = CONCAT(label, ' [forced-precondition-failure]')
             WHERE impact_lever_id = 1
            """,
        )
        lever_error = _assert_failure_preserved_digest(
            connection,
            fragment="Impact Lever precondition: row is neither pre-v4 nor canonical-v4",
        )

        _reset_and_seed(connection, snapshot)
        _execute_statement(
            connection,
            "DELETE FROM tmm_mi_scenario_dimension_template_m WHERE event_type_l2_id = 1",
        )
        invariant_error = _assert_failure_preserved_digest(
            connection,
            fragment="invariant: mapping key missing from active template",
        )

        result = {
            "database": args.database,
            "mysql_version": _mysql_version(connection),
            "canonical_semantic_digest": first_digest,
            "first_apply": "PASS",
            "second_apply_semantic_idempotency": "PASS",
            "master_precondition_failure_rollback": "PASS",
            "master_precondition_error": master_error,
            "impact_lever_precondition_failure_rollback": "PASS",
            "impact_lever_precondition_error": lever_error,
            "post_dml_invariant_failure_rollback": "PASS",
            "post_dml_invariant_error": invariant_error,
        }
        _reset_and_seed(connection, snapshot)
        return result
    finally:
        try:
            _drop_procedure(connection)
        finally:
            connection.close()


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        result = run(args)
    except Exception:
        LOGGER.exception("Model Parameter v4 static SQL verification failed")
        return 1
    LOGGER.info(
        "Model Parameter v4 static SQL verification PASS: %s",
        json.dumps(result, ensure_ascii=False, sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
