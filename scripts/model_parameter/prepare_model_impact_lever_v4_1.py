from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload  # noqa: E402
from apps.persistence.model_impact_lever.service import resolve_binding_support  # noqa: E402


SOURCE_CATALOG_VERSION = "v4.0"
TARGET_CATALOG_VERSION = "v4.1"
CANONICAL_VERSION = "model-impact-lever-canonical-v4.1-0036"
AUDIT_USER = "model-impact-lever-v4.1-v0036"
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_impact_lever_v4_1_20261003.json"
CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.1-0036.json"


CONDITIONAL_BINDING_APPLICABILITY: dict[str, str] = {
    "GDP": (
        "조건부: 상태·가격 자체가 아니라 원인 경로에 Country·Year별 실질 GDP 성장률과 적용 기간이 "
        "명시되어 economic_activity input으로 직접 연결되는 경우"
    ),
    "PMI": (
        "조건부: 상태·가격 자체가 아니라 원인 경로에 Country·Year·Month별 제조업 PMI와 적용 기간이 "
        "명시되어 economic_activity input으로 직접 연결되는 경우"
    ),
    "PowerMix": (
        "조건부: 재고·가격 상태의 원인으로 Country·Year와 영향·상쇄 에너지원의 발전 비중 경로가 "
        "명시되어 전체 합계 1 vector를 구성할 수 있는 경우"
    ),
    "Temperature": (
        "조건부: 재고·가격 상태의 원인으로 Country·Year·Month별 기온 경로가 명시된 경우; "
        "수요 방향을 기온 방향으로 대체 추론하지 않음"
    ),
    "SupplyDisruption": (
        "조건부: 상태·가격·거래 제한의 원인 또는 직접 영향으로 Country·Year·Month별 upstream 최종 "
        "공급량(Mt) 경로가 명시된 경우"
    ),
    "RegionalProductionAdjustment": (
        "조건부: 상태·가격·거래 제한의 원인 또는 직접 영향으로 Province/Basin/Country·Year별 upstream "
        "생산량(Bcm) 경로가 명시된 경우"
    ),
    "LiqUtilAdjustment": (
        "조건부: 상태·가격·거래 제한의 원인 또는 직접 영향으로 실제 Basecase LNG Plant·Train·Year·Month와 "
        "가동률 변화가 명시된 경우"
    ),
    "LiqProdAdjustment": (
        "조건부: 상태·가격·거래 제한의 원인 또는 직접 영향으로 실제 Basecase LNG Plant·Train·Year·Month와 "
        "생산량 변화가 명시된 경우"
    ),
    "PipelineAdjustment": (
        "조건부: 상태·가격·거래 제한의 원인 또는 직접 영향으로 실제 Pipeline·From/To Country·Year·Month와 "
        "최종 송출용량(Mt/y) 경로가 명시된 경우"
    ),
    "RegasAdjustment": (
        "조건부: 상태·가격·거래 제한의 원인 또는 직접 영향으로 실제 Regasification Plant·Year·Month와 "
        "처리용량 경로가 명시된 경우"
    ),
    "PNG Contract Volume": (
        "조건부: 상태·가격·거래 제한의 원인 또는 직접 영향이 LNG가 아닌 PNG 장기계약이며 "
        "Year·From/To Country별 계약 물량 경로로 직접 연결되는 경우"
    ),
    "ShippingCost": ("조건부: 특정 항로 지연비가 아니라 Year별 전역 LNG 선박 charter rate($/day) 경로가 명시된 경우"),
    "ShippingFuelCost": (
        "조건부: LNG·가스 가격 자체가 아니라 Year별 LNG 선박 IFO380 연료가격($/tonne) 경로가 명시된 경우"
    ),
    "CanalToll": ("조건부: 봉쇄·우회·지연 자체가 아니라 Suez 또는 Panama·Year별 통항료($/crossing) 경로가 명시된 경우"),
}

DEMAND_CONTEXT = ("GDP", "PMI", "PowerMix", "Temperature")
SUPPLY_CONTEXT = (
    "SupplyDisruption",
    "RegionalProductionAdjustment",
    "LiqUtilAdjustment",
    "LiqProdAdjustment",
    "PipelineAdjustment",
    "RegasAdjustment",
)
TRADE_CONTEXT = ("PNG Contract Volume",)
TRANSPORT_CONTEXT = ("ShippingCost", "ShippingFuelCost", "CanalToll")

