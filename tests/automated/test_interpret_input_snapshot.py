# ruff: noqa: S101, SLF001

from __future__ import annotations

from typing import Any

import pytest

from apps.agents.interpret_agent.flows.interpret_price.schema import ScenarioPrices
from apps.agents.interpret_agent.persistence import proposal_parameter_service
from apps.agents.interpret_agent.persistence.proposal_parameter_service import (
    ProposalParameterService,
    _accumulate,
    _validate_monthly_rows,
)
from apps.agents.interpret_agent.utils.region_index import INDEX_ORDER
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.model_result.repository import ModelResultRepository


def _months(
    start_year: int = 2026,
    start_month: int = 4,
    end_year: int = 2030,
    end_month: int = 12,
) -> list[str]:
    result: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        result.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return result


def _base_rows(months: list[str] | None = None) -> list[dict[str, Any]]:
    selected_months = _months() if months is None else months
    return [
        {
            "period_key": month,
            "value": 10.0 + offset / 100,
            "case_id": 15,
            "run_id": 500,
            "run_seq": 501,
        }
        for offset, month in enumerate(selected_months)
    ]


def _scenario_rows(months: list[str] | None = None) -> list[dict[str, Any]]:
    selected_months = _months() if months is None else months
    return [
        {
            "period_key": month,
            "base_value": 10.0 + offset / 100,
            "value": 11.0 + offset / 100,
            "case_id": 25,
            "run_id": 700,
            "run_seq": 701,
        }
        for offset, month in enumerate(selected_months)
    ]


def _proposal(
    scenario_id: int,
    proposal_id: int,
    mi_base_case_id: int | None,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "model_param_proposal_id": proposal_id,
        "mi_base_case_id": mi_base_case_id,
    }


def test_proposal_snapshot_requires_one_shared_pinned_mi_base() -> None:
    snapshot = ProposalParameterService._resolve_proposal_snapshot(
        [_proposal(101, 901, 15), _proposal(102, 902, 15)],
    )

    assert snapshot.mi_base_case_id == 15
    assert snapshot.proposal_ids == {"101": 901, "102": 902}

    with pytest.raises(MIBaseError, match="mi_base_case_id"):
        ProposalParameterService._resolve_proposal_snapshot([_proposal(101, 901, None)])
    with pytest.raises(MIBaseError, match="서로 다른 MI Base"):
        ProposalParameterService._resolve_proposal_snapshot(
            [_proposal(101, 901, 15), _proposal(102, 902, 16)],
        )


def test_conflicting_basecase_values_fail_instead_of_overwriting() -> None:
    store: dict[tuple, dict[str, float]] = {}
    key = ("Temperature", "monthly", (("Country", "South Korea"),))
    _accumulate(store, key, "2026-04", 3.5)
    _accumulate(store, key, "2026-04", 3.5)

    with pytest.raises(MIBaseError, match="충돌 값"):
        _accumulate(store, key, "2026-04", 1.0)


def test_model_result_axis_preserves_partial_first_year_through_2030() -> None:
    months = _months()

    assert len(months) == 57
    assert _validate_monthly_rows(_base_rows(months), context="test") == months
    assert months[0] == "2026-04"
    assert months[-1] == "2030-12"


def test_model_result_repository_queries_exact_pinned_base_case() -> None:
    class Mappings:
        def all(self) -> list[dict[str, Any]]:
            return [
                {
                    "period_key": 202604,
                    "value": 10.5,
                    "case_id": 15,
                    "run_id": 500,
                    "run_seq": 501,
                },
            ]

    class Result:
        def mappings(self) -> Mappings:
            return Mappings()

    class Session:
        def __init__(self) -> None:
            self.calls: list[tuple[object, dict[str, object]]] = []

        def execute(self, statement: object, parameters: dict[str, object]) -> Result:
            self.calls.append((statement, parameters))
            return Result()

    session = Session()
    rows = ModelResultRepository(session=session).fetch_mi_base_prices(
        mi_base_case_id=15,
        prc_rgn_nm="East Asia Spot",
    )

    statement, parameters = session.calls[0]
    assert parameters == {"mi_base_case_id": 15, "prc_rgn_nm": "East Asia Spot"}
    assert "c.case_id = :mi_base_case_id" in str(statement)
    assert "MAX(mb.case_id)" not in str(statement)
    assert rows == [
        {
            "period_key": "2026-04",
            "value": 10.5,
            "case_id": 15,
            "run_id": 500,
            "run_seq": 501,
        },
    ]


