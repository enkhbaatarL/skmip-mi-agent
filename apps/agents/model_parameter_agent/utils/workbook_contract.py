# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: EM101, EM102, TRY003
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


PACKAGE_DIR = Path(__file__).resolve().parents[1]
PACKAGE_RESOURCE_DIR = PACKAGE_DIR / "resources"
DEFAULT_WORKBOOK_CONTRACT_PATH = PACKAGE_RESOURCE_DIR / "contracts" / "model-parameter-workbook-contract-v9.json"
V1_PARAMETER_NAMES = frozenset({"GDP", "PMI", "PowerMix", "Temperature", "LiqUtilAdjustment"})
EXTEND10_PARAMETER_NAMES = frozenset(
    {
        *V1_PARAMETER_NAMES,
        "Population",
        "HurricaneIntensity",
        "LiqProdAdjustment",
        "PipelineAdjustment",
        "SupplyDisruption",
    },
)
EXTEND14_PARAMETER_NAMES = frozenset(
    {
        *EXTEND10_PARAMETER_NAMES,
        "User-Adjusted Gas Demand",
        "RegasAdjustment",
        "PNG Contract Volume",
        "ShippingCost",
    },
)
EXPECTED_PARAMETER_NAMES = frozenset(
    {
        *EXTEND14_PARAMETER_NAMES,
        "RegionalProductionAdjustment",
        "ShippingFuelCost",
        "CanalToll",
    },
)
CANAL_SPLIT_PARAMETER_NAMES = frozenset(
    {
        *EXPECTED_PARAMETER_NAMES,
        "Suez Canal Cost",
        "Panama Canal Cost",
    },
)
EXPECTED_WORKBOOK_ROLES = frozenset({"demand", "supply", "trade"})
APPROVED_POWER_MIX_VECTOR_MEMBERS = (
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
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EXCEL_COLUMN_PATTERN = re.compile(r"^[A-Z]{1,3}$")

WorkbookRole = Literal["demand", "supply", "trade"]
ReferenceParser = Literal[
    "annual_deduplicated_rows",
    "annual_rows_to_months",
    "fixed_rows",
    "gdp_growth_from_levels",
    "hurricane_no_event_baseline",
    "liquefaction_production_rows",
    "annual_value_rows",
    "production_seasonality_monthly",
    "year_columns",
    "exact_rows",
    "matrix_time_columns",
    "regional_production_annual",
]
ProposalMode = Literal["auto", "conditional"]
TargetLayout = Literal["fixed_columns", "matrix_time_columns"]
TargetRowPolicy = Literal["appendable", "existing_exact"]
TargetMetadataAuthority = Literal["reference_source", "write_target"]


def _contract_error(detail: str) -> MIBaseError:
    return MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def _safe_relative_path(value: str, *, label: str) -> str:
    if not value or value != value.strip() or "\\" in value:
        raise ValueError(f"{label} must be a non-empty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise ValueError(f"{label} escapes the package resource directory: {value}")
    return path.as_posix()


def _extends_basename(value: object) -> str:
    extends = str(value)
    if PurePosixPath(extends).name != extends or not extends.endswith(".json"):
        raise ValueError("workbook contract extends must be a JSON basename")
    return extends


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WorkbookHorizon(_FrozenModel):
    start_year: int = Field(ge=2000)
    end_year: int = Field(ge=2000)

    @model_validator(mode="after")
    def validate_order(self) -> WorkbookHorizon:
        if self.start_year > self.end_year:
            raise ValueError("horizon.start_year must be less than or equal to horizon.end_year")
        return self

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(range(self.start_year, self.end_year + 1))


class WorkbookArtifact(_FrozenModel):
    filename: str
    sha256: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        normalized = _safe_relative_path(value, label="workbook filename")
        if PurePosixPath(normalized).name != normalized or not normalized.lower().endswith(".xlsm"):
            raise ValueError("workbook filename must be a basename ending in .xlsm")
        return normalized

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("workbook sha256 must contain 64 lowercase hexadecimal characters")
        return value


class ProposalPolicy(_FrozenModel):
    mode: ProposalMode
    may_abstain: bool
    evidence_required: tuple[str, ...]

    @field_validator("evidence_required")
    @classmethod
    def validate_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value) or len(value) != len(set(value)):
            raise ValueError("evidence_required must contain unique non-empty labels")
        return value


class ReferenceTransform(_FrozenModel):
    source_field: str
    operation: Literal["multiply"]
    factor: float
    provenance: str

    @model_validator(mode="after")
    def validate_transform(self) -> ReferenceTransform:
        if not self.source_field.strip() or not self.provenance.strip():
            raise ValueError("reference transform fields must be non-empty")
        if self.factor == 0:
            raise ValueError("reference transform factor must not be zero")
        return self


class AxisTransform(_FrozenModel):
    source_field: str
    operation: Literal["strip_leading_year"]
    allowed_values: tuple[str, ...]

    @model_validator(mode="after")
    def validate_transform(self) -> AxisTransform:
        if not self.source_field.strip():
            raise ValueError("axis transform source_field must be non-empty")
        if (
            not self.allowed_values
            or any(not value.strip() for value in self.allowed_values)
            or len(self.allowed_values) != len(set(self.allowed_values))
        ):
            raise ValueError("axis transform allowed_values must contain unique non-empty values")
        return self


class ReferenceAuxiliarySource(_FrozenModel):
    path: str
    sha256: str
    required_columns: tuple[str, ...]

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _safe_relative_path(value, label="reference auxiliary source")

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("reference auxiliary source sha256 must contain 64 lowercase hexadecimal characters")
        return value

    @field_validator("required_columns")
    @classmethod
    def validate_required_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not item.strip() for item in value) or len(value) != len(set(value)):
            raise ValueError("reference auxiliary source columns must be unique non-empty names")
        return value


