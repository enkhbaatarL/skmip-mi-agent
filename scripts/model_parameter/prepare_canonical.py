from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
import argparse
from datetime import UTC, date, datetime
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.common.configs.database.sync_database.connection import get_sync_session  # noqa: E402


CANONICAL_VERSION = "model-parameter-canonical-v1"
CAPTURE_DATE = date(2026, 8, 7)
OUTPUT_DIR = ROOT_DIR / "scripts" / "model_parameter"
SNAPSHOT_PATH = OUTPUT_DIR / "snapshots" / f"external_dev_before_{CAPTURE_DATE:%Y%m%d}.json"
CANONICAL_PATH = OUTPUT_DIR / f"{CANONICAL_VERSION}.json"

MASTER_COLUMNS = (
    "model_param_id",
    "use_yn",
    "parameter_name",
    "parameter_hint",
    "model_file",
    "model_sheet",
    "model_table",
    "semantic_axes",
    "basecase_read_mode",
    "basecase_header_row",
    "basecase_data_start_row",
    "basecase_column_roles",
    "basecase_row_filter",
    "basecase_year_row",
    "basecase_month_row",
    "basecase_period_row",
    "basecase_value_start_col",
    "basecase_value_end_col",
    "basecase_stop_rule",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)
MAPPING_COLUMNS = (
    "model_param_dimension_map_id",
    "use_yn",
    "event_type_l2_id",
    "dimension_key",
    "dimension_label",
    "mapping_method",
    "model_param_id",
    "comment",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)

ACTIVE_PARAMETER_IDS = frozenset({4, 6, 7, 8, 11, 12, 13, 14, 15, 17})
EXPECTED_PARAMETER_NAMES = {
    1: "CDD",
    2: "Coal Futures Price",
    3: "Gas Futures Price",
    4: "GDP",
    5: "HDD",
    6: "PMI",
    7: "PowerMix",
    8: "Temperature",
    9: "User-Adjusted Gas Demand",
    10: "ElectrificationRate",
    11: "Population",
    12: "HurricaneIntensity",
    13: "LiqProdAdjustment",
    14: "LiqUtilAdjustment",
    15: "PipelineAdjustment",
    16: "RegasAdjustment",
    17: "SupplyDisruption",
    18: "PNG Contract Volume",
    19: "RemainingUnrestrictedAmount",
    20: "ShippingCost",
    21: "VolumeCancelled",
}

MASTER_OVERRIDES: dict[int, dict[str, Any]] = {
    11: {
        "parameter_hint": (
            "국가·연도별 인구의 최종 입력값이다. value는 천 명 단위 절대값으로 입력한다. "
            "proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 인구 자체다. "
            "인구·이민·인구전망 변화가 event에 명시된 경우에만 사용하고, 일반 경기 변화에는 GDP·PMI를 우선한다."
        ),
        "semantic_axes": (
            "slot=J:Year(YYYY, 2026~2030), K:Country(국가명), "
            "value=M:Population (Thousands), 천 명 단위 인구 절대값"
        ),
    },
    12: {
        "parameter_hint": (
            "미국 Gulf of Mexico 허리케인의 월별 강도 최종 입력값이다. value는 0~4 정수이며 "
            "0은 허리케인 영향 없음, 1~4는 승인된 강도 단계다. event가 GoM 허리케인과 적용 Year/Month를 "
            "명시하고 영향 대상 액화 또는 upstream 시설과 연결되는 경우에만 1~4를 제안한다."
        ),
        "semantic_axes": (
            "slot=B:Year(YYYY, 2026~2030), C:Month(1~12); "
            "value=D:Hurricane intensity(0~4 정수, 0=no hurricane)"
        ),
    },
    13: {
        "parameter_hint": (
            "액화 Plant Train·월별 LNG 생산량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. "
            "LUT 기준값은 월 생산능력 x 이용률로 계산한다. proposedValue는 증감폭이 아니라 해당 "
            "Country/LNG Plant/LNG Plant Train/Year/Month의 최종 생산량이며, 대폭·영구 차질이나 신규 Train "
            "ramp-up처럼 생산량 직접 override가 필요한 경우에 사용한다."
        ),
        "semantic_axes": (
            "slot=Country, LNG Plant, LNG Plant Train, Year(YYYY), Month(1~12); "
            "metadata=Life Cycle Category, Nameplate Capacity (MTPA), Period; "
            "value=Production (Mt LNG/month), 월 생산능력 x 이용률"
        ),
    },
    15: {
        "parameter_hint": (
            "파이프라인·월별 송출능력의 최종 절대값이다. value는 Bcm/y 단위이며 0 이상이다. "
            "연간 LUT capacity를 동일 연도의 12개월 기준값으로 확장한다. proposedValue는 증감폭이 아니라 "
            "해당 Pipeline Name/From Country/To Country/Year/Month에 적용할 최종 송출능력이다."
        ),
        "semantic_axes": (
            "slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Pipeline Name, "
            "routing=From Country, To Country; value=H:User adjusted capacity (Bcm/y)"
        ),
    },
    17: {
        "parameter_hint": (
            "국가·연월별 upstream 가스 공급량의 최종 절대값이다. value는 Bcm 단위이며 0 이상이다. "
            "LUT 기준값은 BCProduction의 연간 Base case supply를 동일 Province/PNG-LNG의 원본 월별 "
            "Seasonality 계수와 곱한 뒤 Country/Year/Month로 합산한다. 계수를 재정규화하지 않는다. "
            "proposedValue는 차질량이 아니라 해당 월에 적용할 최종 공급량이다."
        ),
        "semantic_axes": (
            "slot=I:Year(YYYY, 2026~2030), J:Month(1~12), K:Country; "
            "value=M:Volumes (Bcm), Country별 월 공급량 절대값"
        ),
    },
}

