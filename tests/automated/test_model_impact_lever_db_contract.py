from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
from unittest.mock import MagicMock

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import mysql

from apps.persistence.model_impact_lever.models import MiModelImpactLeverModel
from apps.persistence.model_impact_lever.repository import ModelImpactLeverRepository


def test_impact_lever_orm_matches_0030_versioned_keys() -> None:
    table = MiModelImpactLeverModel.__table__
    unique = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint) and constraint.name == "uk_tmm_mi_model_impact_lever_m_01"
    )
    foreign_key = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint) and constraint.name == "fk_tmm_mi_model_impact_lever_m_02"
    )
    indexes = {index.name: tuple(column.name for column in index.columns) for index in table.indexes}

    assert tuple(column.name for column in unique.columns) == ("catalog_version", "lever_code")
    assert indexes["idx_tmm_mi_model_impact_lever_m_01"] == (
        "catalog_version",
        "domain",
        "lever_code",
    )
    assert indexes["idx_tmm_mi_model_impact_lever_m_02"] == (
        "catalog_version",
        "parent_lever_code",
    )
    assert tuple(element.parent.name for element in foreign_key.elements) == (
        "catalog_version",
        "parent_lever_code",
    )
    assert tuple(element.target_fullname for element in foreign_key.elements) == (
        "tmm_mi_model_impact_lever_m.catalog_version",
        "tmm_mi_model_impact_lever_m.lever_code",
    )


def test_active_catalog_query_filters_requested_version_and_active_rows() -> None:
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    ModelImpactLeverRepository(session=session).fetch_active_impact_levers(
        catalog_version="v4",
    )

    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=mysql.dialect())
    where_sql = str(statement.whereclause)
    assert "catalog_version" in where_sql
    assert "use_yn" in where_sql
    assert "del_yn" in where_sql
    assert {"v4", "Y", "N"} <= set(compiled.params.values())
    assert [column.name for column in statement._order_by_clauses] == [  # noqa: SLF001
        "domain",
        "lever_code",
    ]


def test_display_label_query_is_version_scoped_but_can_render_inactive_history() -> None:
    session = MagicMock()
    session.execute.return_value.all.return_value = []

    ModelImpactLeverRepository(session=session).fetch_display_labels(
        catalog_version="v0",
    )

    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=mysql.dialect())
    where_sql = str(statement.whereclause)
    assert "catalog_version" in where_sql
    assert "del_yn" in where_sql
    assert "use_yn" not in where_sql
    assert {"v0", "N"} <= set(compiled.params.values())