class ReferenceSource(_FrozenModel):
    workbook_role: WorkbookRole
    sheet: str
    range: str
    parser: ReferenceParser
    header_row: int = Field(ge=1)
    data_start_row: int = Field(ge=1)
    data_end_row: int | None = Field(default=None, ge=1)
    columns: dict[str, str]
    value_start: str | None = None
    value_end: str | None = None
    year_row: int | None = Field(default=None, ge=1)
    month_row: int | None = Field(default=None, ge=1)
    period_row: int | None = Field(default=None, ge=1)
    column_headers: dict[str, str] = Field(default_factory=dict)
    required_cells: dict[str, str] = Field(default_factory=dict)
    included_rows: tuple[int, ...] = ()
    axis_transforms: dict[str, AxisTransform] = Field(default_factory=dict)
    transforms: dict[str, ReferenceTransform] = Field(default_factory=dict)
    auxiliary_sources: dict[str, ReferenceAuxiliarySource] = Field(default_factory=dict)
    key_axes: tuple[str, ...]
    metadata_axes: tuple[str, ...]
    value_field: str
    reference_unit: str
    value_semantics: str
    expected_record_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_source_shape(self) -> ReferenceSource:  # noqa: C901
        if self.data_start_row <= self.header_row:
            raise ValueError("reference data_start_row must follow header_row")
        if self.data_end_row is not None and self.data_end_row < self.data_start_row:
            raise ValueError("reference data_end_row must not precede data_start_row")
        _validate_named_axes(self.key_axes, self.metadata_axes)
        if any(_EXCEL_COLUMN_PATTERN.fullmatch(column) is None for column in self.columns.values()):
            raise ValueError("reference source columns must be Excel column labels")
        unknown_header_fields = set(self.column_headers) - set(self.columns)
        if unknown_header_fields:
            raise ValueError(f"column_headers contains unknown source fields: {sorted(unknown_header_fields)}")
        _validate_required_cells(self.required_cells)
        _validate_included_rows(
            self.included_rows,
            data_start_row=self.data_start_row,
            data_end_row=self.data_end_row,
        )
        unknown_axis_transforms = set(self.axis_transforms) - set(self.key_axes)
        if unknown_axis_transforms:
            raise ValueError(f"axis_transforms contains unknown key axes: {sorted(unknown_axis_transforms)}")
        missing_axis_transform_fields = {
            transform.source_field
            for transform in self.axis_transforms.values()
            if transform.source_field not in self.columns
        }
        if missing_axis_transform_fields:
            raise ValueError(
                f"axis_transforms contain unknown source fields: {sorted(missing_axis_transform_fields)}",
            )
        unknown_transform_fields = {
            transform.source_field
            for transform in self.transforms.values()
            if transform.source_field not in self.columns
        }
        if unknown_transform_fields:
            raise ValueError(f"transforms contain unknown source fields: {sorted(unknown_transform_fields)}")
        if any(not value.strip() for value in (self.sheet, self.range, self.value_field, self.reference_unit)):
            raise ValueError("reference source text fields must be non-empty")
        if any(not name.strip() for name in self.auxiliary_sources):
            raise ValueError("reference auxiliary source names must be non-empty")
        if self.parser == "matrix_time_columns":
            if self.value_start is None or self.value_end is None or self.year_row is None or self.month_row is None:
                raise ValueError(
                    "matrix_time_columns requires value_start, value_end, year_row, and month_row",
                )
            if (
                _EXCEL_COLUMN_PATTERN.fullmatch(self.value_start) is None
                or _EXCEL_COLUMN_PATTERN.fullmatch(self.value_end) is None
            ):
                raise ValueError("matrix_time_columns value bounds must be Excel column labels")
        return self


