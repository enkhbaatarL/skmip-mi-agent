from __future__ import annotations

# ruff: noqa: CPY001, S101
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy.dialects import mysql

from apps.persistence.model_parameter.repository import ModelParameterRepository


class _ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _ExecuteResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarRows:
        return _ScalarRows(self._rows)


def _proposal_row(
    *,
    proposal_id: int,
    scenario_id: int,
    status: str,
    callback_status: str,
) -> SimpleNamespace:
    created_at = datetime(2026, 9, 17, 9, 0, proposal_id, tzinfo=UTC)
    modified_at = datetime(2026, 9, 17, 10, 0, proposal_id, tzinfo=UTC)
    return SimpleNamespace(
        model_param_proposal_id=proposal_id,
        scenario_id=scenario_id,
        scenario_group_id=20,
        status=status,
        callback_status=callback_status,
        callback_sent_dtm=modified_at if callback_status == "SUCCEEDED" else None,
        crt_dtm=created_at,
        mod_dtm=modified_at,
        proposal_completed_dtm=modified_at if status != "PROCESSING" else None,
        confirmed_dtm=modified_at if status == "CONFIRMED" else None,
        error_code="PROPOSAL_FAILED" if status == "FAILED" else None,
        error_message="safe failure detail" if status == "FAILED" else None,
    )


def test_fetch_proposal_guard_rows_empty_scenario_ids_skip_database() -> None:
    session = Mock()

    result = ModelParameterRepository(session=session).fetch_proposal_guard_rows(
        scenario_group_id=20,
        scenario_ids=[],
    )

    assert result == []
    session.execute.assert_not_called()


def test_fetch_proposal_guard_rows_uses_exact_scope_without_status_filter() -> None:
    session = Mock()
    rows = [
        _proposal_row(
            proposal_id=1,
            scenario_id=101,
            status="PROCESSING",
            callback_status="PENDING",
        ),
        _proposal_row(
            proposal_id=2,
            scenario_id=101,
            status="FAILED",
            callback_status="FAILED",
        ),
        _proposal_row(
            proposal_id=3,
            scenario_id=102,
            status="CONFIRMED",
            callback_status="SUCCEEDED",
        ),
    ]
    session.execute.return_value = _ExecuteResult(rows)

    result = ModelParameterRepository(session=session).fetch_proposal_guard_rows(
        scenario_group_id=20,
        scenario_ids=[101, 102],
    )

    stmt = session.execute.call_args.args[0]
    compiled = str(
        stmt.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        ),
    )
    where_sql = compiled.partition("WHERE")[2].partition("ORDER BY")[0]

    assert "tmm_mi_model_param_proposal_m.scenario_group_id = 20" in where_sql
    assert "tmm_mi_model_param_proposal_m.scenario_id IN (101, 102)" in where_sql
    assert "tmm_mi_model_param_proposal_m.del_yn = 'N'" in where_sql
    assert "tmm_mi_model_param_proposal_m.status" not in where_sql
    assert (
        "ORDER BY tmm_mi_model_param_proposal_m.scenario_id, tmm_mi_model_param_proposal_m.model_param_proposal_id"
    ) in compiled
    assert [row["status"] for row in result] == ["PROCESSING", "FAILED", "CONFIRMED"]
    assert result == [
        {
            "model_param_proposal_id": row.model_param_proposal_id,
            "scenario_id": row.scenario_id,
            "scenario_group_id": row.scenario_group_id,
            "status": row.status,
            "callback_status": row.callback_status,
            "callback_sent_dtm": row.callback_sent_dtm,
            "crt_dtm": row.crt_dtm,
            "mod_dtm": row.mod_dtm,
            "proposal_completed_dtm": row.proposal_completed_dtm,
            "confirmed_dtm": row.confirmed_dtm,
            "error_code": row.error_code,
            "error_message": row.error_message,
        }
        for row in rows
    ]
