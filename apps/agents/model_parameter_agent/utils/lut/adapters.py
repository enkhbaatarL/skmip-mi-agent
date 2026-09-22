# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

from collections.abc import Callable, Mapping
import csv
from dataclasses import dataclass
from datetime import datetime
import io

from apps.agents.model_parameter_agent.utils.lut.keys import (
    apply_numeric_precision,
    canonical_axis_value,
    canonical_key_from_axes,
    strict_float,
    strict_int,
    truncate_numeric_value,
)
from apps.agents.model_parameter_agent.utils.lut.models import (
    CanonicalKey,
    CanonicalValue,
    LutRecord,
    NumericValue,
    ReferenceLoadPolicy,
    domain_error,
    freeze_mapping,
)
from apps.agents.model_parameter_agent.utils.lut.registry import (
    LutFileSpec,
    ParameterLutSpec,
)


ADAPTER_SCHEMA_VERSION = "model-parameter-lut-adapters-v3"
TEMPERATURE_BASE = 18.0
DEGREE_DAY_DIVISOR = 30.0
MTPM_TO_MTPA = 12.0
BCM_TO_MT_LNG = 0.735
LUT_NAMEPLATE_MAX_DECIMAL_PLACES = 2

GDP_POPULATION_COUNTRY_COLUMN = "RE Base Case GDP and Population Data_Country"
GDP_POPULATION_YEAR_COLUMN = "RE Base Case GDP and Population Data_Year"
GDP_VALUE_COLUMN = "RE Base Case GDP and Population Data_GDP"
POPULATION_VALUE_COLUMN = "RE Base Case GDP and Population Data_Population (thousands)"

PMI_DEMAND_COUNTRY_COLUMN = "Selection of PMI Reference Country_Demand Location_Country"
PMI_REFERENCE_COUNTRY_COLUMN = "Selection of PMI Reference Country_Reference Country_Country"
PMI_BASE_REFERENCE_COUNTRY_COLUMN = "Selection of PMI Reference Country_Base Case Reference Country_Country"
PMI_VALUE_COUNTRY_COLUMN = "Base Case PMI Input (do not change)_Country"
PMI_VALUE_MONTH_COLUMN = "Base Case PMI Input (do not change)_Month"
PMI_VALUE_YEAR_PREFIX = "Base Case PMI Input (do not change)_"

FUTURES_DATE_COLUMN = "Futures pricing_Date"
FUTURES_MARKET_COLUMNS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "Coal Futures Price": (
        ("Europe", "Futures pricing_Rotterdam Coal"),
        ("Asia", "Futures pricing_Newcastle Coal"),
    ),
    "Gas Futures Price": (
        ("Europe", "Futures pricing_TTF"),
        ("Asia", "Futures pricing_JKM"),
    ),
}

HURRICANE_PRE_DURATION_COLUMN = "Pre-hurricane upstream production shut-in duration (No. of weeks in a month)"
HURRICANE_PRE_VOLUME_COLUMN = "Pre-hurricane upstream production shut-in volume (% of total monthly volume)"
HURRICANE_POST_DURATION_COLUMN = (
    "During and post-hurricane upstream production shut-in duration (No. of weeks in a month)"
)
HURRICANE_POST_VOLUME_COLUMN = (
    "During and post-hurricane upstream production shut-in volume (% of total monthly volume)"
)


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    path: str
    content: bytes
    sha256: str


def _expanded_column(template: str, year: int) -> str:
    try:
        return template.format(year=year)
    except (KeyError, ValueError) as exc:
        msg = f"invalid LUT year column template {template!r}: {exc}"
        raise domain_error(msg) from exc


def _hurricane_duration_weeks(value: object, *, label: str) -> float:
    text = str(value or "").strip()
    parts = text.split()
    if len(parts) != 2 or parts[1].casefold() not in {"week", "weeks"}:
        msg = f"{label} must use '<number> week(s)' format: {value!r}"
        raise domain_error(msg)
    weeks = strict_float(parts[0], label=label)
    if not 0 <= weeks <= 5:
        msg = f"{label} must be between 0 and 5 weeks: {value!r}"
        raise domain_error(msg)
    return weeks


def _fraction(value: object, *, label: str) -> float:
    fraction = strict_float(value, label=label)
    if not 0 <= fraction <= 1:
        msg = f"{label} must be between 0 and 1: {value!r}"
        raise domain_error(msg)
    return fraction


def _required_headers(file_spec: LutFileSpec, policy: ReferenceLoadPolicy) -> set[str]:
    required: set[str] = set()
    for column in file_spec.required_columns:
        if "{year}" in column:
            required.update(_expanded_column(column, year) for year in policy.years)
        else:
            required.add(column)
    required.update(file_spec.axis_columns.values())
    if file_spec.value_column:
        required.add(file_spec.value_column)
    if file_spec.year_value_column:
        required.update(_expanded_column(file_spec.year_value_column, year) for year in policy.years)
    return required


