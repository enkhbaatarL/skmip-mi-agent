# ruff: noqa: S101

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
from decimal import Decimal
from pathlib import Path

import pytest

from apps.agents.model_parameter_agent.utils.lut import (
    LutCatalog,
    ParameterSpecRegistry,
    ReferenceLoadPolicy,
    build_basecase_index,
    build_slot_catalog,
    canonical_axes_for_candidate,
    clear_lut_runtime_cache,
    get_lut_catalog,
    get_parameter_spec_registry,
    resolve_effective_reference,
    validate_lut_startup,
)
from apps.agents.model_parameter_agent.utils.lut.keys import (
    apply_numeric_precision,
    ceil_numeric_value,
    normalize_numeric_value,
    truncate_numeric_value,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


EXPECTED_COUNTS = {
    "GDP": 815,
    "PMI": 5460,
    "PowerMix": 4200,
    "Temperature": 5040,
    "Population": 845,
    "HurricaneIntensity": 60,
    "LiqProdAdjustment": 19366,
    "LiqUtilAdjustment": 19366,
    "PipelineAdjustment": 360,
    "SupplyDisruption": 4908,
}

DISABLED_PARAMETERS = {"Coal Futures Price", "Gas Futures Price"}


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _tabular_config(
    csv_name: str,
    *,
    metadata_axes: str = "[]",
) -> str:
    return f"""\
TestParameter:
  adapter: tabular
  layout: row
  files:
    values:
      path: {csv_name}
      axis_columns:
        Country: Country
        Year: Year
        Tag: Tag
      value_column: Value
  key_axes: [Country, Year]
  metadata_axes: {metadata_axes}
"""


@pytest.fixture(scope="module")
def real_domain() -> tuple[ParameterSpecRegistry, LutCatalog]:
    clear_lut_runtime_cache()
    policy = ReferenceLoadPolicy()
    registry, catalog = validate_lut_startup(True, policy)  # noqa: FBT003
    assert catalog is not None
    return registry, catalog


def test_default_catalog_matches_final_record_counts(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    assert {
        parameter_name: len(catalog.records_for_parameter(parameter_name)) for parameter_name in registry.specs
    } == {**EXPECTED_COUNTS, **dict.fromkeys(DISABLED_PARAMETERS, 0)}
    assert set(registry.enabled_specs) == set(EXPECTED_COUNTS)
    assert {record.axes["Year"] for record in catalog.records_for_parameter("GDP")} == set(
        range(2026, 2031),
    )
    assert len({record.axes["Country"] for record in catalog.records_for_parameter("GDP")}) == 163
    assert len({record.axes["Country"] for record in catalog.records_for_parameter("PMI")}) == 91
    assert "Other Africa" in {record.axes["Country"] for record in catalog.records_for_parameter("PMI")}
    referenced_names = {path.name for path in registry.referenced_paths}
    assert "Demand_Model_Input_PMIInput_value_based_t1.csv" in referenced_names
    assert "Demand_Model_LUT_General_value_based_t6.csv" in referenced_names


def test_exact_gdp_temperature_and_liq_transforms(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    _, catalog = real_domain
    china_2026 = catalog.lookup("GDP", {"Country": "China", "Year": 2026})
    assert china_2026 is not None
    assert "exact_year_minus_one=2025" in china_2026.diagnostics
    assert catalog.lookup("GDP", {"Country": "China", "Year": 2025}) is None

    us_january = catalog.lookup(
        "Temperature",
        {"Country": "United States", "Year": 2026, "Month": 1},
    )
    assert us_january is not None
    assert us_january.value == truncate_numeric_value(
        18.0 - 513.0162988115451 / 30.0,
        label="US January temperature",
        max_decimal_places=5,
    )
    assert "degree_days_branch=hdd" in us_january.diagnostics

    liq_record = catalog.records_for_parameter("LiqUtilAdjustment")[0]
    assert set(liq_record.metadata) == {
        "Period",
        "Life Cycle Category",
        "Nameplate Capacity (MTPA)",
    }
    assert "Nameplate Capacity" not in liq_record.metadata
    assert "capacity_transform=mtpm_x_12" in liq_record.diagnostics

    qatar_t12 = catalog.lookup(
        "LiqUtilAdjustment",
        {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "QatarGas LNG T12",
            "Year": 2026,
            "Month": 7,
        },
    )
    assert qatar_t12 is not None
    assert qatar_t12.value == 0
    assert qatar_t12.metadata["Nameplate Capacity (MTPA)"] == 7.8


def test_exact_new_parameter_transforms(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    _, catalog = real_domain

    population = catalog.lookup("Population", {"Country": "China", "Year": 2026})
    assert population is not None
    assert population.value == 1400888.91666
    assert population.diagnostics == ("unit=thousand_people",)

    hurricane = catalog.lookup("HurricaneIntensity", {"Year": 2026, "Month": 1})
    assert hurricane is not None
    assert hurricane.value == 0
    assert "hurricane_baseline=no_hurricane" in hurricane.diagnostics
    assert "validated_impacted_plant_count=16" in hurricane.diagnostics

    production = catalog.lookup(
        "LiqProdAdjustment",
        {
            "Country": "Australia",
            "LNG Plant": "Australia Pacific LNG",
            "LNG Plant Train": "Australia Pacific LNG T1",
            "Year": 2026,
            "Month": 1,
        },
    )
    assert production is not None
    assert production.value == 0.37478
    assert production.metadata["Nameplate Capacity (MTPA)"] == 4.5
    assert production.diagnostics == ("production_transform=capacity_mtpm_x_utilisation",)

    pipeline_axes = {
        "Pipeline Name": "Power of Siberia 1 (Yakutia-Khabarovsk-Vladivostok Pipeline)",
        "From Country": "Russia",
        "To Country": "China",
        "Year": 2026,
    }
    for month in (1, 12):
        pipeline = catalog.lookup("PipelineAdjustment", {**pipeline_axes, "Month": month})
        assert pipeline is not None
        assert pipeline.value == 38
        assert pipeline.diagnostics == ("annual_capacity_expanded_to_month",)

    supply = catalog.lookup(
        "SupplyDisruption",
        {"Country": "Mexico", "Year": 2026, "Month": 12},
    )
    assert supply is not None
    assert supply.value == 1.81221
    assert "seasonality_policy=raw_not_renormalized" in supply.diagnostics
    assert "aggregated_production_rows=37" in supply.diagnostics

    pmi = catalog.lookup("PMI", {"Country": "Other Africa", "Year": 2026, "Month": 1})
    assert pmi is not None
    assert pmi.value == 50
    assert "pmi_reference_country=Iran" in pmi.diagnostics


def test_disabled_startup_validates_yaml_without_opening_missing_csv(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config" / "test_lut_config.yaml",
        _tabular_config("missing.csv", metadata_axes="[Tag]"),
    )
    clear_lut_runtime_cache()
    registry, catalog = validate_lut_startup(
        False,  # noqa: FBT003
        ReferenceLoadPolicy(),
        config_path=config,
        lut_root=tmp_path,
    )
    assert catalog is None
    assert registry.is_registered("TestParameter")
    with pytest.raises(MIBaseError, match="not accessible"):
        validate_lut_startup(
            True,  # noqa: FBT003
            ReferenceLoadPolicy(),
            config_path=config,
            lut_root=tmp_path,
        )


def test_active_lut_requires_every_year_in_configured_horizon(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("values.csv", metadata_axes="[Tag]"),
    )
    _write(
        tmp_path / "values.csv",
        "Country,Year,Tag,Value\nA,2026,x,1\nA,2027,x,2\n",
    )
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match=r"complete configured horizon.*missing_years=\[2028\]"):
        get_lut_catalog(ReferenceLoadPolicy(2026, 2028), registry=registry)


def test_disabled_parameter_is_structurally_validated_but_not_cataloged(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("pending.csv", metadata_axes="[Tag]").replace(
            "TestParameter:\n",
            "TestParameter:\n  enabled: false\n",
        ),
    )
    pending = _write(tmp_path / "pending.csv", "Country,Year,Tag\nA,2025,x\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    assert not registry.specs["TestParameter"].enabled
    with pytest.raises(MIBaseError, match="missing required headers"):
        get_lut_catalog(ReferenceLoadPolicy(), registry=registry)

    _write(pending, "Country,Year,Tag,Value\nA,2025,x,1\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    catalog = get_lut_catalog(ReferenceLoadPolicy(), registry=registry)
    assert catalog.records == ()
    assert catalog.records_for_parameter("TestParameter") == ()


def test_auxiliary_reference_is_header_validated_but_not_cataloged(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
basecase: {}
lut:
  TestParameter:
    adapter: tabular
    layout: row
    files:
      values:
        path: values.csv
        axis_columns: {Country: Country, Year: Year}
        value_column: Value
    key_axes: [Country, Year]
references:
  countries:
    path: countries.csv
    required_columns: [Country, Region]
""",
    )
    _write(tmp_path / "values.csv", "Country,Year,Value\nA,2026,1\n")
    countries = _write(tmp_path / "countries.csv", "Country\nA\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    assert set(registry.references) == {"countries"}
    with pytest.raises(MIBaseError, match="missing required headers"):
        get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)

    _write(countries, "Country,Region\nA,Asia\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    catalog = get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
    assert len(catalog.records) == 1
    assert catalog.records[0].parameter_name == "TestParameter"


def test_reference_load_policy_rejects_reversed_horizon() -> None:
    with pytest.raises(MIBaseError, match="start_year must be less than or equal") as caught:
        ReferenceLoadPolicy(2030, 2026)
    assert caught.value.error_code is ErrorCode.INVALID_REQUEST

    assert ReferenceLoadPolicy(value_max_decimal_places=-1).value_max_decimal_places == -1
    with pytest.raises(MIBaseError, match="-1 or greater"):
        ReferenceLoadPolicy(value_max_decimal_places=-2)


@pytest.mark.parametrize(
    ("yaml_text", "expected"),
    [
        (
            """\
X:
  adapter: tabular
  layout: row
  files: {values: {path: ../escape.csv, axis_columns: {Country: Country, Year: Year}, value_column: Value}}
  key_axes: [Country, Year]
""",
            "escapes",
        ),
        (
            """\
X:
  adapter: tabular
  layout: row
  files: {values: {path: values.csv, axis_columns: {Country: Country, Year: Year}, value_column: Value}}
  key_axes: [Country, Year]
  metadata_axes: [Year]
""",
            "overlap",
        ),
        (
            """\
X:
  adapter: unknown
  files: {values: {path: values.csv, required_columns: [A]}}
  key_axes: [Country]
""",
            "adapter",
        ),
        (
            """\
X:
  adapter: tabular
  layout: row
  files: {values: {path: values.csv, axis_columns: {Country: Country, Year: Year}, value_column: Value}}
  key_axes: [Country, Year]
  unexpected: true
""",
            "unexpected",
        ),
    ],
)
def test_registry_rejects_escape_overlap_unknown_and_extra_fields(
    tmp_path: Path,
    yaml_text: str,
    expected: str,
) -> None:
    config = _write(tmp_path / "config.yaml", yaml_text)
    clear_lut_runtime_cache()
    with pytest.raises(MIBaseError, match=expected) as caught:
        get_parameter_spec_registry(config, lut_root=tmp_path)
    assert caught.value.error_code is ErrorCode.INVALID_REQUEST


@pytest.mark.parametrize(
    ("csv_text", "expected"),
    [
        ("Country,Year,Tag\nA,2026,x\n", "missing required headers"),
        ("Country,Year,Tag,Value\nA,2026,x,nan\n", "finite number"),
        ("Country,Year,Tag,Value\nA,2026.5,x,1\n", "integer"),
    ],
)
def test_catalog_rejects_missing_header_nonfinite_and_noninteger(
    tmp_path: Path,
    csv_text: str,
    expected: str,
) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("values.csv", metadata_axes="[Tag]"),
    )
    _write(tmp_path / "values.csv", csv_text)
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match=expected):
        get_lut_catalog(ReferenceLoadPolicy(), registry=registry)


def test_tabular_adapter_rejects_month_outside_one_to_twelve(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
MonthlyParameter:
  adapter: tabular
  layout: row
  files:
    values:
      path: values.csv
      axis_columns: {Country: Country, Year: Year, Month: Month}
      value_column: Value
  key_axes: [Country, Year, Month]
""",
    )
    _write(tmp_path / "values.csv", "Country,Year,Month,Value\nA,2026,13,1\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match="Month must be between 1 and 12"):
        get_lut_catalog(ReferenceLoadPolicy(), registry=registry)


def test_identical_duplicate_dedupes_but_value_or_metadata_conflict_fails(
    tmp_path: Path,
) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("values.csv", metadata_axes="[Tag]"),
    )
    values = tmp_path / "values.csv"
    _write(values, "Country,Year,Tag,Value\nA,2026,x,1\nA,2026,x,1\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    policy = ReferenceLoadPolicy(2026, 2026)
    catalog = get_lut_catalog(policy, registry=registry)
    assert len(catalog.records) == 1
    assert len(catalog.diagnostics) == 1
    assert "deduped identical" in catalog.diagnostics[0]

    _write(values, "Country,Year,Tag,Value\nA,2026,x,1\nA,2026,x,2\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match="conflicting duplicate"):
        get_lut_catalog(policy, registry=registry)

    _write(values, "Country,Year,Tag,Value\nA,2026,x,1\nA,2026,y,1\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match="conflicting duplicate"):
        get_lut_catalog(policy, registry=registry)


def test_catalog_is_deeply_immutable_and_cache_is_thread_safe() -> None:
    clear_lut_runtime_cache()
    policy = ReferenceLoadPolicy()

    def load() -> LutCatalog:
        return get_lut_catalog(policy)

    with ThreadPoolExecutor(max_workers=8) as executor:
        catalogs = list(executor.map(lambda _: load(), range(16)))
    assert len({id(catalog) for catalog in catalogs}) == 1
    catalog = catalogs[0]
    with pytest.raises(TypeError):
        catalog.records[0].axes["Country"] = "mutated"  # type: ignore[index]
    with pytest.raises(TypeError):
        catalog.registry.specs["Other"] = catalog.registry.specs["GDP"]  # type: ignore[index]
    narrower = get_lut_catalog(ReferenceLoadPolicy(2027, 2030))
    assert narrower.version != catalog.version
    assert narrower is not catalog


def test_catalog_version_and_warm_cache_identity_follow_csv_content(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("values.csv", metadata_axes="[Tag]"),
    )
    values = _write(tmp_path / "values.csv", "Country,Year,Tag,Value\nA,2026,x,1\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    policy = ReferenceLoadPolicy(2026, 2026)
    first = get_lut_catalog(policy, registry=registry)
    assert get_lut_catalog(policy, registry=registry) is first

    _write(values, "Country,Year,Tag,Value\nA,2026,x,20\n")
    second = get_lut_catalog(policy, registry=registry)
    assert second is not first
    assert second.version != first.version
    assert second.records[0].value == 20


def test_basecase_and_lut_values_use_bounded_precision(
    tmp_path: Path,
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("values.csv", metadata_axes="[Tag]"),
    )
    _write(
        tmp_path / "values.csv",
        "Country,Year,Tag,Value\nA,2026,x,1.23456789\nB,2026,x,8.0000001\n",
    )
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    catalog = get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
    assert catalog.lookup("TestParameter", {"Country": "A", "Year": 2026}).value == 1.23456
    integer_lut_value = catalog.lookup("TestParameter", {"Country": "B", "Year": 2026}).value
    assert integer_lut_value == 8
    assert isinstance(integer_lut_value, int)

    real_registry, _ = real_domain
    candidate = {
        "candidate_key": "gdp",
        "canonical_parameter_name": "GDP",
        "basecase_read_mode": "fixed_columns",
        "basecase_column_roles": "A:Country,B:Year,C:GDP",
    }
    index = build_basecase_index(
        [
            {
                "candidate_key": "gdp",
                "reference_id": "base-decimal",
                "axes": {"Country": "A", "Year": 2026},
                "value": 9.87654999,
            },
            {
                "candidate_key": "gdp",
                "reference_id": "base-integer",
                "axes": {"Country": "B", "Year": 2026},
                "value": 8.0000001,
            },
        ],
        [candidate],
        registry=real_registry,
    )
    assert index.lookup("gdp", {"Country": "A", "Year": 2026}).value == 9.87654
    integer_basecase_value = index.lookup("gdp", {"Country": "B", "Year": 2026}).value
    assert integer_basecase_value == 8
    assert isinstance(integer_basecase_value, int)


def test_reference_load_policy_applies_configured_precision_to_basecase(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, _ = real_domain
    policy = ReferenceLoadPolicy(
        value_max_decimal_places=2,
        value_precision_mode="round",
    )
    candidate = {
        "candidate_key": "gdp",
        "canonical_parameter_name": "GDP",
        "basecase_read_mode": "fixed_columns",
        "basecase_column_roles": "A:Country,B:Year,C:GDP",
    }

    index = build_basecase_index(
        [
            {
                "candidate_key": "gdp",
                "reference_id": "base-policy",
                "axes": {"Country": "A", "Year": 2026},
                "value": 1.23678,
            },
        ],
        [candidate],
        policy=policy,
        registry=registry,
    )

    assert index.policy is policy
    assert index.lookup("gdp", {"Country": "A", "Year": 2026}).value == 1.24


def test_numeric_precision_applies_to_negative_values_and_serializes_zero_as_int() -> None:
    assert truncate_numeric_value(1.234569, label="positive", max_decimal_places=5) == 1.23456
    assert truncate_numeric_value(-1.234569, label="negative", max_decimal_places=5) == -1.23456
    assert normalize_numeric_value(-1.234569, label="negative LUT", max_decimal_places=5) == -1.23457
    assert (
        apply_numeric_precision(
            -1.234569,
            label="configured trunc",
            max_decimal_places=5,
            mode="trunc",
        )
        == -1.23456
    )
    assert (
        apply_numeric_precision(
            -1.234569,
            label="configured round",
            max_decimal_places=5,
            mode="round",
        )
        == -1.23457
    )
    assert ceil_numeric_value(1.234561, label="positive ceil", max_decimal_places=5) == 1.23457
    assert ceil_numeric_value(-1.234561, label="negative ceil", max_decimal_places=5) == -1.23456
    assert normalize_numeric_value(1.234565, label="positive half", max_decimal_places=5) == 1.23457
    assert normalize_numeric_value(-1.234565, label="negative half", max_decimal_places=5) == -1.23457
    for mode in ("trunc", "ceil", "round"):
        assert (
            apply_numeric_precision(
                -1.23456789,
                label=f"disabled {mode}",
                max_decimal_places=-1,
                mode=mode,
            )
            == -1.23456789
        )
    assert (
        truncate_numeric_value(
            Decimal("1.234569999999999999"),
            label="decimal",
            max_decimal_places=5,
        )
        == 1.23456
    )
    integer_value = truncate_numeric_value(8.0000001, label="integer", max_decimal_places=5)
    assert integer_value == 8
    assert isinstance(integer_value, int)
    zero_value = truncate_numeric_value(0.0, label="zero", max_decimal_places=5)
    assert zero_value == 0
    assert isinstance(zero_value, int)


def test_reference_load_policy_applies_configured_precision_to_lut(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("values.csv", metadata_axes="[Tag]"),
    )
    _write(
        tmp_path / "values.csv",
        "Country,Year,Tag,Value\nA,2026,x,-1.23456789\n",
    )
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)

    truncate_catalog = get_lut_catalog(
        ReferenceLoadPolicy(
            2026,
            2026,
            value_max_decimal_places=3,
            value_precision_mode="trunc",
        ),
        registry=registry,
    )
    assert truncate_catalog.lookup("TestParameter", {"Country": "A", "Year": 2026}).value == -1.234

    round_catalog = get_lut_catalog(
        ReferenceLoadPolicy(
            2026,
            2026,
            value_max_decimal_places=3,
            value_precision_mode="round",
        ),
        registry=registry,
    )
    assert round_catalog.lookup("TestParameter", {"Country": "A", "Year": 2026}).value == -1.235


def test_metadata_axes_enable_non_time_basecase_metadata_fallback(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        _tabular_config("values.csv", metadata_axes="[Tag]"),
    )
    _write(
        tmp_path / "values.csv",
        "Country,Year,Tag,Value\nA,2026,lut-tag,0.5\nA,2027,lut-tag,1.0\n",
    )
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    policy = ReferenceLoadPolicy(2026, 2027)
    catalog = get_lut_catalog(policy, registry=registry)
    candidate = {
        "candidate_key": "custom",
        "canonical_parameter_name": "TestParameter",
        "basecase_read_mode": "fixed_columns",
        "basecase_column_roles": "A:Country,B:Year,C:Tag,D:TestParameter",
    }
    index = build_basecase_index(
        [
            {
                "candidate_key": "custom",
                "reference_id": "base-other-year",
                "axes": {"Country": "A", "Year": 2026, "Tag": "base-tag"},
                "value": None,
            },
        ],
        [candidate],
        policy=policy,
        registry=registry,
    )

    effective = resolve_effective_reference(
        "custom",
        {"Country": "A", "Year": 2027},
        index,
        catalog,
    )

    assert effective is not None
    assert effective.actual_basecase_value is None
    assert effective.llm_reference_value == 1
    assert effective.metadata["Tag"] == "base-tag"
    assert "basecase_non_time_axes_with_lut_value" in effective.diagnostics


def test_basecase_index_isolates_candidates_and_resolves_all_source_modes(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    candidates = [
        {
            "candidate_key": "gdp-a",
            "canonical_parameter_name": "GDP",
            "basecase_read_mode": "fixed_columns",
            "basecase_column_roles": "A:Country,B:Year,C:GDP",
        },
        {
            "candidate_key": "gdp-b",
            "canonical_parameter_name": "GDP",
            "basecase_read_mode": "fixed_columns",
            "basecase_column_roles": "A:Country,B:Year,C:GDP",
        },
    ]
    basecase_records = [
        {
            "candidate_key": "gdp-a",
            "reference_id": "base-a-china",
            "axes": {"Country": "China", "Year": 2026},
            "value": 9.0,
        },
        {
            "candidate_key": "gdp-a",
            "reference_id": "base-a-only",
            "axes": {"Country": "Basecase Only", "Year": 2026},
            "value": 1.5,
        },
        {
            "candidate_key": "gdp-b",
            "reference_id": "base-b-china",
            "axes": {"Country": "China", "Year": 2026},
            "value": 8.0,
        },
    ]
    index = build_basecase_index(
        basecase_records,
        candidates,
        registry=registry,
    )
    assert index.lookup("gdp-a", {"Country": "China", "Year": 2026}).value == 9.0
    assert index.lookup("gdp-b", {"Country": "China", "Year": 2026}).value == 8.0

    source_off = resolve_effective_reference(
        "gdp-a",
        {"Country": "China", "Year": 2026},
        index,
    )
    assert source_off is not None
    assert source_off.actual_basecase_value == 9.0
    assert source_off.lut_default_value is None
    assert source_off.lut_version is None
    assert (
        resolve_effective_reference(
            "gdp-a",
            {"Country": "Japan", "Year": 2026},
            index,
        )
        is None
    )

    override = resolve_effective_reference(
        "gdp-a",
        {"Country": "China", "Year": 2026},
        index,
        catalog,
    )
    assert override is not None
    assert override.actual_basecase_value == 9.0
    assert override.lut_default_value is not None
    assert override.llm_reference_value == 9.0
    assert override.effective_source == "basecase"

    lut_only = resolve_effective_reference(
        "gdp-a",
        {"Country": "Japan", "Year": 2026},
        index,
        catalog,
    )
    assert lut_only is not None
    assert lut_only.actual_basecase_value is None
    assert lut_only.llm_reference_value == lut_only.lut_default_value
    assert lut_only.effective_source == "lut"

    basecase_only = resolve_effective_reference(
        "gdp-a",
        {"Country": "Basecase Only", "Year": 2026},
        index,
        catalog,
    )
    assert basecase_only is not None
    assert basecase_only.actual_basecase_value == 1.5
    assert basecase_only.lut_default_value is None
    assert (
        resolve_effective_reference(
            "gdp-a",
            {"Country": "Exact Miss", "Year": 2026},
            index,
            catalog,
        )
        is None
    )


def test_unregistered_parameter_preserves_all_actual_axes_without_metadata(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, _ = real_domain
    candidate = {
        "candidate_key": "custom",
        "canonical_parameter_name": "CustomAdjustment",
        "basecase_read_mode": "fixed_columns",
        "basecase_column_roles": "A:Country,B:Period,C:CustomAdjustment",
    }
    assert canonical_axes_for_candidate(candidate, registry=registry) == ("Country", "Period")
    index = build_basecase_index(
        [
            {
                "candidate_key": "custom",
                "reference_id": "custom-1",
                "axes": {"Country": "A", "Period": 99},
                "value": 2,
            },
        ],
        [candidate],
        registry=registry,
    )
    assert index.candidate_key_axes["custom"] == ("Country", "Period")
    assert index.candidate_metadata_axes["custom"] == ()
    assert index.lookup("custom", {"Country": "A", "Period": 99}) is not None


def test_compact_slot_catalog_preserves_leaf_specific_periods_and_exact_membership(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    candidates = [
        {
            "candidate_key": "liq",
            "canonical_parameter_name": "LiqUtilAdjustment",
            "basecase_read_mode": "matrix_time_columns",
            "basecase_column_roles": (
                "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)"
            ),
        },
    ]
    index = build_basecase_index([], candidates, registry=registry)
    slot_catalog = build_slot_catalog(index, catalog)
    candidate_catalog = slot_catalog.for_candidate("liq")
    assert candidate_catalog is not None
    assert candidate_catalog.time_axes == ("Year", "Month")
    assert candidate_catalog.non_time_axes == ("Country", "LNG Plant", "LNG Plant Train")
    assert len(candidate_catalog.leaves) == 347

    all_periods = {(year, month) for year in range(2026, 2031) for month in range(1, 13)}
    partial_leaf = next(leaf for leaf in candidate_catalog.leaves if len(leaf.available_periods) < len(all_periods))
    available = {(period.values["Year"], period.values["Month"]) for period in partial_leaf.available_periods}
    existing_year, existing_month = next(iter(available))
    missing_year, missing_month = next(iter(all_periods - available))
    assert slot_catalog.contains(
        "liq",
        {**partial_leaf.axes, "Year": existing_year, "Month": existing_month},
    )
    assert not slot_catalog.contains(
        "liq",
        {**partial_leaf.axes, "Year": missing_year, "Month": missing_month},
    )


def test_slot_catalog_excludes_value_less_basecase_without_exact_lut_but_keeps_metadata(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    candidate = {
        "candidate_key": "liq",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "basecase_read_mode": "matrix_time_columns",
        "basecase_column_roles": (
            "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)"
        ),
    }
    axes = {
        "Country": "No Value Country",
        "LNG Plant": "No Value Plant",
        "LNG Plant Train": "No Value Train",
        "Year": 2026,
        "Month": 7,
        "Period": 1,
        "Life Cycle Category": "Operating",
        "Nameplate Capacity (MTPA)": 6.599999,
    }
    index = build_basecase_index(
        [
            {
                "candidate_key": "liq",
                "reference_id": "base-metadata-only",
                "axes": axes,
                "value": None,
            },
        ],
        [candidate],
        registry=registry,
    )

    indexed = index.lookup("liq", axes)
    assert indexed is not None
    assert indexed.value is None
    assert indexed.metadata["Nameplate Capacity (MTPA)"] == 6.599999
    assert catalog.lookup("LiqUtilAdjustment", axes) is None
    assert not build_slot_catalog(index).contains("liq", axes)
    assert not build_slot_catalog(index, catalog).contains("liq", axes)
    assert resolve_effective_reference("liq", axes, index, catalog) is None


def test_liq_metadata_uses_exact_basecase_values_when_override_exists(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    lut_record = catalog.records_for_parameter("LiqUtilAdjustment")[0]
    candidate = {
        "candidate_key": "liq",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "basecase_read_mode": "matrix_time_columns",
        "basecase_column_roles": (
            "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)"
        ),
    }
    basecase_axes = {
        **lut_record.axes,
        "Period": 999,
        "Life Cycle Category": "Basecase Lifecycle",
        "Nameplate Capacity (MTPA)": 77.7,
    }
    index = build_basecase_index(
        [
            {
                "candidate_key": "liq",
                "reference_id": "base-liq",
                "axes": basecase_axes,
                "value": 0.42,
            },
        ],
        [candidate],
        registry=registry,
    )
    effective = resolve_effective_reference("liq", lut_record.axes, index, catalog)
    assert effective is not None
    assert dict(effective.metadata) == {
        "Period": 999,
        "Life Cycle Category": "Basecase Lifecycle",
        "Nameplate Capacity (MTPA)": 77.7,
    }
    assert effective.actual_basecase_value == 0.42
    assert effective.lut_default_value == lut_record.value


def test_liq_metadata_uses_basecase_non_time_axes_before_lut_metadata(
    real_domain: tuple[ParameterSpecRegistry, LutCatalog],
) -> None:
    registry, catalog = real_domain
    target_axes = {
        "Country": "Russia",
        "LNG Plant": "Arctic LNG 2",
        "LNG Plant Train": "Arctic LNG 2 T3",
        "Year": 2026,
        "Month": 7,
    }
    lut_record = catalog.lookup("LiqUtilAdjustment", target_axes)
    assert lut_record is not None
    assert lut_record.metadata["Nameplate Capacity (MTPA)"] == 6.59
    candidate = {
        "candidate_key": "liq",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "basecase_read_mode": "matrix_time_columns",
        "basecase_column_roles": (
            "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)"
        ),
    }
    basecase_index = build_basecase_index(
        [
            {
                "candidate_key": "liq",
                "reference_id": "base-arctic-t3-other-period",
                "axes": {
                    **target_axes,
                    "Month": 6,
                    "Period": 102,
                    "Life Cycle Category": "Under Construction",
                    "Nameplate Capacity (MTPA)": 6.599999,
                },
                "value": None,
            },
        ],
        [candidate],
        registry=registry,
    )
    slot_catalog = build_slot_catalog(basecase_index, catalog)

    effective = resolve_effective_reference("liq", target_axes, basecase_index, catalog)

    assert slot_catalog.contains("liq", target_axes)
    candidate_catalog = slot_catalog.for_candidate("liq")
    assert candidate_catalog is not None
    target_leaf = next(
        leaf
        for leaf in candidate_catalog.leaves
        if all(leaf.axes[axis_name] == target_axes[axis_name] for axis_name in candidate_catalog.non_time_axes)
    )
    assert target_leaf.applicability_attributes == {
        "Life Cycle Category": ("Under Construction",),
    }
    assert effective is not None
    assert effective.actual_basecase_value is None
    assert effective.lut_default_value == lut_record.value
    assert effective.llm_reference_value == lut_record.value
    assert effective.effective_source == "lut"
    assert effective.basecase_reference_id == "base-arctic-t3-other-period"
    assert effective.metadata["Period"] == lut_record.metadata["Period"]
    assert effective.metadata["Life Cycle Category"] == "Under Construction"
    assert effective.metadata["Nameplate Capacity (MTPA)"] == 6.599999
    assert "basecase_non_time_axes_with_lut_value" in effective.diagnostics

    lut_only_index = build_basecase_index([], [candidate], registry=registry)
    lut_only = resolve_effective_reference("liq", target_axes, lut_only_index, catalog)
    assert lut_only is not None
    assert lut_only.basecase_reference_id is None
    assert lut_only.metadata["Nameplate Capacity (MTPA)"] == 6.59
    assert "lut_only" in lut_only.diagnostics


def test_gdp_requires_exact_previous_year_in_source(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
GDP:
  adapter: gdp_growth
  files:
    values:
      path: gdp.csv
      required_columns: [Country, Year, GDP]
  key_axes: [Country, Year]
""",
    )
    gdp_header = (
        "RE Base Case GDP and Population Data_Country,"
        "RE Base Case GDP and Population Data_Year,"
        "RE Base Case GDP and Population Data_GDP"
    )
    _write(
        tmp_path / "gdp.csv",
        f"{gdp_header}\nA,2025,100\nA,2026,110\nA,2026,110\nA,2028,140\n",
    )
    # The adapter intentionally requires the production canonical headers, so the
    # fixture spec must declare those exact headers too.
    _write(
        config,
        """\
GDP:
  adapter: gdp_growth
  files:
    values:
      path: gdp.csv
      required_columns:
        - RE Base Case GDP and Population Data_Country
        - RE Base Case GDP and Population Data_Year
        - RE Base Case GDP and Population Data_GDP
  key_axes: [Country, Year]
""",
    )
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match=r"missing_years=\[2027, 2028\]"):
        get_lut_catalog(ReferenceLoadPolicy(2026, 2028), registry=registry)
    catalog = get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
    assert len(catalog.records) == 1
    assert any("deduped_identical_lut_source_key" in diagnostic for diagnostic in catalog.diagnostics)
    assert catalog.lookup("GDP", {"Country": "A", "Year": 2026}).value == pytest.approx(0.1)
    assert catalog.lookup("GDP", {"Country": "A", "Year": 2028}) is None


def test_liq_adapter_excludes_closed_case_insensitively_and_converts_capacity(
    tmp_path: Path,
) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
LiqUtilAdjustment:
  adapter: liq_util
  files:
    values:
      path: liq.csv
      required_columns:
        - Country
        - Plant Name
        - Plant Train
        - Year
        - Month
        - Period
        - Infra Life Cycle
        - LNG train capacity (Million tonnes LNG per month)
        - LNG plant utilisation %
  key_axes: [Country, LNG Plant, LNG Plant Train, Year, Month]
  metadata_axes: [Period, Life Cycle Category, Nameplate Capacity (MTPA)]
""",
    )
    header = [
        "Country",
        "Plant Name",
        "Plant Train",
        "Year",
        "Month",
        "Period",
        "Infra Life Cycle",
        "LNG train capacity (Million tonnes LNG per month)",
        "LNG plant utilisation %",
    ]
    rows = [
        ["A", "P", "T1", 2026, 1, 1, "cLoSeD", 1, 0.1],
        ["A", "P", "T2", 2026, 1, 1, "Operational", 1, 0.2],
    ]
    with (tmp_path / "liq.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    catalog = get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
    assert len(catalog.records) == 1
    assert catalog.records[0].axes["LNG Plant Train"] == "T2"
    assert catalog.records[0].metadata["Nameplate Capacity (MTPA)"] == 12
    assert isinstance(catalog.records[0].metadata["Nameplate Capacity (MTPA)"], int)


def test_liq_prod_adapter_excludes_closed_and_multiplies_capacity_by_utilisation(
    tmp_path: Path,
) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
LiqProdAdjustment:
  adapter: liq_prod
  files:
    values:
      path: liq.csv
      required_columns:
        - Country
        - Plant Name
        - Plant Train
        - Year
        - Month
        - Period
        - Infra Life Cycle
        - LNG train capacity (Million tonnes LNG per month)
        - LNG plant utilisation %
  key_axes: [Country, LNG Plant, LNG Plant Train, Year, Month]
  metadata_axes: [Period, Life Cycle Category, Nameplate Capacity (MTPA)]
""",
    )
    _write(
        tmp_path / "liq.csv",
        "Country,Plant Name,Plant Train,Year,Month,Period,Infra Life Cycle,"
        "LNG train capacity (Million tonnes LNG per month),LNG plant utilisation %\n"
        "A,P,T1,2026,1,1,Closed,99,1\n"
        "A,P,T2,2026,1,2,Operational,1.25,0.4\n",
    )
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    catalog = get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
    assert len(catalog.records) == 1
    assert catalog.records[0].axes["LNG Plant Train"] == "T2"
    assert catalog.records[0].value == 0.5
    assert catalog.records[0].metadata["Nameplate Capacity (MTPA)"] == 15


def test_hurricane_adapter_validates_all_declared_numeric_fields(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
HurricaneIntensity:
  adapter: hurricane_intensity
  files:
    intensity:
      path: intensity.csv
      required_columns:
        - Intensity
        - Pre-hurricane upstream production shut-in duration (No. of weeks in a month)
        - Pre-hurricane upstream production shut-in volume (% of total monthly volume)
        - During and post-hurricane upstream production shut-in duration (No. of weeks in a month)
        - During and post-hurricane upstream production shut-in volume (% of total monthly volume)
        - Net impact (Monthly upstream production decrease by %)
    plants:
      path: plants.csv
      required_columns:
        - Liquefaction plants impacted by a hurricane in GoM
        - Impacted by hurricane?
  key_axes: [Year, Month]
""",
    )
    header = [
        "Intensity",
        "Pre-hurricane upstream production shut-in duration (No. of weeks in a month)",
        "Pre-hurricane upstream production shut-in volume (% of total monthly volume)",
        "During and post-hurricane upstream production shut-in duration (No. of weeks in a month)",
        "During and post-hurricane upstream production shut-in volume (% of total monthly volume)",
        "Net impact (Monthly upstream production decrease by %)",
    ]
    valid_rows = [
        [1, "0 weeks", 0, "0 weeks", 0, 0],
        [2, "0 weeks", 0, "1 week", 0.2, 0.05],
        [3, "1 week", 0.5, "2 weeks", 0.5, 0.375],
        [4, "1 week", 0.9, "3 weeks", 0.9, 0.9],
    ]
    _write(
        tmp_path / "plants.csv",
        "Liquefaction plants impacted by a hurricane in GoM,Impacted by hurricane?\nPlant A,Yes\n",
    )
    invalid_cases = (
        (1, "", "week"),
        (2, 1.1, "between 0 and 1"),
        (3, "six weeks", "finite number"),
        (4, -0.1, "between 0 and 1"),
    )
    for column_index, invalid_value, expected_message in invalid_cases:
        rows = [list(row) for row in valid_rows]
        rows[0][column_index] = invalid_value
        with (tmp_path / "intensity.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        clear_lut_runtime_cache()
        registry = get_parameter_spec_registry(config, lut_root=tmp_path)
        with pytest.raises(MIBaseError, match=expected_message):
            get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)


def test_pmi_adapter_requires_complete_exact_reference_country_join(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
PMI:
  adapter: pmi_reference
  files:
    references:
      path: references.csv
      required_columns:
        - Selection of PMI Reference Country_Demand Location_Country
        - Selection of PMI Reference Country_Reference Country_Country
        - Selection of PMI Reference Country_Base Case Reference Country_Country
    values:
      path: values.csv
      required_columns:
        - Base Case PMI Input (do not change)_Country
        - Base Case PMI Input (do not change)_Month
        - Base Case PMI Input (do not change)_{year}.0
  key_axes: [Country, Year, Month]
""",
    )
    reference_header = (
        "Selection of PMI Reference Country_Demand Location_Country,"
        "Selection of PMI Reference Country_Reference Country_Country,"
        "Selection of PMI Reference Country_Base Case Reference Country_Country\n"
    )
    references = _write(tmp_path / "references.csv", reference_header + "Demand,Missing,Missing\n")
    values_header = (
        "Base Case PMI Input (do not change)_Country,"
        "Base Case PMI Input (do not change)_Month,"
        "Base Case PMI Input (do not change)_2026.0\n"
    )
    _write(
        tmp_path / "values.csv",
        values_header + "".join(f"Reference,{month},50\n" for month in range(1, 13)),
    )
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match="join is missing an exact value"):
        get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)

    _write(references, reference_header + "Demand,Reference,Reference\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    catalog = get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
    assert len(catalog.records) == 12
    january = catalog.lookup("PMI", {"Country": "Demand", "Year": 2026, "Month": 1})
    assert january is not None
    assert january.value == 50
    assert january.diagnostics == ("pmi_reference_country=Reference",)


def test_supply_disruption_aggregates_signed_rows_without_renormalizing_seasonality(
    tmp_path: Path,
) -> None:
    config = _write(
        tmp_path / "config.yaml",
        """\
SupplyDisruption:
  adapter: supply_disruption
  files:
    production:
      path: production.csv
      required_columns:
        - Year
        - Life Cycle Category
        - Country
        - Province/Basin
        - Oil and gas detail
        - Base case supply (Bcm)
    seasonality:
      path: seasonality.csv
      required_columns: [Year, Month, Period, Province, PNG/LNG, Seasonality]
  key_axes: [Country, Year, Month]
""",
    )
    production = _write(
        tmp_path / "production.csv",
        "Year,Life Cycle Category,Country,Province/Basin,Oil and gas detail,Base case supply (Bcm)\n"
        "2026,Operational,Mexico,GoM,Feed gas to LNG,10\n"
        "2026,Operational,Mexico,GoM,Feed gas to LNG,-2\n"
        "2026,cLoSeD,Mexico,GoM,Feed gas to LNG,1000\n",
    )
    seasonality_header = "Year,Month,Period,Province,PNG/LNG,Seasonality\n"
    seasonality_rows = "".join(
        f"2026,{month},{month},GoM,Feed gas to LNG,{0.25 if month == 1 else 0.1}\n" for month in range(1, 13)
    )
    seasonality = _write(tmp_path / "seasonality.csv", seasonality_header + seasonality_rows)
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    catalog = get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
    assert len(catalog.records) == 12
    january = catalog.lookup(
        "SupplyDisruption",
        {"Country": "Mexico", "Year": 2026, "Month": 1},
    )
    assert january is not None
    assert january.value == 2
    assert january.diagnostics == (
        "seasonality_policy=raw_not_renormalized",
        "aggregated_production_rows=2",
    )

    _write(seasonality, seasonality_header + seasonality_rows.rsplit("\n", 2)[0] + "\n")
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match="join is missing exact rows"):
        get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)

    _write(
        seasonality,
        seasonality_header + seasonality_rows.replace("2026,1,1,", "2026,1,,", 1),
    )
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(MIBaseError, match=r"Period.*finite number"):
        get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)

    _write(seasonality, seasonality_header + seasonality_rows)
    _write(
        production,
        "Year,Life Cycle Category,Country,Province/Basin,Oil and gas detail,Base case supply (Bcm)\n"
        "2026,Operational,Mexico,GoM,Feed gas to LNG,1\n"
        "2026,Operational,Mexico,GoM,Feed gas to LNG,-2\n",
    )
    clear_lut_runtime_cache()
    registry = get_parameter_spec_registry(config, lut_root=tmp_path)
    with pytest.raises(
        MIBaseError,
        match="aggregated monthly supply must be non-negative",
    ):
        get_lut_catalog(ReferenceLoadPolicy(2026, 2026), registry=registry)
