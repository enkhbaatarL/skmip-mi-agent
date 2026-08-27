from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.common.configs.database.sync_database.connection import get_sync_session  # noqa: E402


CANONICAL_VERSION = "model-impact-lever-canonical-v3"
CATALOG_VERSION = "v3"
CAPTURE_DATE = date(2026, 8, 7)
OUTPUT_DIR = ROOT_DIR / "scripts" / "model_parameter"
SNAPSHOT_PATH = OUTPUT_DIR / "snapshots" / f"external_dev_impact_lever_before_v3_{CAPTURE_DATE:%Y%m%d}.json"
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
IMPACT_LEVER_COLUMNS = (
    "impact_lever_id",
    "lever_code",
    "domain",
    "label",
    "description",
    "applicability_hint",
    "parent_lever_code",
    "parameter_bindings",
    "catalog_version",
    "use_yn",
    "crt_usr_logn_id",
    "crt_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
    "del_yn",
)

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
ACTIVE_PARAMETER_NAMES = {
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "Population",
    "HurricaneIntensity",
    "LiqProdAdjustment",
    "LiqUtilAdjustment",
    "PipelineAdjustment",
    "SupplyDisruption",
}
EXPECTED_LEVER_CODES = {
    "weather_demand",
    "power_generation_mix",
    "economic_activity",
    "direct_gas_demand",
    "upstream_production",
    "liquefaction_availability",
    "regasification_capacity",
    "natural_disaster_disruption",
    "pipeline_capacity",
    "shipping_cost",
    "route_disruption",
    "contract_volume",
    "trade_restriction",
    "inventory_condition",
    "regional_price_spread",
    "financial_market_sentiment",
}


def _binding(
    parameter_name: str,
    *,
    role: str,
    applicability: str,
) -> dict[str, str]:
    return {
        "parameter_name": parameter_name,
        "role": role,
        "applicability": applicability,
        "support_status": "executable",
    }


CANONICAL_BINDINGS = {
    "weather_demand": [
        _binding(
            "Temperature",
            role="primary",
            applicability="국가·연·월별 평균 기온(°C) 최종 절대값 조정",
        ),
        _binding(
            "HDD",
            role="alternative",
            applicability="국가·연·월별 난방도일 조정 경로",
        ),
        _binding(
            "CDD",
            role="alternative",
            applicability="국가·연·월별 냉방도일 조정 경로",
        ),
    ],
    "power_generation_mix": [
        _binding(
            "PowerMix",
            role="primary",
            applicability="국가·연·에너지원별 발전 비중 최종값 조정",
        ),
    ],
    "economic_activity": [
        _binding(
            "GDP",
            role="primary",
            applicability="국가·연도별 실질 GDP 성장률 최종값 조정",
        ),
        _binding(
            "PMI",
            role="alternative",
            applicability="국가·연·월별 산업 경기 PMI 절대지수 조정",
        ),
    ],
    "direct_gas_demand": [],
    "upstream_production": [
        _binding(
            "SupplyDisruption",
            role="primary",
            applicability="국가·연·월별 upstream 가스 공급량(Bcm) 최종값 조정",
        ),
    ],
    "liquefaction_availability": [
        _binding(
            "LiqUtilAdjustment",
            role="primary",
            applicability="기존 액화 Plant Train의 단기·부분 차질 또는 회복을 월별 가동률 최종값으로 조정",
        ),
        _binding(
            "LiqProdAdjustment",
            role="alternative",
            applicability="대폭·영구 생산 손실 또는 신규 Train ramp-up을 월별 생산량 최종값으로 직접 조정",
        ),
    ],
    "regasification_capacity": [
        _binding(
            "RegasAdjustment",
            role="primary",
            applicability="재기화 플랜트·연·월별 처리용량 최종값 조정 경로",
        ),
    ],
    "natural_disaster_disruption": [
        _binding(
            "HurricaneIntensity",
            role="primary",
            applicability=(
                "미국 Gulf of Mexico 허리케인의 강도 1~4와 적용 Year/Month를, "
                "승인된 액화 또는 upstream 영향 시설에 한해 조정"
            ),
        ),
    ],
    "pipeline_capacity": [
        _binding(
            "PipelineAdjustment",
            role="primary",
            applicability=(
                "Pipeline·From/To·연·월별 송출용량(Bcm/y) 최종값 또는 타 파이프라인 대체를 조정; "
                "LNG 전환만인 경우 액화시설 가용성 경로를 사용"
            ),
        ),
    ],
    "shipping_cost": [
        _binding(
            "ShippingCost",
            role="primary",
            applicability="영향 범위·연도별 해상 운송비 절대값 조정 경로",
        ),
    ],
    "route_disruption": [
        _binding(
            "ShippingCost",
            role="primary",
            applicability="항로 우회·지연에 따른 영향 범위·연도별 운송비 효과 조정 경로",
        ),
    ],
    "contract_volume": [],
    "trade_restriction": [],
    "inventory_condition": [],
    "regional_price_spread": [],
    "financial_market_sentiment": [],
}