RESTORED_MAPPING_OVERRIDES: dict[int, dict[str, Any]] = {
    2: {
        "mapping_method": "direct",
        "model_param_id": 17,
        "comment": (
            "생산시설 가동 변화가 upstream 공급량에 직접 연결되면 SupplyDisruption을 적용한다. "
            "utilization_change_amount는 영향 Country와 최종 월 공급량 조정폭의 근거로 사용하고, "
            "period/onset_pattern/recovery_pattern은 적용 Year/Month와 변화 경로에 반영한다."
        ),
    },
    5: {
        "mapping_method": "direct",
        "model_param_id": 17,
        "comment": (
            "대체 가스전 증산이나 다른 upstream 공급이 명시되면 대체 Country의 SupplyDisruption 최종 공급량을 "
            "상향 조정한다. alt_gas_supply_availability는 상쇄 가능한 물량과 월별 배분의 근거로 사용한다."
        ),
    },
    9: {
        "mapping_method": "direct",
        "model_param_id": 13,
        "comment": (
            "액화 Plant Train의 대폭·영구 생산 손실 또는 회복을 월 생산량 최종값으로 직접 반영한다. "
            "utilization_change_amount와 period/onset_pattern/recovery_pattern을 생산량의 크기와 월별 경로에 사용하며, "
            "단기·부분 차질은 LiqUtilAdjustment를 우선한다."
        ),
    },
    16: {
        "mapping_method": "direct",
        "model_param_id": 13,
        "comment": (
            "신규 액화 Train의 COD와 ramp-up 완료 가동률을 기준으로 월 생산량을 산정한다. "
            "target_utilization_at_ramp_up은 nameplate 월 생산능력에 곱하고 cod_timing/ramp_up_pattern은 적용 월에 "
            "반영한다. FID 무산이 명시되면 신규 생산량은 0으로 처리한다."
        ),
    },
    18: {
        "mapping_method": "direct",
        "model_param_id": 15,
        "comment": (
            "파이프라인 송출능력 변화가 명시되면 해당 Pipeline/From/To/Year/Month의 최종 Bcm/y capacity를 산정한다. "
            "utilization_change_amount는 capacity 조정폭에, period/onset/recovery/structural_change는 "
            "적용 월과 지속성에 반영한다."
        ),
    },
    23: {
        "mapping_method": "direct",
        "model_param_id": 15,
        "comment": (
            "타 파이프라인 노선으로 대체 공급이 가능한 경우 해당 대체 Pipeline의 최종 송출능력을 상향 조정한다. "
            "LNG 전환만 설명된 경우에는 PipelineAdjustment 대신 LiqUtilAdjustment 경로를 사용한다."
        ),
    },
    66: {
        "mapping_method": "routing",
        "model_param_id": 17,
        "comment": (
            "affected_facility_type이 생산·upstream 시설이고 자연재해가 Country별 가스 생산량을 직접 훼손하는 경우 "
            "SupplyDisruption을 선택한다. 액화·수입 시설 피해에는 해당 시설 파라미터를 우선한다."
        ),
    },
    68: {
        "mapping_method": "routing",
        "model_param_id": 13,
        "comment": (
            "affected_facility_type이 수출·액화 시설이고 자연재해가 Train 생산량의 대폭·영구 손실 또는 ramp-up 변경을 "
            "명시하는 경우 LiqProdAdjustment를 선택한다. 단기 가동률 차질은 LiqUtilAdjustment를 우선한다."
        ),
    },
    70: {
        "mapping_method": "routing",
        "model_param_id": 12,
        "comment": (
            "event가 미국 Gulf of Mexico 허리케인이고 강도 1~4와 영향 Year/Month를 식별할 수 있으며 승인된 GoM "
            "액화 또는 upstream 영향 시설과 연결되는 경우에만 HurricaneIntensity를 선택한다. "
            "일반 자연재해에는 선택하지 않는다."
        ),
    },
    96: {
        "mapping_method": "direct",
        "model_param_id": 13,
        "comment": (
            "지정학적 긴장·전쟁이 액화 Plant Train 생산량의 대폭·영구 감소를 유발하면 LiqProdAdjustment로 월별 최종 "
            "생산량을 직접 조정한다. 부분·단기 가동률 차질은 LiqUtilAdjustment를 우선한다."
        ),
    },
    97: {
        "mapping_method": "direct",
        "model_param_id": 17,
        "comment": (
            "지정학적 긴장·전쟁이 upstream 가스 생산을 훼손하면 supply_disruption_intensity와 period/pattern을 근거로 "
            "해당 Country/Year/Month의 최종 공급량을 조정한다."
        ),
    },
    106: {
        "mapping_method": "direct",
        "model_param_id": 13,
        "comment": (
            "경제 제재·무역 제한이 액화 Plant Train 생산량의 직접 감소를 유발하면 LiqProdAdjustment로 "
            "월별 최종 생산량을 "
            "조정한다. 부분·단기 가동률 차질은 LiqUtilAdjustment를 우선한다."
        ),
    },
    107: {
        "mapping_method": "direct",
        "model_param_id": 17,
        "comment": (
            "경제 제재·무역 제한이 upstream 가스 생산을 직접 제한하면 supply_disruption_intensity와 "
            "period/pattern을 근거로 "
            "해당 Country/Year/Month의 최종 공급량을 조정한다."
        ),
    },
}

