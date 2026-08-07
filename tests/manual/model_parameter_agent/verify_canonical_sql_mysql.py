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
import sys
from typing import Any

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import Cursor, DictCursor


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

LOGGER = logging.getLogger("model_parameter_canonical_sql_verify")
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_20260807.json"
CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v1.json"
SQL_PATH = ROOT_DIR / "scripts/model_parameter/apply_model_parameter_canonical_v1.sql"

ALLOWED_DATABASE_PATTERN = re.compile(r"model_parameter_sql_verify(?:_[a-z0-9_]+)?")

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

SCHEMA_STATEMENTS = (
    "DROP TABLE IF EXISTS tmm_mi_model_param_dimension_map",
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
        CONSTRAINT ck_tmm_mi_scenario_dimension_template_m_01 CHECK (JSON_TYPE(template_json) = 'ARRAY')
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
            "Reset an explicitly isolated MySQL database, seed the captured 128-row snapshot, and verify the "
            "canonical static SQL twice plus transaction rollback failure paths."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=33319)
    parser.add_argument("--user", default="verify")
    parser.add_argument("--password", default="verify")
    parser.add_argument("--database", default="model_parameter_sql_verify")
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        msg = f"JSON root must be an object: {path}"
        raise TypeError(msg)
    return document


def _validate_isolated_database_name(database: str) -> None:
    if ALLOWED_DATABASE_PATTERN.fullmatch(database) is None:
        msg = (
            "refusing destructive verification outside the isolated database namespace: "
            f"database={database!r}, required_pattern={ALLOWED_DATABASE_PATTERN.pattern!r}"
        )
        raise RuntimeError(msg)


def _connect(args: argparse.Namespace) -> Connection:
    _validate_isolated_database_name(args.database)
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


def _static_sql_statements(document: str) -> list[str]:
    start_marker = "DELIMITER //"
    end_marker = "DELIMITER ;"
    if document.count(start_marker) != 1 or document.count(end_marker) != 1:
        msg = "canonical SQL must contain one DELIMITER // block and one DELIMITER ; terminator"
        raise RuntimeError(msg)
    payload = document.split(start_marker, maxsplit=1)[1].split(end_marker, maxsplit=1)[0]
    statements = [chunk.strip() for chunk in payload.split("//") if chunk.strip()]
    if len(statements) != 4 or not statements[1].startswith("CREATE PROCEDURE"):
        msg = f"unexpected canonical SQL statement layout: statement_count={len(statements)}"
        raise RuntimeError(msg)
    return statements


def _execute_static_sql(connection: Connection) -> None:
    document = SQL_PATH.read_text(encoding="utf-8")
    for statement in _static_sql_statements(document):
        _execute_statement(connection, statement)


def _drop_procedure(connection: Connection) -> None:
    _execute_statement(connection, "DROP PROCEDURE IF EXISTS apply_model_parameter_canonical_v1")