LEVER_OVERRIDES = {
    "natural_disaster_disruption": {
        "label": "미국 GoM 허리케인 차질",
        "description": (
            "미국 Gulf of Mexico 허리케인이 승인된 액화 또는 upstream 시설에 일으키는 월별 물리적 공급 차질"
        ),
        "applicability_hint": (
            "미국 Gulf of Mexico 허리케인으로 강도 1~4, 적용 Year/Month, 승인된 영향 시설을 "
            "식별할 수 있을 때만 사용한다. 태풍·지진 등 기타 자연재해는 영향 시설에 따라 "
            "upstream 생산, 액화시설, 재기화 또는 파이프라인 레버를 사용한다."
        ),
    },
    "pipeline_capacity": {
        "description": ("PNG 파이프라인 송출 가동률·수송용량의 단발적·구조적 변화와 타 파이프라인 노선 대체"),
        "applicability_hint": (
            "기간, 대상 Pipeline과 From/To, 송출용량 대비 변화 폭, 단발·구조적 여부, "
            "발생·회복 패턴 또는 타 파이프라인 대체를 분기할 때 사용한다. "
            "LNG 전환만 설명된 경우 액화시설 가용성 레버를 사용한다."
        ),
    },
}

REVIEW_DECISIONS = {
    "CDD": (
        "catalog_capability",
        ["weather_demand"],
        "master는 비활성이지만 weather catalog capability를 보존하며 런타임에서 INACTIVE로 강등한다.",
    ),
    "Coal Futures Price": (
        "unbound",
        [],
        "2026년 이후 futures strip과 활성 mapping이 없어 binding하지 않는다.",
    ),
    "Gas Futures Price": (
        "unbound",
        [],
        "2026년 이후 futures strip과 활성 mapping이 없어 binding하지 않는다.",
    ),
    "GDP": ("executable", ["economic_activity"], "활성 master와 승인된 경제 강도 direct mapping이 있다."),
    "HDD": (
        "catalog_capability",
        ["weather_demand"],
        "master는 비활성이지만 weather catalog capability를 보존하며 런타임에서 INACTIVE로 강등한다.",
    ),
    "PMI": ("executable", ["economic_activity"], "활성 master와 승인된 경제 강도 direct mapping이 있다."),
    "PowerMix": (
        "executable",
        ["power_generation_mix"],
        "활성 master와 발전 믹스 direct/routing mapping 및 LUT가 있다.",
    ),
    "Temperature": (
        "executable",
        ["weather_demand"],
        "활성 master와 한파·폭염 direct mapping 및 LUT가 있다.",
    ),
    "User-Adjusted Gas Demand": (
        "unbound",
        [],
        "비활성 master이며 승인된 활성 mapping과 LUT가 없다.",
    ),
    "ElectrificationRate": (
        "unbound",
        [],
        "유효 Basecase·LUT·승인 mapping이 없어 binding하지 않는다.",
    ),
    "Population": (
        "unbound",
        [],
        "행 추가 금지 범위에서 안전한 전용 인구 레버가 없고 economic_activity에 넣으면 일반 경기에도 항상 후보화된다.",
    ),
    "HurricaneIntensity": (
        "executable",
        ["natural_disaster_disruption"],
        "활성 master이며 미국 GoM 허리케인 조건부 routing과 승인 LUT가 있다.",
    ),
    "LiqProdAdjustment": (
        "executable",
        ["liquefaction_availability"],
        "활성 master이며 대폭·영구 생산량 또는 ramp-up 조정 mapping과 LUT가 있다.",
    ),
    "LiqUtilAdjustment": (
        "executable",
        ["liquefaction_availability"],
        "활성 master이며 단기·부분 가동률 조정 mapping과 LUT가 있다.",
    ),
    "PipelineAdjustment": (
        "executable",
        ["pipeline_capacity"],
        "활성 master와 pipeline capacity direct mapping 및 LUT가 있어 v3에 추가한다.",
    ),
    "RegasAdjustment": (
        "catalog_capability",
        ["regasification_capacity"],
        "master는 비활성이지만 regas catalog capability를 보존하며 런타임에서 INACTIVE로 강등한다.",
    ),
    "SupplyDisruption": (
        "executable",
        ["upstream_production"],
        "활성 master이며 국가·연·월 upstream 공급량 mapping과 LUT가 있다.",
    ),
    "PNG Contract Volume": (
        "unbound",
        [],
        "비활성 Trade master이며 승인된 활성 mapping과 LUT가 없다.",
    ),
    "RemainingUnrestrictedAmount": (
        "unbound",
        [],
        "비활성 Trade master이며 승인된 활성 mapping과 LUT가 없다.",
    ),
    "ShippingCost": (
        "catalog_capability",
        ["shipping_cost", "route_disruption"],
        "master는 비활성이지만 shipping catalog capability를 보존하며 런타임에서 INACTIVE로 강등한다.",
    ),
    "VolumeCancelled": (
        "unbound",
        [],
        "비활성 Trade master이며 승인된 활성 mapping과 LUT가 없다.",
    ),
}