class WriteTarget(_FrozenModel):
    workbook_role: WorkbookRole
    sheet: str
    table: str
    layout: TargetLayout
    header_row: int = Field(ge=1)
    data_start_row: int = Field(ge=1)
    data_end_row: int | None = Field(default=None, ge=1)
    columns: dict[str, str]
    column_headers: dict[str, str] = Field(default_factory=dict)
    required_cells: dict[str, str] = Field(default_factory=dict)
    included_rows: tuple[int, ...] = ()
    axis_transforms: dict[str, AxisTransform] = Field(default_factory=dict)
    key_axes: tuple[str, ...]
    metadata_axes: tuple[str, ...]
    value_field: str
    write_unit: str
    value_semantics: str
    observed_record_count: int = Field(ge=0)
    row_policy: TargetRowPolicy = "appendable"
    metadata_authority: TargetMetadataAuthority = "reference_source"

    @model_validator(mode="after")
    def validate_target_shape(self) -> WriteTarget:
        if self.data_start_row <= self.header_row:
            raise ValueError("write target data_start_row must follow header_row")
        if self.data_end_row is not None and self.data_end_row < self.data_start_row:
            raise ValueError("write target data_end_row must not precede data_start_row")
        _validate_named_axes(self.key_axes, self.metadata_axes)
        control_fields = {"value_start", "value_end", "year_row", "month_row", "period_row"}
        if any(
            _EXCEL_COLUMN_PATTERN.fullmatch(column) is None
            for field, column in self.columns.items()
            if field not in control_fields
        ):
            raise ValueError("write target columns must be Excel column labels")
        unknown_header_fields = set(self.column_headers) - set(self.columns)
        if unknown_header_fields:
            raise ValueError(f"column_headers contains unknown target fields: {sorted(unknown_header_fields)}")
        _validate_required_cells(self.required_cells)
        _validate_included_rows(
            self.included_rows,
            data_start_row=self.data_start_row,
            data_end_row=self.data_end_row,
        )
        unknown_axis_transforms = set(self.axis_transforms) - set(self.key_axes)
        if unknown_axis_transforms:
            raise ValueError(f"axis_transforms contains unknown key axes: {sorted(unknown_axis_transforms)}")
        missing_axis_transform_fields = {
            transform.source_field
            for transform in self.axis_transforms.values()
            if transform.source_field not in self.columns
        }
        if missing_axis_transform_fields:
            raise ValueError(
                f"axis_transforms contain unknown target fields: {sorted(missing_axis_transform_fields)}",
            )
        if any(not value.strip() for value in (self.sheet, self.table, self.value_field, self.write_unit)):
            raise ValueError("write target text fields must be non-empty")
        if self.metadata_authority == "write_target" and self.row_policy != "existing_exact":
            raise ValueError("write-target metadata authority requires an existing-exact row policy")
        return self


