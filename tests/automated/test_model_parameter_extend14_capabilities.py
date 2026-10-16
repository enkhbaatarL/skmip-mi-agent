# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: S101
from copy import deepcopy

import pytest

from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    partition_proposal_parameter_candidates,
)
from apps.agents.model_parameter_agent.utils.proposal_capabilities import (
    EXPECTED_CATALOG_CHECKSUMS,
    EXPECTED_COMPATIBILITY_PARAMETER_IDS,
    EXPECTED_EXTEND17_PARAMETER_IDS,
    EXPECTED_EXTEND17_RELEASE_ID,
    load_proposal_capability_contract,
)
from apps.common.exceptions.custom import MIBaseError


def _candidate(
    entry: object,
    *,
    catalog_version: str = "v4.1",
) -> dict[str, object]:
    target = entry.model_target  # type: ignore[attr-defined]
    return {
        "candidate_key": f"parameter|{entry.model_param_id}",  # type: ignore[attr-defined]
        "mapping_strategy": "v4",
        "model_param_id": entry.model_param_id,  # type: ignore[attr-defined]
        "canonical_parameter_name": entry.parameter_name,  # type: ignore[attr-defined]
        "parameter_name": entry.parameter_name,  # type: ignore[attr-defined]
        "model_file": target.model_file,
        "model_sheet": target.model_sheet,
        "model_table": target.model_table,
        "impact_catalog_version": catalog_version,
        "impact_catalog_checksum": EXPECTED_CATALOG_CHECKSUMS[catalog_version],
    }


def test_extend17_contract_has_exact_release_scope_and_reference_policies() -> None:
    contract = load_proposal_capability_contract()

    assert contract.release_id == EXPECTED_EXTEND17_RELEASE_ID
    assert contract.current_catalog_version == "v4.1"
    assert contract.catalog_checksums == EXPECTED_CATALOG_CHECKSUMS
    assert frozenset(contract.by_id) == EXPECTED_COMPATIBILITY_PARAMETER_IDS
    assert 9 not in contract.by_id
    assert contract.by_id[11].parameter_name == "Population"
    assert contract.by_id[11].exact_axes == ("Country", "Year")
    assert contract.by_id[11].constraints["minimum"] == 0
    assert contract.by_id[12].parameter_name == "HurricaneIntensity"
    assert contract.by_id[12].exact_axes == ("Year", "Month")
    assert contract.by_id[12].constraints["maximum"] == 4
    assert contract.by_id[12].constraints["integer_only"] is True
    assert contract.by_id[13].parameter_name == "LiqProdAdjustment"
    assert contract.by_id[13].exact_axes == (
        "Country",
        "LNG Plant",
        "LNG Plant Train",
        "Year",
        "Month",
    )
    assert contract.by_id[13].constraints["unit"] == "Mt LNG/month"
    assert contract.by_id[15].parameter_name == "PipelineAdjustment"
    assert contract.by_id[15].reference_mode == "v4_workbook_then_lut"
    assert contract.by_id[15].exact_axes == (
        "Pipeline Name",
        "From Country",
        "To Country",
        "Year",
        "Month",
    )
    assert contract.by_id[15].constraints["unit"] == "Mt/y"
    assert contract.by_id[16].parameter_name == "RegasAdjustment"
    assert contract.by_id[16].exact_axes == (
        "Continent",
        "Region",
        "Country",
        "Regasification plant",
        "Life Cycle Category",
        "Nameplate capacity (MTPA)",
        "Year",
        "Month",
    )
    assert contract.by_id[17].parameter_name == "SupplyDisruption"
    assert contract.by_id[17].reference_mode == "v4_workbook_then_lut"
    assert contract.by_id[17].exact_axes == ("Country", "Year", "Month")
    assert contract.by_id[17].model_target.model_sheet == "ProductionAdjustment"
    assert contract.by_id[17].constraints["unit"] == "Mt"
    assert contract.by_id[18].parameter_name == "PNG Contract Volume"
    assert contract.by_id[18].exact_axes == ("Year", "From Country", "To Country")
    assert contract.by_id[18].constraints["unit"] == "Mt LNG"
    assert contract.by_id[20].parameter_name == "ShippingCost"
    assert contract.by_id[20].exact_axes == ("Year",)
    assert contract.by_id[20].constraints["unit"] == "$/d"
    assert contract.by_id[22].parameter_name == "RegionalProductionAdjustment"
    assert contract.by_id[22].exact_axes == ("Year", "Province/Country")
    assert contract.by_id[22].model_target.model_sheet == "ProductionAdjustment"
    assert contract.by_id[22].model_target.model_table == "table1"
    assert contract.by_id[22].constraints["unit"] == "Bcm"
    assert contract.by_id[22].constraints["annual_regional_production_evidence_required"] is True
    assert contract.by_id[23].parameter_name == "ShippingFuelCost"
    assert contract.by_id[23].exact_axes == ("Year",)
    assert contract.by_id[23].model_target.model_table == "table3"
    assert contract.by_id[23].constraints["unit"] == "$/tonne"
    assert contract.by_id[23].constraints["shipping_fuel_evidence_required"] is True
    assert contract.by_id[24].parameter_name == "CanalToll"
    assert contract.by_id[24].exact_axes == ("Canal", "Year")
    assert contract.by_id[24].model_target.model_table == "table4"
    assert contract.by_id[24].constraints["unit"] == "$/crossing"
    assert contract.by_id[24].constraints["canal_toll_evidence_required"] is True
    assert contract.by_id[24].catalog_versions == ("v4.0",)
    assert contract.by_id[25].parameter_name == "Suez Canal Cost"
    assert contract.by_id[25].exact_axes == ("Canal", "Year")
    assert contract.by_id[25].model_target.model_table == "table4"
    assert contract.by_id[25].constraints["canal"] == "Suez"
    assert contract.by_id[25].catalog_versions == ("v4.1",)
    assert contract.by_id[26].parameter_name == "Panama Canal Cost"
    assert contract.by_id[26].exact_axes == ("Canal", "Year")
    assert contract.by_id[26].model_target.model_table == "table5"
    assert contract.by_id[26].constraints["canal"] == "Panama"
    assert contract.by_id[26].catalog_versions == ("v4.1",)
    assert all(
        contract.by_id[model_param_id].constraints["basecase_only"]
        for model_param_id in {16, 18, 20, 22, 23, 24, 25, 26}
    )
    assert {entry.reference_mode for entry in contract.parameters} == {"v4_workbook_then_lut"}


