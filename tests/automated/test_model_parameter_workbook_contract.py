# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path

from openpyxl import Workbook
import pytest

from apps.agents.model_parameter_agent.utils.lut import (
    ReferenceLoadPolicy,
    build_basecase_index,
    build_slot_catalog,
    get_lut_catalog,
    resolve_effective_reference,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    ParameterKnowledgeBase,
    build_authoritative_blocked_keys,
    build_basecase_records,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    get_model_parameter_resource_paths,
)
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    EXPECTED_PARAMETER_NAMES,
    ModelParameterWorkbookContract,
    WorkbookArtifact,
    load_workbook_contract,
    validate_candidate_write_target,
    validate_workbook_hashes,
    workbook_contract_schema_hash,
)
from apps.agents.model_parameter_agent.utils.workbook_reference import (
    WorkbookReferenceBundle,
    WorkbookReferenceRecord,
    _gdp_growth_records,
    _liq_util_records,
    _power_mix_records,
    clear_workbook_reference_cache,
    extract_workbook_references,
)
from apps.common.exceptions.custom import MIBaseError


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    ROOT_DIR / "apps/agents/model_parameter_agent/resources/contracts/model-parameter-workbook-contract-v4.json"
)
V1_CONTRACT_PATH = (
    ROOT_DIR / "apps/agents/model_parameter_agent/resources/contracts/model-parameter-workbook-contract-v1.json"
)
EXPECTED_SOURCE_COUNTS = {
    "GDP": 815,
    "PMI": 5_040,
    "PowerMix": 4_200,
    "Temperature": 5_040,
    "LiqUtilAdjustment": 23_820,
    "PipelineAdjustment": 420,
    "SupplyDisruption": 4_908,
}
OBSERVED_LEGACY_TARGET_COUNTS = {
    "GDP": 93,
    "PMI": 48,
    "PowerMix": 57,
    "Temperature": 150,
    "LiqUtilAdjustment": 33_348,
    "PipelineAdjustment": 60,
    "SupplyDisruption": 0,
}


@pytest.fixture(scope="module")
def reference_bundle() -> WorkbookReferenceBundle:
    clear_workbook_reference_cache()
    return extract_workbook_references()


def _record_for(
    bundle: WorkbookReferenceBundle,
    parameter_name: str,
    canonical_key: tuple[str | int | float, ...],
) -> WorkbookReferenceRecord:
    return next(record for record in bundle.records_for(parameter_name) if record.canonical_key == canonical_key)


