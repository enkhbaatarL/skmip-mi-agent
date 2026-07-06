"""제안 파라미터(입력 feature) 및 예측 가격 로딩 서비스.

현재 데이터 출처:
- `temp_data/proposal_parameters_sample.json` : 시나리오별 입력 feature 시계열
  (현재 기온 1종, 국가 3개). feature 개수는 향후 확장될 수 있다.
- `temp_data/price_forecast_v2.json` : 시나리오별 예측 가격(JKM/TTF/HH) 시계열

`scenario_group_id`는 향후 DB 조회 키로 사용될 예정이며, 지금은 샘플 파일을
그대로 로드한다(파일 → DB 전환 시 이 서비스만 교체하면 된다).
"""

from __future__ import annotations

import json
from pathlib import Path

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
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode

_TEMP_DATA_DIR = Path(__file__).resolve().parents[1] / "temp_data"
_PROPOSAL_FILE = _TEMP_DATA_DIR / "proposal_parameters_sample_v2.json"
_PRICE_FILE = _TEMP_DATA_DIR / "price_forecast_v2.json"


def _norm_scenario_id(raw: object) -> str:
    return str(raw).strip()


def _ym_from_date(value: str) -> str:
    # "2023-10-01 00:00:00" → "2023-10"
    return str(value)[:7]


def _extract_geo(param: dict) -> tuple[str, str | None]:
    """geo 라벨을 country → region → continent 우선순위로 첫 유효값을 추출한다.

    코드가 지수를 결정하지 않으므로 라벨 문자열 자체만 안정적으로 실으면 된다.
    base/scenario에서 동일 규칙을 적용하므로 매칭 키(feature, region, qualifier)가
    양쪽에서 동일하게 채워진다. 반환: (라벨 문자열, geo_level). 셋 다 없으면 ("", None).
    """
    for level in ("country", "region", "continent"):
        value = param.get(level)
        if value:
            return str(value), level
    return "", None


def _period_key(point: dict, granularity: str) -> str:
    """월/연 granularity에 맞춰 기간 키를 표준화한다(monthly=YYYY-MM, annual=YYYY)."""
    if "ym" in point:
        return str(point["ym"])
    if "year" in point:
        return str(point["year"])
    # 방어적 폴백
    return str(point.get("date", ""))[: (7 if granularity == "monthly" else 4)]


def _load_json(path: Path) -> object:
    if not path.exists():
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=f"입력 파일을 찾을 수 없습니다: {path.name}",
        )
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