POPULATION_MAPPING = {
    "model_param_dimension_map_id": None,
    "use_yn": "Y",
    "event_type_l2_id": 21,
    "dimension_key": "economic_intensity",
    "dimension_label": "강도",
    "mapping_method": "routing",
    "model_param_id": 11,
    "comment": (
        "event에 인구·이민·인구전망 변화가 명시되어 Country/Year별 인구 절대값이 직접 달라지는 경우에만 "
        "Population을 선택한다. 일반 경기 변화나 산업활동 변화에는 GDP·PMI를 우선하고 Population을 선택하지 않는다."
    ),
    "crt_usr_logn_id": CANONICAL_VERSION,
    "crt_dtm": None,
    "mod_usr_logn_id": CANONICAL_VERSION,
    "mod_dtm": None,
    "del_yn": "N",
}


def _json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    msg = f"unsupported JSON value: {type(value).__name__}"
    raise TypeError(msg)


def _fetch_rows(query: str) -> list[dict[str, Any]]:
    session = get_sync_session()
    try:
        return [dict(row) for row in session.execute(text(query)).mappings().all()]
    finally:
        session.close()


def _assert_master_identity(master_rows: list[dict[str, Any]]) -> None:
    actual = {int(row["model_param_id"]): str(row["parameter_name"]) for row in master_rows}
    if actual != EXPECTED_PARAMETER_NAMES:
        msg = f"unexpected model parameter identity matrix: {actual!r}"
        raise RuntimeError(msg)