CONDITIONAL_BINDINGS_BY_LEVER: dict[str, tuple[str, ...]] = {
    "route_disruption": TRANSPORT_CONTEXT,
    "trade_restriction": (*SUPPLY_CONTEXT, *TRADE_CONTEXT),
    "inventory_condition": (*DEMAND_CONTEXT, *SUPPLY_CONTEXT, *TRADE_CONTEXT),
    "regional_price_spread": (
        *DEMAND_CONTEXT,
        *SUPPLY_CONTEXT,
        *TRADE_CONTEXT,
        *TRANSPORT_CONTEXT,
    ),
    "financial_market_sentiment": ("GDP", "PMI"),
}

TARGET_ID_BY_CODE: dict[str, int] = {
    "direct_gas_demand": 56,
    "economic_activity": 57,
    "population_demographics": 58,
    "power_generation_mix": 59,
    "weather_demand": 60,
    "financial_market_sentiment": 61,
    "inventory_condition": 62,
    "regional_price_spread": 63,
    "liquefaction_production_override": 64,
    "liquefaction_utilization": 65,
    "pipeline_capacity": 66,
    "regasification_capacity": 67,
    "regional_upstream_production": 68,
    "upstream_production": 69,
    "us_gom_hurricane_disruption": 70,
    "canal_toll": 71,
    "lng_charter_rate": 72,
    "lng_vessel_fuel_cost": 73,
    "png_contract_volume": 74,
    "route_disruption": 75,
    "trade_restriction": 76,
}


CONDITIONAL_HINTS = {
    "route_disruption": (
        "물리적 transit 차질과 회복을 기록한다. v4.1에서는 동일 근거에 전역 LNG charter rate, IFO380 "
        "연료가격 또는 Suez/Panama 통항료의 해당 모델 축이 직접 있으면 조건부 binding을 검토한다."
    ),
    "trade_restriction": (
        "LNG·PNG, 적용 연월, From/To와 대상 asset·scope를 확인한다. 제한의 직접 결과가 기존 공급·시설·PNG "
        "계약 model input 축으로 특정될 때만 조건부 binding을 검토하고 제한량을 다른 입력으로 대체하지 않는다."
    ),
    "inventory_condition": (
        "재고량 자체의 writable input은 없다. 재고 변화의 명시된 원인이 기온·발전믹스·경기 또는 upstream·액화·"
        "pipeline·재기화·PNG 계약의 실제 모델 축으로 연결될 때만 해당 조건부 binding을 검토한다."
    ),
    "regional_price_spread": (
        "가격 spread 자체의 writable input은 없다. spread의 명시된 원인이 수요·공급·운송의 실제 모델 축으로 "
        "연결될 때만 조건부 binding을 검토하고 가격 방향을 수급 입력 방향으로 대체하지 않는다."
    ),
    "financial_market_sentiment": (
        "환율·금리·위험 프리미엄 자체의 writable input은 없다. Country·Year GDP 또는 Country·Year·Month PMI "
        "경로가 직접 제시된 경우에만 조건부 binding을 검토한다."
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        message = f"JSON root must be an object: {path}"
        raise TypeError(message)
    return document


def _conditional_binding(parameter_name: str) -> dict[str, str]:
    return {
        "parameter_name": parameter_name,
        "role": "alternative",
        "selection_mode": "conditional",
        "applicability": CONDITIONAL_BINDING_APPLICABILITY[parameter_name],
        "support_status": "executable",
    }


def _hydrated_checksum(
    rows: list[dict[str, Any]],
    *,
    master_use_by_name: Mapping[str, str],
) -> str:
    payload: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (str(item["domain"]), str(item["lever_code"]))):
        hydrated_bindings: list[dict[str, Any]] = []
        for binding in row["parameter_bindings"]:
            parameter_name = str(binding["parameter_name"])
            support_status, unsupported_reason = resolve_binding_support(
                requested_status=str(binding["support_status"]),
                master_use_yn=master_use_by_name[parameter_name],
                requested_reason_code=binding.get("unsupported_reason_code"),
            )
            hydrated_binding: dict[str, Any] = {
                "parameter_name": parameter_name,
                "role": binding.get("role") or "primary",
                "selection_mode": binding.get("selection_mode") or "deterministic",
                "applicability": binding.get("applicability") or "",
                "support_status": support_status,
                "unsupported_reason_code": unsupported_reason,
            }
            if hydrated_binding["selection_mode"] == "deterministic":
                hydrated_binding.pop("selection_mode")
            hydrated_bindings.append(hydrated_binding)
        lever = ModelImpactLeverPayload.model_validate(
            {
                **row,
                "impact_lever_id": int(row["source_impact_lever_id"]),
                "parameter_bindings": hydrated_bindings,
            },
        ).model_dump(mode="json", exclude={"impact_lever_id"})
        for binding in lever["parameter_bindings"]:
            if binding.get("selection_mode") == "deterministic":
                binding.pop("selection_mode", None)
        payload.append(lever)
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    ).hexdigest()