class ProposalParameterService:
    """입력 feature/가격 데이터를 정규화된 `InterpretInput`으로 제공."""

    def __init__(
        self,
        proposal_path: Path = _PROPOSAL_FILE,
        price_path: Path = _PRICE_FILE,
    ) -> None:
        self._proposal_path = proposal_path
        self._price_path = price_path

    def load_interpret_input(
        self,
        scenario_group_id: int | None = None,
        scenario_ids: list[str] | None = None,
    ) -> InterpretInput:
        """정규화된 해석 입력을 로드한다.

        scenario_group_id는 향후 DB 조회 키(현재 미사용).
        scenario_ids가 주어지면 base를 제외한 대상 시나리오를 필터링한다.
        """
        proposal_raw = self._load_proposal()
        price_raw = self._load_price()

        all_ids = list(proposal_raw.keys())
        if BASE_SCENARIO_ID not in all_ids:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"기준 시나리오 '{BASE_SCENARIO_ID}'가 입력에 없습니다.",
            )

        target_ids = [sid for sid in all_ids if sid != BASE_SCENARIO_ID]
        if scenario_ids:
            wanted = {str(s) for s in scenario_ids}
            target_ids = [sid for sid in target_ids if sid in wanted]
            missing = wanted - set(all_ids)
            if missing:
                raise MIBaseError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    detail=f"입력에 없는 시나리오: {sorted(missing)}",
                )
        if not target_ids:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="해석 대상 시나리오가 없습니다.",
            )

        features = self._collect_feature_names(proposal_raw)
        months = self._collect_months(proposal_raw, price_raw)

        return InterpretInput(
            scenario_group_id=scenario_group_id,
            base_scenario_id=BASE_SCENARIO_ID,
            scenario_ids=target_ids,
            features=features,
            period_start=months[0] if months else None,
            period_end=months[-1] if months else None,
            scenario_features={
                sid: proposal_raw[sid]
                for sid in [BASE_SCENARIO_ID, *target_ids]
                if sid in proposal_raw
            },
            scenario_prices={
                sid: price_raw[sid]
                for sid in [BASE_SCENARIO_ID, *target_ids]
                if sid in price_raw
            },
        )

    # ---------------------------------------------------------------- #
    def _load_proposal(self) -> dict[str, ScenarioFeatures]:
        raw = _load_json(self._proposal_path)
        if not isinstance(raw, list):
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail="proposal_parameters 형식 오류(list 아님)",
            )
        result: dict[str, ScenarioFeatures] = {}
        for entry in raw:
            sid = _norm_scenario_id(entry.get("scenario_id"))
            series_list: list[FeatureSeries] = []
            for param in entry.get("proposal_parameters", []):
                # geo 라벨은 country → region → continent 우선순위로 첫 유효값을 쓴다.
                region, geo_level = _extract_geo(param)
                granularity = str(param.get("granularity", "monthly"))
                points = param.get("series", [])
                periods = [_period_key(pt, granularity) for pt in points]
                values = [float(pt["value"]) for pt in points]
                # feature 부가 구분(예: energy_source). parameter_name 외 식별 필드.
                qualifier = param.get("energy_source")
                # 지수는 더 이상 매핑으로 채우지 않는다. 상류가 명시한 경우만 존중.
                index = param.get("benchmark") or param.get("index") or None
                series_list.append(
                    FeatureSeries(
                        feature=str(param.get("parameter_name", "")),
                        region=region,
                        geo_level=geo_level,
                        index=str(index) if index else None,
                        unit=str(param.get("unit", "")),
                        granularity=granularity,
                        qualifier=str(qualifier) if qualifier else None,
                        periods=periods,
                        values=values,
                    )
                )
            result[sid] = ScenarioFeatures(scenario_id=sid, features=series_list)
        return result

    def _load_price(self) -> dict[str, ScenarioPrices]:
        raw = _load_json(self._price_path)
        if not isinstance(raw, list):
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail="price_forecast 형식 오류(list 아님)",
            )
        # (scenario_id, index) → {ym: value}
        grouped: dict[str, dict[str, dict[str, float]]] = {}
        for row in raw:
            sid = _norm_scenario_id(row.get("scenario_id"))
            index = str(row.get("benchmark", ""))
            ym = _ym_from_date(str(row.get("forecast_date", "")))
            grouped.setdefault(sid, {}).setdefault(index, {})[ym] = float(
                row.get("forecast_median", 0.0)
            )

        result: dict[str, ScenarioPrices] = {}
        for sid, by_index in grouped.items():
            series_list: list[PriceSeries] = []
            ordered = [ix for ix in INDEX_ORDER if ix in by_index]
            ordered += [ix for ix in by_index if ix not in INDEX_ORDER]
            for index in ordered:
                months = sorted(by_index[index].keys())
                series_list.append(
                    PriceSeries(
                        index=index,
                        months=months,
                        values=[by_index[index][m] for m in months],
                    )
                )
            result[sid] = ScenarioPrices(scenario_id=sid, prices=series_list)
        return result

    @staticmethod
    def _collect_feature_names(proposal: dict[str, ScenarioFeatures]) -> list[str]:
        seen: list[str] = []
        for sf in proposal.values():
            for fs in sf.features:
                if fs.feature not in seen:
                    seen.append(fs.feature)
        return seen

    @staticmethod
    def _collect_months(
        proposal: dict[str, ScenarioFeatures],
        price: dict[str, ScenarioPrices],
    ) -> list[str]:
        # 표시용 기간은 월 단위 시계열(월간 feature + 가격) 기준으로만 계산한다.
        months: set[str] = set()
        for sf in proposal.values():
            for fs in sf.features:
                if fs.granularity == "monthly":
                    months.update(fs.periods)
        for sp in price.values():
            for ps in sp.prices:
                months.update(ps.months)
        return sorted(months)