def test_contract_locks_v4_read_only_scope_targets_and_policies() -> None:
    contract = load_workbook_contract()

    assert contract.schema_version == 4
    assert contract.release_id == "new-bc-v4"
    assert contract.capability == "read_only_proposal"
    assert contract.api_version == "v4"
    assert contract.generation_strategy == "multi_event_model_lever_dimensions"
    assert contract.public_api_unchanged is True
    assert set(contract.parameters) == EXPECTED_PARAMETER_NAMES
    assert contract.horizon.years == (2026, 2027, 2028, 2029, 2030)
    assert {
        name: parameter.reference_source.expected_record_count for name, parameter in contract.parameters.items()
    } == EXPECTED_SOURCE_COUNTS
    assert {
        name: parameter.write_target.observed_record_count for name, parameter in contract.parameters.items()
    } == OBSERVED_LEGACY_TARGET_COUNTS

    power_mix = contract.parameters["PowerMix"]
    assert power_mix.reference_source.key_axes == ("Country", "Year", "Energy Source")
    assert power_mix.write_target.value_field == "% Power Mix"
    assert power_mix.constraints.atomic_group_axes == ("Country", "Year")
    assert power_mix.constraints.vector_axis == "Energy Source"
    assert power_mix.constraints.vector_members == (
        "Liquids",
        "Hydro",
        "Solar",
        "Wind",
        "Bioenergy",
        "Gas",
        "Coal",
        "Nuclear",
        "Geothermal",
        "Other",
    )
    assert power_mix.constraints.minimum == 0
    assert power_mix.constraints.maximum == 1
    assert power_mix.constraints.sum == 1
    assert power_mix.constraints.sum_tolerance == 1e-6
    assert power_mix.constraints.require_complete_vector is True

    liq_util = contract.parameters["LiqUtilAdjustment"]
    assert liq_util.proposal_policy.mode == "conditional"
    assert liq_util.proposal_policy.may_abstain is True
    assert liq_util.constraints.direct_evidence_required is True
    assert liq_util.constraints.minimum == 0
    assert liq_util.constraints.maximum is None
    assert liq_util.reference_source.transforms == {}
    assert liq_util.write_target.row_policy == "existing_exact"
    assert liq_util.write_target.metadata_authority == "write_target"

    pipeline = contract.parameters["PipelineAdjustment"]
    assert pipeline.reference_source.parser == "annual_rows_to_months"
    assert pipeline.reference_source.key_axes == (
        "Pipeline Name",
        "From Country",
        "To Country",
        "Year",
        "Month",
    )
    assert pipeline.constraints.minimum == 0
    assert pipeline.reference_source.reference_unit == "Mt/y"
    assert pipeline.write_target.value_field == "User adjusted capacity (Mt/y)"

    supply = contract.parameters["SupplyDisruption"]
    assert supply.reference_source.parser == "production_seasonality_monthly"
    assert set(supply.reference_source.auxiliary_sources) == {"seasonality"}
    assert supply.reference_source.transforms == {}
    assert supply.reference_source.reference_unit == "Mt"
    assert supply.write_target.sheet == "ProductionAdjustment"
    assert supply.write_target.value_field == "Volumes (Mt)"
    assert supply.constraints.minimum == 0

    weakened_document = contract.model_dump(mode="json")
    weakened_document["parameters"]["LiqUtilAdjustment"]["constraints"]["minimum"] = None
    with pytest.raises(ValueError, match="zero minimum"):
        ModelParameterWorkbookContract.model_validate(weakened_document)


def test_v1_contract_remains_an_immutable_five_parameter_compatibility_artifact() -> None:
    contract = load_workbook_contract(V1_CONTRACT_PATH)

    assert contract.schema_version == 1
    assert contract.release_id == "new-bc-v1"
    assert set(contract.parameters) == {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "LiqUtilAdjustment",
    }


def test_contract_hash_is_canonical_and_workbook_hashes_match() -> None:
    contract = load_workbook_contract()
    reordered_document = dict(reversed(list(contract.model_dump(mode="json").items())))
    reordered_contract = ModelParameterWorkbookContract.model_validate(reordered_document)

    assert workbook_contract_schema_hash(contract) == workbook_contract_schema_hash(reordered_contract)
    paths = validate_workbook_hashes(contract)
    assert {role: path.name for role, path in paths.items()} == {
        "demand": "Demand Model_Input.xlsm",
        "supply": "Supply Model_Input.xlsm",
        "trade": "Trade Model_Input.xlsm",
    }

    invalid_workbooks = dict(contract.workbooks)
    invalid_workbooks["demand"] = WorkbookArtifact(
        filename=invalid_workbooks["demand"].filename,
        sha256="0" * 64,
    )
    invalid_contract = contract.model_copy(update={"workbooks": invalid_workbooks})
    with pytest.raises(MIBaseError, match="Workbook sha256 mismatch for demand"):
        validate_workbook_hashes(invalid_contract)


def test_candidate_write_target_validation_is_fail_closed() -> None:
    contract = load_workbook_contract()
    parameter = validate_candidate_write_target(
        contract,
        {
            "canonical_parameter_name": "GDP",
            "parameter_name": "GDP",
            "model_file": "Demand",
            "model_sheet": "GDPPopulationAdjustment",
            "model_table": "table1",
        },
    )
    assert parameter.write_target.value_field == "% change (+/-)"

    with pytest.raises(MIBaseError, match="Candidate write target mismatch for GDP"):
        validate_candidate_write_target(
            contract,
            {
                "canonical_parameter_name": "GDP",
                "model_file": "Demand",
                "model_sheet": "BCInput",
                "model_table": "table1",
            },
        )
    with pytest.raises(MIBaseError, match="not covered by the workbook contract"):
        validate_candidate_write_target(
            contract,
            {
                "canonical_parameter_name": "Population",
                "model_file": "Demand",
                "model_sheet": "GDPPopulationAdjustment",
                "model_table": "table1",
            },
        )