class ParameterConstraints(_FrozenModel):
    minimum: float | None
    maximum: float | None
    atomic_group_axes: tuple[str, ...]
    vector_axis: str | None
    vector_members: tuple[str, ...]
    sum: float | None
    sum_tolerance: float | None
    require_complete_vector: bool
    direct_evidence_required: bool

    @model_validator(mode="after")
    def validate_bounds(self) -> ParameterConstraints:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("constraint minimum must not exceed maximum")
        if self.sum_tolerance is not None and self.sum_tolerance <= 0:
            raise ValueError("constraint sum_tolerance must be positive")
        if len(self.vector_members) != len(set(self.vector_members)):
            raise ValueError("constraint vector_members must not contain duplicates")
        if self.vector_axis is None and self.vector_members:
            raise ValueError("constraint vector_members require vector_axis")
        return self


class WorkbookParameterContract(_FrozenModel):
    proposal_policy: ProposalPolicy
    reference_source: ReferenceSource
    write_target: WriteTarget
    constraints: ParameterConstraints

    @model_validator(mode="after")
    def validate_parameter_shape(self) -> WorkbookParameterContract:
        if self.reference_source.key_axes != self.write_target.key_axes:
            raise ValueError("reference_source and write_target key_axes must match")
        if self.reference_source.workbook_role != self.write_target.workbook_role:
            raise ValueError("reference_source and write_target workbook_role must match")
        unknown_group_axes = set(self.constraints.atomic_group_axes) - set(self.reference_source.key_axes)
        if unknown_group_axes:
            raise ValueError(f"atomic_group_axes are not key axes: {sorted(unknown_group_axes)}")
        if (
            self.constraints.vector_axis is not None
            and self.constraints.vector_axis not in self.reference_source.key_axes
        ):
            raise ValueError("vector_axis must be one of the reference key_axes")
        return self


