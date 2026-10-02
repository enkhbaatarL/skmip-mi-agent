# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: S101
from copy import deepcopy

import pytest

from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    partition_proposal_parameter_candidates,
)
from apps.agents.model_parameter_agent.utils.proposal_capabilities import (
    EXPECTED_EXTEND16_CATALOG_CHECKSUM,
    EXPECTED_EXTEND16_PARAMETER_IDS,
    load_proposal_capability_contract,
)
from apps.common.exceptions.custom import MIBaseError


def _candidate(entry: object) -> dict[str, object]:
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
    }


def test_extend16_contract_has_exact_release_scope_and_reference_policies() -> None:
    contract = load_proposal_capability_contract()

    assert contract.release_id == "extend16-v7"
    assert contract.catalog_version == "v4.0"
    assert contract.catalog_checksum == EXPECTED_EXTEND16_CATALOG_CHECKSUM
    assert frozenset(contract.by_id) == EXPECTED_EXTEND16_PARAMETER_IDS
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
    assert all(
        contract.by_id[model_param_id].constraints["basecase_only"]
        for model_param_id in {16, 18, 20, 22, 23, 24}
    )
    assert {entry.reference_mode for entry in contract.parameters} == {"v4_workbook_then_lut"}


def test_v4_scope_accepts_exactly_the_extend16_id_name_target_tuples() -> None:
    contract = load_proposal_capability_contract()
    allowed, excluded = partition_proposal_parameter_candidates(
        [_candidate(entry) for entry in contract.parameters],
    )

    assert {int(item["model_param_id"]) for item in allowed} == EXPECTED_EXTEND16_PARAMETER_IDS
    assert excluded == []
    assert {item["proposal_capability_release_id"] for item in allowed} == {"extend16-v7"}
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
    }