def test_authoritative_sources_extract_expected_horizon_records(
    reference_bundle: WorkbookReferenceBundle,
) -> None:
    assert {
        parameter_name: len(records) for parameter_name, records in reference_bundle.records_by_parameter.items()
    } == EXPECTED_SOURCE_COUNTS
    assert len(reference_bundle.warnings) == 30
    assert all("GDP prior-year GDP level is unavailable" in warning for warning in reference_bundle.warnings)
    assert any("Western Sahara" in warning for warning in reference_bundle.warnings)
    assert any("Falkland Islands" in warning for warning in reference_bundle.warnings)
    assert any("Neutral Zone" in warning for warning in reference_bundle.warnings)
    assert len(reference_bundle.blocked_keys_by_parameter["GDP"]) == 30
    assert all(
        not blocked_keys
        for parameter_name, blocked_keys in reference_bundle.blocked_keys_by_parameter.items()
        if parameter_name != "GDP"
    )
    assert extract_workbook_references() is reference_bundle
    liq_target_slots = reference_bundle.write_target_slots_for("LiqUtilAdjustment")
    assert len(liq_target_slots) == EXPECTED_SOURCE_COUNTS["LiqUtilAdjustment"]
    assert {slot.canonical_key for slot in liq_target_slots} == {
        record.canonical_key for record in reference_bundle.records_for("LiqUtilAdjustment")
    }
    assert all(
        not target_slots
        for parameter_name, target_slots in reference_bundle.write_target_slots_by_parameter.items()
        if parameter_name != "LiqUtilAdjustment"
    )

    with pytest.raises(TypeError):
        reference_bundle.records_by_parameter["GDP"] = ()  # type: ignore[index]


