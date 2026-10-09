"""제안 파라미터(입력 feature) 및 예측 가격 로딩 서비스.

데이터 출처(라이브 DB):
- 입력 feature: `tmm_mi_model_param_proposal_m.proposal_parameters` JSON
  (`ModelParameterRepository`). `values[*].basecaseValue`=MI Base 입력,
  `proposedValue`=시나리오 입력. 그룹화 축(Country/Region/DegreeDayType 등)은
  `modelTarget.slotAxesFieldNames` 로 가변 정의되며, Year/Month 는 시간 축으로 분리한다.
- 예측 가격 결과: 모델 실행 결과 테이블(`ModelResultRepository`, read-only raw SQL).
  MI Base=`base_case_prc`, 시나리오=`user_adj_prc`. 지수(JKM/TTF/HH) 각각을
  `INDEX_PRICE_REGION` 매핑으로 조회하며 항상 monthly 기준이다.

정규화 결과는 기존 해석 파이프라인이 그대로 소비하는 `InterpretInput` 이다
(시나리오 features=proposedValue, base features=모든 proposal basecaseValue 병합).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
import re
from typing import Any

from sqlalchemy.orm import Session

from apps.agents.interpret_agent.constants import INTERPRET_AGENT_VERSION
from apps.agents.interpret_agent.flows.interpret_price.schema import (
    FeatureSeries,
    InterpretInput,
    PriceSeries,
    ScenarioFeatures,
    ScenarioPrices,
)
from apps.agents.interpret_agent.utils.region_index import (
    BASE_SCENARIO_ID,
    INDEX_ORDER,
    INDEX_PRICE_REGION,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.model_result.repository import ModelResultRepository


# 시간 축(그룹 키에서 제외하고 기간 키 생성에 사용).
_TIME_AXES = ("Year", "Month")
# region 라벨로 승격할 geo 성격 축 힌트(소문자 부분일치).
_GEO_AXIS_HINTS = ("country", "region", "continent", "area", "zone", "nation")
_PRICE_BASE_REL_TOLERANCE = 1e-9
_PRICE_BASE_ABS_TOLERANCE = 1e-9
_MONTH_KEY_RE = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True)
class _ProposalSnapshot:
    mi_base_case_id: int
    proposal_ids: dict[str, int]


def _resolve_granularity(axes: list[str]) -> str:
    return "monthly" if "Month" in axes else "annual"


def _period_key(record: dict, granularity: str) -> str | None:
    year = record.get("Year")
    if year is None:
        return None
    if granularity == "monthly":
        month = record.get("Month")
        if month is None:
            return None
        return f"{int(year):04d}-{int(month):02d}"
    return f"{int(year):04d}"


def _derive_region(group_keys: dict[str, str]) -> tuple[str, str | None, str | None]:
    """가변 group_keys에서 표시용 (region, geo_level, qualifier)를 파생한다.

    - region: geo 성격 축(Country/Region 등)의 값, 없으면 첫 축 값.
    - geo_level: region으로 채택된 축 이름(라벨 품질 힌트).
    - qualifier: region 축을 제외한 나머지 축을 "k=v"로 결합(없으면 None).
    """
    if not group_keys:
        return "", None, None
    region_axis: str | None = None
    for axis in group_keys:
        if any(hint in axis.lower() for hint in _GEO_AXIS_HINTS):
            region_axis = axis
            break
    if region_axis is None:
        region_axis = next(iter(group_keys))
    region = group_keys[region_axis]
    others = [f"{k}={v}" for k, v in group_keys.items() if k != region_axis]
    qualifier = ", ".join(others) if others else None
    return region, region_axis, qualifier


def _accumulate(
    store: dict[tuple, dict[str, float]],
    key: tuple,
    period: str,
    value: object,
) -> None:
    if value is None:
        return
    normalized = float(value)
    period_values = store.setdefault(key, {})
    existing = period_values.get(period)
    if existing is not None and not isclose(
        existing,
        normalized,
        rel_tol=0.0,
        abs_tol=0.0,
    ):
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=(
                "제안 파라미터에 동일 feature·축·기간의 충돌 값이 있습니다. "
                f"key={key}, period={period}, values=({existing}, {normalized})"
            ),
        )
    period_values[period] = normalized


def _build_feature_series(store: dict[tuple, dict[str, float]]) -> list[FeatureSeries]:
    series: list[FeatureSeries] = []
    for (feature, granularity, gk_items), period_map in store.items():
        group_keys = dict(gk_items)
        region, geo_level, qualifier = _derive_region(group_keys)
        periods = sorted(period_map.keys())
        series.append(
            FeatureSeries(
                feature=feature,
                region=region,
                geo_level=geo_level,
                index=None,
                unit="",
                granularity=granularity,
                qualifier=qualifier,
                group_keys=group_keys,
                periods=periods,
                values=[period_map[p] for p in periods],
            )
        )
    return series


class ProposalParameterService:
    """DB에서 입력 feature/가격을 정규화된 `InterpretInput`으로 제공."""

    def load_interpret_input(
        self,
        scenario_group_id: int | None = None,
        scenario_ids: list[int] | None = None,
    ) -> InterpretInput:
        if scenario_group_id is None:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="scenario_group_id가 필요합니다.",
            )

        from apps.common.configs.database.sync_database.connection import (
            get_sync_session,
        )

        session = get_sync_session()
        try:
            # 해석 대상 시나리오는 제안 파라미터(proposal) 자체를 근거로 결정한다.
            # (scenario 마스터 테이블 정합성에 의존하지 않아 견고함)
            wanted_ids = [int(str(s).strip()) for s in scenario_ids] if scenario_ids else None
            proposals = ModelParameterRepository(session=session).fetch_proposals_by_group(
                scenario_group_id, wanted_ids
            )
            if not proposals:
                detail = f"그룹 {scenario_group_id}의 해석 대상 제안 파라미터가 없습니다." + (
                    f" (요청 시나리오: {sorted(set(wanted_ids))})" if wanted_ids else ""
                )
                raise MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=detail)

            snapshot = self._resolve_proposal_snapshot(proposals)
            logger.info(
                "[interpret_price] pinned proposal snapshot | "
                f"mi_base_case_id={snapshot.mi_base_case_id} "
                f"| proposal_ids={snapshot.proposal_ids}"
            )
            scenario_features, base_features, target_ids = self._normalize_features(proposals)
            scenario_prices, mi_base_price_run_seq, scenario_price_run_seqs = self._load_prices(
                session,
                scenario_group_id,
                target_ids,
                mi_base_case_id=snapshot.mi_base_case_id,
            )

            features = self._collect_feature_names(base_features, scenario_features)
            months = self._collect_price_months(scenario_prices)

            return InterpretInput(
                scenario_group_id=scenario_group_id,
                base_scenario_id=BASE_SCENARIO_ID,
                mi_base_case_id=snapshot.mi_base_case_id,
                mi_base_price_run_seq=mi_base_price_run_seq,
                model_param_proposal_ids=snapshot.proposal_ids,
                scenario_price_run_seqs=scenario_price_run_seqs,
                scenario_ids=target_ids,
                features=features,
                period_start=months[0] if months else None,
                period_end=months[-1] if months else None,
                scenario_features=scenario_features,
                scenario_prices=scenario_prices,
            )
        finally:
            session.close()

    # ---------------------------------------------------------------- #
    @staticmethod
    def _resolve_proposal_snapshot(proposals: list[dict[str, Any]]) -> _ProposalSnapshot:
        proposal_ids: dict[str, int] = {}
        invalid_base_scenarios: list[int] = []
        base_case_ids: set[int] = set()

        for proposal in proposals:
            scenario_id = int(proposal["scenario_id"])
            proposal_id = proposal.get("model_param_proposal_id")
            if isinstance(proposal_id, bool) or not isinstance(proposal_id, int) or proposal_id <= 0:
                raise MIBaseError(
                    ErrorCode.DATA_RETRIEVAL_FAILED,
                    detail=(
                        f"Scenario {scenario_id}의 Model Parameter proposal ID가 유효하지 않습니다: {proposal_id!r}"
                    ),
                )
            proposal_ids[str(scenario_id)] = proposal_id

            mi_base_case_id = proposal.get("mi_base_case_id")
            if isinstance(mi_base_case_id, bool) or not isinstance(mi_base_case_id, int) or mi_base_case_id <= 0:
                invalid_base_scenarios.append(scenario_id)
            else:
                base_case_ids.add(mi_base_case_id)

        if invalid_base_scenarios:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=(
                    f"Interpret Agent {INTERPRET_AGENT_VERSION}은 proposal에 고정된 양수 "
                    "mi_base_case_id가 필요합니다. "
                    f"invalid_scenario_ids={sorted(invalid_base_scenarios)}"
                ),
            )
        if len(base_case_ids) != 1:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=(
                    "하나의 해석 요청에 서로 다른 MI Base case를 섞을 수 없습니다. "
                    f"mi_base_case_ids={sorted(base_case_ids)}"
                ),
            )

        return _ProposalSnapshot(
            mi_base_case_id=next(iter(base_case_ids)),
            proposal_ids=proposal_ids,
        )

    def _normalize_features(
        self, proposals: list[dict]
    ) -> tuple[dict[str, ScenarioFeatures], list[FeatureSeries], list[str]]:
        base_store: dict[tuple, dict[str, float]] = {}
        scen_stores: dict[str, dict[tuple, dict[str, float]]] = {}
        target_ids: list[str] = []

        for proposal in proposals:
            sid = str(proposal["scenario_id"])
            if sid not in scen_stores:
                scen_stores[sid] = {}
                target_ids.append(sid)
            store = scen_stores[sid]

            for param in proposal.get("proposal_parameters") or []:
                feature = str(param.get("parameterName", ""))
                target = param.get("modelTarget") or {}
                axes = [str(a) for a in (target.get("slotAxesFieldNames") or [])]
                granularity = _resolve_granularity(axes)
                group_axes = [a for a in axes if a not in _TIME_AXES]

                for record in param.get("values") or []:
                    period = _period_key(record, granularity)
                    if period is None:
                        continue
                    group_keys = {axis: str(record.get(axis)) for axis in group_axes if record.get(axis) is not None}
                    key = (
                        feature,
                        granularity,
                        tuple(sorted(group_keys.items())),
                    )
                    _accumulate(base_store, key, period, record.get("basecaseValue"))
                    _accumulate(store, key, period, record.get("proposedValue"))

        base_features = _build_feature_series(base_store)
        scenario_features: dict[str, ScenarioFeatures] = {
            BASE_SCENARIO_ID: ScenarioFeatures(scenario_id=BASE_SCENARIO_ID, features=base_features)
        }
        for sid in target_ids:
            scenario_features[sid] = ScenarioFeatures(scenario_id=sid, features=_build_feature_series(scen_stores[sid]))
        return scenario_features, base_features, target_ids

    def _load_prices(
        self,
        session: Session,
        scenario_group_id: int,
        target_ids: list[str],
        *,
        mi_base_case_id: int,
    ) -> tuple[dict[str, ScenarioPrices], int, dict[str, int]]:
        repo = ModelResultRepository(session=session)
        base_series: list[PriceSeries] = []
        scenario_series: dict[str, list[PriceSeries]] = {sid: [] for sid in target_ids}
        scenario_run_seqs: dict[str, set[int]] = {sid: set() for sid in target_ids}
        base_price_axis: list[str] | None = None
        base_run_seqs: set[int] = set()

        for index in INDEX_ORDER:
            prc_rgn_nm = INDEX_PRICE_REGION[index]

            base_rows = repo.fetch_mi_base_prices(
                mi_base_case_id=mi_base_case_id,
                prc_rgn_nm=prc_rgn_nm,
            )
            if base_rows:
                base_price_axis = _validate_base_price_rows(
                    base_rows,
                    mi_base_case_id=mi_base_case_id,
                    index=index,
                    expected_axis=base_price_axis,
                )
                base_run_seqs.update(_run_sequences(base_rows))
                base_series.append(_price_series(index, base_rows))

            scenario_rows = repo.fetch_scenario_prices(scenario_group_id, prc_rgn_nm)
            for sid in target_ids:
                rows = scenario_rows.get(int(sid)) or []
                if rows:
                    self._validate_price_base_alignment(
                        scenario_id=sid,
                        index=index,
                        mi_base_case_id=mi_base_case_id,
                        base_rows=base_rows,
                        scenario_rows=rows,
                    )
                    scenario_run_seqs[sid].update(_run_sequences(rows))
                    scenario_series[sid].append(_price_series(index, rows))

        # 가격 결과가 전혀 없으면(빈 결과) 에러로 처리한다.
        if not base_series:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=(f"MI Base 가격 결과가 없습니다 (group={scenario_group_id}, indices={list(INDEX_ORDER)})."),
            )
        base_run_seq = _resolve_single_run_seq(
            base_run_seqs,
            context=f"MI Base case={mi_base_case_id}",
        )
        empty_scenarios = [sid for sid in target_ids if not scenario_series[sid]]
        if empty_scenarios:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"시나리오 가격 결과가 없습니다: {empty_scenarios}",
            )

        resolved_run_seqs = {
            sid: _resolve_single_run_seq(run_seqs, context=f"Scenario={sid}")
            for sid, run_seqs in scenario_run_seqs.items()
        }

        scenario_prices: dict[str, ScenarioPrices] = {
            BASE_SCENARIO_ID: ScenarioPrices(scenario_id=BASE_SCENARIO_ID, prices=base_series)
        }
        for sid in target_ids:
            scenario_prices[sid] = ScenarioPrices(scenario_id=sid, prices=scenario_series[sid])
        logger.info(
            "[interpret_price] pinned input snapshot | "
            f"mi_base_case_id={mi_base_case_id} | base_run_seq={base_run_seq} "
            f"| price_axis={_axis_summary(base_price_axis or [])} "
            f"| scenario_run_seqs={resolved_run_seqs}"
        )
        return scenario_prices, base_run_seq, resolved_run_seqs

    @staticmethod
    def _validate_price_base_alignment(
        *,
        scenario_id: str,
        index: str,
        mi_base_case_id: int,
        base_rows: list[dict[str, Any]],
        scenario_rows: list[dict[str, Any]],
    ) -> None:
        if not base_rows:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=(
                    "Scenario 가격 run의 Base를 검증할 pinned MI Base 가격이 없습니다. "
                    f"scenario_id={scenario_id}, index={index}, mi_base_case_id={mi_base_case_id}"
                ),
            )

        pinned_periods = _validate_monthly_rows(
            base_rows,
            context=f"MI Base case={mi_base_case_id}, index={index}",
        )
        scenario_periods = _validate_monthly_rows(
            scenario_rows,
            context=f"Scenario={scenario_id}, index={index}",
        )
        if scenario_periods != pinned_periods:
            pinned_set = set(pinned_periods)
            scenario_set = set(scenario_periods)
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=(
                    "Scenario와 pinned MI Base의 월 축이 일치하지 않습니다. "
                    f"scenario_id={scenario_id}, index={index}, "
                    f"base_axis={_axis_summary(pinned_periods)}, "
                    f"scenario_axis={_axis_summary(scenario_periods)}, "
                    f"missing={sorted(pinned_set - scenario_set)[:5]}, "
                    f"extra={sorted(scenario_set - pinned_set)[:5]}"
                ),
            )

        pinned_by_period = {row["period_key"]: float(row["value"]) for row in base_rows}
        mismatches: list[dict[str, float | str]] = []
        for row in scenario_rows:
            period = str(row["period_key"])
            scenario_base = float(row["base_value"])
            pinned_base = pinned_by_period[period]
            if not isclose(
                scenario_base,
                pinned_base,
                rel_tol=_PRICE_BASE_REL_TOLERANCE,
                abs_tol=_PRICE_BASE_ABS_TOLERANCE,
            ):
                mismatches.append(
                    {
                        "period": period,
                        "scenario_run_base": scenario_base,
                        "pinned_base": pinned_base,
                    }
                )

        if mismatches:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=(
                    "Scenario 가격 run이 proposal에 고정된 MI Base 가격과 일치하지 않습니다. "
                    f"scenario_id={scenario_id}, index={index}, mi_base_case_id={mi_base_case_id}, "
                    f"mismatches={mismatches[:5]}"
                ),
            )

    @staticmethod
    def _collect_feature_names(
        base_features: list[FeatureSeries],
        scenario_features: dict[str, ScenarioFeatures],
    ) -> list[str]:
        seen: list[str] = []
        for fs in base_features:
            if fs.feature not in seen:
                seen.append(fs.feature)
        for sf in scenario_features.values():
            for fs in sf.features:
                if fs.feature not in seen:
                    seen.append(fs.feature)
        return seen

    @staticmethod
    def _collect_price_months(
        scenario_prices: dict[str, ScenarioPrices],
    ) -> list[str]:
        # 플랫폼 가격 차트와 동일하게 수급모델 monthly 결과 축만 표시 기간으로 사용한다.
        months: set[str] = set()
        for sp in scenario_prices.values():
            for ps in sp.prices:
                months.update(ps.months)
        return sorted(months)


def _price_series(index: str, rows: list[dict]) -> PriceSeries:
    months = [row["period_key"] for row in rows]
    return PriceSeries(
        index=index,
        months=months,
        values=[row["value"] for row in rows],
    )


def _validate_base_price_rows(
    rows: list[dict[str, Any]],
    *,
    mi_base_case_id: int,
    index: str,
    expected_axis: list[str] | None,
) -> list[str]:
    current_axis = _validate_monthly_rows(
        rows,
        context=f"MI Base case={mi_base_case_id}, index={index}",
    )
    if expected_axis is not None and current_axis != expected_axis:
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=(
                "MI Base 가격 지수별 월 축이 서로 다릅니다. "
                f"mi_base_case_id={mi_base_case_id}, index={index}, "
                f"expected={_axis_summary(expected_axis)}, "
                f"actual={_axis_summary(current_axis)}"
            ),
        )
    case_ids = _metadata_ints(rows, "case_id")
    if case_ids != {mi_base_case_id}:
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=(
                "고정된 MI Base case와 조회 결과 case가 일치하지 않습니다. "
                f"expected={mi_base_case_id}, actual={sorted(case_ids)}"
            ),
        )
    return current_axis


def _metadata_ints(rows: list[dict[str, Any]], key: str) -> set[int]:
    values: set[int] = set()
    for row in rows:
        raw = row.get(key)
        if isinstance(raw, bool) or raw is None:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"가격 결과의 {key} 증적이 없습니다: row={row}",
            )
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"가격 결과의 {key}가 정수가 아닙니다: value={raw!r}",
            ) from exc
        if value <= 0:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"가격 결과의 {key}가 양수가 아닙니다: value={value}",
            )
        values.add(value)
    return values


def _run_sequences(rows: list[dict[str, Any]]) -> set[int]:
    return _metadata_ints(rows, "run_seq")


def _resolve_single_run_seq(run_seqs: set[int], *, context: str) -> int:
    if len(run_seqs) != 1:
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=(
                "하나의 가격 해석에 서로 다른 run을 섞을 수 없습니다. "
                f"context={context}, run_seqs={sorted(run_seqs)}"
            ),
        )
    return next(iter(run_seqs))


def _validate_monthly_rows(
    rows: list[dict[str, Any]],
    *,
    context: str,
) -> list[str]:
    periods = [str(row.get("period_key") or "") for row in rows]
    ordinals: list[int] = []
    for period in periods:
        match = _MONTH_KEY_RE.fullmatch(period)
        if match is None:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"수급모델 월 키가 YYYY-MM 형식이 아닙니다. context={context}, period={period!r}",
            )
        year, month = (int(part) for part in match.groups())
        if not 1 <= month <= 12:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"수급모델 월 키의 월 범위가 잘못됐습니다. context={context}, period={period}",
            )
        ordinals.append(year * 12 + month - 1)

    if len(periods) != len(set(periods)):
        duplicates = sorted({period for period in periods if periods.count(period) > 1})
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=f"수급모델 월 축에 중복이 있습니다. context={context}, duplicates={duplicates[:5]}",
        )
    if ordinals != sorted(ordinals):
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=f"수급모델 월 축이 오름차순이 아닙니다. context={context}, axis={_axis_summary(periods)}",
        )
    gaps = [
        f"{periods[index - 1]}->{periods[index]}"
        for index in range(1, len(periods))
        if ordinals[index] != ordinals[index - 1] + 1
    ]
    if gaps:
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=f"수급모델 월 축이 연속적이지 않습니다. context={context}, gaps={gaps[:5]}",
        )
    return periods


def _axis_summary(periods: list[str]) -> dict[str, str | int | None]:
    return {
        "start": periods[0] if periods else None,
        "end": periods[-1] if periods else None,
        "count": len(periods),
    }