def build_canonical(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    master_rows = [row for row in snapshot["master"] if isinstance(row, dict)]
    master_use_by_name = {
        str(row["parameter_name"]): str(row["use_yn"]) for row in master_rows if row.get("del_yn") == "N"
    }
    source_rows = [
        row
        for row in snapshot["impact_levers"]
        if isinstance(row, dict)
        and row.get("catalog_version") == SOURCE_CATALOG_VERSION
        and row.get("use_yn") == "Y"
        and row.get("del_yn") == "N"
    ]
    if len(source_rows) != 21:
        message = f"expected 21 active {SOURCE_CATALOG_VERSION} levers, found {len(source_rows)}"
        raise RuntimeError(message)

    rows: list[dict[str, Any]] = []
    for source in source_rows:
        lever_code = str(source["lever_code"])
        bindings = [dict(binding) for binding in source.get("parameter_bindings") or []]
        for binding in bindings:
            binding.pop("selection_mode", None)
        bindings.extend(
            _conditional_binding(parameter_name) for parameter_name in CONDITIONAL_BINDINGS_BY_LEVER.get(lever_code, ())
        )
        row = {
            "source_impact_lever_id": int(source["impact_lever_id"]),
            "target_impact_lever_id": TARGET_ID_BY_CODE[lever_code],
            "lever_code": lever_code,
            "domain": source["domain"],
            "label": source["label"],
            "description": source["description"],
            "applicability_hint": CONDITIONAL_HINTS.get(
                lever_code,
                source.get("applicability_hint"),
            ),
            "parent_lever_code": source.get("parent_lever_code"),
            "parameter_bindings": bindings,
            "catalog_version": TARGET_CATALOG_VERSION,
            "use_yn": "Y",
            "del_yn": "N",
        }
        ModelImpactLeverPayload.model_validate(
            {**row, "impact_lever_id": row["source_impact_lever_id"]},
        )
        rows.append(row)

    source_codes = {str(row["lever_code"]) for row in source_rows}
    target_codes = {str(row["lever_code"]) for row in rows}
    if source_codes != target_codes:
        message = "v4.1 must preserve the exact v4.0 Lever Full Set"
        raise RuntimeError(message)

    binding_count = sum(len(row["parameter_bindings"]) for row in rows)
    conditional_binding_count = sum(
        binding.get("selection_mode") == "conditional" for row in rows for binding in row["parameter_bindings"]
    )
    return {
        "canonical_version": CANONICAL_VERSION,
        "catalog_version": TARGET_CATALOG_VERSION,
        "source_catalog_version": SOURCE_CATALOG_VERSION,
        "audit_user": AUDIT_USER,
        "generated_from_snapshot": str(SNAPSHOT_PATH.relative_to(ROOT_DIR)),
        "snapshot_sha256": hashlib.sha256(SNAPSHOT_PATH.read_bytes()).hexdigest(),
        "source_catalog_checksum": "416017351f2b9539370963a3ca413914876da55a1db3f41e3dacd34bd466c763",
        "hydrated_catalog_checksum": _hydrated_checksum(
            rows,
            master_use_by_name=master_use_by_name,
        ),
        "impact_lever_count": len(rows),
        "binding_occurrence_count": binding_count,
        "conditional_binding_occurrence_count": conditional_binding_count,
        "conditional_binding_lever_count": len(CONDITIONAL_BINDINGS_BY_LEVER),
        "lever_full_set": sorted(source_codes),
        "impact_levers": sorted(
            rows,
            key=lambda item: (str(item["domain"]), str(item["lever_code"])),
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        message = "prepare_model_impact_lever_v4_1.py does not accept arguments"
        raise ValueError(message)
    snapshot = _load_json(SNAPSHOT_PATH)
    canonical = build_canonical(snapshot)
    CANONICAL_PATH.write_text(
        json.dumps(canonical, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(  # noqa: T201
        json.dumps(
            {
                "path": str(CANONICAL_PATH),
                "lever_count": canonical["impact_lever_count"],
                "binding_count": canonical["binding_occurrence_count"],
                "conditional_binding_count": canonical["conditional_binding_occurrence_count"],
                "checksum": canonical["hydrated_catalog_checksum"],
            },
            ensure_ascii=False,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
