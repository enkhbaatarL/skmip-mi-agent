from __future__ import annotations

# Validation policy:
# - DB-only columns are logged as warnings because they are forward-compatible.
# - DB nullable columns for ORM non-nullable fields are warnings because the
#   application can still provide values, though DB data quality is looser.
# - Missing ORM tables/columns, stricter DB nullability, and incompatible column
#   definitions are errors because application code may depend on them at runtime.
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Boolean, Engine, Table, inspect
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.sql.type_api import TypeEngine


class SchemaMismatchError(RuntimeError):
    """Raised when the database schema is incompatible with ORM metadata."""


@dataclass(frozen=True)
class SchemaValidationResult:
    """Schema validation result grouped by startup impact.

    errors block application startup.
    warnings are logged, but do not block startup.
    """

    errors: list[str]
    warnings: list[str]


def _type_details(column_type: TypeEngine[Any]) -> dict[str, Any]:
    return {
        attribute: getattr(column_type, attribute, None)
        for attribute in ("length", "precision", "scale", "fsp", "unsigned")
        if getattr(column_type, attribute, None) is not None
    }


def _types_match(expected: TypeEngine[Any], actual: TypeEngine[Any]) -> bool:
    if isinstance(expected, Boolean) and isinstance(actual, TINYINT) and actual.display_width == 1:
        # MySQL stores BOOL/BOOLEAN as TINYINT(1), and reflection returns TINYINT.
        return True

    if not isinstance(actual, expected._type_affinity):  # noqa: SLF001
        return False

    expected_details = _type_details(expected)
    actual_details = _type_details(actual)
    return all(actual_details.get(key) == value for key, value in expected_details.items())


def find_schema_validation_result(engine: Engine, tables: Sequence[Table]) -> SchemaValidationResult:
    """Return blocking errors and non-blocking warnings for ORM/DB schema differences."""
    inspector = inspect(engine)
    database_tables = set(inspector.get_table_names())
    errors: list[str] = []
    warnings: list[str] = []

    for table in sorted(tables, key=lambda item: item.name):
        if table.name not in database_tables:
            errors.append(f"{table.name}: missing table")
            continue

        expected_columns = {column.name: column for column in table.columns}
        actual_columns = {column["name"]: column for column in inspector.get_columns(table.name)}

        missing_columns = sorted(expected_columns.keys() - actual_columns.keys())
        unexpected_columns = sorted(actual_columns.keys() - expected_columns.keys())
        if missing_columns:
            errors.append(f"{table.name}: missing columns {missing_columns}")
        if unexpected_columns:
            # DB-only columns are forward-compatible and should not block startup.
            warnings.append(f"{table.name}: unexpected columns {unexpected_columns}")

        for column_name in sorted(expected_columns.keys() & actual_columns.keys()):
            expected = expected_columns[column_name]
            actual = actual_columns[column_name]

            if not _types_match(expected.type, actual["type"]):
                errors.append(
                    f"{table.name}.{column_name}: type mismatch (ORM={expected.type!s}, DB={actual['type']!s})"
                )

            actual_nullable = bool(actual["nullable"])
            if expected.nullable != actual_nullable:
                message = (
                    f"{table.name}.{column_name}: nullable mismatch (ORM={expected.nullable}, DB={actual_nullable})"
                )
                if expected.nullable is False and actual_nullable is True:
                    # ORM nullable=False, DB nullable=True (DB가 더 느슨함) → warning
                    warnings.append(message)
                else:
                    # ORM nullable=True, DB nullable=False (DB가 더 엄격함) → error
                    errors.append(message)

        expected_pk = {column.name for column in table.primary_key.columns}
        actual_pk = set(inspector.get_pk_constraint(table.name).get("constrained_columns") or [])
        if expected_pk != actual_pk:
            errors.append(f"{table.name}: primary key mismatch (ORM={sorted(expected_pk)}, DB={sorted(actual_pk)})")

    return SchemaValidationResult(errors=errors, warnings=warnings)


def find_schema_mismatches(engine: Engine, tables: Sequence[Table]) -> list[str]:
    """Return blocking ORM/DB schema differences for the supplied application tables."""
    return find_schema_validation_result(engine, tables).errors


def validate_schema(engine: Engine, tables: Sequence[Table]) -> None:
    """Fail application startup on blocking schema differences; log warnings only."""
    result = find_schema_validation_result(engine, tables)
    if result.warnings:
        from apps.common.logging.logger_config import logger

        details = "\n".join(f"- {warning}" for warning in result.warnings)
        logger.warning("ORM/DB schema validation warnings (non-blocking):\n{}", details)
    if result.errors:
        details = "\n".join(f"- {error}" for error in result.errors)
        raise SchemaMismatchError(f"ORM/DB schema validation failed:\n{details}")