class ModelParameterWorkbookContract(_FrozenModel):
    schema_version: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
    release_id: Literal[
        "new-bc-v1",
        "new-bc-v2",
        "new-bc-v3",
        "new-bc-v4",
        "new-bc-v5",
        "new-bc-v6",
        "new-bc-v7",
        "new-bc-v8",
        "new-bc-v9",
    ]
    capability: Literal["read_only_proposal"]
    api_version: Literal["v4"]
    generation_strategy: Literal["multi_event_model_lever_dimensions"]
    public_api_unchanged: Literal[True]
    horizon: WorkbookHorizon
    resource_directory: str
    workbooks: dict[WorkbookRole, WorkbookArtifact]
    parameters: dict[str, WorkbookParameterContract]

    @field_validator("resource_directory")
    @classmethod
    def validate_resource_directory(cls, value: str) -> str:
        return _safe_relative_path(value, label="resource_directory")

    @model_validator(mode="after")
    def validate_release_invariants(self) -> ModelParameterWorkbookContract:  # noqa: C901
        if set(self.workbooks) != EXPECTED_WORKBOOK_ROLES:
            raise ValueError(
                "workbook roles must be exactly demand, supply, and trade",
            )
        expected_parameters = (
            V1_PARAMETER_NAMES
            if self.release_id == "new-bc-v1"
            else frozenset({*V1_PARAMETER_NAMES, "PipelineAdjustment", "SupplyDisruption"})
            if self.release_id in {"new-bc-v2", "new-bc-v3", "new-bc-v4"}
            else EXTEND10_PARAMETER_NAMES
            if self.release_id == "new-bc-v5"
            else EXTEND14_PARAMETER_NAMES
            if self.release_id == "new-bc-v6"
            else CANAL_SPLIT_PARAMETER_NAMES
            if self.release_id == "new-bc-v9"
            else EXPECTED_PARAMETER_NAMES
        )
        expected_schema_version = {
            "new-bc-v1": 1,
            "new-bc-v2": 2,
            "new-bc-v3": 3,
            "new-bc-v4": 4,
            "new-bc-v5": 5,
            "new-bc-v6": 6,
            "new-bc-v7": 7,
            "new-bc-v8": 8,
            "new-bc-v9": 9,
        }[self.release_id]
        if self.schema_version != expected_schema_version:
            raise ValueError("workbook contract schema version and release ID disagree")
        if set(self.parameters) != expected_parameters:
            raise ValueError(f"parameter names must be exactly {sorted(expected_parameters)}")
        power_mix = self.parameters["PowerMix"]
        if (
            power_mix.constraints.atomic_group_axes != ("Country", "Year")
            or power_mix.constraints.vector_axis != "Energy Source"
            or power_mix.constraints.vector_members != APPROVED_POWER_MIX_VECTOR_MEMBERS
            or power_mix.constraints.minimum != 0.0
            or power_mix.constraints.maximum != 1.0
            or power_mix.constraints.sum != 1.0
            or power_mix.constraints.sum_tolerance != 0.000001
            or not power_mix.constraints.require_complete_vector
        ):
            raise ValueError("PowerMix must declare the approved complete-vector atomic constraints")
        liq_util = self.parameters["LiqUtilAdjustment"]
        nameplate_transform = liq_util.reference_source.transforms.get("Nameplate Capacity (MTPA)")
        if (
            liq_util.proposal_policy.mode != "conditional"
            or not liq_util.proposal_policy.may_abstain
            or not liq_util.constraints.direct_evidence_required
            or liq_util.constraints.minimum != 0.0
            or liq_util.constraints.maximum is not None
        ):
            raise ValueError(
                "LiqUtilAdjustment must retain its evidence gate, zero minimum, and unbounded maximum",
            )
        if self.release_id in {
            "new-bc-v4",
            "new-bc-v5",
            "new-bc-v6",
            "new-bc-v7",
            "new-bc-v8",
            "new-bc-v9",
        }:
            if (
                nameplate_transform is not None
                or liq_util.write_target.row_policy != "existing_exact"
                or liq_util.write_target.metadata_authority != "write_target"
            ):
                raise ValueError(
                    "new-bc-v4 LiqUtilAdjustment must use exact existing target rows and target-owned metadata",
                )
        elif (
            nameplate_transform is None
            or nameplate_transform.source_field != "Monthly Capacity (MTPM)"
            or nameplate_transform.operation != "multiply"
            or nameplate_transform.factor != 12.0
        ):
            raise ValueError("legacy workbook contracts must retain the MTPM-to-MTPA transform")
        if self.release_id in {
            "new-bc-v2",
            "new-bc-v3",
            "new-bc-v4",
            "new-bc-v5",
            "new-bc-v6",
            "new-bc-v7",
            "new-bc-v8",
            "new-bc-v9",
        }:
            pipeline = self.parameters["PipelineAdjustment"]
            supply = self.parameters["SupplyDisruption"]
            if (
                pipeline.reference_source.parser != "annual_rows_to_months"
                or pipeline.reference_source.key_axes
                != ("Pipeline Name", "From Country", "To Country", "Year", "Month")
                or pipeline.constraints.minimum != 0.0
            ):
                raise ValueError("PipelineAdjustment must retain the approved monthly exact-slot workbook contract")
            if (
                supply.reference_source.parser != "production_seasonality_monthly"
                or supply.reference_source.key_axes != ("Country", "Year", "Month")
                or set(supply.reference_source.auxiliary_sources) != {"seasonality"}
                or supply.constraints.minimum != 0.0
            ):
                raise ValueError("SupplyDisruption must retain the approved production-seasonality workbook contract")
            if self.release_id in {
                "new-bc-v3",
                "new-bc-v4",
                "new-bc-v5",
                "new-bc-v6",
                "new-bc-v7",
                "new-bc-v8",
            } and (
                pipeline.reference_source.reference_unit != pipeline.write_target.write_unit
                or supply.reference_source.reference_unit != supply.write_target.write_unit
                or pipeline.write_target.value_field != "User adjusted capacity (Mt/y)"
                or supply.write_target.sheet != "ProductionAdjustment"
                or supply.write_target.value_field != "Volumes (Mt)"
            ):
                raise ValueError("new-bc-v3+ must use the final workbook target sheets and Mt units")
        if self.release_id in {"new-bc-v5", "new-bc-v6", "new-bc-v7", "new-bc-v8", "new-bc-v9"}:
            population = self.parameters["Population"]
            hurricane = self.parameters["HurricaneIntensity"]
            liq_prod = self.parameters["LiqProdAdjustment"]
            if (
                population.reference_source.parser != "annual_value_rows"
                or population.reference_source.key_axes != ("Country", "Year")
                or population.constraints.minimum != 0.0
            ):
                raise ValueError("Population must use the approved non-negative annual workbook contract")
            if (
                hurricane.reference_source.parser != "hurricane_no_event_baseline"
                or hurricane.reference_source.key_axes != ("Year", "Month")
                or hurricane.constraints.minimum != 0.0
                or hurricane.constraints.maximum != 4.0
                or not hurricane.constraints.direct_evidence_required
            ):
                raise ValueError("HurricaneIntensity must retain its GoM evidence gate and integer 0..4 range")
            if (
                liq_prod.reference_source.parser != "liquefaction_production_rows"
                or liq_prod.reference_source.key_axes != ("Country", "LNG Plant", "LNG Plant Train", "Year", "Month")
                or liq_prod.constraints.minimum != 0.0
                or not liq_prod.constraints.direct_evidence_required
                or liq_prod.write_target.row_policy != "existing_exact"
                or liq_prod.write_target.metadata_authority != "write_target"
            ):
                raise ValueError("LiqProdAdjustment must retain its exact-slot production override contract")
        if self.release_id in {"new-bc-v6", "new-bc-v7", "new-bc-v8", "new-bc-v9"}:
            basecase_only = {
                "User-Adjusted Gas Demand": ("exact_rows", ("Country", "Year", "Month", "Demand Sub-Sector")),
                "RegasAdjustment": (
                    "matrix_time_columns",
                    (
                        "Continent",
                        "Region",
                        "Country",
                        "Regasification plant",
                        "Life Cycle Category",
                        "Nameplate capacity (MTPA)",
                        "Year",
                        "Month",
                    ),
                ),
                "PNG Contract Volume": ("exact_rows", ("Year", "From Country", "To Country")),
                "ShippingCost": ("exact_rows", ("Year",)),
            }
            for parameter_name, (parser, exact_axes) in basecase_only.items():
                parameter = self.parameters[parameter_name]
                if (
                    parameter.reference_source.parser != parser
                    or parameter.reference_source.key_axes != exact_axes
                    or parameter.reference_source.data_end_row is None
                    or parameter.write_target.key_axes != exact_axes
                    or parameter.write_target.data_end_row is None
                    or parameter.write_target.row_policy != "existing_exact"
                    or parameter.reference_source.reference_unit != parameter.write_target.write_unit
                    or parameter.constraints.minimum != 0.0
                    or parameter.constraints.maximum is not None
                    or not parameter.constraints.direct_evidence_required
                ):
                    raise ValueError(
                        f"{parameter_name} must retain its non-negative existing-exact Basecase-only contract",
                    )
        if self.release_id in {"new-bc-v7", "new-bc-v8", "new-bc-v9"}:
            new_parameters = {
                "RegionalProductionAdjustment": (
                    "regional_production_annual",
                    ("Year", "Province/Country"),
                    "Bcm",
                ),
                "ShippingFuelCost": ("exact_rows", ("Year",), "$/tonne"),
                "CanalToll": ("exact_rows", ("Canal", "Year"), "$/crossing"),
            }
            for parameter_name, (parser, exact_axes, unit) in new_parameters.items():
                parameter = self.parameters[parameter_name]
                if (
                    parameter.reference_source.parser != parser
                    or parameter.reference_source.key_axes != exact_axes
                    or parameter.write_target.key_axes != exact_axes
                    or parameter.reference_source.reference_unit != unit
                    or parameter.write_target.write_unit != unit
                    or parameter.constraints.minimum != 0.0
                    or parameter.constraints.maximum is not None
                    or not parameter.constraints.direct_evidence_required
                ):
                    raise ValueError(
                        f"{parameter_name} must retain its non-negative direct-evidence v7+ contract",
                    )
        if self.release_id in {"new-bc-v8", "new-bc-v9"}:
            for parameter_name in ("LiqProdAdjustment", "LiqUtilAdjustment"):
                columns = self.parameters[parameter_name].write_target.columns
                if (
                    columns.get("value_start") != "G"
                    or columns.get("value_end") != "CL"
                    or columns.get("year_row") != "7"
                    or columns.get("month_row") != "8"
                    or columns.get("period_row") != "9"
                ):
                    raise ValueError(
                        f"{parameter_name} must retain the reviewed G:CL 84-month write-target boundary",
                    )
        if self.release_id == "new-bc-v9":
            split_canal_targets = {
                "Suez Canal Cost": ("table4", ("Suez",), 5),
                "Panama Canal Cost": ("table5", ("Panama",), 5),
            }
            for parameter_name, (model_table, allowed_canals, record_count) in split_canal_targets.items():
                parameter = self.parameters[parameter_name]
                reference = parameter.reference_source
                target = parameter.write_target
                if (
                    reference.parser != "exact_rows"
                    or reference.key_axes != ("Canal", "Year")
                    or target.key_axes != ("Canal", "Year")
                    or reference.axis_transforms.get("Canal") is None
                    or reference.axis_transforms["Canal"].allowed_values != allowed_canals
                    or target.axis_transforms.get("Canal") is None
                    or target.axis_transforms["Canal"].allowed_values != allowed_canals
                    or reference.reference_unit != "$/crossing"
                    or target.write_unit != "$/crossing"
                    or target.table != model_table
                    or reference.expected_record_count != record_count
                    or target.observed_record_count != record_count
                    or target.row_policy != "existing_exact"
                    or parameter.constraints.minimum != 0.0
                    or parameter.constraints.maximum is not None
                    or not parameter.constraints.direct_evidence_required
                ):
                    raise ValueError(
                        f"{parameter_name} must retain its dedicated canal/table v9 contract",
                    )
        return self


