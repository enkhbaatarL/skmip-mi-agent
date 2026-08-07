from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
IMPACT_LEVER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-impact-lever-canonical-v3.json"
MODEL_PARAMETER_CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v1.json"

EXPECTED_CANONICAL_VERSION = "model-impact-lever-canonical-v3"
EXPECTED_CATALOG_VERSION = "v3"
EXPECTED_IMPACT_LEVER_IDS = frozenset(range(1, 17))
EXPECTED_LEVER_DOMAINS = {
    "weather_demand": "demand",
    "power_generation_mix": "demand",
    "economic_activity": "demand",
    "direct_gas_demand": "demand",
    "upstream_production": "supply",
    "liquefaction_availability": "supply",
    "regasification_capacity": "supply",
    "natural_disaster_disruption": "supply",
    "pipeline_capacity": "supply",
    "shipping_cost": "trade",
    "route_disruption": "trade",
    "contract_volume": "trade",
    "trade_restriction": "trade",
    "inventory_condition": "price_only",
    "regional_price_spread": "price_only",
    "financial_market_sentiment": "price_only",
}
EXPECTED_BINDING_ROLES_BY_LEVER = {
    "weather_demand": {
        "Temperature": "primary",
        "HDD": "alternative",
        "CDD": "alternative",
    },
    "power_generation_mix": {"PowerMix": "primary"},
    "economic_activity": {"GDP": "primary", "PMI": "alternative"},
    "direct_gas_demand": {},
    "upstream_production": {"SupplyDisruption": "primary"},
    "liquefaction_availability": {
        "LiqUtilAdjustment": "primary",
        "LiqProdAdjustment": "alternative",
    },
    "regasification_capacity": {"RegasAdjustment": "primary"},
    "natural_disaster_disruption": {"HurricaneIntensity": "primary"},
    "pipeline_capacity": {"PipelineAdjustment": "primary"},
    "shipping_cost": {"ShippingCost": "primary"},
    "route_disruption": {"ShippingCost": "primary"},
    "contract_volume": {},
    "trade_restriction": {},
    "inventory_condition": {},
    "regional_price_spread": {},
    "financial_market_sentiment": {},
}
EXPECTED_ACTIVE_PARAMETER_NAMES = frozenset(
    {
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
    },
)
EXPECTED_EFFECTIVE_EXECUTABLE_NAMES = EXPECTED_ACTIVE_PARAMETER_NAMES - {"Population"}
EXPECTED_CATALOG_CAPABILITY_NAMES = frozenset(
    {
        "CDD",
        "HDD",
        "RegasAdjustment",
        "ShippingCost",
    },
)
EXPECTED_COUNTS = {
    "impact_levers": 16,
    "raw_executable_binding_occurrences": 14,
    "effective_executable_binding_occurrences": 9,
    "effective_known_unsupported_binding_occurrences": 5,
    "binding_occurrences": 14,
}
EXPECTED_TOP_LEVEL_KEYS = {
    "canonical_version",
    "catalog_version",
    "audit_user",
    "generated_from_snapshot",
    "snapshot_sha256",
    "impact_lever_count",
    "expected_counts",
    "active_parameter_names",
    "impact_levers",
    "model_parameter_review",
}
EXPECTED_BINDING_KEYS = {
    "parameter_name",
    "role",
    "applicability",
    "support_status",
}
EXPECTED_REVIEW_KEYS = {
    "model_param_id",
    "parameter_name",
    "use_yn",
    "del_yn",
    "binding_decision",
    "lever_codes",
    "reason",
}


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), f"Expected a JSON object: {path}"
    return document


def _non_empty_string(value: object, *, field: str) -> str:
    assert isinstance(value, str), f"{field} must be a string"
    assert value.strip(), f"{field} must not be blank"
    return value