def _database_value(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?", value):
        return datetime.fromisoformat(value)
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


def _reset_and_seed(connection: Connection, snapshot: Mapping[str, Any]) -> None:
    _drop_procedure(connection)
    for statement in SCHEMA_STATEMENTS:
        _execute_statement(connection, statement)
    _insert_rows(
        connection,
        table="tmm_mi_model_param_m",
        columns=MASTER_COLUMNS,
        rows=snapshot["master"],
    )
    _insert_rows(
        connection,
        table="tmm_mi_scenario_dimension_template_m",
        columns=TEMPLATE_COLUMNS,
        rows=snapshot["scenario_dimension_templates"],
    )
    _insert_rows(
        connection,
        table="tmm_mi_model_param_dimension_map",
        columns=MAPPING_COLUMNS,
        rows=snapshot["dimension_mappings"],
    )


def _read_rows(connection: Connection, *, table: str, columns: Sequence[str], order_by: str) -> list[dict[str, Any]]:
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


def _normalized(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _projection(row: Mapping[str, Any], columns: Iterable[str]) -> tuple[Any, ...]:
    return tuple(_normalized(row.get(column)) for column in columns)


def _indexed(rows: Iterable[Mapping[str, Any]], id_column: str) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for source in rows:
        row = dict(source)
        row_id = int(row[id_column])
        if row_id in indexed:
            msg = f"duplicate {id_column}: {row_id}"
            raise RuntimeError(msg)
        indexed[row_id] = row
    return indexed


def _assert_canonical_read_back(connection: Connection, canonical: Mapping[str, Any]) -> None:
    actual_master = _indexed(_read_master(connection), "model_param_id")
    expected_master = _indexed(canonical["master"], "model_param_id")
    master_stable_columns = tuple(column for column in MASTER_COLUMNS if column != "mod_dtm")
    if len(actual_master) != 21 or len(expected_master) != 21:
        msg = "unexpected master count during canonical read-back"
        raise RuntimeError(msg)
    for row_id, expected in expected_master.items():
        if _projection(actual_master[row_id], master_stable_columns) != _projection(expected, master_stable_columns):
            msg = f"master canonical read-back mismatch: model_param_id={row_id}"
            raise RuntimeError(msg)

    actual_mappings = _read_mappings(connection)
    expected_mappings = [dict(row) for row in canonical["dimension_mappings"]]
    expected_by_id = _indexed(
        (row for row in expected_mappings if row["model_param_dimension_map_id"] is not None),
        "model_param_dimension_map_id",
    )
    actual_by_id = _indexed(actual_mappings, "model_param_dimension_map_id")
    mapping_stable_columns = tuple(column for column in MAPPING_COLUMNS if column != "mod_dtm")
    for row_id, expected in expected_by_id.items():
        if _projection(actual_by_id[row_id], mapping_stable_columns) != _projection(expected, mapping_stable_columns):
            msg = f"mapping canonical read-back mismatch: mapping_id={row_id}"
            raise RuntimeError(msg)

    population_expected = next(
        row
        for row in expected_mappings
        if (row["event_type_l2_id"], row["dimension_key"], row["model_param_id"]) == (21, "economic_intensity", 11)
    )
    population_actual = [
        row
        for row in actual_mappings
        if (row["event_type_l2_id"], row["dimension_key"], row["model_param_id"]) == (21, "economic_intensity", 11)
    ]
    if len(actual_mappings) != 129 or len(population_actual) != 1:
        msg = f"unexpected canonical mapping counts: total={len(actual_mappings)}, population={len(population_actual)}"
        raise RuntimeError(msg)
    population_columns = tuple(
        column for column in MAPPING_COLUMNS if column not in {"model_param_dimension_map_id", "crt_dtm", "mod_dtm"}
    )
    if _projection(population_actual[0], population_columns) != _projection(population_expected, population_columns):
        msg = "Population canonical read-back mismatch"
        raise RuntimeError(msg)

    active_names = {
        row["parameter_name"] for row in actual_master.values() if row["use_yn"] == "Y" and row["del_yn"] == "N"
    }
    if active_names != set(canonical["active_parameter_names"]):
        msg = f"active parameter name mismatch: {sorted(active_names)}"
        raise RuntimeError(msg)
    method_counts = Counter(row["mapping_method"] for row in actual_mappings)
    if method_counts != {"direct": 35, "routing": 6, "indirect": 55, "na": 33}:
        msg = f"mapping method count mismatch: {dict(method_counts)}"
        raise RuntimeError(msg)


def _digest(connection: Connection, *, include_mod_dtm: bool) -> str:
    document: dict[str, list[dict[str, Any]]] = {
        "master": _read_master(connection),
        "mappings": _read_mappings(connection),
        "templates": _read_templates(connection),
    }
    for rows in document.values():
        for row in rows:
            if not include_mod_dtm:
                row.pop("mod_dtm", None)
            for key, value in row.items():
                row[key] = _normalized(value)
    serialized = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _expect_static_sql_failure(connection: Connection, *, message_fragment: str) -> str:
    try:
        _execute_static_sql(connection)
    except pymysql.MySQLError as exc:
        message = str(exc)
        if message_fragment not in message:
            msg = f"unexpected static SQL failure: expected={message_fragment!r}, actual={message!r}"
            raise RuntimeError(msg) from exc
        return message
    finally:
        _drop_procedure(connection)
    msg = f"static SQL unexpectedly succeeded; expected failure containing {message_fragment!r}"
    raise RuntimeError(msg)


def run(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = _load_json(SNAPSHOT_PATH)
    canonical = _load_json(CANONICAL_PATH)
    connection = _connect(args)
    try:
        _reset_and_seed(connection, snapshot)
        _execute_static_sql(connection)
        _assert_canonical_read_back(connection, canonical)
        first_digest = _digest(connection, include_mod_dtm=False)

        _execute_static_sql(connection)
        _assert_canonical_read_back(connection, canonical)
        second_digest = _digest(connection, include_mod_dtm=False)
        if second_digest != first_digest:
            msg = f"semantic idempotency digest mismatch: first={first_digest}, second={second_digest}"
            raise RuntimeError(msg)

        _reset_and_seed(connection, snapshot)
        _execute_statement(
            connection,
            """
            UPDATE tmm_mi_model_param_m
               SET parameter_hint = CONCAT(parameter_hint, ' [forced-precondition-failure]')
             WHERE model_param_id = 21
            """,
        )
        precondition_before = _digest(connection, include_mod_dtm=True)
        precondition_error = _expect_static_sql_failure(
            connection,
            message_fragment="master precondition: row is neither snapshot nor canonical",
        )
        precondition_after = _digest(connection, include_mod_dtm=True)
        if precondition_after != precondition_before:
            msg = "precondition failure changed table state instead of preserving it"
            raise RuntimeError(msg)

        _reset_and_seed(connection, snapshot)
        _execute_statement(
            connection,
            "DELETE FROM tmm_mi_scenario_dimension_template_m WHERE event_type_l2_id = 1",
        )
        invariant_before = _digest(connection, include_mod_dtm=True)
        invariant_error = _expect_static_sql_failure(
            connection,
            message_fragment="invariant: mapping key missing from active template",
        )
        invariant_after = _digest(connection, include_mod_dtm=True)
        if invariant_after != invariant_before:
            msg = "post-DML invariant failure did not roll back the complete transaction"
            raise RuntimeError(msg)

        return {
            "database": args.database,
            "mysql_version": _mysql_version(connection),
            "canonical_semantic_digest": first_digest,
            "first_apply": "PASS",
            "second_apply_idempotency": "PASS",
            "precondition_failure_rollback": "PASS",
            "precondition_error": precondition_error,
            "post_dml_invariant_failure_rollback": "PASS",
            "post_dml_invariant_error": invariant_error,
        }
    finally:
        try:
            _drop_procedure(connection)
        finally:
            connection.close()


def _mysql_version(connection: Connection) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION() AS mysql_version")
        row = cursor.fetchone()
    return str(row["mysql_version"])


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        result = run(args)
    except Exception:
        LOGGER.exception("canonical static SQL verification failed")
        return 1
    LOGGER.info("canonical static SQL verification PASS: %s", json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
