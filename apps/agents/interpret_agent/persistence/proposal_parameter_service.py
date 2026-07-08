"""제안 파라미터(입력 feature) 및 예측 가격 로딩 서비스.

데이터 출처(라이브 DB):
- 입력 feature: `tmm_mi_model_param_proposal_m.proposal_parameters` JSON
  (`ModelInputRepository`, 기존 ORM). `values[*].basecaseValue`=MI Base 입력,
  `proposedValue`=시나리오 입력. 그룹화 축(Country/Region/DegreeDayType 등)은
  `modelTarget.slotAxesFieldNames` 로 가변 정의되며, Year/Month 는 시간 축으로 분리한다.
- 예측 가격 결과: 모델 실행 결과 테이블(`ModelResultRepository`, read-only raw SQL).
  MI Base=`base_case_prc`, 시나리오=`user_adj_prc`. 지수(JKM/TTF/HH) 각각을
  `INDEX_PRICE_REGION` 매핑으로 조회하며 항상 monthly 기준이다.

정규화 결과는 기존 해석 파이프라인이 그대로 소비하는 `InterpretInput` 이다
(시나리오 features=proposedValue, base features=모든 proposal basecaseValue 병합).
"""

from __future__ import annotations

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
from apps.common.values.error_codes import ErrorCode
from apps.persistence.model_input.repository import ModelInputRepository
from apps.persistence.model_result.repository import ModelResultRepository

# 시간 축(그룹 키에서 제외하고 기간 키 생성에 사용).
_TIME_AXES = ("Year", "Month")
# region 라벨로 승격할 geo 성격 축 힌트(소문자 부분일치).
_GEO_AXIS_HINTS = ("country", "region", "continent", "area", "zone", "nation")


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
    store.setdefault(key, {})[period] = float(value)


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
        scenario_ids: list[str] | None = None,
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
            wanted_ids = (
                [int(str(s).strip()) for s in scenario_ids] if scenario_ids else None
            )
            proposals = ModelInputRepository(session=session).fetch_proposals_by_group(
                scenario_group_id, wanted_ids
            )
            if not proposals:
                detail = (
                    f"그룹 {scenario_group_id}의 해석 대상 제안 파라미터가 없습니다."
                    + (f" (요청 시나리오: {sorted(set(wanted_ids))})" if wanted_ids else "")
                )
                raise MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=detail)

            scenario_features, base_features, target_ids = self._normalize_features(
                proposals
            )
            scenario_prices = self._load_prices(
                session, scenario_group_id, target_ids
            )

            features = self._collect_feature_names(base_features, scenario_features)
            months = self._collect_months(scenario_features, scenario_prices)

            return InterpretInput(
                scenario_group_id=scenario_group_id,
                base_scenario_id=BASE_SCENARIO_ID,
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
                    group_keys = {
                        axis: str(record.get(axis))
                        for axis in group_axes
                        if record.get(axis) is not None
                    }
                    key = (
                        feature,
                        granularity,
                        tuple(sorted(group_keys.items())),
                    )
                    _accumulate(base_store, key, period, record.get("basecaseValue"))
                    _accumulate(store, key, period, record.get("proposedValue"))

        base_features = _build_feature_series(base_store)
        scenario_features: dict[str, ScenarioFeatures] = {
            BASE_SCENARIO_ID: ScenarioFeatures(
                scenario_id=BASE_SCENARIO_ID, features=base_features
            )
        }
        for sid in target_ids:
            scenario_features[sid] = ScenarioFeatures(
                scenario_id=sid, features=_build_feature_series(scen_stores[sid])
            )
        return scenario_features, base_features, target_ids

    def _load_prices(
        self,
        session,
        scenario_group_id: int,
        target_ids: list[str],
    ) -> dict[str, ScenarioPrices]:
        repo = ModelResultRepository(session=session)
        base_series: list[PriceSeries] = []
        scenario_series: dict[str, list[PriceSeries]] = {sid: [] for sid in target_ids}

        for index in INDEX_ORDER:
            prc_rgn_nm = INDEX_PRICE_REGION[index]

            base_rows = repo.fetch_mi_base_prices(prc_rgn_nm)
            if base_rows:
                base_series.append(_price_series(index, base_rows))

            scenario_rows = repo.fetch_scenario_prices(scenario_group_id, prc_rgn_nm)
            for sid in target_ids:
                rows = scenario_rows.get(int(sid)) or []
                if rows:
                    scenario_series[sid].append(_price_series(index, rows))

        # 가격 결과가 전혀 없으면(빈 결과) 에러로 처리한다.
        if not base_series:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=(
                    f"MI Base 가격 결과가 없습니다 "
                    f"(group={scenario_group_id}, indices={list(INDEX_ORDER)})."
                ),
            )
        empty_scenarios = [sid for sid in target_ids if not scenario_series[sid]]
        if empty_scenarios:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"시나리오 가격 결과가 없습니다: {empty_scenarios}",
            )

        scenario_prices: dict[str, ScenarioPrices] = {
            BASE_SCENARIO_ID: ScenarioPrices(
                scenario_id=BASE_SCENARIO_ID, prices=base_series
            )
        }
        for sid in target_ids:
            scenario_prices[sid] = ScenarioPrices(
                scenario_id=sid, prices=scenario_series[sid]
            )
        return scenario_prices

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
    def _collect_months(
        scenario_features: dict[str, ScenarioFeatures],
        scenario_prices: dict[str, ScenarioPrices],
    ) -> list[str]:
        # 표시용 기간은 월 단위 시계열(월간 feature + 가격) 기준.
        months: set[str] = set()
        for sf in scenario_features.values():
            for fs in sf.features:
                if fs.granularity == "monthly":
                    months.update(fs.periods)
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