def test_v4_1_scope_accepts_exactly_the_extend17_id_name_target_tuples() -> None:
    contract = load_proposal_capability_contract()
    allowed, excluded = partition_proposal_parameter_candidates(
        [_candidate(entry) for entry in contract.parameters_for("v4.1")],
    )

    assert {int(item["model_param_id"]) for item in allowed} == EXPECTED_EXTEND17_PARAMETER_IDS
    assert excluded == []
    assert {item["proposal_capability_release_id"] for item in allowed} == {
        EXPECTED_EXTEND17_RELEASE_ID,
    }
    assert all(item["proposal_evidence_policy"] == "explicit_or_unique_inferred" for item in allowed)


@pytest.mark.parametrize("field", ["model_param_id", "model_sheet", "model_table"])
def test_v4_scope_rejects_capability_identity_mismatch_before_llm(field: str) -> None:
    entry = load_proposal_capability_contract().by_id[15]
    candidate = _candidate(entry)
    candidate[field] = 999 if field == "model_param_id" else "mismatch"

    with pytest.raises(MIBaseError, match="capability contract"):
        partition_proposal_parameter_candidates([candidate])


def test_v4_scope_excludes_unknown_or_inactive_parameter() -> None:
    candidate = _candidate(load_proposal_capability_contract().by_id[15])
    candidate.update(
        {
            "model_param_id": 19,
            "canonical_parameter_name": "RemainingUnrestrictedAmount",
            "parameter_name": "RemainingUnrestrictedAmount",
        },
    )

    allowed, excluded = partition_proposal_parameter_candidates([candidate])

    assert allowed == []
    assert excluded[0]["canonical_parameter_name"] == "RemainingUnrestrictedAmount"


def test_v4_0_scope_keeps_legacy_canal_toll_and_rejects_split_parameters() -> None:
    contract = load_proposal_capability_contract()
    candidates = [
        _candidate(entry, catalog_version="v4.0")
        for entry in contract.parameters_for("v4.0")
    ]
    candidates.extend(
        _candidate(contract.by_id[model_param_id], catalog_version="v4.0")
        for model_param_id in (25, 26)
    )

    allowed, excluded = partition_proposal_parameter_candidates(candidates)

    assert 24 in {int(item["model_param_id"]) for item in allowed}
    assert {item["canonical_parameter_name"] for item in excluded} == {
        "Suez Canal Cost",
        "Panama Canal Cost",
    }


def test_legacy_scope_remains_the_existing_five_names() -> None:
    contract = load_proposal_capability_contract()
    legacy_candidates = []
    for entry in contract.parameters:
        candidate = deepcopy(_candidate(entry))
        candidate["mapping_strategy"] = "v3"
        legacy_candidates.append(candidate)

    allowed, excluded = partition_proposal_parameter_candidates(legacy_candidates)

    assert {item["canonical_parameter_name"] for item in allowed} == {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "LiqUtilAdjustment",
    }
    assert {item["canonical_parameter_name"] for item in excluded} == {
        "Population",
        "HurricaneIntensity",
        "LiqProdAdjustment",
        "PipelineAdjustment",
        "SupplyDisruption",
        "RegasAdjustment",
        "PNG Contract Volume",
        "ShippingCost",
        "RegionalProductionAdjustment",
        "ShippingFuelCost",
        "CanalToll",
        "Suez Canal Cost",
        "Panama Canal Cost",
    }
