from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Engine, Table, inspect
from sqlalchemy.sql.type_api import TypeEngine


class SchemaMismatchError(RuntimeError):
    """Raised when the database schema is incompatible with ORM metadata."""


def _type_details(column_type: TypeEngine[Any]) -> dict[str, Any]:
    return {
        attribute: getattr(column_type, attribute, None)
        for attribute in ("length", "precision", "scale", "fsp", "unsigned")
        if getattr(column_type, attribute, None) is not None
    }


def _types_match(expected: TypeEngine[Any], actual: TypeEngine[Any]) -> bool:
    if not isinstance(actual, expected._type_affinity):  # noqa: SLF001
        return False

    expected_details = _type_details(expected)
    actual_details = _type_details(actual)
    return all(actual_details.get(key) == value for key, value in expected_details.items())


def find_schema_mismatches(engine: Engine, tables: Sequence[Table]) -> list[str]:
    """Return ORM/DB schema differences for the supplied application tables."""
    inspector = inspect(engine)
    database_tables = set(inspector.get_table_names())
    mismatches: list[str] = []

    for table in sorted(tables, key=lambda item: item.name):
        if table.name not in database_tables:
            mismatches.append(f"{table.name}: missing table")
            continue

        expected_columns = {column.name: column for column in table.columns}
        actual_columns = {column["name"]: column for column in inspector.get_columns(table.name)}

        missing_columns = sorted(expected_columns.keys() - actual_columns.keys())
        unexpected_columns = sorted(actual_columns.keys() - expected_columns.keys())
        if missing_columns:
            mismatches.append(f"{table.name}: missing columns {missing_columns}")
        if unexpected_columns:
            mismatches.append(f"{table.name}: unexpected columns {unexpected_columns}")

        for column_name in sorted(expected_columns.keys() & actual_columns.keys()):
            expected = expected_columns[column_name]
            actual = actual_columns[column_name]

            if not _types_match(expected.type, actual["type"]):
                mismatches.append(
                    f"{table.name}.{column_name}: type mismatch "
                    f"(ORM={expected.type!s}, DB={actual['type']!s})"
                )

            actual_nullable = bool(actual["nullable"])
            if expected.nullable != actual_nullable:
                mismatches.append(
                    f"{table.name}.{column_name}: nullable mismatch "
                    f"(ORM={expected.nullable}, DB={actual_nullable})"
                )

        expected_pk = {column.name for column in table.primary_key.columns}
        actual_pk = set(inspector.get_pk_constraint(table.name).get("constrained_columns") or [])
        if expected_pk != actual_pk:
            mismatches.append(
                f"{table.name}: primary key mismatch "
                f"(ORM={sorted(expected_pk)}, DB={sorted(actual_pk)})"
            )

    return mismatches


def validate_schema(engine: Engine, tables: Sequence[Table]) -> None:
    """Fail application startup when ORM metadata and the DB schema differ."""
    mismatches = find_schema_mismatches(engine, tables)
    if mismatches:
        details = "\n".join(f"- {mismatch}" for mismatch in mismatches)
        raise SchemaMismatchError(f"ORM/DB schema validation failed:\n{details}")
