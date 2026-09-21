# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: ANN401, C901, EM101, EM102, FBT001, TRY003
from collections import defaultdict
from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any

from apps.agents.model_parameter_agent.utils.lut.keys import (
    canonical_axis_value,
    canonical_key_from_axes,
    strict_int,
    truncate_numeric_value,
)
from apps.agents.model_parameter_agent.utils.lut.models import CanonicalKey, CanonicalValue, NumericValue
from apps.agents.model_parameter_agent.utils.workbook_contract import (
    PACKAGE_RESOURCE_DIR,
    ModelParameterWorkbookContract,
    ReferenceSource,
    WorkbookParameterContract,
    load_workbook_contract,
    resolve_workbook_paths,
    validate_workbook_hashes,
    workbook_contract_canonical_bytes,
    workbook_contract_schema_hash,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


NAMEPLATE_MAX_DECIMAL_PLACES = 2


def _reference_error(detail: str) -> MIBaseError:
    return MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


@dataclass(frozen=True, slots=True)
class WorkbookReferenceRecord:
    parameter_name: str
    canonical_key: CanonicalKey
    axes: Mapping[str, CanonicalValue]
    value: NumericValue
    metadata: Mapping[str, CanonicalValue]
    reference_id: str
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkbookReferenceBundle:
    contract: ModelParameterWorkbookContract
    records_by_parameter: Mapping[str, tuple[WorkbookReferenceRecord, ...]]
    blocked_keys_by_parameter: Mapping[str, frozenset[CanonicalKey]]
    warnings: tuple[str, ...] = ()

    def records_for(self, parameter_name: str) -> tuple[WorkbookReferenceRecord, ...]:
        return self.records_by_parameter.get(parameter_name, ())


def _require_workbook_loader() -> Any:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise _reference_error("openpyxl is required to read the v4 workbook contract resources") from exc
    return load_workbook


def _column_index(column: str) -> int:
    try:
        from openpyxl.utils.cell import column_index_from_string
    except ImportError as exc:
        raise _reference_error("openpyxl is required to resolve workbook columns") from exc
    return column_index_from_string(column)


def _column_letter(column: int) -> str:
    try:
        from openpyxl.utils.cell import get_column_letter
    except ImportError as exc:
        raise _reference_error("openpyxl is required to resolve workbook columns") from exc
    return get_column_letter(column)


def _source_bounds(source: ReferenceSource) -> tuple[int, int]:
    start, separator, end = source.range.partition(":")
    if not separator:
        raise _reference_error(f"Invalid source column range for {source.sheet}: {source.range}")
    start_column = _column_index(start)
    end_column = _column_index(end)
    if start_column > end_column:
        raise _reference_error(f"Source column range is reversed for {source.sheet}: {source.range}")
    return start_column, end_column


def _validate_source_headers(worksheet: Any, source: ReferenceSource, *, parameter_name: str) -> None:
    start_column, end_column = _source_bounds(source)
    for source_field, column_label in source.columns.items():
        column = _column_index(column_label)
        if not start_column <= column <= end_column:
            raise _reference_error(
                f"{parameter_name} source column {column_label} is outside contract range {source.range}",
            )
        expected_header = source.column_headers.get(source_field, source_field)
        actual_header = worksheet.cell(source.header_row, column).value
        if str(actual_header or "").strip() != expected_header:
            raise _reference_error(
                f"{parameter_name} source header mismatch at {source.sheet}!{column_label}{source.header_row}: "
                f"expected={expected_header!r}, actual={actual_header!r}",
            )


def _finite_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _record(
    parameter_name: str,
    parameter: WorkbookParameterContract,
    *,
    axes: Mapping[str, object],
    value: float,
    metadata: Mapping[str, object] | None,
    reference_id: str,
    diagnostics: tuple[str, ...] = (),
) -> WorkbookReferenceRecord:
    canonical_axes = MappingProxyType(
        {
            axis_name: canonical_axis_value(axis_name, axes[axis_name])
            for axis_name in parameter.reference_source.key_axes
        },
    )
    metadata_values = metadata or {}
    canonical_metadata = MappingProxyType(
        {
            axis_name: canonical_axis_value(axis_name, metadata_values[axis_name])
            for axis_name in parameter.reference_source.metadata_axes
            if axis_name in metadata_values
            and metadata_values[axis_name] is not None
            and str(metadata_values[axis_name]).strip()
        },
    )
    return WorkbookReferenceRecord(
        parameter_name=parameter_name,
        canonical_key=canonical_key_from_axes(canonical_axes, parameter.reference_source.key_axes),
        axes=canonical_axes,
        value=int(value) if value.is_integer() else value,
        metadata=canonical_metadata,
        reference_id=reference_id,
        diagnostics=diagnostics,
    )


def _cell_reference_id(
    contract: ModelParameterWorkbookContract,
    parameter: WorkbookParameterContract,
    *,
    row: int,
    column: int,
) -> str:
    source = parameter.reference_source
    return f"{contract.release_id}:{source.workbook_role}:{source.sheet}:{_column_letter(column)}{row}"


def _deduplicate_records(
    parameter_name: str,
    records: Sequence[WorkbookReferenceRecord],
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    by_key: dict[CanonicalKey, WorkbookReferenceRecord] = {}
    conflicts: set[CanonicalKey] = set()
    for record in records:
        previous = by_key.get(record.canonical_key)
        if previous is None:
            by_key[record.canonical_key] = record
            continue
        if previous.value != record.value or dict(previous.metadata) != dict(record.metadata):
            conflicts.add(record.canonical_key)
    for key in conflicts:
        by_key.pop(key, None)
    warnings = tuple(f"{parameter_name} conflicting duplicate exact key excluded: {key!r}" for key in sorted(conflicts))
    return tuple(by_key[key] for key in sorted(by_key)), warnings, frozenset(conflicts)


def _gdp_growth_records(
    contract: ModelParameterWorkbookContract,
    parameter_name: str,
    parameter: WorkbookParameterContract,
    worksheet: Any,
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    source = parameter.reference_source
    year_column = _column_index(source.columns["Year"])
    country_column = _column_index(source.columns["Country"])
    value_column = _column_index(source.columns["GDP"])
    start_column, end_column = _source_bounds(source)
    required_years = set(contract.horizon.years) | {contract.horizon.start_year - 1}
    levels: dict[tuple[str, int], tuple[float, int]] = {}
    conflicted_level_keys: set[tuple[str, int]] = set()
    blocked_source_keys: set[CanonicalKey] = set()
    warnings: list[str] = []
    for row_number, values in enumerate(
        worksheet.iter_rows(
            min_row=source.data_start_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ),
        start=source.data_start_row,
    ):
        year_value = values[year_column - start_column]
        country_value = values[country_column - start_column]
        if year_value is None and country_value is None:
            continue
        try:
            year = strict_int(year_value, label=f"{parameter_name}:{row_number}:Year")
        except MIBaseError:
            continue
        if year not in required_years:
            continue
        country = str(country_value or "").strip()
        value = _finite_number(values[value_column - start_column])
        if not country or value is None:
            warnings.append(f"{parameter_name} invalid GDP level excluded at row {row_number}")
            if country and year in contract.horizon.years:
                blocked_source_keys.add((country, year))
            if country and year + 1 in contract.horizon.years:
                blocked_source_keys.add((country, year + 1))
            continue
        key = (country, year)
        if key in conflicted_level_keys:
            continue
        previous = levels.get(key)
        if previous is not None and previous[0] != value:
            warnings.append(f"{parameter_name} conflicting GDP level excluded for {key!r}")
            levels.pop(key, None)
            conflicted_level_keys.add(key)
            continue
        levels[key] = (value, row_number)

    for country, year in conflicted_level_keys:
        if year in contract.horizon.years:
            blocked_source_keys.add((country, year))
        if year + 1 in contract.horizon.years:
            blocked_source_keys.add((country, year + 1))

    records: list[WorkbookReferenceRecord] = []
    for (country, year), (current_value, row_number) in levels.items():
        if year not in contract.horizon.years:
            continue
        prior = levels.get((country, year - 1))
        if prior is None or prior[0] == 0:
            warnings.append(f"{parameter_name} prior-year GDP level is unavailable for {(country, year)!r}")
            blocked_source_keys.add((country, year))
            continue
        growth = (current_value - prior[0]) / prior[0]
        records.append(
            _record(
                parameter_name,
                parameter,
                axes={"Country": country, "Year": year},
                value=growth,
                metadata=None,
                reference_id=_cell_reference_id(
                    contract,
                    parameter,
                    row=row_number,
                    column=value_column,
                ),
                diagnostics=("value_transform=gdp_year_over_year_growth",),
            ),
        )
    deduplicated, duplicate_warnings, blocked_keys = _deduplicate_records(parameter_name, records)
    return deduplicated, (*warnings, *duplicate_warnings), blocked_keys | frozenset(blocked_source_keys)


def _year_column_records(
    contract: ModelParameterWorkbookContract,
    parameter_name: str,
    parameter: WorkbookParameterContract,
    worksheet: Any,
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    source = parameter.reference_source
    start_column, end_column = _source_bounds(source)
    country_column = _column_index(source.columns["Country"])
    month_column = _column_index(source.columns["Month"])
    metadata_columns = {axis_name: _column_index(source.columns[axis_name]) for axis_name in source.metadata_axes}
    header_values = next(
        worksheet.iter_rows(
            min_row=source.header_row,
            max_row=source.header_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ),
    )
    year_columns: dict[int, int] = {}
    for offset, raw_header in enumerate(header_values):
        try:
            year = strict_int(raw_header, label=f"{parameter_name}:year header")
        except MIBaseError:
            continue
        if year in contract.horizon.years:
            year_columns[start_column + offset] = year
    if set(year_columns.values()) != set(contract.horizon.years):
        raise _reference_error(
            f"{parameter_name} source does not contain every contract horizon year: {sorted(year_columns.values())}",
        )

    records: list[WorkbookReferenceRecord] = []
    blocked_source_keys: set[CanonicalKey] = set()
    warnings: list[str] = []
    for row_number, values in enumerate(
        worksheet.iter_rows(
            min_row=source.data_start_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ),
        start=source.data_start_row,
    ):
        country_value = values[country_column - start_column]
        month_value = values[month_column - start_column]
        if country_value is None and month_value is None:
            continue
        country = str(country_value or "").strip()
        try:
            month = strict_int(month_value, label=f"{parameter_name}:{row_number}:Month")
        except MIBaseError:
            continue
        if not country or not 1 <= month <= 12:
            warnings.append(f"{parameter_name} invalid Country/Month excluded at row {row_number}")
            continue
        metadata = {axis_name: values[column - start_column] for axis_name, column in metadata_columns.items()}
        for column, year in year_columns.items():
            value = _finite_number(values[column - start_column])
            if value is None:
                blocked_source_keys.add((country, year, month))
                warnings.append(
                    f"{parameter_name} invalid cached value excluded at {_column_letter(column)}{row_number}",
                )
                continue
            records.append(
                _record(
                    parameter_name,
                    parameter,
                    axes={"Country": country, "Year": year, "Month": month},
                    value=value,
                    metadata=metadata,
                    reference_id=_cell_reference_id(
                        contract,
                        parameter,
                        row=row_number,
                        column=column,
                    ),
                ),
            )
    deduplicated, duplicate_warnings, blocked_keys = _deduplicate_records(parameter_name, records)
    return deduplicated, (*warnings, *duplicate_warnings), blocked_keys | frozenset(blocked_source_keys)


def _power_mix_records(
    contract: ModelParameterWorkbookContract,
    parameter_name: str,
    parameter: WorkbookParameterContract,
    worksheet: Any,
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    source = parameter.reference_source
    start_column, end_column = _source_bounds(source)
    columns = {name: _column_index(column) for name, column in source.columns.items()}
    records: list[WorkbookReferenceRecord] = []
    blocked_source_keys: set[CanonicalKey] = set()
    blocked_group_keys: set[tuple[CanonicalValue, ...]] = set()
    warnings: list[str] = []
    for row_number, values in enumerate(
        worksheet.iter_rows(
            min_row=source.data_start_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ),
        start=source.data_start_row,
    ):
        year_value = values[columns["Year"] - start_column]
        country_value = values[columns["Country"] - start_column]
        energy_source_value = values[columns["Energy Source Use"] - start_column]
        if year_value is None and country_value is None and energy_source_value is None:
            continue
        try:
            year = strict_int(year_value, label=f"{parameter_name}:{row_number}:Year")
        except MIBaseError:
            continue
        if year not in contract.horizon.years:
            continue
        country = str(country_value or "").strip()
        energy_source = str(energy_source_value or "").strip()
        value = _finite_number(values[columns["Yearly Power Mix"] - start_column])
        if not country or not energy_source or value is None:
            if country:
                blocked_group_keys.add((country, year))
            if country and energy_source:
                blocked_source_keys.add((country, year, energy_source))
            warnings.append(f"{parameter_name} invalid annual source row excluded at row {row_number}")
            continue
        records.append(
            _record(
                parameter_name,
                parameter,
                axes={"Country": country, "Year": year, "Energy Source": energy_source},
                value=value,
                metadata=None,
                reference_id=_cell_reference_id(
                    contract,
                    parameter,
                    row=row_number,
                    column=columns["Yearly Power Mix"],
                ),
                diagnostics=("monthly_rows_deduplicated_to_annual_vector",),
            ),
        )
    deduplicated, duplicate_warnings, duplicate_blocked_keys = _deduplicate_records(
        parameter_name,
        records,
    )
    key_axis_positions = {axis_name: index for index, axis_name in enumerate(source.key_axes)}
    group_axes = parameter.constraints.atomic_group_axes
    vector_axis = parameter.constraints.vector_axis
    expected_members = set(parameter.constraints.vector_members)
    if vector_axis is None:
        raise _reference_error("PowerMix contract vector_axis is required")

    def group_for_key(key: CanonicalKey) -> tuple[CanonicalValue, ...]:
        return tuple(key[key_axis_positions[axis_name]] for axis_name in group_axes)

    blocked_group_keys.update(group_for_key(key) for key in duplicate_blocked_keys)
    grouped_records: dict[tuple[CanonicalValue, ...], list[WorkbookReferenceRecord]] = defaultdict(list)
    for record in deduplicated:
        grouped_records[group_for_key(record.canonical_key)].append(record)

    invalid_groups: set[tuple[CanonicalValue, ...]] = set(blocked_group_keys)
    for group_key, group_records in grouped_records.items():
        members = {str(record.axes.get(vector_axis) or "").strip() for record in group_records}
        values = [float(record.value) for record in group_records]
        valid = (
            len(group_records) == len(expected_members)
            and members == expected_members
            and all(
                (parameter.constraints.minimum is None or value >= parameter.constraints.minimum)
                and (parameter.constraints.maximum is None or value <= parameter.constraints.maximum)
                for value in values
            )
            and parameter.constraints.sum is not None
            and parameter.constraints.sum_tolerance is not None
            and math.isclose(
                math.fsum(values),
                parameter.constraints.sum,
                rel_tol=0.0,
                abs_tol=parameter.constraints.sum_tolerance,
            )
        )
        if not valid:
            invalid_groups.add(group_key)

    atomic_blocked_keys = set(blocked_source_keys) | set(duplicate_blocked_keys)
    for group_key in invalid_groups:
        group_values = dict(zip(group_axes, group_key, strict=True))
        for member in parameter.constraints.vector_members:
            atomic_blocked_keys.add(
                canonical_key_from_axes(
                    {**group_values, vector_axis: member},
                    source.key_axes,
                ),
            )
        warnings.append(
            f"{parameter_name} invalid atomic source vector excluded: {group_key!r}",
        )
    valid_records = tuple(
        record for record in deduplicated if group_for_key(record.canonical_key) not in invalid_groups
    )
    return (
        valid_records,
        (*warnings, *duplicate_warnings),
        frozenset(atomic_blocked_keys),
    )


def _liq_util_records(
    contract: ModelParameterWorkbookContract,
    parameter_name: str,
    parameter: WorkbookParameterContract,
    worksheet: Any,
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    source = parameter.reference_source
    start_column, end_column = _source_bounds(source)
    columns = {name: _column_index(column) for name, column in source.columns.items()}
    records: list[WorkbookReferenceRecord] = []
    blocked_source_keys: set[CanonicalKey] = set()
    warnings: list[str] = []
    for row_number, values in enumerate(
        worksheet.iter_rows(
            min_row=source.data_start_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ),
        start=source.data_start_row,
    ):
        year_value = values[columns["Year"] - start_column]
        if year_value is None:
            continue
        try:
            year = strict_int(year_value, label=f"{parameter_name}:{row_number}:Year")
        except MIBaseError:
            continue
        if year not in contract.horizon.years:
            continue
        country = str(values[columns["Country"] - start_column] or "").strip()
        plant = str(values[columns["Plant Name"] - start_column] or "").strip()
        train = str(values[columns["Plant Train"] - start_column] or "").strip()
        try:
            month = strict_int(
                values[columns["Month"] - start_column],
                label=f"{parameter_name}:{row_number}:Month",
            )
        except MIBaseError:
            warnings.append(f"{parameter_name} invalid Month excluded at row {row_number}")
            continue
        exact_key = (country, plant, train, year, month)
        try:
            period = strict_int(
                values[columns["Period"] - start_column],
                label=f"{parameter_name}:{row_number}:Period",
            )
        except MIBaseError:
            if country and plant and train and 1 <= month <= 12:
                blocked_source_keys.add(exact_key)
            warnings.append(f"{parameter_name} invalid Period excluded at row {row_number}")
            continue
        life_cycle = str(values[columns["Infra Life Cycle"] - start_column] or "").strip()
        capacity_mtpm = _finite_number(values[columns["Monthly Capacity (MTPM)"] - start_column])
        utilisation = _finite_number(values[columns["LNG plant utilisation %"] - start_column])
        if (
            not country
            or not plant
            or not train
            or not 1 <= month <= 12
            or capacity_mtpm is None
            or utilisation is None
        ):
            if country and plant and train and 1 <= month <= 12 and (capacity_mtpm is None or utilisation is None):
                blocked_source_keys.add(exact_key)
            warnings.append(f"{parameter_name} invalid source row excluded at row {row_number}")
            continue
        if (parameter.constraints.minimum is not None and utilisation < parameter.constraints.minimum) or (
            parameter.constraints.maximum is not None and utilisation > parameter.constraints.maximum
        ):
            blocked_source_keys.add(exact_key)
            warnings.append(
                f"{parameter_name} out-of-range source value excluded at row {row_number}",
            )
            continue
        nameplate_transform = source.transforms["Nameplate Capacity (MTPA)"]
        nameplate_mtpa = truncate_numeric_value(
            capacity_mtpm * nameplate_transform.factor,
            label=f"{parameter_name}:{row_number}:Nameplate Capacity (MTPA)",
            max_decimal_places=NAMEPLATE_MAX_DECIMAL_PLACES,
        )
        records.append(
            _record(
                parameter_name,
                parameter,
                axes={
                    "Country": country,
                    "LNG Plant": plant,
                    "LNG Plant Train": train,
                    "Year": year,
                    "Month": month,
                },
                value=utilisation,
                metadata={
                    "Period": period,
                    **({"Life Cycle Category": life_cycle} if life_cycle else {}),
                    "Nameplate Capacity (MTPA)": nameplate_mtpa,
                },
                reference_id=_cell_reference_id(
                    contract,
                    parameter,
                    row=row_number,
                    column=columns["LNG plant utilisation %"],
                ),
                diagnostics=(
                    "capacity_transform=mtpm_x_12",
                    f"transform_provenance={nameplate_transform.provenance}",
                    *(("missing_metadata=Life Cycle Category",) if not life_cycle else ()),
                ),
            ),
        )
    deduplicated, duplicate_warnings, blocked_keys = _deduplicate_records(parameter_name, records)
    return deduplicated, (*warnings, *duplicate_warnings), blocked_keys | frozenset(blocked_source_keys)


def _pipeline_records(
    contract: ModelParameterWorkbookContract,
    parameter_name: str,
    parameter: WorkbookParameterContract,
    worksheet: Any,
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    source = parameter.reference_source
    start_column, end_column = _source_bounds(source)
    columns = {name: _column_index(column) for name, column in source.columns.items()}
    records: list[WorkbookReferenceRecord] = []
    blocked_source_keys: set[CanonicalKey] = set()
    warnings: list[str] = []
    for row_number, values in enumerate(
        worksheet.iter_rows(
            min_row=source.data_start_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ),
        start=source.data_start_row,
    ):
        year_value = values[columns["Year"] - start_column]
        pipeline_value = values[columns["Pipeline Name"] - start_column]
        if year_value is None and pipeline_value is None:
            continue
        try:
            year = strict_int(year_value, label=f"{parameter_name}:{row_number}:Year")
        except MIBaseError:
            continue
        if year not in contract.horizon.years:
            continue
        pipeline = str(pipeline_value or "").strip()
        from_country = str(values[columns["From Country"] - start_column] or "").strip()
        to_country = str(values[columns["To Country"] - start_column] or "").strip()
        capacity = _finite_number(values[columns["Pipeline Capacity"] - start_column])
        if not pipeline or not from_country or not to_country:
            warnings.append(f"{parameter_name} invalid pipeline identity excluded at row {row_number}")
            continue
        fixed_key = (pipeline, from_country, to_country, year)
        if capacity is None or capacity < 0:
            blocked_source_keys.update((*fixed_key, month) for month in range(1, 13))
            warnings.append(f"{parameter_name} invalid capacity excluded at row {row_number}")
            continue
        capacity_reference = _cell_reference_id(
            contract,
            parameter,
            row=row_number,
            column=columns["Pipeline Capacity"],
        )
        records.extend(
            _record(
                parameter_name,
                parameter,
                axes={
                    "Pipeline Name": pipeline,
                    "From Country": from_country,
                    "To Country": to_country,
                    "Year": year,
                    "Month": month,
                },
                value=capacity,
                metadata=None,
                reference_id=f"{capacity_reference}:month:{month}",
                diagnostics=(
                    "annual_capacity_expanded_to_month",
                    "source_header_legacy_unit_label=Pipeline capacity (Mt)",
                ),
            )
            for month in range(1, 13)
        )
    deduplicated, duplicate_warnings, duplicate_blocked_keys = _deduplicate_records(parameter_name, records)
    return (
        deduplicated,
        (*warnings, *duplicate_warnings),
        frozenset(blocked_source_keys) | duplicate_blocked_keys,
    )


def _supply_disruption_records(
    contract: ModelParameterWorkbookContract,
    parameter_name: str,
    parameter: WorkbookParameterContract,
    worksheet: Any,
    *,
    resource_root: Path,
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    source = parameter.reference_source
    seasonality_source = source.auxiliary_sources["seasonality"]
    seasonality_path = (resource_root / seasonality_source.path).resolve(strict=True)
    if not seasonality_path.is_relative_to(resource_root.resolve()):
        raise _reference_error(f"{parameter_name} seasonality source escapes the resource root")

    seasonality: dict[tuple[int, int, str, str], tuple[float, int]] = {}
    with seasonality_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        actual_columns = tuple(reader.fieldnames or ())
        if not set(seasonality_source.required_columns).issubset(actual_columns):
            raise _reference_error(
                f"{parameter_name} seasonality headers differ: "
                f"required={seasonality_source.required_columns}, actual={actual_columns}",
            )
        for row_number, row in enumerate(reader, start=2):
            year = strict_int(row["Year"], label=f"{parameter_name}:seasonality:{row_number}:Year")
            if year not in contract.horizon.years:
                continue
            month = strict_int(row["Month"], label=f"{parameter_name}:seasonality:{row_number}:Month")
            period = strict_int(row["Period"], label=f"{parameter_name}:seasonality:{row_number}:Period")
            province = str(canonical_axis_value("Province", row["Province"]))
            supply_type = str(canonical_axis_value("PNG/LNG", row["PNG/LNG"]))
            coefficient = _finite_number(row["Seasonality"])
            if not 1 <= month <= 12 or period < 0 or coefficient is None or coefficient < 0:
                raise _reference_error(f"{parameter_name} invalid seasonality row: {row_number}")
            key = (year, month, province, supply_type)
            previous = seasonality.get(key)
            if previous is not None and previous[0] != coefficient:
                raise _reference_error(f"{parameter_name} conflicting seasonality exact key: {key!r}")
            seasonality.setdefault(key, (coefficient, row_number))

    start_column, end_column = _source_bounds(source)
    columns = {name: _column_index(column) for name, column in source.columns.items()}
    transform = source.transforms["Base case supply (Bcm)"]
    totals: dict[tuple[str, int, int], float] = defaultdict(float)
    source_counts: dict[tuple[str, int, int], int] = defaultdict(int)
    first_references: dict[tuple[str, int, int], str] = {}
    for row_number, values in enumerate(
        worksheet.iter_rows(
            min_row=source.data_start_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ),
        start=source.data_start_row,
    ):
        year_value = values[columns["Year"] - start_column]
        if year_value is None:
            continue
        try:
            year = strict_int(year_value, label=f"{parameter_name}:{row_number}:Year")
        except MIBaseError:
            continue
        if year not in contract.horizon.years:
            continue
        life_cycle = str(values[columns["Life Cycle Category"] - start_column] or "").strip()
        if not life_cycle:
            raise _reference_error(f"{parameter_name} lifecycle is empty at workbook row {row_number}")
        if life_cycle.casefold() == "closed":
            continue
        country = str(canonical_axis_value("Country", values[columns["Country"] - start_column]))
        province = str(canonical_axis_value("Province", values[columns["Province/Basin"] - start_column]))
        supply_type = str(canonical_axis_value("PNG/LNG", values[columns["PNG/LNG"] - start_column]))
        annual_supply_mt = _finite_number(values[columns["Base case supply (Mt)"] - start_column])
        if not country or not province or not supply_type or annual_supply_mt is None:
            raise _reference_error(f"{parameter_name} invalid production row: {row_number}")
        annual_supply_bcm = annual_supply_mt * transform.factor
        for month in range(1, 13):
            seasonality_key = (year, month, province, supply_type)
            seasonality_record = seasonality.get(seasonality_key)
            if seasonality_record is None:
                raise _reference_error(
                    f"{parameter_name} production/seasonality join is missing: key={seasonality_key!r}",
                )
            coefficient, seasonality_row = seasonality_record
            output_key = (country, year, month)
            totals[output_key] += annual_supply_bcm * coefficient
            source_counts[output_key] += 1
            first_references.setdefault(
                output_key,
                f"{_cell_reference_id(contract, parameter, row=row_number, column=columns['Base case supply (Mt)'])}"
                f"|{contract.release_id}:seasonality:{seasonality_path.name}:row:{seasonality_row}",
            )

    negative_totals = {key: total for key, total in totals.items() if total < 0}
    if negative_totals:
        raise _reference_error(
            f"{parameter_name} aggregated monthly supply must be non-negative: {next(iter(negative_totals.items()))!r}",
        )
    records = tuple(
        _record(
            parameter_name,
            parameter,
            axes={"Country": country, "Year": year, "Month": month},
            value=total,
            metadata=None,
            reference_id=first_references[(country, year, month)],
            diagnostics=(
                "production_transform=mt_divided_by_0.735",
                "seasonality_policy=raw_not_renormalized",
                f"aggregated_production_rows={source_counts[(country, year, month)]}",
            ),
        )
        for (country, year, month), total in sorted(totals.items())
    )
    return records, (), frozenset()


def _extract_parameter_records(
    contract: ModelParameterWorkbookContract,
    parameter_name: str,
    parameter: WorkbookParameterContract,
    workbook: Any,
    *,
    resource_root: Path,
) -> tuple[tuple[WorkbookReferenceRecord, ...], tuple[str, ...], frozenset[CanonicalKey]]:
    source = parameter.reference_source
    if source.sheet not in workbook.sheetnames:
        raise _reference_error(f"{parameter_name} source sheet is missing: {source.sheet}")
    worksheet = workbook[source.sheet]
    _validate_source_headers(worksheet, source, parameter_name=parameter_name)
    if source.parser == "gdp_growth_from_levels":
        return _gdp_growth_records(contract, parameter_name, parameter, worksheet)
    if source.parser == "year_columns":
        return _year_column_records(contract, parameter_name, parameter, worksheet)
    if source.parser == "annual_deduplicated_rows":
        return _power_mix_records(contract, parameter_name, parameter, worksheet)
    if source.parser == "fixed_rows":
        return _liq_util_records(contract, parameter_name, parameter, worksheet)
    if source.parser == "annual_rows_to_months":
        return _pipeline_records(contract, parameter_name, parameter, worksheet)
    if source.parser == "production_seasonality_monthly":
        return _supply_disruption_records(
            contract,
            parameter_name,
            parameter,
            worksheet,
            resource_root=resource_root,
        )
    raise _reference_error(f"Unsupported workbook reference parser: {source.parser}")


def _extract_workbook_references_uncached(
    resolved_contract: ModelParameterWorkbookContract,
    *,
    resource_root: Path,
    enforce_expected_counts: bool,
) -> WorkbookReferenceBundle:
    workbook_paths = validate_workbook_hashes(resolved_contract, resource_root=resource_root)
    parameters_by_role: dict[str, list[tuple[str, WorkbookParameterContract]]] = defaultdict(list)
    for parameter_name, parameter in resolved_contract.parameters.items():
        parameters_by_role[parameter.reference_source.workbook_role].append((parameter_name, parameter))

    loader = _require_workbook_loader()
    records_by_parameter: dict[str, tuple[WorkbookReferenceRecord, ...]] = {}
    blocked_keys_by_parameter: dict[str, frozenset[CanonicalKey]] = {}
    warnings: list[str] = []
    for role in sorted(parameters_by_role):
        workbook = loader(
            workbook_paths[role],
            read_only=True,
            data_only=True,
            keep_links=False,
        )
        try:
            for parameter_name, parameter in sorted(parameters_by_role[role]):
                records, parameter_warnings, blocked_keys = _extract_parameter_records(
                    resolved_contract,
                    parameter_name,
                    parameter,
                    workbook,
                    resource_root=resource_root,
                )
                if enforce_expected_counts and len(records) != parameter.reference_source.expected_record_count:
                    raise _reference_error(
                        f"{parameter_name} reference count mismatch: "
                        f"expected={parameter.reference_source.expected_record_count}, actual={len(records)}",
                    )
                records_by_parameter[parameter_name] = records
                blocked_keys_by_parameter[parameter_name] = blocked_keys
                warnings.extend(parameter_warnings)
        finally:
            workbook.close()
    return WorkbookReferenceBundle(
        contract=resolved_contract,
        records_by_parameter=MappingProxyType(records_by_parameter),
        blocked_keys_by_parameter=MappingProxyType(blocked_keys_by_parameter),
        warnings=tuple(warnings),
    )


@lru_cache(maxsize=4)
def _extract_workbook_references_cached(
    contract_hash: str,
    canonical_contract: bytes,
    resource_root: str,
    workbook_signatures: tuple[tuple[str, str, int, int], ...],
    enforce_expected_counts: bool,
) -> WorkbookReferenceBundle:
    contract = ModelParameterWorkbookContract.model_validate_json(canonical_contract)
    if workbook_contract_schema_hash(contract) != contract_hash:
        raise _reference_error("Workbook contract canonical hash changed while preparing the reference cache")
    if not workbook_signatures:
        raise _reference_error("Workbook reference cache requires file signatures")
    return _extract_workbook_references_uncached(
        contract,
        resource_root=Path(resource_root),
        enforce_expected_counts=enforce_expected_counts,
    )


def extract_workbook_references(
    contract: ModelParameterWorkbookContract | None = None,
    *,
    resource_root: Path = PACKAGE_RESOURCE_DIR,
    enforce_expected_counts: bool = True,
    use_cache: bool = True,
) -> WorkbookReferenceBundle:
    resolved_contract = contract or load_workbook_contract()
    resolved_root = resource_root.resolve()
    if not use_cache:
        return _extract_workbook_references_uncached(
            resolved_contract,
            resource_root=resolved_root,
            enforce_expected_counts=enforce_expected_counts,
        )
    paths = resolve_workbook_paths(resolved_contract, resource_root=resolved_root)
    signatures = tuple(
        (
            role,
            str(path),
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for role, path in sorted(paths.items())
    ) + tuple(
        (
            f"{parameter_name}:{source_name}",
            str(path),
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for parameter_name, parameter in sorted(resolved_contract.parameters.items())
        for source_name, source in sorted(parameter.reference_source.auxiliary_sources.items())
        for path in ((resolved_root / source.path).resolve(strict=True),)
    )
    canonical_contract = workbook_contract_canonical_bytes(resolved_contract)
    return _extract_workbook_references_cached(
        workbook_contract_schema_hash(resolved_contract),
        canonical_contract,
        str(resolved_root),
        signatures,
        enforce_expected_counts,
    )


def clear_workbook_reference_cache() -> None:
    _extract_workbook_references_cached.cache_clear()


__all__ = [
    "WorkbookReferenceBundle",
    "WorkbookReferenceRecord",
    "clear_workbook_reference_cache",
    "extract_workbook_references",
]