def _validate_named_axes(key_axes: tuple[str, ...], metadata_axes: tuple[str, ...]) -> None:
    if not key_axes or any(not axis.strip() for axis in (*key_axes, *metadata_axes)):
        raise ValueError("axes must contain non-empty names and key_axes must not be empty")
    if len(key_axes) != len(set(key_axes)) or len(metadata_axes) != len(set(metadata_axes)):
        raise ValueError("axes must not contain duplicates")
    overlap = sorted(set(key_axes) & set(metadata_axes))
    if overlap:
        raise ValueError(f"key_axes and metadata_axes overlap: {overlap}")


def _validate_required_cells(required_cells: Mapping[str, str]) -> None:
    if any(re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", cell) is None for cell in required_cells):
        raise ValueError("required_cells keys must be absolute A1-style cell references")
    if any(not value.strip() for value in required_cells.values()):
        raise ValueError("required_cells values must be non-empty")


def _validate_included_rows(
    included_rows: tuple[int, ...],
    *,
    data_start_row: int,
    data_end_row: int | None,
) -> None:
    if not included_rows:
        return
    if len(included_rows) != len(set(included_rows)) or tuple(sorted(included_rows)) != included_rows:
        raise ValueError("included_rows must contain unique rows in ascending order")
    if any(row < data_start_row or (data_end_row is not None and row > data_end_row) for row in included_rows):
        raise ValueError("included_rows must stay inside the declared data row bounds")


def load_workbook_contract(
    path: Path = DEFAULT_WORKBOOK_CONTRACT_PATH,
) -> ModelParameterWorkbookContract:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("schema_version") in {2, 3, 4, 5, 6, 7, 8, 9} and "extends" in document:
            extends = _extends_basename(document.pop("extends"))
            base_path = path.parent / extends
            base_document = load_workbook_contract(base_path).model_dump(mode="json")
            base_document.update({key: value for key, value in document.items() if key != "parameters"})
            base_document["parameters"] = {
                **base_document.get("parameters", {}),
                **document.get("parameters", {}),
            }
            document = base_document
        return ModelParameterWorkbookContract.model_validate(document)
    except OSError as exc:
        raise _contract_error(f"Unable to read workbook contract: {path}") from exc
    except ValueError as exc:
        raise _contract_error(f"Invalid workbook contract {path}: {exc}") from exc


def workbook_contract_canonical_bytes(contract: ModelParameterWorkbookContract) -> bytes:
    return json.dumps(
        contract.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def workbook_contract_schema_hash(contract: ModelParameterWorkbookContract) -> str:
    return hashlib.sha256(workbook_contract_canonical_bytes(contract)).hexdigest()


def workbook_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise _contract_error(f"Unable to read workbook resource: {path}") from exc
    return digest.hexdigest()


def resolve_workbook_paths(
    contract: ModelParameterWorkbookContract,
    *,
    resource_root: Path = PACKAGE_RESOURCE_DIR,
) -> Mapping[WorkbookRole, Path]:
    resolved_root = resource_root.resolve()
    release_root = (resolved_root / contract.resource_directory).resolve()
    if not release_root.is_relative_to(resolved_root):
        raise _contract_error(f"Workbook release path escapes package resources: {contract.resource_directory}")
    paths: dict[WorkbookRole, Path] = {}
    for role, artifact in contract.workbooks.items():
        workbook_path = (release_root / artifact.filename).resolve()
        if not workbook_path.is_relative_to(release_root):
            raise _contract_error(f"Workbook path escapes release directory: {artifact.filename}")
        if not workbook_path.is_file():
            raise _contract_error(f"Workbook resource is missing: {workbook_path}")
        paths[role] = workbook_path
    return MappingProxyType(paths)


def validate_workbook_hashes(
    contract: ModelParameterWorkbookContract,
    *,
    resource_root: Path = PACKAGE_RESOURCE_DIR,
) -> Mapping[WorkbookRole, Path]:
    paths = resolve_workbook_paths(contract, resource_root=resource_root)
    for role, path in paths.items():
        actual_sha256 = workbook_sha256(path)
        expected_sha256 = contract.workbooks[role].sha256
        if actual_sha256 != expected_sha256:
            raise _contract_error(
                f"Workbook sha256 mismatch for {role}: expected={expected_sha256}, actual={actual_sha256}",
            )
    resolved_root = resource_root.resolve()
    for parameter_name, parameter in contract.parameters.items():
        for source_name, source in parameter.reference_source.auxiliary_sources.items():
            path = (resolved_root / source.path).resolve()
            if not path.is_relative_to(resolved_root) or not path.is_file():
                raise _contract_error(
                    f"Workbook auxiliary source is missing: parameter={parameter_name}, source={source_name}",
                )
            actual_sha256 = workbook_sha256(path)
            if actual_sha256 != source.sha256:
                raise _contract_error(
                    "Workbook auxiliary source sha256 mismatch: "
                    f"parameter={parameter_name}, source={source_name}, "
                    f"expected={source.sha256}, actual={actual_sha256}",
                )
    return paths


def validate_candidate_write_target(
    contract: ModelParameterWorkbookContract,
    candidate: Mapping[str, object],
) -> WorkbookParameterContract:
    canonical_name = candidate.get("canonical_parameter_name") or candidate.get("parameter_name")
    if not isinstance(canonical_name, str) or canonical_name not in contract.parameters:
        raise _contract_error(f"Candidate is not covered by the workbook contract: {canonical_name!r}")
    alternate_name = candidate.get("parameter_name")
    if isinstance(alternate_name, str) and "canonical_parameter_name" in candidate and alternate_name != canonical_name:
        raise _contract_error(
            f"Candidate parameter names disagree: canonical={canonical_name!r}, parameter_name={alternate_name!r}",
        )
    parameter = contract.parameters[canonical_name]
    target = parameter.write_target
    expected_model_file = target.workbook_role.title()
    actual_model_file = candidate.get("model_file")
    actual_sheet = candidate.get("model_sheet")
    actual_table = candidate.get("model_table") or candidate.get("table_name")
    mismatches: list[str] = []
    if actual_model_file != expected_model_file:
        mismatches.append(f"model_file expected={expected_model_file!r} actual={actual_model_file!r}")
    if actual_sheet != target.sheet:
        mismatches.append(f"model_sheet expected={target.sheet!r} actual={actual_sheet!r}")
    if actual_table != target.table:
        mismatches.append(f"model_table expected={target.table!r} actual={actual_table!r}")
    if mismatches:
        raise _contract_error(f"Candidate write target mismatch for {canonical_name}: {'; '.join(mismatches)}")
    return parameter


__all__ = [
    "APPROVED_POWER_MIX_VECTOR_MEMBERS",
    "DEFAULT_WORKBOOK_CONTRACT_PATH",
    "EXPECTED_PARAMETER_NAMES",
    "AxisTransform",
    "ModelParameterWorkbookContract",
    "ParameterConstraints",
    "ProposalPolicy",
    "ReferenceAuxiliarySource",
    "ReferenceSource",
    "ReferenceTransform",
    "WorkbookArtifact",
    "WorkbookHorizon",
    "WorkbookParameterContract",
    "WriteTarget",
    "load_workbook_contract",
    "resolve_workbook_paths",
    "validate_candidate_write_target",
    "validate_workbook_hashes",
    "workbook_contract_canonical_bytes",
    "workbook_contract_schema_hash",
    "workbook_sha256",
]