def _json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    message = f"unsupported JSON value: {type(value).__name__}"
    raise TypeError(message)


def _decode_json_array(value: object, *, lever_code: str) -> list[dict[str, Any]]:
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, list) or not all(isinstance(item, dict) for item in decoded):
        message = f"invalid parameter_bindings: lever_code={lever_code}"
        raise RuntimeError(message)
    return [dict(item) for item in decoded]


def _fetch_rows(session: Any, query: str) -> list[dict[str, Any]]:  # noqa: ANN401
    return [dict(row) for row in session.execute(text(query)).mappings().all()]


def _validate_source(
    master_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    lever_rows: list[dict[str, Any]],
) -> None:
    identity = {int(row["model_param_id"]): str(row["parameter_name"]) for row in master_rows}
    if identity != EXPECTED_PARAMETER_NAMES:
        message = f"unexpected model parameter identity matrix: {identity!r}"
        raise RuntimeError(message)
    active_names = {
        str(row["parameter_name"]) for row in master_rows if row.get("use_yn") == "Y" and row.get("del_yn") == "N"
    }
    if active_names != ACTIVE_PARAMETER_NAMES:
        message = f"unexpected active parameter names: {sorted(active_names)}"
        raise RuntimeError(message)
    if len(mapping_rows) != 129:
        message = f"unexpected dimension mapping count: {len(mapping_rows)}"
        raise RuntimeError(message)
    lever_codes = {str(row["lever_code"]) for row in lever_rows}
    if len(lever_rows) != 16 or lever_codes != EXPECTED_LEVER_CODES:
        message = f"unexpected impact lever identity matrix: count={len(lever_rows)}, codes={sorted(lever_codes)}"
        raise RuntimeError(message)
    if any(
        row.get("catalog_version") != "v2" or row.get("use_yn") != "Y" or row.get("del_yn") != "N" for row in lever_rows
    ):
        message = "impact lever source must be the active, non-deleted v2 catalog"
        raise RuntimeError(message)