def _read_rows(
    file_spec: LutFileSpec,
    snapshot: FileSnapshot,
    policy: ReferenceLoadPolicy,
) -> list[tuple[int, dict[str, str]]]:
    try:
        text = snapshot.content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        msg = f"LUT CSV is not UTF-8: {file_spec.relative_path}"
        raise domain_error(msg) from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fieldnames = reader.fieldnames
    if not fieldnames:
        msg = f"LUT CSV has no header: {file_spec.relative_path}"
        raise domain_error(msg)
    if len(fieldnames) != len(set(fieldnames)):
        msg = f"LUT CSV contains duplicate headers: {file_spec.relative_path}"
        raise domain_error(msg)
    missing = sorted(_required_headers(file_spec, policy) - set(fieldnames))
    if missing:
        raise domain_error(
            f"LUT CSV is missing required headers in {file_spec.relative_path}: " + ", ".join(missing),
        )
    rows: list[tuple[int, dict[str, str]]] = []
    for row in reader:
        if None in row:
            msg = f"LUT CSV row has more values than headers in {file_spec.relative_path}:{reader.line_num}"
            raise domain_error(
                msg,
            )
        rows.append((reader.line_num, row))
    return rows


def validate_file_structure(
    file_spec: LutFileSpec,
    snapshot: FileSnapshot,
    policy: ReferenceLoadPolicy,
) -> None:
    """Validate UTF-8 CSV shape and configured headers without building catalog records."""
    _read_rows(file_spec, snapshot, policy)


def _reference_id(file_spec: LutFileSpec, line_number: int) -> str:
    return f"lut:{file_spec.relative_path}:row:{line_number}"


def _record(
    spec: ParameterLutSpec,
    *,
    policy: ReferenceLoadPolicy,
    axes: Mapping[str, CanonicalValue],
    value: NumericValue,
    metadata: Mapping[str, CanonicalValue] | None,
    reference_id: str,
    diagnostics: tuple[str, ...] = (),
) -> LutRecord:
    canonical_key = canonical_key_from_axes(axes, spec.key_axes)
    return LutRecord(
        parameter_name=spec.parameter_name,
        canonical_key=canonical_key,
        axes=freeze_mapping(axes),
        value=apply_numeric_precision(
            value,
            label=f"{spec.parameter_name} LUT value",
            max_decimal_places=policy.value_max_decimal_places,
            mode=policy.value_precision_mode,
        ),
        metadata=freeze_mapping(metadata),
        reference_id=reference_id,
        diagnostics=diagnostics,
    )


def _tabular_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    records: list[LutRecord] = []
    for line_number, row in rows:
        base_axes = {
            axis_name: canonical_axis_value(axis_name, row[column_name])
            for axis_name, column_name in file_spec.axis_columns.items()
        }
        month = base_axes.get("Month")
        if isinstance(month, int) and not 1 <= month <= 12:
            msg = f"Month must be between 1 and 12: {file_spec.relative_path}:{line_number}"
            raise domain_error(
                msg,
            )
        if spec.layout == "row":
            year = base_axes.get("Year")
            if not isinstance(year, int):
                msg = f"row LUT requires an integer Year axis: {file_spec.relative_path}:{line_number}"
                raise domain_error(msg)
            if not policy.contains_year(year):
                continue
            value_column = file_spec.value_column
            if value_column is None:
                msg = "row LUT value_column is not configured"
                raise domain_error(msg)
            records.append(
                _record(
                    spec,
                    policy=policy,
                    axes=base_axes,
                    value=strict_float(
                        row[value_column],
                        label=f"{file_spec.relative_path}:{line_number}:{value_column}",
                    ),
                    metadata={
                        axis_name: base_axes[axis_name] for axis_name in spec.metadata_axes if axis_name in base_axes
                    },
                    reference_id=_reference_id(file_spec, line_number),
                ),
            )
            continue

        year_template = file_spec.year_value_column
        if year_template is None:
            msg = "year_columns LUT year_value_column is not configured"
            raise domain_error(msg)
        for year in policy.years:
            axes = {**base_axes, "Year": year}
            value_column = _expanded_column(year_template, year)
            records.append(
                _record(
                    spec,
                    policy=policy,
                    axes=axes,
                    value=strict_float(
                        row[value_column],
                        label=f"{file_spec.relative_path}:{line_number}:{value_column}",
                    ),
                    metadata={axis_name: axes[axis_name] for axis_name in spec.metadata_axes if axis_name in axes},
                    reference_id=f"{_reference_id(file_spec, line_number)}:year:{year}",
                ),
            )
    return records