def test_scenario_price_repository_preserves_base_and_run_evidence() -> None:
    grouped = ModelResultRepository._group_rows_by_scenario(
        [
            {
                "scenario_id": 101,
                "period_key": 202604,
                "base_value": 10.5,
                "value": 11.5,
                "case_id": 25,
                "run_id": 700,
                "run_seq": 701,
            },
        ],
    )

    assert grouped == {
        101: [
            {
                "period_key": "2026-04",
                "base_value": 10.5,
                "value": 11.5,
                "case_id": 25,
                "run_id": 700,
                "run_seq": 701,
            },
        ],
    }


@pytest.mark.parametrize(
    ("months", "message"),
    [
        (["2026-04", "2026-04"], "중복"),
        (["2026-04", "2026-06"], "연속적이지"),
        (["2026-05", "2026-04"], "오름차순"),
        (["2026-13"], "월 범위"),
        (["202604"], "YYYY-MM"),
    ],
)
def test_model_result_axis_rejects_invalid_month_sequences(
    months: list[str],
    message: str,
) -> None:
    with pytest.raises(MIBaseError, match=message):
        _validate_monthly_rows(_base_rows(months), context="test")


def test_scenario_run_must_match_pinned_base_axis_and_values() -> None:
    service = ProposalParameterService()
    base_rows = _base_rows()

    service._validate_price_base_alignment(
        scenario_id="101",
        index="JKM",
        mi_base_case_id=15,
        base_rows=base_rows,
        scenario_rows=_scenario_rows(),
    )

    with pytest.raises(MIBaseError, match="월 축이 일치하지"):
        service._validate_price_base_alignment(
            scenario_id="101",
            index="JKM",
            mi_base_case_id=15,
            base_rows=base_rows,
            scenario_rows=_scenario_rows(_months()[:-1]),
        )

    mismatched_values = _scenario_rows()
    mismatched_values[3]["base_value"] = 999.0
    with pytest.raises(MIBaseError, match="고정된 MI Base 가격과 일치하지"):
        service._validate_price_base_alignment(
            scenario_id="101",
            index="JKM",
            mi_base_case_id=15,
            base_rows=base_rows,
            scenario_rows=mismatched_values,
        )


def test_price_loader_uses_exact_case_and_records_run_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object, object]] = []

    class FakeModelResultRepository:
        def __init__(self, *, session: object) -> None:
            calls.append(("session", session, None))

        def fetch_mi_base_prices(
            self,
            *,
            mi_base_case_id: int,
            prc_rgn_nm: str,
        ) -> list[dict[str, Any]]:
            calls.append(("base", mi_base_case_id, prc_rgn_nm))
            return _base_rows()

        def fetch_scenario_prices(
            self,
            scenario_group_id: int,
            prc_rgn_nm: str,
        ) -> dict[int, list[dict[str, Any]]]:
            calls.append(("scenario", scenario_group_id, prc_rgn_nm))
            return {101: _scenario_rows()}

    monkeypatch.setattr(
        proposal_parameter_service,
        "ModelResultRepository",
        FakeModelResultRepository,
    )

    prices, base_run_seq, run_seqs = ProposalParameterService()._load_prices(
        object(),
        52,
        ["101"],
        mi_base_case_id=15,
    )

    assert base_run_seq == 501
    assert run_seqs == {"101": 701}
    assert len(prices["MI Base"].prices) == len(INDEX_ORDER)
    assert len(prices["101"].prices) == len(INDEX_ORDER)
    assert prices["101"].prices[0].months[0] == "2026-04"
    assert prices["101"].prices[0].months[-1] == "2030-12"
    assert [call[1] for call in calls if call[0] == "base"] == [15] * len(INDEX_ORDER)


def test_meta_period_comes_only_from_model_result_axis() -> None:
    scenario_prices = {
        "MI Base": ScenarioPrices(
            scenario_id="MI Base",
            prices=[],
        ),
        "101": ScenarioPrices(
            scenario_id="101",
            prices=[
                {
                    "index": "JKM",
                    "months": _months(),
                    "values": [10.0] * len(_months()),
                },
            ],
        ),
    }

    periods = ProposalParameterService._collect_price_months(scenario_prices)

    assert periods[0] == "2026-04"
    assert periods[-1] == "2030-12"
