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

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


PACKAGE_DIR = Path(__file__).resolve().parents[1]
PACKAGE_RESOURCE_DIR = PACKAGE_DIR / "resources"
DEFAULT_WORKBOOK_CONTRACT_PATH = PACKAGE_RESOURCE_DIR / "contracts" / "model-parameter-workbook-contract-v1.json"
EXPECTED_PARAMETER_NAMES = frozenset({"GDP", "PMI", "PowerMix", "Temperature", "LiqUtilAdjustment"})
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
    "fixed_rows",
    "gdp_growth_from_levels",
    "year_columns",
]
ProposalMode = Literal["auto", "conditional"]
TargetLayout = Literal["fixed_columns", "matrix_time_columns"]


def _contract_error(detail: str) -> MIBaseError:
    return MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def _safe_relative_path(value: str, *, label: str) -> str:
    if not value or value != value.strip() or "\\" in value:
        raise ValueError(f"{label} must be a non-empty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise ValueError(f"{label} escapes the package resource directory: {value}")
    return path.as_posix()


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


class ReferenceSource(_FrozenModel):
    workbook_role: WorkbookRole
    sheet: str
    range: str
    parser: ReferenceParser
    header_row: int = Field(ge=1)
    data_start_row: int = Field(ge=1)
    columns: dict[str, str]
    column_headers: dict[str, str] = Field(default_factory=dict)
    transforms: dict[str, ReferenceTransform] = Field(default_factory=dict)
    key_axes: tuple[str, ...]
    metadata_axes: tuple[str, ...]
    value_field: str
    reference_unit: str
    value_semantics: str
    expected_record_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_source_shape(self) -> ReferenceSource:
        if self.data_start_row <= self.header_row:
            raise ValueError("reference data_start_row must follow header_row")
        _validate_named_axes(self.key_axes, self.metadata_axes)
        if any(_EXCEL_COLUMN_PATTERN.fullmatch(column) is None for column in self.columns.values()):
            raise ValueError("reference source columns must be Excel column labels")
        unknown_header_fields = set(self.column_headers) - set(self.columns)
        if unknown_header_fields:
            raise ValueError(f"column_headers contains unknown source fields: {sorted(unknown_header_fields)}")
        unknown_transform_fields = {
            transform.source_field
            for transform in self.transforms.values()
            if transform.source_field not in self.columns
        }
        if unknown_transform_fields:
            raise ValueError(f"transforms contain unknown source fields: {sorted(unknown_transform_fields)}")
        if any(not value.strip() for value in (self.sheet, self.range, self.value_field, self.reference_unit)):
            raise ValueError("reference source text fields must be non-empty")
        return self


class WriteTarget(_FrozenModel):
    workbook_role: WorkbookRole
    sheet: str
    table: str
    layout: TargetLayout
    header_row: int = Field(ge=1)
    data_start_row: int = Field(ge=1)
    columns: dict[str, str]
    key_axes: tuple[str, ...]
    metadata_axes: tuple[str, ...]
    value_field: str
    write_unit: str
    value_semantics: str
    observed_record_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_target_shape(self) -> WriteTarget:
        if self.data_start_row <= self.header_row:
            raise ValueError("write target data_start_row must follow header_row")
        _validate_named_axes(self.key_axes, self.metadata_axes)
        if any(not value.strip() for value in (self.sheet, self.table, self.value_field, self.write_unit)):
            raise ValueError("write target text fields must be non-empty")
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
    schema_version: Literal[1]
    release_id: Literal["new-bc-v1"]
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
    def validate_release_invariants(self) -> ModelParameterWorkbookContract:
        if set(self.workbooks) != EXPECTED_WORKBOOK_ROLES:
            raise ValueError(
                "workbook roles must be exactly demand, supply, and trade",
            )
        if set(self.parameters) != EXPECTED_PARAMETER_NAMES:
            raise ValueError(f"parameter names must be exactly {sorted(EXPECTED_PARAMETER_NAMES)}")
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
            or nameplate_transform is None
            or nameplate_transform.source_field != "Monthly Capacity (MTPM)"
            or nameplate_transform.operation != "multiply"
            or nameplate_transform.factor != 12.0
        ):
            raise ValueError(
                "LiqUtilAdjustment must retain its evidence gate, zero minimum, unbounded maximum, "
                "and MTPM-to-MTPA transform",
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


def load_workbook_contract(
    path: Path = DEFAULT_WORKBOOK_CONTRACT_PATH,
) -> ModelParameterWorkbookContract:
    try:
        raw = path.read_text(encoding="utf-8")
        return ModelParameterWorkbookContract.model_validate_json(raw)
    except OSError as exc:
        raise _contract_error(f"Unable to read workbook contract: {path}") from exc
    except ValidationError as exc:
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
    "ModelParameterWorkbookContract",
    "ParameterConstraints",
    "ProposalPolicy",
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
