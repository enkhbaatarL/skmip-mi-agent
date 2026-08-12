# ruff: noqa: PT009, S101

from __future__ import annotations

import unittest

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.dialects.mysql import TINYINT

from apps.common.configs.database.schema_validation import (
    SchemaMismatchError,
    _types_match,
    find_schema_mismatches,
    find_schema_validation_result,
    validate_schema,
)


class SchemaValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_matching_schema_has_no_mismatches(self) -> None:
        metadata = MetaData()
        table = Table(
            "items",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
        )
        metadata.create_all(self.engine)

        self.assertEqual(find_schema_mismatches(self.engine, [table]), [])

    def test_mysql_tinyint_one_matches_boolean(self) -> None:
        assert _types_match(Boolean(), TINYINT(display_width=1))

    def test_mysql_tinyint_without_boolean_width_does_not_match_boolean(self) -> None:
        assert not _types_match(Boolean(), TINYINT())

    def test_schema_difference_raises_with_details(self) -> None:
        orm_metadata = MetaData()
        table = Table(
            "items",
            orm_metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
        )

        db_metadata = MetaData()
        Table(
            "items",
            db_metadata,
            Column("id", Integer, primary_key=True),
        )
        db_metadata.create_all(self.engine)

        with self.assertRaisesRegex(SchemaMismatchError, "missing columns.*name"):
            validate_schema(self.engine, [table])

    def test_db_looser_nullable_mismatch_is_warning_only(self) -> None:
        orm_metadata = MetaData()
        table = Table(
            "items",
            orm_metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
        )

        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name VARCHAR(50) NULL)"))

        result = find_schema_validation_result(self.engine, [table])

        self.assertTrue(any("items.name: nullable mismatch" in warning for warning in result.warnings))
        self.assertFalse(any("items.name: nullable mismatch" in error for error in result.errors))

    def test_db_stricter_nullable_mismatch_is_error(self) -> None:
        orm_metadata = MetaData()
        table = Table(
            "items",
            orm_metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=True),
        )

        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name VARCHAR(50) NOT NULL)"))

        result = find_schema_validation_result(self.engine, [table])

        self.assertTrue(any("items.name: nullable mismatch" in error for error in result.errors))
        self.assertFalse(any("items.name: nullable mismatch" in warning for warning in result.warnings))

    def test_unexpected_columns_are_warnings_only(self) -> None:
        orm_metadata = MetaData()
        table = Table(
            "items",
            orm_metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
        )

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE items ("
                    "id INTEGER PRIMARY KEY, "
                    "name VARCHAR(50) NOT NULL, "
                    "legacy_name VARCHAR(50) NULL"
                    ")"
                )
            )

        result = find_schema_validation_result(self.engine, [table])

        self.assertTrue(any("items: unexpected columns ['legacy_name']" in warning for warning in result.warnings))
        self.assertFalse(any("unexpected columns" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