def test_authoritative_sources_preserve_representative_values_and_power_vector(
    reference_bundle: WorkbookReferenceBundle,
) -> None:
    gdp = _record_for(reference_bundle, "GDP", ("United States", 2026))
    assert gdp.value == pytest.approx(0.020638022790823538)
    assert gdp.reference_id.startswith("new-bc-v4:demand:BCInput:U")
    assert gdp.diagnostics == ("value_transform=gdp_year_over_year_growth",)

    pmi = _record_for(reference_bundle, "PMI", ("China", 2026, 1))
    assert pmi.value == 50
    assert pmi.metadata == {"Continent": "Asia", "Region": "East Asia"}

    temperature = _record_for(reference_bundle, "Temperature", ("China", 2026, 1))
    assert temperature.value == pytest.approx(0.013969278033794644)

    power_vector = [
        record
        for record in reference_bundle.records_for("PowerMix")
        if record.axes["Country"] == "Algeria" and record.axes["Year"] == 2026
    ]
    assert len(power_vector) == 10
    assert {record.axes["Energy Source"] for record in power_vector} == {
        "Bioenergy",
        "Coal",
        "Gas",
        "Geothermal",
        "Hydro",
        "Liquids",
        "Nuclear",
        "Other",
        "Solar",
        "Wind",
    }
    assert sum(float(record.value) for record in power_vector) == pytest.approx(1.0, abs=1e-6)

    power_groups: dict[tuple[str, int], list[WorkbookReferenceRecord]] = defaultdict(list)
    for record in reference_bundle.records_for("PowerMix"):
        power_groups[(str(record.axes["Country"]), int(record.axes["Year"]))].append(record)
    expected_members = set(reference_bundle.contract.parameters["PowerMix"].constraints.vector_members)
    assert len(power_groups) == 420
    assert all(
        len(records) == 10
        and {str(record.axes["Energy Source"]) for record in records} == expected_members
        and all(0 <= float(record.value) <= 1 for record in records)
        and math.isclose(
            math.fsum(float(record.value) for record in records),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
        for records in power_groups.values()
    )

    liq_util = _record_for(
        reference_bundle,
        "LiqUtilAdjustment",
        ("Australia", "Australia Pacific LNG", "Australia Pacific LNG T1", 2026, 1),
    )
    assert liq_util.value == pytest.approx(1.00333333333333)
    assert liq_util.metadata == {
        "Period": 97,
        "Life Cycle Category": "Operational",
        "Nameplate Capacity (MTPA)": 4.5,
    }
    assert liq_util.value > 1
    assert "metadata_authority=write_target" in liq_util.diagnostics
    assert "write_target_exact_slot_verified" in liq_util.diagnostics
    assert "write_target_metadata_canonicalized" in liq_util.diagnostics

    pipeline = _record_for(
        reference_bundle,
        "PipelineAdjustment",
        ("MedGaz Pipeline", "Algeria", "Spain", 2026, 1),
    )
    assert pipeline.value == pytest.approx(8.5995)
    assert "annual_capacity_expanded_to_month" in pipeline.diagnostics

    supply = _record_for(reference_bundle, "SupplyDisruption", ("Algeria", 2026, 1))
    assert supply.value == pytest.approx(6.476770267764433)
    assert "seasonality_policy=raw_not_renormalized" in supply.diagnostics


def test_gdp_invalid_source_keys_are_projected_to_the_matching_v4_candidate(
    reference_bundle: WorkbookReferenceBundle,
) -> None:
    blocked = build_authoritative_blocked_keys(
        [
            {
                "candidate_key": "gdp-candidate",
                "canonical_parameter_name": "GDP",
                "parameter_name": "GDP",
                "model_file": "Demand",
                "model_sheet": "GDPPopulationAdjustment",
                "model_table": "table1",
            },
        ],
        {
            "scenario_group": {
                "api_version": "v4",
                "generation_strategy": "multi_event_model_lever_dimensions",
            },
        },
    )

    assert blocked == {
        "gdp-candidate": reference_bundle.blocked_keys_by_parameter["GDP"],
    }
    assert len(blocked["gdp-candidate"]) == 30
    assert (
        build_authoritative_blocked_keys(
            [],
            {
                "scenario_group": {
                    "api_version": "v3",
                    "generation_strategy": "multi_event_model_lever_dimensions",
                },
            },
        )
        == {}
    )


def test_v4_runtime_adapter_preserves_counts_and_blocked_keys(
    reference_bundle: WorkbookReferenceBundle,
) -> None:
    registry = get_model_parameter_resource_paths().lut_registry
    targets = {
        "GDP": ("Demand", "GDPPopulationAdjustment", "table1"),
        "PMI": ("Demand", "PMIAdjustment", "table1"),
        "PowerMix": ("Demand", "PowerMixAdjustment", "table1"),
        "Temperature": ("Demand", "WeatherAdjustment", "table2"),
        "LiqUtilAdjustment": ("Supply", "LiqUtilAdjustment", "table1"),
        "PipelineAdjustment": ("Supply", "PipelineAdjustment", "table1"),
        "SupplyDisruption": ("Supply", "ProductionAdjustment", "table2"),
    }
    candidates = [
        {
            "candidate_key": f"candidate-{parameter_name}",
            "mapping_strategy": "v4",
            "canonical_parameter_name": parameter_name,
            "parameter_name": parameter_name,
            "model_file": model_file,
            "model_sheet": model_sheet,
            "model_table": model_table,
            "proposal_reference_mode": "v4_workbook_then_lut",
            "proposal_exact_axes": list(registry.specs[parameter_name].key_axes),
        }
        for parameter_name, (model_file, model_sheet, model_table) in targets.items()
    ]
    scenario_context = {
        "scenario_group": {
            "api_version": "v4",
            "generation_strategy": "multi_event_model_lever_dimensions",
        },
    }
    records, warnings = build_basecase_records(
        ParameterKnowledgeBase(
            mapping_source="test",
            basecase_dir_path="",
            parameter_definitions={},
            mapping_rules=[],
            basecase_profiles={},
        ),
        candidates,
        scenario_context,
        registry=registry,
    )
    blocked = build_authoritative_blocked_keys(candidates, scenario_context)
    index = build_basecase_index(
        records,
        candidates,
        registry=registry,
        blocked_exact_keys_by_candidate=blocked,
    )
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[str(record["parameter_name"])] += 1

    assert counts == EXPECTED_SOURCE_COUNTS
    assert warnings == list(reference_bundle.warnings)
    assert index.blocked_exact_keys_by_candidate["candidate-GDP"] == (reference_bundle.blocked_keys_by_parameter["GDP"])
    assert all(
        not keys
        for candidate_key, keys in index.blocked_exact_keys_by_candidate.items()
        if candidate_key != "candidate-GDP"
    )
    assert any(
        "Life Cycle Category" not in record.metadata
        for record in index.records_for_candidate("candidate-LiqUtilAdjustment")
    )
    power_mix_groups: dict[tuple[str, int], list[float]] = defaultdict(list)
    for record in index.records_for_candidate("candidate-PowerMix"):
        power_mix_groups[(str(record.axes["Country"]), int(record.axes["Year"]))].append(
            float(record.value),
        )
    assert len(power_mix_groups) == 420
    assert all(
        len(values) == 10 and math.fsum(values) == pytest.approx(1.0, abs=1e-6) for values in power_mix_groups.values()
    )


def test_liq_runtime_excludes_legacy_lut_identity_and_emits_exact_target_identity() -> None:
    registry = get_model_parameter_resource_paths().lut_registry
    candidate = {
        "candidate_key": "candidate-LiqUtilAdjustment",
        "mapping_strategy": "v4",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "parameter_name": "LiqUtilAdjustment",
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "proposal_reference_mode": "v4_workbook_then_lut",
        "proposal_exact_axes": list(registry.specs["LiqUtilAdjustment"].key_axes),
    }
    scenario_context = {
        "scenario_group": {
            "api_version": "v4",
            "generation_strategy": "multi_event_model_lever_dimensions",
        },
    }
    records, _ = build_basecase_records(
        ParameterKnowledgeBase(
            mapping_source="test",
            basecase_dir_path="",
            parameter_definitions={},
            mapping_rules=[],
            basecase_profiles={},
        ),
        [candidate],
        scenario_context,
        registry=registry,
    )
    policy = ReferenceLoadPolicy()
    catalog = get_lut_catalog(policy, registry=registry)
    blocked = build_authoritative_blocked_keys(
        [candidate],
        scenario_context,
        lut_catalog=catalog,
    )
    index = build_basecase_index(
        records,
        [candidate],
        policy=policy,
        registry=registry,
        blocked_exact_keys_by_candidate=blocked,
    )
    slot_catalog = build_slot_catalog(index, catalog)
    legacy_axes = {
        "Country": "United States",
        "LNG Plant": "Cove Point LNG",
        "LNG Plant Train": "Cove Point LNG T1",
        "Year": 2026,
        "Month": 1,
    }
    target_axes = {
        "Country": "United States",
        "LNG Plant": "Cove Point Export",
        "LNG Plant Train": "Cove Point Export",
        "Year": 2026,
        "Month": 1,
    }

    assert tuple(legacy_axes.values()) in blocked["candidate-LiqUtilAdjustment"]
    assert not slot_catalog.contains("candidate-LiqUtilAdjustment", legacy_axes)
    assert resolve_effective_reference("candidate-LiqUtilAdjustment", legacy_axes, index, catalog) is None
    assert slot_catalog.contains("candidate-LiqUtilAdjustment", target_axes)
    effective = resolve_effective_reference("candidate-LiqUtilAdjustment", target_axes, index, catalog)
    assert effective is not None
    assert dict(effective.axes) == target_axes
    assert effective.metadata["Life Cycle Category"] == "Operational"
    assert effective.metadata["Nameplate Capacity (MTPA)"] == 5.25


def test_power_mix_source_group_is_dropped_and_blocked_atomically() -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters["PowerMix"]
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = parameter.reference_source.sheet
    values = (0.03, 0.12, 0.08, 0.09, 0.03, 0.35, 0.16, 0.12, 0.01, 0.01)
    for row, (member, value) in enumerate(
        zip(parameter.constraints.vector_members, values, strict=True),
        start=parameter.reference_source.data_start_row,
    ):
        worksheet[f"Z{row}"] = "Testland"
        worksheet[f"AA{row}"] = 2027
        worksheet[f"AB{row}"] = 1
        worksheet[f"AC{row}"] = member
        worksheet[f"AE{row}"] = 1.1 if member == "Gas" else value

    records, warnings, blocked_keys = _power_mix_records(
        contract,
        "PowerMix",
        parameter,
        worksheet,
    )
    workbook.close()

    assert records == ()
    assert len(blocked_keys) == 10
    assert all(key[:2] == ("Testland", 2027) for key in blocked_keys)
    assert any("invalid atomic source vector" in warning for warning in warnings)


def test_gdp_conflicting_level_remains_blocked_after_later_duplicate() -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters["GDP"]
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = parameter.reference_source.sheet
    for row, (year, value) in enumerate(
        ((2025, 100.0), (2026, 110.0), (2026, 120.0), (2026, 130.0)),
        start=parameter.reference_source.data_start_row,
    ):
        worksheet[f"Q{row}"] = year
        worksheet[f"T{row}"] = "Testland"
        worksheet[f"U{row}"] = value

    records, warnings, blocked_keys = _gdp_growth_records(
        contract,
        "GDP",
        parameter,
        worksheet,
    )
    workbook.close()

    assert records == ()
    assert {("Testland", 2026), ("Testland", 2027)} <= blocked_keys
    assert any("conflicting GDP level" in warning for warning in warnings)


def _liq_source_row(
    worksheet: object,
    *,
    period: object = 1,
    capacity: object = 0.5,
    utilisation: object = 0.9,
    life_cycle: object = "Operational",
) -> None:
    row = 8
    worksheet[f"B{row}"] = 2026
    worksheet[f"C{row}"] = 1
    worksheet[f"D{row}"] = period
    worksheet[f"E{row}"] = "Testland"
    worksheet[f"F{row}"] = "Test LNG"
    worksheet[f"G{row}"] = "Test LNG T1"
    worksheet[f"H{row}"] = life_cycle
    worksheet[f"I{row}"] = capacity
    worksheet[f"N{row}"] = utilisation


@pytest.mark.parametrize(
    ("period", "capacity", "utilisation"),
    [("invalid", 0.5, 0.9), (1, 0.5, -0.1)],
)
def test_liq_invalid_identifiable_source_key_is_blocked(
    period: object,
    capacity: object,
    utilisation: object,
) -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters["LiqUtilAdjustment"]
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = parameter.reference_source.sheet
    _liq_source_row(
        worksheet,
        period=period,
        capacity=capacity,
        utilisation=utilisation,
    )

    records, warnings, blocked_keys = _liq_util_records(
        contract,
        "LiqUtilAdjustment",
        parameter,
        worksheet,
    )
    workbook.close()

    assert records == ()
    assert blocked_keys == frozenset({("Testland", "Test LNG", "Test LNG T1", 2026, 1)})
    assert warnings


def test_liq_v4_source_capacity_is_not_used_as_target_metadata() -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters["LiqUtilAdjustment"]
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = parameter.reference_source.sheet
    _liq_source_row(worksheet, capacity=None)

    records, warnings, blocked_keys = _liq_util_records(
        contract,
        "LiqUtilAdjustment",
        parameter,
        worksheet,
    )
    workbook.close()

    assert len(records) == 1
    assert "Nameplate Capacity (MTPA)" not in records[0].metadata
    assert records[0].diagnostics == ("metadata_authority=write_target",)
    assert warnings == ()
    assert blocked_keys == frozenset()


def test_liq_blank_lifecycle_is_preserved_as_optional_source_metadata() -> None:
    contract = load_workbook_contract()
    parameter = contract.parameters["LiqUtilAdjustment"]
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = parameter.reference_source.sheet
    _liq_source_row(worksheet, life_cycle=None)

    records, warnings, blocked_keys = _liq_util_records(
        contract,
        "LiqUtilAdjustment",
        parameter,
        worksheet,
    )
    workbook.close()

    assert len(records) == 1
    assert "Life Cycle Category" not in records[0].metadata
    assert "missing_metadata=Life Cycle Category" in records[0].diagnostics
    assert warnings == ()
    assert blocked_keys == frozenset()
