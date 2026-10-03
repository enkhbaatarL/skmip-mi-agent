from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    _lever_support_issues,
    _lever_support_status,
)
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload
from apps.persistence.model_impact_lever.service import _hydrate_catalog
from scripts.model_parameter.apply_model_impact_lever_v4_1 import (
    _expected_target_identity_rows,
    _target_identity_matches,
)
from scripts.model_parameter.prepare_model_impact_lever_v4_1 import CONDITIONAL_HINTS


ROOT_DIR = Path(__file__).resolve().parents[2]
CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v4.1-0036.json"
SNAPSHOT_PATH = ROOT_DIR / "scripts/model_parameter/snapshots/external_dev_before_model_impact_lever_v4_1_20261003.json"
EXPECTED_V4_0_CHECKSUM = "416017351f2b9539370963a3ca413914876da55a1db3f41e3dacd34bd466c763"
EXPECTED_V4_1_CHECKSUM = "7f4ef0b7aa60efb550b9175654fd82350f0c293debf880a9180e7e935db54d69"
EXPECTED_CONDITIONAL_BINDINGS = {
    "route_disruption": {"ShippingCost", "ShippingFuelCost", "CanalToll"},
    "trade_restriction": {
        "SupplyDisruption",
        "RegionalProductionAdjustment",
        "LiqUtilAdjustment",
        "LiqProdAdjustment",
        "PipelineAdjustment",
        "RegasAdjustment",
        "PNG Contract Volume",
    },
    "inventory_condition": {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "SupplyDisruption",
        "RegionalProductionAdjustment",
        "LiqUtilAdjustment",
        "LiqProdAdjustment",
        "PipelineAdjustment",
        "RegasAdjustment",
        "PNG Contract Volume",
    },
    "regional_price_spread": {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "SupplyDisruption",
        "RegionalProductionAdjustment",
        "LiqUtilAdjustment",
        "LiqProdAdjustment",
        "PipelineAdjustment",
        "RegasAdjustment",
        "PNG Contract Volume",
        "ShippingCost",
        "ShippingFuelCost",
        "CanalToll",
    },
    "financial_market_sentiment": {"GDP", "PMI"},
}


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _repository(
    rows: list[dict[str, object]],
    master: list[dict[str, object]],
) -> SimpleNamespace:
    ordered = sorted(rows, key=lambda row: (str(row["domain"]), str(row["lever_code"])))
    definitions = [
        {
            "canonical_parameter_name": row["parameter_name"],
            "use_yn": row["use_yn"],
        }
        for row in master
        if row.get("del_yn") == "N"
    ]
    return SimpleNamespace(
        fetch_active_impact_levers=lambda *, catalog_version: [
            {
                **row,
                "impact_lever_id": int(
                    row.get("impact_lever_id") or row.get("source_impact_lever_id") or 0,
                ),
            }
            for row in ordered
            if row["catalog_version"] == catalog_version
        ],
        fetch_parameter_definitions_by_names=lambda _names: definitions,
    )


def test_v4_1_preserves_full_set_and_expands_only_approved_conditional_bindings() -> None:
    canonical = _load(CANONICAL_PATH)
    snapshot = _load(SNAPSHOT_PATH)
    target_rows = canonical["impact_levers"]
    snapshot_rows = snapshot["impact_levers"]
    assert isinstance(target_rows, list)
    assert isinstance(snapshot_rows, list)
    source_rows = [
        row
        for row in snapshot_rows
        if row["catalog_version"] == "v4.0" and row["use_yn"] == "Y" and row["del_yn"] == "N"
    ]
    source_by_code = {row["lever_code"]: row for row in source_rows}
    target_by_code = {row["lever_code"]: row for row in target_rows}

    assert canonical["canonical_version"] == "model-impact-lever-canonical-v4.1-0036"
    assert canonical["catalog_version"] == "v4.1"
    assert canonical["audit_user"] == "model-impact-lever-v4.1-v0036"
    assert sorted(row["target_impact_lever_id"] for row in canonical["impact_levers"]) == list(range(56, 77))
    assert canonical["hydrated_catalog_checksum"] == EXPECTED_V4_1_CHECKSUM
    assert len(source_by_code) == len(target_by_code) == 21
    assert set(source_by_code) == set(target_by_code) == set(canonical["lever_full_set"])
    assert canonical["binding_occurrence_count"] == 56
    assert canonical["conditional_binding_occurrence_count"] == 37

    for lever_code, target in target_by_code.items():
        source = source_by_code[lever_code]
        assert {key: target[key] for key in ("lever_code", "domain", "label", "description", "parent_lever_code")} == {
            key: source[key] for key in ("lever_code", "domain", "label", "description", "parent_lever_code")
        }
        assert target["applicability_hint"] == CONDITIONAL_HINTS.get(
            lever_code,
            source["applicability_hint"],
        )
        conditional = {
            binding["parameter_name"]
            for binding in target["parameter_bindings"]
            if binding.get("selection_mode") == "conditional"
        }
        assert conditional == EXPECTED_CONDITIONAL_BINDINGS.get(lever_code, set())
        if target["domain"] == "price_only":
            assert target["parameter_bindings"]
            assert all(binding.get("selection_mode") == "conditional" for binding in target["parameter_bindings"])