def test_impact_lever_canonical_v3_catalog_rows_are_complete_and_unique() -> None:
    canonical = _load_json(IMPACT_LEVER_CANONICAL_PATH)
    impact_levers = canonical["impact_levers"]

    assert set(canonical) == EXPECTED_TOP_LEVEL_KEYS
    assert canonical["canonical_version"] == EXPECTED_CANONICAL_VERSION
    assert canonical["catalog_version"] == EXPECTED_CATALOG_VERSION
    _non_empty_string(canonical["audit_user"], field="audit_user")
    generated_from_snapshot = _non_empty_string(
        canonical["generated_from_snapshot"],
        field="generated_from_snapshot",
    )
    assert (ROOT_DIR / generated_from_snapshot).is_file()
    assert (
        canonical["snapshot_sha256"]
        == hashlib.sha256(
            (ROOT_DIR / generated_from_snapshot).read_bytes(),
        ).hexdigest()
    )
    assert canonical["expected_counts"] == EXPECTED_COUNTS
    assert canonical["impact_lever_count"] == len(impact_levers) == EXPECTED_COUNTS["impact_levers"]
    assert isinstance(impact_levers, list)

    ids = [row["impact_lever_id"] for row in impact_levers]
    codes = [row["lever_code"] for row in impact_levers]
    assert all(isinstance(impact_lever_id, int) and not isinstance(impact_lever_id, bool) for impact_lever_id in ids)
    assert set(ids) == EXPECTED_IMPACT_LEVER_IDS
    assert len(ids) == len(set(ids))
    assert len(codes) == len(set(codes))
    assert set(codes) == set(EXPECTED_LEVER_DOMAINS)

    for row in impact_levers:
        lever_code = _non_empty_string(row["lever_code"], field="lever_code")
        assert row["domain"] in {"demand", "supply", "trade", "price_only"}
        assert row["domain"] == EXPECTED_LEVER_DOMAINS[lever_code]
        assert row["catalog_version"] == EXPECTED_CATALOG_VERSION
        assert row["use_yn"] in {"Y", "N"}
        assert row["del_yn"] in {"Y", "N"}
        assert row["use_yn"] == "Y"
        assert row["del_yn"] == "N"
        _non_empty_string(row["label"], field=f"{lever_code}.label")
        _non_empty_string(row["description"], field=f"{lever_code}.description")
        if row["applicability_hint"] is not None:
            _non_empty_string(row["applicability_hint"], field=f"{lever_code}.applicability_hint")

        parent_lever_code = row["parent_lever_code"]
        assert parent_lever_code is None or parent_lever_code in EXPECTED_LEVER_DOMAINS
        assert parent_lever_code != lever_code


def test_raw_bindings_preserve_catalog_capability_and_match_master_authority() -> None:
    canonical = _load_json(IMPACT_LEVER_CANONICAL_PATH)
    master_canonical = _load_json(MODEL_PARAMETER_CANONICAL_PATH)
    impact_levers = canonical["impact_levers"]
    master_rows = master_canonical["master"]
    master_by_name = {row["parameter_name"]: row for row in master_rows}

    assert len(master_by_name) == len(master_rows) == 21
    active_names = {name for name, row in master_by_name.items() if row["use_yn"] == "Y" and row["del_yn"] == "N"}
    assert active_names == EXPECTED_ACTIVE_PARAMETER_NAMES
    assert canonical["active_parameter_names"] == sorted(EXPECTED_ACTIVE_PARAMETER_NAMES)

    raw_binding_occurrences: list[tuple[str, dict[str, Any]]] = []
    for lever in impact_levers:
        lever_code = lever["lever_code"]
        bindings = lever["parameter_bindings"]
        assert isinstance(bindings, list)

        parameter_names: list[str] = []
        roles_by_name: dict[str, str] = {}
        for binding in bindings:
            assert isinstance(binding, dict)
            assert set(binding) == EXPECTED_BINDING_KEYS
            parameter_name = _non_empty_string(
                binding["parameter_name"],
                field=f"{lever_code}.parameter_name",
            )
            assert parameter_name in master_by_name, f"Unknown model parameter binding: {parameter_name}"
            assert binding["role"] in {"primary", "alternative"}
            _non_empty_string(
                binding["applicability"],
                field=f"{lever_code}.{parameter_name}.applicability",
            )
            assert binding["support_status"] == "executable"
            assert "unsupported_reason_code" not in binding

            parameter_names.append(parameter_name)
            roles_by_name[parameter_name] = binding["role"]
            raw_binding_occurrences.append((lever_code, binding))

        assert len(parameter_names) == len(set(parameter_names)), f"Duplicate binding in lever: {lever_code}"
        assert roles_by_name == EXPECTED_BINDING_ROLES_BY_LEVER[lever_code]
        if lever["domain"] == "price_only":
            assert bindings == []

    raw_names = [binding["parameter_name"] for _, binding in raw_binding_occurrences]
    effective_statuses = [
        "executable" if master_by_name[name]["use_yn"] == "Y" else "known_unsupported" for name in raw_names
    ]

    assert len(raw_binding_occurrences) == EXPECTED_COUNTS["raw_executable_binding_occurrences"]
    assert len(raw_binding_occurrences) == EXPECTED_COUNTS["binding_occurrences"]
    assert Counter(effective_statuses) == {
        "executable": EXPECTED_COUNTS["effective_executable_binding_occurrences"],
        "known_unsupported": EXPECTED_COUNTS["effective_known_unsupported_binding_occurrences"],
    }
    assert {name for name in raw_names if master_by_name[name]["use_yn"] == "Y"} == (
        EXPECTED_EFFECTIVE_EXECUTABLE_NAMES
    )
    assert {name for name in raw_names if master_by_name[name]["use_yn"] == "N"} == (EXPECTED_CATALOG_CAPABILITY_NAMES)
    assert "Population" not in raw_names
    assert Counter(raw_names)["ShippingCost"] == 2