def _put_exact_source_value(
    values: dict[CanonicalKey, float],
    key: CanonicalKey,
    value: float,
    *,
    label: str,
) -> bool:
    previous = values.get(key)
    if previous is None:
        values[key] = value
        return False
    if previous != value:
        msg = f"conflicting duplicate LUT source key in {label}: {key!r}"
        raise domain_error(msg)
    return True


def _gdp_growth_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Country", "Year"):
        msg = "gdp_growth adapter key_axes must be [Country, Year]"
        raise domain_error(msg)
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    country_column = GDP_POPULATION_COUNTRY_COLUMN
    year_column = GDP_POPULATION_YEAR_COLUMN
    value_column = GDP_VALUE_COLUMN
    values: dict[CanonicalKey, float] = {}
    references: dict[CanonicalKey, str] = {}
    duplicate_keys: set[CanonicalKey] = set()
    for line_number, row in rows:
        country = canonical_axis_value("Country", row[country_column])
        year = strict_int(row[year_column], label=f"{file_spec.relative_path}:{line_number}:{year_column}")
        gdp = strict_float(row[value_column], label=f"{file_spec.relative_path}:{line_number}:{value_column}")
        key = (country, year)
        if _put_exact_source_value(values, key, gdp, label=file_spec.relative_path):
            duplicate_keys.add(key)
        references.setdefault(key, _reference_id(file_spec, line_number))

    records: list[LutRecord] = []
    countries = sorted({key[0] for key in values}, key=str)
    for country in countries:
        for year in policy.years:
            current = values.get((country, year))
            previous = values.get((country, year - 1))
            if current is None or previous is None or previous <= 0:
                continue
            diagnostics = [f"exact_year_minus_one={year - 1}"]
            if (country, year) in duplicate_keys or (country, year - 1) in duplicate_keys:
                diagnostics.append(
                    f"deduped_identical_lut_source_key={file_spec.relative_path}:{country}:{year}",
                )
            records.append(
                _record(
                    spec,
                    policy=policy,
                    axes={"Country": country, "Year": year},
                    value=current / previous - 1.0,
                    metadata=None,
                    reference_id=references[(country, year)],
                    diagnostics=tuple(diagnostics),
                ),
            )
    return records


def _futures_price_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Month-Year", "Region"):
        msg = "futures_price adapter key_axes must be [Month-Year, Region]"
        raise domain_error(msg)
    market_columns = FUTURES_MARKET_COLUMNS.get(spec.parameter_name)
    if market_columns is None:
        msg = f"futures_price adapter does not support parameter: {spec.parameter_name}"
        raise domain_error(msg)
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    records: list[LutRecord] = []
    for line_number, row in rows:
        raw_date = str(row[FUTURES_DATE_COLUMN] or "").strip()
        try:
            month = datetime.fromisoformat(raw_date)
        except ValueError as exc:
            msg = f"invalid futures month in {file_spec.relative_path}:{line_number}: {raw_date!r}"
            raise domain_error(msg) from exc
        if month.day != 1:
            msg = f"futures month must use the first day in {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if not policy.contains_year(month.year):
            continue
        month_year = month.strftime("%b %Y")
        for region, value_column in market_columns:
            records.append(
                _record(
                    spec,
                    policy=policy,
                    axes={"Month-Year": month_year, "Region": region},
                    value=strict_float(
                        row[value_column],
                        label=f"{file_spec.relative_path}:{line_number}:{value_column}",
                    ),
                    metadata=None,
                    reference_id=f"{_reference_id(file_spec, line_number)}:region:{region}",
                ),
            )
    return records