def _canonical_master(master_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _assert_master_identity(master_rows)
    canonical: list[dict[str, Any]] = []
    for source in master_rows:
        row = dict(source)
        model_param_id = int(row["model_param_id"])
        row.update(MASTER_OVERRIDES.get(model_param_id, {}))
        row["use_yn"] = "Y" if model_param_id in ACTIVE_PARAMETER_IDS else "N"
        row["del_yn"] = "N"
        row["mod_usr_logn_id"] = CANONICAL_VERSION
        row["mod_dtm"] = None
        canonical.append(row)
    return canonical


def _canonical_mappings(mapping_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {
        int(row["model_param_dimension_map_id"]): dict(row)
        for row in mapping_rows
        if row.get("model_param_dimension_map_id") is not None
    }
    expected_ids = set(range(1, 129))
    if set(by_id) != expected_ids and set(by_id) != expected_ids | {
        int(row["model_param_dimension_map_id"])
        for row in mapping_rows
        if row.get("model_param_id") == 11
        and row.get("event_type_l2_id") == 21
        and row.get("dimension_key") == "economic_intensity"
    }:
        msg = f"unexpected mapping ids/count: count={len(mapping_rows)}"
        raise RuntimeError(msg)

    canonical: list[dict[str, Any]] = []
    for mapping_id in range(1, 129):
        row = dict(by_id[mapping_id])
        if mapping_id in RESTORED_MAPPING_OVERRIDES:
            row.update(RESTORED_MAPPING_OVERRIDES[mapping_id])
            row["use_yn"] = "Y"
            row["del_yn"] = "N"
            row["mod_usr_logn_id"] = CANONICAL_VERSION
            row["mod_dtm"] = None
        canonical.append(row)

    existing_population = next(
        (
            dict(row)
            for row in mapping_rows
            if row.get("model_param_id") == 11
            and row.get("event_type_l2_id") == 21
            and row.get("dimension_key") == "economic_intensity"
        ),
        None,
    )
    population = dict(POPULATION_MAPPING)
    if existing_population is not None:
        population["model_param_dimension_map_id"] = existing_population.get("model_param_dimension_map_id")
        population["crt_usr_logn_id"] = existing_population.get("crt_usr_logn_id")
        population["crt_dtm"] = existing_population.get("crt_dtm")
    canonical.append(population)
    return canonical


def _write_json(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, default=_json_default)
        output.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture the current DB state and build the canonical Model Parameter matrix",
    )
    parser.add_argument(
        "--replace-snapshot",
        action="store_true",
        help="Replace the dated snapshot. Do not use after applying the canonical DML.",
    )
    args = parser.parse_args()

    master_rows = _fetch_rows(
        f"SELECT {', '.join(MASTER_COLUMNS)} FROM tmm_mi_model_param_m ORDER BY model_param_id",  # noqa: S608
    )
    mapping_rows = _fetch_rows(
        f"SELECT {', '.join(f'`{column}`' if column == 'comment' else column for column in MAPPING_COLUMNS)} "  # noqa: S608
        "FROM tmm_mi_model_param_dimension_map ORDER BY model_param_dimension_map_id",
    )
    template_rows = _fetch_rows(
        "SELECT scenario_dimension_template_id,event_type_l2_id,template_json,del_yn "
        "FROM tmm_mi_scenario_dimension_template_m WHERE del_yn='N' ORDER BY event_type_l2_id",
    )
    captured_at = datetime.now(UTC).isoformat()
    snapshot = {
        "snapshot_version": 1,
        "captured_at_utc": captured_at,
        "source": "configured metadata database (credentials and host intentionally omitted)",
        "master_count": len(master_rows),
        "mapping_count": len(mapping_rows),
        "master": master_rows,
        "dimension_mappings": mapping_rows,
        "scenario_dimension_templates": template_rows,
    }
    _write_json(
        SNAPSHOT_PATH,
        snapshot,
        exclusive=not args.replace_snapshot,
    )

    canonical_master = _canonical_master(master_rows)
    canonical_mappings = _canonical_mappings(mapping_rows)
    canonical = {
        "canonical_version": CANONICAL_VERSION,
        "generated_from_snapshot": str(SNAPSHOT_PATH.relative_to(ROOT_DIR)),
        "audit_user": CANONICAL_VERSION,
        "active_parameter_names": [
            EXPECTED_PARAMETER_NAMES[model_param_id]
            for model_param_id in sorted(ACTIVE_PARAMETER_IDS)
        ],
        "master_count": len(canonical_master),
        "mapping_count": len(canonical_mappings),
        "master": canonical_master,
        "dimension_mappings": canonical_mappings,
    }
    _write_json(CANONICAL_PATH, canonical, exclusive=False)
    sys.stdout.write(
        f"SNAPSHOT {SNAPSHOT_PATH}\n"
        f"CANONICAL {CANONICAL_PATH}\n"
        f"MASTER_COUNT {len(canonical_master)}\n"
        f"MAPPING_COUNT {len(canonical_mappings)}\n",
    )


if __name__ == "__main__":
    main()