def test_model_parameter_review_exactly_covers_master_and_binding_decisions() -> None:
    canonical = _load_json(IMPACT_LEVER_CANONICAL_PATH)
    master_canonical = _load_json(MODEL_PARAMETER_CANONICAL_PATH)
    review_rows = canonical["model_parameter_review"]
    master_rows = master_canonical["master"]
    master_by_name = {row["parameter_name"]: row for row in master_rows}

    lever_codes_by_parameter: defaultdict[str, set[str]] = defaultdict(set)
    for lever in canonical["impact_levers"]:
        for binding in lever["parameter_bindings"]:
            lever_codes_by_parameter[binding["parameter_name"]].add(lever["lever_code"])

    assert isinstance(review_rows, list)
    assert len(review_rows) == len(master_rows) == 21
    assert all(isinstance(row, dict) and set(row) == EXPECTED_REVIEW_KEYS for row in review_rows)

    review_by_name = {row["parameter_name"]: row for row in review_rows}
    assert len(review_by_name) == len(review_rows)
    assert set(review_by_name) == set(master_by_name)
    assert {(row["model_param_id"], row["parameter_name"]) for row in review_rows} == {
        (row["model_param_id"], row["parameter_name"]) for row in master_rows
    }

    decision_counts: Counter[str] = Counter()
    for parameter_name, master_row in master_by_name.items():
        review = review_by_name[parameter_name]
        expected_lever_codes = lever_codes_by_parameter.get(parameter_name, set())
        if expected_lever_codes:
            expected_decision = "executable" if master_row["use_yn"] == "Y" else "catalog_capability"
        else:
            expected_decision = "unbound"

        assert review["model_param_id"] == master_row["model_param_id"]
        assert review["use_yn"] == master_row["use_yn"]
        assert review["del_yn"] == master_row["del_yn"]
        assert review["binding_decision"] in {"executable", "catalog_capability", "unbound"}
        assert review["binding_decision"] == expected_decision
        assert isinstance(review["lever_codes"], list)
        assert len(review["lever_codes"]) == len(set(review["lever_codes"]))
        assert set(review["lever_codes"]) == expected_lever_codes
        _non_empty_string(review["reason"], field=f"{parameter_name}.reason")
        decision_counts[review["binding_decision"]] += 1

    assert decision_counts == {"executable": 9, "catalog_capability": 4, "unbound": 8}
    assert review_by_name["Population"]["binding_decision"] == "unbound"
    assert review_by_name["Population"]["lever_codes"] == []
    assert {
        name for name, review in review_by_name.items() if review["binding_decision"] == "catalog_capability"
    } == EXPECTED_CATALOG_CAPABILITY_NAMES
