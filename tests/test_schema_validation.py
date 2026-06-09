from __future__ import annotations

import unittest

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text

from apps.common.configs.database.schema_validation import (
    SchemaMismatchError,
    find_schema_mismatches,
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
            Column("legacy_name", String(50), nullable=True),
        )
        db_metadata.create_all(self.engine)

        with self.assertRaisesRegex(SchemaMismatchError, "missing columns.*name"):
            validate_schema(self.engine, [table])

    def test_nullable_mismatch_is_reported(self) -> None:
        orm_metadata = MetaData()
        table = Table(
            "items",
            orm_metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
        )

        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name VARCHAR(50) NULL)"))

        mismatches = find_schema_mismatches(self.engine, [table])

        self.assertTrue(any("items.name: nullable mismatch" in mismatch for mismatch in mismatches))


if __name__ == "__main__":
    unittest.main()
