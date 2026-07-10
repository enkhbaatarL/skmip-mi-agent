from __future__ import annotations

from collections.abc import Callable, Mapping
import csv
from dataclasses import dataclass
import io

from apps.agents.model_parameter_agent.utils.lut.keys import (
    canonical_axis_value,
    canonical_key_from_axes,
    strict_float,
    strict_int,
)
from apps.agents.model_parameter_agent.utils.lut.models import (
    CanonicalKey,
    CanonicalValue,
    LutLoadPolicy,
    LutRecord,
    domain_error,
    freeze_mapping,
)
from apps.agents.model_parameter_agent.utils.lut.registry import (
    LutFileSpec,
    ParameterLutSpec,
)


ADAPTER_SCHEMA_VERSION = "model-parameter-lut-adapters-v1"
TEMPERATURE_BASE = 18.0
DEGREE_DAY_DIVISOR = 30.0
MTPM_TO_MTPA = 12.0


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


def _required_headers(file_spec: LutFileSpec, policy: LutLoadPolicy) -> set[str]:
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
    policy: LutLoadPolicy,
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


def _reference_id(file_spec: LutFileSpec, line_number: int) -> str:
    return f"lut:{file_spec.relative_path}:row:{line_number}"


def _record(
    spec: ParameterLutSpec,
    *,
    axes: Mapping[str, CanonicalValue],
    value: float,
    metadata: Mapping[str, CanonicalValue] | None,
    reference_id: str,
    diagnostics: tuple[str, ...] = (),
) -> LutRecord:
    canonical_key = canonical_key_from_axes(axes, spec.key_axes)
    return LutRecord(
        parameter_name=spec.parameter_name,
        canonical_key=canonical_key,
        axes=freeze_mapping(axes),
        value=strict_float(value, label=f"{spec.parameter_name} LUT value"),
        metadata=freeze_mapping(metadata),
        reference_id=reference_id,
        diagnostics=diagnostics,
    )


def _tabular_records(
    spec: ParameterLutSpec,
    policy: LutLoadPolicy,
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
    policy: LutLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    if spec.key_axes != ("Country", "Year"):
        msg = "gdp_growth adapter key_axes must be [Country, Year]"
        raise domain_error(msg)
    file_spec = spec.files["values"]
    rows = _read_rows(file_spec, snapshots["values"], policy)
    country_column = "RE Base Case GDP and Population Data_Country"
    year_column = "RE Base Case GDP and Population Data_Year"
    value_column = "RE Base Case GDP and Population Data_GDP"
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
                    axes={"Country": country, "Year": year},
                    value=current / previous - 1.0,
                    metadata=None,
                    reference_id=references[(country, year)],
                    diagnostics=tuple(diagnostics),
                ),
            )
    return records


def _degree_day_values(
    file_spec: LutFileSpec,
    snapshot: FileSnapshot,
    policy: LutLoadPolicy,
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
    policy: LutLoadPolicy,
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
                axes={"Country": country, "Year": year, "Month": month},
                value=temperature,
                metadata=None,
                reference_id=reference_id,
                diagnostics=tuple(diagnostics),
            ),
        )
    return records


def _liq_util_records(
    spec: ParameterLutSpec,
    policy: LutLoadPolicy,
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
                axes=axes,
                value=utilisation,
                metadata={
                    "Period": period,
                    "Life Cycle Category": life_cycle,
                    "Nameplate Capacity (MTPA)": capacity_mtpm * MTPM_TO_MTPA,
                },
                reference_id=_reference_id(file_spec, line_number),
                diagnostics=("capacity_transform=mtpm_x_12",),
            ),
        )
    return records


Adapter = Callable[
    [ParameterLutSpec, LutLoadPolicy, Mapping[str, FileSnapshot]],
    list[LutRecord],
]

ADAPTERS: Mapping[str, Adapter] = {
    "tabular": _tabular_records,
    "gdp_growth": _gdp_growth_records,
    "temperature_degree_days": _temperature_records,
    "liq_util": _liq_util_records,
}


def load_parameter_records(
    spec: ParameterLutSpec,
    policy: LutLoadPolicy,
    snapshots: Mapping[str, FileSnapshot],
) -> list[LutRecord]:
    adapter = ADAPTERS.get(spec.adapter)
    if adapter is None:
        msg = f"unknown LUT adapter: {spec.adapter}"
        raise domain_error(msg)
    return adapter(spec, policy, snapshots)