def _pmi_reference_records(  # noqa: C901
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Country", "Year", "Month"):
        msg = "pmi_reference adapter key_axes must be [Country, Year, Month]"
        raise domain_error(msg)

    reference_spec = spec.files["references"]
    reference_rows = _read_rows(reference_spec, snapshots["references"], policy)
    demand_to_reference: dict[str, str] = {}
    demand_reference_ids: dict[str, str] = {}
    for line_number, row in reference_rows:
        demand_country = str(canonical_axis_value("Country", row[PMI_DEMAND_COUNTRY_COLUMN]))
        reference_country = str(canonical_axis_value("Country", row[PMI_REFERENCE_COUNTRY_COLUMN]))
        base_reference_country = str(canonical_axis_value("Country", row[PMI_BASE_REFERENCE_COUNTRY_COLUMN]))
        if reference_country != base_reference_country:
            msg = (
                "PMI reference-country columns disagree in "
                f"{reference_spec.relative_path}:{line_number}: "
                f"reference={reference_country!r}, base_reference={base_reference_country!r}"
            )
            raise domain_error(msg)
        previous = demand_to_reference.get(demand_country)
        if previous is not None and previous != reference_country:
            msg = f"conflicting PMI demand-country mapping: {demand_country!r}"
            raise domain_error(msg)
        demand_to_reference[demand_country] = reference_country
        demand_reference_ids.setdefault(demand_country, _reference_id(reference_spec, line_number))

    value_spec = spec.files["values"]
    value_rows = _read_rows(value_spec, snapshots["values"], policy)
    values: dict[CanonicalKey, float] = {}
    value_reference_ids: dict[CanonicalKey, str] = {}
    duplicate_keys: set[CanonicalKey] = set()
    for line_number, row in value_rows:
        reference_country = canonical_axis_value("Country", row[PMI_VALUE_COUNTRY_COLUMN])
        month = strict_int(
            row[PMI_VALUE_MONTH_COLUMN],
            label=f"{value_spec.relative_path}:{line_number}:{PMI_VALUE_MONTH_COLUMN}",
        )
        if not 1 <= month <= 12:
            msg = f"Month must be between 1 and 12: {value_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        for year in policy.years:
            value_column = f"{PMI_VALUE_YEAR_PREFIX}{year}.0"
            value = strict_float(
                row[value_column],
                label=f"{value_spec.relative_path}:{line_number}:{value_column}",
            )
            key = (reference_country, year, month)
            if _put_exact_source_value(values, key, value, label=value_spec.relative_path):
                duplicate_keys.add(key)
            value_reference_ids.setdefault(key, f"{_reference_id(value_spec, line_number)}:year:{year}")

    records: list[LutRecord] = []
    for demand_country, reference_country in sorted(demand_to_reference.items()):
        for year in policy.years:
            for month in range(1, 13):
                source_key = (reference_country, year, month)
                value = values.get(source_key)
                if value is None:
                    msg = (
                        "PMI reference-country join is missing an exact value: "
                        f"demand_country={demand_country!r}, reference_country={reference_country!r}, "
                        f"year={year}, month={month}"
                    )
                    raise domain_error(msg)
                diagnostics = [f"pmi_reference_country={reference_country}"]
                if source_key in duplicate_keys:
                    diagnostics.append(
                        f"deduped_identical_lut_source_key={value_spec.relative_path}:{source_key!r}",
                    )
                records.append(
                    _record(
                        spec,
                        policy=policy,
                        axes={"Country": demand_country, "Year": year, "Month": month},
                        value=value,
                        metadata=None,
                        reference_id=(f"{demand_reference_ids[demand_country]}|{value_reference_ids[source_key]}"),
                        diagnostics=tuple(diagnostics),
                    ),
                )
    return records


def _population_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Country", "Year"):
        msg = "population adapter key_axes must be [Country, Year]"
        raise domain_error(msg)
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    records: list[LutRecord] = []
    for line_number, row in rows:
        country = canonical_axis_value("Country", row[GDP_POPULATION_COUNTRY_COLUMN])
        year = strict_int(
            row[GDP_POPULATION_YEAR_COLUMN],
            label=f"{file_spec.relative_path}:{line_number}:{GDP_POPULATION_YEAR_COLUMN}",
        )
        population = strict_float(
            row[POPULATION_VALUE_COLUMN],
            label=f"{file_spec.relative_path}:{line_number}:{POPULATION_VALUE_COLUMN}",
        )
        if population < 0:
            msg = f"Population must be non-negative: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if not policy.contains_year(year):
            continue
        records.append(
            _record(
                spec,
                policy=policy,
                axes={"Country": country, "Year": year},
                value=population,
                metadata=None,
                reference_id=_reference_id(file_spec, line_number),
                diagnostics=("unit=thousand_people",),
            ),
        )
    return records


def _degree_day_values(
    file_spec: LutFileSpec,
    snapshot: FileSnapshot,
    policy: ReferenceLoadPolicy,
    *,
    prefix: str,
) -> tuple[dict[CanonicalKey, float], dict[CanonicalKey, str], set[CanonicalKey]]:
    rows = _read_rows(file_spec, snapshot, policy)
    values: dict[CanonicalKey, float] = {}
    references: dict[CanonicalKey, str] = {}
    duplicate_keys: set[CanonicalKey] = set()
    country_column = f"{prefix}Country"
    month_column = f"{prefix}Month"
    for line_number, row in rows:
        country = canonical_axis_value("Country", row[country_column])
        month = strict_int(row[month_column], label=f"{file_spec.relative_path}:{line_number}:{month_column}")
        if not 1 <= month <= 12:
            msg = f"Month must be between 1 and 12: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        for year in policy.years:
            value_column = f"{prefix}{year}.0"
            value = strict_float(
                row[value_column],
                label=f"{file_spec.relative_path}:{line_number}:{value_column}",
            )
            key = (country, year, month)
            if _put_exact_source_value(values, key, value, label=file_spec.relative_path):
                duplicate_keys.add(key)
            references.setdefault(key, f"{_reference_id(file_spec, line_number)}:year:{year}")
    return values, references, duplicate_keys


def _temperature_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Country", "Year", "Month"):
        msg = "temperature_degree_days adapter key_axes must be [Country, Year, Month]"
        raise domain_error(msg)
    hdd, hdd_refs, hdd_duplicate_keys = _degree_day_values(
        spec.files["hdd"],
        snapshots["hdd"],
        policy,
        prefix="Base Case HDD Input_",
    )
    cdd, cdd_refs, cdd_duplicate_keys = _degree_day_values(
        spec.files["cdd"],
        snapshots["cdd"],
        policy,
        prefix="Base Case CDD Input_",
    )
    records: list[LutRecord] = []
    for key in sorted(set(hdd) | set(cdd), key=lambda item: tuple(map(str, item))):
        hdd_value = hdd.get(key, 0.0)
        cdd_value = cdd.get(key, 0.0)
        if hdd_value > 0:
            temperature = TEMPERATURE_BASE - hdd_value / DEGREE_DAY_DIVISOR
            branch = "hdd"
            reference_id = hdd_refs[key]
        elif cdd_value > 0:
            temperature = TEMPERATURE_BASE + cdd_value / DEGREE_DAY_DIVISOR
            branch = "cdd"
            reference_id = cdd_refs[key]
        else:
            temperature = TEMPERATURE_BASE
            branch = "neutral"
            reference_id = hdd_refs.get(key) or cdd_refs[key]
        country, year, month = key
        diagnostics = [f"degree_days_branch={branch}"]
        if key in hdd_duplicate_keys or key in cdd_duplicate_keys:
            diagnostics.append(f"deduped_identical_lut_source_key=degree_days:{key!r}")
        records.append(
            _record(
                spec,
                policy=policy,
                axes={"Country": country, "Year": year, "Month": month},
                value=temperature,
                metadata=None,
                reference_id=reference_id,
                diagnostics=tuple(diagnostics),
            ),
        )
    return records


def _hurricane_intensity_records(  # noqa: C901
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Year", "Month"):
        msg = "hurricane_intensity adapter key_axes must be [Year, Month]"
        raise domain_error(msg)

    intensity_spec = spec.files["intensity"]
    intensity_rows = _read_rows(intensity_spec, snapshots["intensity"], policy)
    impacts_by_intensity: dict[int, float] = {}
    for line_number, row in intensity_rows:
        label_prefix = f"{intensity_spec.relative_path}:{line_number}"
        intensity = strict_int(
            row["Intensity"],
            label=f"{label_prefix}:Intensity",
        )
        _hurricane_duration_weeks(
            row[HURRICANE_PRE_DURATION_COLUMN],
            label=f"{label_prefix}:{HURRICANE_PRE_DURATION_COLUMN}",
        )
        _fraction(
            row[HURRICANE_PRE_VOLUME_COLUMN],
            label=f"{label_prefix}:{HURRICANE_PRE_VOLUME_COLUMN}",
        )
        _hurricane_duration_weeks(
            row[HURRICANE_POST_DURATION_COLUMN],
            label=f"{label_prefix}:{HURRICANE_POST_DURATION_COLUMN}",
        )
        _fraction(
            row[HURRICANE_POST_VOLUME_COLUMN],
            label=f"{label_prefix}:{HURRICANE_POST_VOLUME_COLUMN}",
        )
        impact = strict_float(
            row["Net impact (Monthly upstream production decrease by %)"],
            label=f"{label_prefix}:Net impact",
        )
        if intensity not in {1, 2, 3, 4}:
            msg = f"Hurricane intensity must be one of 1,2,3,4: {intensity_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if not 0 <= impact <= 1:
            msg = f"Hurricane net impact must be between 0 and 1: {intensity_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        previous = impacts_by_intensity.get(intensity)
        if previous is not None and previous != impact:
            msg = f"conflicting hurricane intensity impact: intensity={intensity}"
            raise domain_error(msg)
        impacts_by_intensity[intensity] = impact
    if set(impacts_by_intensity) != {1, 2, 3, 4}:
        missing = sorted({1, 2, 3, 4} - set(impacts_by_intensity))
        msg = f"Hurricane intensity table is incomplete: missing={missing}"
        raise domain_error(msg)

    plants_spec = spec.files["plants"]
    plant_rows = _read_rows(plants_spec, snapshots["plants"], policy)
    impacted_by_plant: dict[str, bool] = {}
    for line_number, row in plant_rows:
        plant = str(
            canonical_axis_value(
                "LNG Plant",
                row["Liquefaction plants impacted by a hurricane in GoM"],
            ),
        )
        raw_impacted = str(row["Impacted by hurricane?"] or "").strip().casefold()
        if raw_impacted not in {"yes", "no"}:
            msg = f"Impacted by hurricane? must be Yes or No: {plants_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        impacted = raw_impacted == "yes"
        previous = impacted_by_plant.get(plant)
        if previous is not None and previous != impacted:
            msg = f"conflicting hurricane plant classification: {plant!r}"
            raise domain_error(msg)
        impacted_by_plant[plant] = impacted
    impacted_count = sum(impacted_by_plant.values())
    if impacted_count == 0:
        msg = "Hurricane plant table has no impacted facilities"
        raise domain_error(msg)

    validation_reference = f"lut:{intensity_spec.relative_path}+{plants_spec.relative_path}:no-hurricane-baseline"
    diagnostics = (
        "hurricane_baseline=no_hurricane",
        f"validated_intensity_count={len(impacts_by_intensity)}",
        f"validated_impacted_plant_count={impacted_count}",
    )
    return [
        _record(
            spec,
            policy=policy,
            axes={"Year": year, "Month": month},
            value=0,
            metadata=None,
            reference_id=validation_reference,
            diagnostics=diagnostics,
        )
        for year in policy.years
        for month in range(1, 13)
    ]


def _liq_util_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    expected_key_axes = ("Country", "LNG Plant", "LNG Plant Train", "Year", "Month")
    expected_metadata_axes = ("Period", "Life Cycle Category", "Nameplate Capacity (MTPA)")
    if spec.key_axes != expected_key_axes or spec.metadata_axes != expected_metadata_axes:
        msg = "liq_util adapter requires the canonical business key and authoritative metadata axes"
        raise domain_error(
            msg,
        )
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    records: list[LutRecord] = []
    for line_number, row in rows:
        year = strict_int(row["Year"], label=f"{file_spec.relative_path}:{line_number}:Year")
        month = strict_int(row["Month"], label=f"{file_spec.relative_path}:{line_number}:Month")
        if not 1 <= month <= 12:
            msg = f"Month must be between 1 and 12: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        life_cycle = str(row["Infra Life Cycle"] or "").strip()
        if not life_cycle:
            msg = f"Infra Life Cycle must not be empty: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if life_cycle.casefold() == "closed":
            continue
        if not policy.contains_year(year):
            continue
        axes = {
            "Country": canonical_axis_value("Country", row["Country"]),
            "LNG Plant": canonical_axis_value("LNG Plant", row["Plant Name"]),
            "LNG Plant Train": canonical_axis_value("LNG Plant Train", row["Plant Train"]),
            "Year": year,
            "Month": month,
        }
        period = strict_int(row["Period"], label=f"{file_spec.relative_path}:{line_number}:Period")
        capacity_mtpm = strict_float(
            row["LNG train capacity (Million tonnes LNG per month)"],
            label=f"{file_spec.relative_path}:{line_number}:capacity",
        )
        utilisation = strict_float(
            row["LNG plant utilisation %"],
            label=f"{file_spec.relative_path}:{line_number}:utilisation",
        )
        records.append(
            _record(
                spec,
                policy=policy,
                axes=axes,
                value=utilisation,
                metadata={
                    "Period": period,
                    "Life Cycle Category": life_cycle,
                    "Nameplate Capacity (MTPA)": truncate_numeric_value(
                        capacity_mtpm * MTPM_TO_MTPA,
                        label=f"{file_spec.relative_path}:{line_number}:nameplate capacity",
                        max_decimal_places=LUT_NAMEPLATE_MAX_DECIMAL_PLACES,
                    ),
                },
                reference_id=_reference_id(file_spec, line_number),
                diagnostics=("capacity_transform=mtpm_x_12",),
            ),
        )
    return records


def _liq_prod_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    expected_key_axes = ("Country", "LNG Plant", "LNG Plant Train", "Year", "Month")
    expected_metadata_axes = ("Period", "Life Cycle Category", "Nameplate Capacity (MTPA)")
    if spec.key_axes != expected_key_axes or spec.metadata_axes != expected_metadata_axes:
        msg = "liq_prod adapter requires the canonical business key and authoritative metadata axes"
        raise domain_error(msg)
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    records: list[LutRecord] = []
    for line_number, row in rows:
        year = strict_int(row["Year"], label=f"{file_spec.relative_path}:{line_number}:Year")
        month = strict_int(row["Month"], label=f"{file_spec.relative_path}:{line_number}:Month")
        if not 1 <= month <= 12:
            msg = f"Month must be between 1 and 12: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        life_cycle = str(row["Infra Life Cycle"] or "").strip()
        if not life_cycle:
            msg = f"Infra Life Cycle must not be empty: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if life_cycle.casefold() == "closed":
            continue
        if not policy.contains_year(year):
            continue
        capacity_mtpm = strict_float(
            row["LNG train capacity (Million tonnes LNG per month)"],
            label=f"{file_spec.relative_path}:{line_number}:capacity",
        )
        utilisation = strict_float(
            row["LNG plant utilisation %"],
            label=f"{file_spec.relative_path}:{line_number}:utilisation",
        )
        if capacity_mtpm < 0 or utilisation < 0:
            msg = f"LiqProd capacity and utilisation must be non-negative: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        axes = {
            "Country": canonical_axis_value("Country", row["Country"]),
            "LNG Plant": canonical_axis_value("LNG Plant", row["Plant Name"]),
            "LNG Plant Train": canonical_axis_value("LNG Plant Train", row["Plant Train"]),
            "Year": year,
            "Month": month,
        }
        period = strict_int(row["Period"], label=f"{file_spec.relative_path}:{line_number}:Period")
        records.append(
            _record(
                spec,
                policy=policy,
                axes=axes,
                value=capacity_mtpm * utilisation,
                metadata={
                    "Period": period,
                    "Life Cycle Category": life_cycle,
                    "Nameplate Capacity (MTPA)": truncate_numeric_value(
                        capacity_mtpm * MTPM_TO_MTPA,
                        label=f"{file_spec.relative_path}:{line_number}:nameplate capacity",
                        max_decimal_places=LUT_NAMEPLATE_MAX_DECIMAL_PLACES,
                    ),
                },
                reference_id=_reference_id(file_spec, line_number),
                diagnostics=("production_transform=capacity_mtpm_x_utilisation",),
            ),
        )
    return records


def _pipeline_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    expected_key_axes = ("Pipeline Name", "From Country", "To Country", "Year", "Month")
    if spec.key_axes != expected_key_axes:
        msg = "pipeline adapter requires [Pipeline Name, From Country, To Country, Year, Month]"
        raise domain_error(msg)
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    records: list[LutRecord] = []
    for line_number, row in rows:
        year = strict_int(row["Year"], label=f"{file_spec.relative_path}:{line_number}:Year")
        capacity_bcm = strict_float(
            row["Pipeline capacity (Bcm)"],
            label=f"{file_spec.relative_path}:{line_number}:Pipeline capacity (Bcm)",
        )
        if capacity_bcm < 0:
            msg = f"Pipeline capacity must be non-negative: {file_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if not policy.contains_year(year):
            continue
        fixed_axes = {
            "Pipeline Name": canonical_axis_value("Pipeline Name", row["Major pipeline"]),
            "From Country": canonical_axis_value("From Country", row["From country"]),
            "To Country": canonical_axis_value("To Country", row["To country"]),
            "Year": year,
        }
        records.extend(
            [
                _record(
                    spec,
                    policy=policy,
                    axes={**fixed_axes, "Month": month},
                    value=capacity_bcm * BCM_TO_MT_LNG,
                    metadata=None,
                    reference_id=f"{_reference_id(file_spec, line_number)}:month:{month}",
                    diagnostics=("unit_conversion=bcm_to_mt_lng_x_0.735", "annual_capacity_expanded_to_month"),
                )
                for month in range(1, 13)
            ],
        )
    return records


def _supply_disruption_records(  # noqa: C901
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Country", "Year", "Month"):
        msg = "supply_disruption adapter key_axes must be [Country, Year, Month]"
        raise domain_error(msg)

    seasonality_spec = spec.files["seasonality"]
    seasonality_rows = _read_rows(seasonality_spec, snapshots["seasonality"], policy)
    seasonality: dict[tuple[int, int, str, str], float] = {}
    seasonality_references: dict[tuple[int, int, str, str], str] = {}
    for line_number, row in seasonality_rows:
        year = strict_int(row["Year"], label=f"{seasonality_spec.relative_path}:{line_number}:Year")
        month = strict_int(row["Month"], label=f"{seasonality_spec.relative_path}:{line_number}:Month")
        period = strict_int(
            row["Period"],
            label=f"{seasonality_spec.relative_path}:{line_number}:Period",
        )
        if not 1 <= month <= 12:
            msg = f"Month must be between 1 and 12: {seasonality_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if period < 0:
            msg = f"Period must be non-negative: {seasonality_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if not policy.contains_year(year):
            continue
        province = str(canonical_axis_value("Province", row["Province"]))
        supply_type = str(canonical_axis_value("PNG/LNG", row["PNG/LNG"]))
        coefficient = strict_float(
            row["Seasonality"],
            label=f"{seasonality_spec.relative_path}:{line_number}:Seasonality",
        )
        if coefficient < 0:
            msg = f"Seasonality must be non-negative: {seasonality_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        key = (year, month, province, supply_type)
        previous = seasonality.get(key)
        if previous is not None and previous != coefficient:
            msg = f"conflicting duplicate SeasonalityLogic exact key: {key!r}"
            raise domain_error(msg)
        seasonality[key] = coefficient
        seasonality_references.setdefault(key, _reference_id(seasonality_spec, line_number))

    production_spec = spec.files["production"]
    production_rows = _read_rows(production_spec, snapshots["production"], policy)
    totals: dict[tuple[str, int, int], float] = {}
    source_counts: dict[tuple[str, int, int], int] = {}
    first_references: dict[tuple[str, int, int], str] = {}
    missing_joins: list[str] = []
    for line_number, row in production_rows:
        year = strict_int(row["Year"], label=f"{production_spec.relative_path}:{line_number}:Year")
        life_cycle = str(row["Life Cycle Category"] or "").strip()
        if not life_cycle:
            msg = f"Life Cycle Category must not be empty: {production_spec.relative_path}:{line_number}"
            raise domain_error(msg)
        if life_cycle.casefold() == "closed" or not policy.contains_year(year):
            continue
        country = str(canonical_axis_value("Country", row["Country"]))
        province = str(canonical_axis_value("Province", row["Province/Basin"]))
        supply_type = str(canonical_axis_value("PNG/LNG", row["Oil and gas detail"]))
        annual_supply_bcm = strict_float(
            row["Base case supply (Bcm)"],
            label=f"{production_spec.relative_path}:{line_number}:Base case supply (Bcm)",
        )
        annual_supply_mt = annual_supply_bcm * BCM_TO_MT_LNG
        for month in range(1, 13):
            seasonality_key = (year, month, province, supply_type)
            coefficient = seasonality.get(seasonality_key)
            if coefficient is None:
                if len(missing_joins) < 10:
                    missing_joins.append(
                        f"year={year}, month={month}, province={province!r}, type={supply_type!r}",
                    )
                continue
            output_key = (country, year, month)
            totals[output_key] = totals.get(output_key, 0.0) + annual_supply_mt * coefficient
            source_counts[output_key] = source_counts.get(output_key, 0) + 1
            first_references.setdefault(
                output_key,
                f"{_reference_id(production_spec, line_number)}|{seasonality_references[seasonality_key]}",
            )
    if missing_joins:
        msg = "SupplyDisruption production/seasonality join is missing exact rows: " + "; ".join(missing_joins)
        raise domain_error(msg)

    for output_key, total in sorted(totals.items()):
        if total < 0:
            msg = (
                "SupplyDisruption aggregated monthly supply must be non-negative: "
                f"key={output_key!r}, value={total}"
            )
            raise domain_error(msg)

    return [
        _record(
            spec,
            policy=policy,
            axes={"Country": country, "Year": year, "Month": month},
            value=totals[(country, year, month)],
            metadata=None,
            reference_id=first_references[(country, year, month)],
            diagnostics=(
                "unit_conversion=bcm_to_mt_lng_x_0.735",
                "seasonality_policy=raw_not_renormalized",
                f"aggregated_production_rows={source_counts[(country, year, month)]}",
            ),
        )
        for country, year, month in sorted(totals)
    ]


Adapter = Callable[
    [ParameterLutSpec, ReferenceLoadPolicy, Mapping[str, FileSnapshot]],
    list[LutRecord],
]

ADAPTERS: Mapping[str, Adapter] = {
    "tabular": _tabular_records,
    "futures_price": _futures_price_records,
    "gdp_growth": _gdp_growth_records,
    "hurricane_intensity": _hurricane_intensity_records,
    "liq_prod": _liq_prod_records,
    "temperature_degree_days": _temperature_records,
    "liq_util": _liq_util_records,
    "pipeline": _pipeline_records,
    "pmi_reference": _pmi_reference_records,
    "population": _population_records,
    "supply_disruption": _supply_disruption_records,
}


def load_parameter_records(
    spec: ParameterLutSpec,
    policy: ReferenceLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    adapter = ADAPTERS.get(spec.adapter)
    if adapter is None:
        msg = f"unknown LUT adapter: {spec.adapter}"
        raise domain_error(msg)
    return adapter(spec, policy, snapshots)