def test_v4_0_checksum_remains_stable_and_v4_1_checksum_includes_conditional_mode() -> None:
    canonical = _load(CANONICAL_PATH)
    snapshot = _load(SNAPSHOT_PATH)
    master = snapshot["master"]
    snapshot_rows = snapshot["impact_levers"]
    target_rows = canonical["impact_levers"]
    assert isinstance(master, list)
    assert isinstance(snapshot_rows, list)
    assert isinstance(target_rows, list)

    v4_0_rows = [
        row
        for row in snapshot_rows
        if row["catalog_version"] == "v4.0" and row["use_yn"] == "Y" and row["del_yn"] == "N"
    ]
    _, v4_0_version, v4_0_checksum = _hydrate_catalog(
        _repository(v4_0_rows, master),
        catalog_version="v4.0",
    )
    v4_1_catalog, v4_1_version, v4_1_checksum = _hydrate_catalog(
        _repository(target_rows, master),
        catalog_version="v4.1",
    )

    assert v4_0_version == "v4.0"
    assert v4_0_checksum == EXPECTED_V4_0_CHECKSUM
    assert v4_1_version == "v4.1"
    assert v4_1_checksum == EXPECTED_V4_1_CHECKSUM
    assert len(v4_1_catalog) == 21
    assert all(
        binding.selection_mode == "conditional"
        for lever in v4_1_catalog
        if lever.domain == "price_only"
        for binding in lever.parameter_bindings
    )
    catalog_by_code = {lever.lever_code: lever for lever in v4_1_catalog}
    inventory = catalog_by_code["inventory_condition"]
    assert _lever_support_status(["inventory_condition"], catalog_by_code) == "partial"
    assert _lever_support_issues(inventory) == []


def test_price_only_payload_allows_only_fail_closed_conditional_bindings() -> None:
    payload = {
        "impact_lever_id": 1,
        "lever_code": "inventory_condition",
        "domain": "price_only",
        "label": "재고",
        "description": "재고 상태",
        "parameter_bindings": [
            {
                "parameter_name": "SupplyDisruption",
                "role": "alternative",
                "selection_mode": "conditional",
                "applicability": "명시된 공급 원인만",
                "support_status": "executable",
            },
        ],
        "catalog_version": "v4.1",
    }

    parsed = ModelImpactLeverPayload.model_validate(payload)
    assert parsed.parameter_bindings[0].selection_mode == "conditional"

    payload["parameter_bindings"][0]["selection_mode"] = "deterministic"
    with pytest.raises(
        ValueError,
        match="price_only lever bindings must use conditional",
    ):
        ModelImpactLeverPayload.model_validate(payload)


def test_v4_1_target_identity_uses_pinned_ids_and_non_personal_audit() -> None:
    canonical = _load(CANONICAL_PATH)
    canonical_rows = canonical["impact_levers"]
    assert isinstance(canonical_rows, list)

    actual_rows = _expected_target_identity_rows(canonical_rows)
    assert _target_identity_matches(actual_rows, canonical_rows)
    assert {row["impact_lever_id"] for row in actual_rows} == set(range(56, 77))
    assert {row["crt_usr_logn_id"] for row in actual_rows} == {"model-impact-lever-v4.1-v0036"}

    actual_rows[0]["impact_lever_id"] = 77
    assert not _target_identity_matches(actual_rows, canonical_rows)