def _canonical_levers(lever_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for source in lever_rows:
        row = dict(source)
        lever_code = str(row["lever_code"])
        _decode_json_array(row.get("parameter_bindings"), lever_code=lever_code)
        row.update(LEVER_OVERRIDES.get(lever_code, {}))
        row["parameter_bindings"] = CANONICAL_BINDINGS[lever_code]
        row["catalog_version"] = CATALOG_VERSION
        row["use_yn"] = "Y"
        row["mod_usr_logn_id"] = CANONICAL_VERSION
        row["mod_dtm"] = None
        row["del_yn"] = "N"
        canonical.append(row)
    return canonical


def _parameter_review(master_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    review: list[dict[str, Any]] = []
    for row in master_rows:
        parameter_name = str(row["parameter_name"])
        binding_decision, lever_codes, reason = REVIEW_DECISIONS[parameter_name]
        review.append(
            {
                "model_param_id": int(row["model_param_id"]),
                "parameter_name": parameter_name,
                "use_yn": str(row["use_yn"]),
                "del_yn": str(row["del_yn"]),
                "binding_decision": binding_decision,
                "lever_codes": lever_codes,
                "reason": reason,
            },
        )
    return review


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, default=_json_default)
        output.write("\n")


def main() -> None:
    existing_paths = [path for path in (SNAPSHOT_PATH, CANONICAL_PATH) if path.exists()]
    if existing_paths:
        message = f"refusing to overwrite existing v3 evidence: {existing_paths}"
        raise FileExistsError(message)

    session = get_sync_session()
    try:
        session.execute(text("SET TRANSACTION READ ONLY"))
        master_rows = _fetch_rows(
            session,
            f"SELECT {', '.join(MASTER_COLUMNS)} "  # noqa: S608
            "FROM tmm_mi_model_param_m ORDER BY model_param_id",
        )
        mapping_columns = ", ".join(f"`{column}`" if column == "comment" else column for column in MAPPING_COLUMNS)
        mapping_rows = _fetch_rows(
            session,
            f"SELECT {mapping_columns} FROM tmm_mi_model_param_dimension_map "  # noqa: S608
            "ORDER BY model_param_dimension_map_id",
        )
        lever_rows = _fetch_rows(
            session,
            f"SELECT {', '.join(IMPACT_LEVER_COLUMNS)} "  # noqa: S608
            "FROM tmm_mi_model_impact_lever_m ORDER BY impact_lever_id",
        )
        session.rollback()
    finally:
        session.close()

    _validate_source(master_rows, mapping_rows, lever_rows)
    normalized_snapshot_levers: list[dict[str, Any]] = []
    for source in lever_rows:
        row = dict(source)
        row["parameter_bindings"] = _decode_json_array(
            row.get("parameter_bindings"),
            lever_code=str(row["lever_code"]),
        )
        normalized_snapshot_levers.append(row)

    captured_at = datetime.now(UTC).isoformat()
    snapshot = {
        "snapshot_version": 1,
        "captured_at_utc": captured_at,
        "source": "configured external development metadata database (credentials and host omitted)",
        "master_count": len(master_rows),
        "mapping_count": len(mapping_rows),
        "impact_lever_count": len(normalized_snapshot_levers),
        "master": master_rows,
        "dimension_mappings": mapping_rows,
        "impact_levers": normalized_snapshot_levers,
    }
    canonical_levers = _canonical_levers(normalized_snapshot_levers)
    _write_json_exclusive(SNAPSHOT_PATH, snapshot)
    snapshot_sha256 = hashlib.sha256(SNAPSHOT_PATH.read_bytes()).hexdigest()
    canonical = {
        "canonical_version": CANONICAL_VERSION,
        "catalog_version": CATALOG_VERSION,
        "audit_user": CANONICAL_VERSION,
        "generated_from_snapshot": str(SNAPSHOT_PATH.relative_to(ROOT_DIR)),
        "snapshot_sha256": snapshot_sha256,
        "impact_lever_count": len(canonical_levers),
        "expected_counts": {
            "impact_levers": 16,
            "binding_occurrences": 14,
            "raw_executable_binding_occurrences": 14,
            "effective_executable_binding_occurrences": 9,
            "effective_known_unsupported_binding_occurrences": 5,
        },
        "active_parameter_names": sorted(ACTIVE_PARAMETER_NAMES),
        "impact_levers": canonical_levers,
        "model_parameter_review": _parameter_review(master_rows),
    }
    _write_json_exclusive(CANONICAL_PATH, canonical)
    sys.stdout.write(
        f"SNAPSHOT {SNAPSHOT_PATH}\n"
        f"CANONICAL {CANONICAL_PATH}\n"
        f"MASTER_COUNT {len(master_rows)}\n"
        f"MAPPING_COUNT {len(mapping_rows)}\n"
        f"IMPACT_LEVER_COUNT {len(canonical_levers)}\n",
    )


if __name__ == "__main__":
    main()
